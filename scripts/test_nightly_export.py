"""Pruebas del script nocturno de telemetría (scripts/nightly_export.py, ticket #DEV-53).

No tocan Supabase ni lanzan el pipeline real: la base es un SQLite temporal (con `telemetry_events` y
`ops.job_runs` como en las migraciones 002 y 006), el subproceso del pipeline se simula y el CSV se
escribe en una carpeta temporal. Se ejecutan con el entorno del script, desde la raíz del repositorio:
    uv run --project services/jobs python -m unittest scripts/test_nightly_export.py
"""

import csv
import logging
import signal
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nightly_export as nightly  # noqa: E402
from brasaland_jobs import job_runner  # noqa: E402
from brasaland_jobs.logs import LOGGER_NAME  # noqa: E402
from sqlalchemy import JSON, Column, DateTime, MetaData, Numeric, Table, Text, create_engine, event, insert  # noqa: E402

TODAY = date(2026, 11, 25)
DAY = date(2026, 11, 24)

source = MetaData()
telemetry_events = Table(
    "telemetry_events",
    source,
    Column("id", Text, primary_key=True),
    Column("timestamp", DateTime(timezone=True), nullable=False),
    Column("service", Text, nullable=False),
    Column("event_type", Text, nullable=False),
    Column("level", Text),
    Column("value", Numeric),
    Column("message", Text),
    Column("tags", JSON),
)


class Database:
    """SQLite temporal con `telemetry_events` y el esquema `ops` adjuntado."""

    def __init__(self, folder: Path) -> None:
        ops_db = folder / "ops.db"
        self.engine = create_engine(f"sqlite:///{(folder / 'main.db').as_posix()}")

        @event.listens_for(self.engine, "connect")
        def attach_ops(dbapi_connection, _record):
            dbapi_connection.execute(f"ATTACH DATABASE '{ops_db.as_posix()}' AS ops")

        source.create_all(self.engine)
        job_runner.metadata.create_all(self.engine)

    def add_event(self, event_id: str, timestamp: datetime, event_type: str = "page_viewed", **tags) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                insert(telemetry_events).values(
                    id=event_id,
                    timestamp=timestamp,
                    service="backoffice",
                    event_type=event_type,
                    level="info",
                    value=None,
                    message=None,
                    tags={"environment": "development", **tags},
                )
            )

    def runs(self):
        with self.engine.connect() as conn:
            return job_runner.list_runs(conn, nightly.JOB_NAME)


# --- Configuración ----------------------------------------------------------------------------------


class ConfigTests(unittest.TestCase):
    def test_target_date_por_defecto_es_ayer_en_utc(self):
        self.assertEqual(nightly.resolve_target_date({}, TODAY), DAY)
        self.assertEqual(nightly.resolve_target_date({"TARGET_DATE": "  "}, TODAY), DAY)

    def test_target_date_desde_el_entorno(self):
        self.assertEqual(nightly.resolve_target_date({"TARGET_DATE": "2026-01-15"}, TODAY), date(2026, 1, 15))

    def test_target_date_con_formato_invalido(self):
        for raw in ("2026/11/24", "20261124", "24-11-2026", "2026-11-31", "ayer"):
            with self.subTest(raw=raw), self.assertRaises(nightly.ConfigError):
                nightly.resolve_target_date({"TARGET_DATE": raw}, TODAY)

    def test_target_date_debe_ser_un_dia_terminado(self):
        for raw in ("2026-11-25", "2026-12-01"):
            with self.subTest(raw=raw), self.assertRaisesRegex(nightly.ConfigError, "ya terminado"):
                nightly.resolve_target_date({"TARGET_DATE": raw}, TODAY)

    def test_load_config_exige_la_conexion(self):
        with self.assertRaisesRegex(nightly.ConfigError, "JOBS_DATABASE_URL"):
            nightly.load_config({}, TODAY)

    def test_load_config_valores_por_defecto(self):
        config = nightly.load_config({"JOBS_DATABASE_URL": "sqlite://"}, TODAY)
        self.assertEqual(config["target_date"], DAY)
        self.assertEqual((config["stale_minutes"], config["timeout_minutes"]), (120, 90))
        self.assertIsNone(config["pipeline_environment"])

    def test_el_timeout_del_pipeline_debe_ser_menor_que_el_umbral_de_abandono(self):
        env = {"JOBS_DATABASE_URL": "sqlite://", "NIGHTLY_PIPELINE_TIMEOUT_MINUTES": "120"}
        with self.assertRaisesRegex(nightly.ConfigError, "menor que"):
            nightly.load_config(env, TODAY)

    def test_minutos_invalidos(self):
        for raw in ("0", "-5", "diez", "1.5"):
            with self.subTest(raw=raw), self.assertRaises(nightly.ConfigError):
                nightly.load_config({"JOBS_DATABASE_URL": "sqlite://", "NIGHTLY_STALE_MINUTES": raw}, TODAY)


class PipelineWeeksTests(unittest.TestCase):
    def test_cuatro_semanas_cerradas_a_fecha_del_dia_siguiente(self):
        # Martes 24-nov → mañana es miércoles de la semana del 23-nov, en curso: las 4 anteriores.
        self.assertEqual(nightly.pipeline_weeks(DAY), (date(2026, 10, 26), date(2026, 11, 16)))

    def test_el_domingo_cierra_su_semana(self):
        # Domingo 22-nov → mañana es lunes 23: la semana del 16-nov ya está cerrada y entra.
        self.assertEqual(nightly.pipeline_weeks(date(2026, 11, 22)), (date(2026, 10, 26), date(2026, 11, 16)))
        # Sábado 21-nov → mañana es domingo 22, aún en la semana del 16: queda fuera.
        self.assertEqual(nightly.pipeline_weeks(date(2026, 11, 21)), (date(2026, 10, 19), date(2026, 11, 9)))

    def test_misma_fecha_misma_ventana(self):
        self.assertEqual(nightly.pipeline_weeks(date(2026, 1, 15)), nightly.pipeline_weeks(date(2026, 1, 15)))

    def test_comando_del_pipeline(self):
        command = nightly.pipeline_command(date(2026, 10, 26), date(2026, 11, 16), None)
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(Path(command[1]), nightly.REPO_ROOT / "data" / "pipelines" / "pipeline.py")
        self.assertEqual(command[2:], ["--week-from", "2026-10-26", "--week-to", "2026-11-16"])
        self.assertEqual(nightly.pipeline_command(DAY, DAY, "development")[-2:], ["--environment", "development"])


# --- Export del CSV -----------------------------------------------------------------------------------


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="nightly-export-"))
        self.db = Database(self.folder)
        self.path = nightly.export_path(DAY, self.folder / "exports")

    def tearDown(self):
        self.db.engine.dispose()

    def read(self):
        with self.path.open(encoding="utf-8", newline="") as file:
            return list(csv.reader(file))

    def test_nombre_del_archivo(self):
        self.assertEqual(nightly.export_path(DAY).name, "telemetry_2026-11-24.csv")
        self.assertEqual(nightly.export_path(DAY).parent, nightly.REPO_ROOT / "data" / "raw" / "telemetry_exports")

    def test_exporta_solo_el_dia_en_utc_en_orden(self):
        self.db.add_event("e3", datetime(2026, 11, 24, 23, 59, 59, tzinfo=UTC))
        self.db.add_event("e1", datetime(2026, 11, 24, 0, 0, tzinfo=UTC), "login_succeeded", user_id="u-1")
        self.db.add_event("antes", datetime(2026, 11, 23, 23, 59, 59, tzinfo=UTC))
        self.db.add_event("despues", datetime(2026, 11, 25, 0, 0, tzinfo=UTC))
        self.db.add_event("e2", datetime(2026, 11, 24, 12, 30, tzinfo=UTC), "stock_waste_registered", total_cost=12.5)

        self.assertEqual(nightly.export_csv(self.db.engine, DAY, self.path), 3)
        rows = self.read()
        self.assertEqual(rows[0], nightly.CSV_COLUMNS)
        self.assertEqual([row[0] for row in rows[1:]], ["e1", "e2", "e3"])
        self.assertEqual(rows[1][1], "2026-11-24T00:00:00+00:00")
        self.assertEqual(rows[1][2:4], ["backoffice", "login_succeeded"])
        self.assertEqual(rows[1][7], '{"environment":"development","user_id":"u-1"}')
        self.assertEqual(rows[2][7], '{"environment":"development","total_cost":12.5}')

    def test_un_dia_sin_eventos_deja_solo_el_encabezado(self):
        self.assertEqual(nightly.export_csv(self.db.engine, DAY, self.path), 0)
        self.assertEqual(self.read(), [nightly.CSV_COLUMNS])

    def test_no_sobrescribe_un_csv_existente(self):
        self.db.add_event("e1", datetime(2026, 11, 24, 8, tzinfo=UTC))
        nightly.export_csv(self.db.engine, DAY, self.path)
        before = self.path.read_bytes()
        self.db.add_event("e2", datetime(2026, 11, 24, 9, tzinfo=UTC))
        self.assertIsNone(nightly.export_csv(self.db.engine, DAY, self.path))
        self.assertEqual(self.path.read_bytes(), before)

    def test_un_fallo_a_mitad_no_deja_archivo(self):
        self.db.add_event("e1", datetime(2026, 11, 24, 8, tzinfo=UTC))
        self.db.add_event("e2", datetime(2026, 11, 24, 9, tzinfo=UTC))
        original = nightly.format_row
        calls = []

        def broken(row):
            calls.append(row)
            if len(calls) == 2:
                raise OSError("disco lleno")
            return original(row)

        with mock.patch.object(nightly, "format_row", side_effect=broken), self.assertRaises(OSError):
            nightly.export_csv(self.db.engine, DAY, self.path)
        self.assertEqual(list(self.path.parent.iterdir()), [])  # ni el CSV ni el temporal


# --- Pipeline -----------------------------------------------------------------------------------------


class RunPipelineTests(unittest.TestCase):
    def test_codigo_distinto_de_cero_es_un_fallo(self):
        with mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 3)) as run:
            with self.assertRaisesRegex(nightly.PipelineFailed, "código 3"):
                nightly.run_pipeline(["python", "pipeline.py"], 90)
        self.assertEqual(run.call_args.kwargs["timeout"], 90 * 60)
        self.assertEqual(run.call_args.kwargs["cwd"], nightly.REPO_ROOT)

    def test_codigo_cero_termina_bien(self):
        with mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
            nightly.run_pipeline(["python", "pipeline.py"], 90)

    def test_un_timeout_se_propaga(self):
        expired = subprocess.TimeoutExpired(["python"], 60)
        with mock.patch.object(subprocess, "run", side_effect=expired), self.assertRaises(subprocess.TimeoutExpired):
            nightly.run_pipeline(["python", "pipeline.py"], 1)

    def test_sigterm_se_convierte_en_salida_143(self):
        with self.assertRaises(SystemExit) as raised:
            nightly._raise_on_sigterm(signal.SIGTERM, None)
        self.assertEqual(raised.exception.code, 143)


# --- Ejecución completa (main) ------------------------------------------------------------------------


class MainTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp(prefix="nightly-main-"))
        self.db = Database(self.folder)
        self.exports = self.folder / "exports"
        self.db.add_event("e1", datetime(2026, 11, 24, 10, tzinfo=UTC))
        self.pipeline_calls = []
        self.pipeline_code = 0
        patches = [
            mock.patch.object(nightly, "create_jobs_engine", return_value=self.db.engine),
            mock.patch.object(subprocess, "run", side_effect=self.fake_pipeline),
            mock.patch.object(signal, "signal"),  # no cambiar los manejadores del proceso de pruebas
            # El logger sin el handler de stderr: assertLogs captura las líneas sin imprimirlas.
            mock.patch.object(nightly, "configure_logging", side_effect=lambda: logging.getLogger(LOGGER_NAME)),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def tearDown(self):
        self.db.engine.dispose()

    def fake_pipeline(self, command, **kwargs):
        self.pipeline_calls.append(command)
        return subprocess.CompletedProcess(command, self.pipeline_code)

    def run_main(self, **env):
        with self.assertLogs(LOGGER_NAME, level="INFO") as logs:
            code = nightly.main({"JOBS_DATABASE_URL": "sqlite://", **env}, today=TODAY, export_dir=self.exports)
        return code, logs.records

    def test_ejecucion_correcta(self):
        code, records = self.run_main()
        self.assertEqual(code, 0)
        [run] = self.db.runs()
        self.assertEqual((run["status"], run["target_date"]), ("completed", DAY))
        self.assertTrue((self.exports / "telemetry_2026-11-24.csv").exists())
        self.assertEqual(len(self.pipeline_calls), 1)
        self.assertEqual(self.pipeline_calls[0][2:], ["--week-from", "2026-10-26", "--week-to", "2026-11-16"])
        statuses = [record.status for record in records]
        self.assertEqual(statuses[0], "pending")
        self.assertEqual(statuses[-1], "completed")
        self.assertTrue(all(record.job == "nightly_export" for record in records))

    def test_dos_ejecuciones_el_mismo_dia_equivalen_a_una(self):
        self.run_main()
        csv_before = (self.exports / "telemetry_2026-11-24.csv").read_bytes()
        runs_before = self.db.runs()
        self.db.add_event("e2", datetime(2026, 11, 24, 11, tzinfo=UTC))
        code, records = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.pipeline_calls), 1)  # el pipeline no se relanza
        self.assertEqual((self.exports / "telemetry_2026-11-24.csv").read_bytes(), csv_before)
        self.assertEqual(self.db.runs(), runs_before)  # ninguna fila nueva
        [record] = records
        self.assertEqual((record.status, record.levelno), ("skipped", logging.INFO))

    def test_target_date_desde_el_entorno(self):
        code, _ = self.run_main(TARGET_DATE="2026-11-22", NIGHTLY_PIPELINE_ENVIRONMENT="development")
        self.assertEqual(code, 0)
        self.assertEqual(self.db.runs()[0]["target_date"], date(2026, 11, 22))
        self.assertTrue((self.exports / "telemetry_2026-11-22.csv").exists())
        self.assertEqual(
            self.pipeline_calls[0][2:],
            ["--week-from", "2026-10-26", "--week-to", "2026-11-16", "--environment", "development"],
        )

    def test_fallo_del_pipeline_deja_failed_y_codigo_1(self):
        self.pipeline_code = 1
        code, records = self.run_main()
        self.assertEqual(code, 1)
        [run] = self.db.runs()
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["error_message"], "PipelineFailed: El pipeline terminó con código 1.")
        errors = [record for record in records if record.levelno == logging.ERROR]
        self.assertTrue(errors and all(record.status == "failed" for record in errors))
        self.assertIsNotNone(errors[0].exc_info)  # la traza va al log

    def test_reintento_tras_un_fallo_no_reexporta_pero_relanza_el_pipeline(self):
        self.pipeline_code = 1
        self.run_main()
        csv_before = (self.exports / "telemetry_2026-11-24.csv").read_bytes()
        self.pipeline_code = 0
        code, records = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual([run["status"] for run in self.db.runs()], ["failed", "completed"])
        self.assertEqual(len(self.pipeline_calls), 2)
        self.assertEqual((self.exports / "telemetry_2026-11-24.csv").read_bytes(), csv_before)
        self.assertTrue(any("ya existía" in record.getMessage() for record in records))

    def test_cancelada_si_otra_instancia_tiene_el_lock(self):
        with self.db.engine.begin() as conn:
            other = job_runner.create_run(conn, nightly.JOB_NAME, date(2026, 11, 23), now=datetime.now(UTC))
            job_runner.start_run(conn, other, now=datetime.now(UTC))
        code, records = self.run_main()
        self.assertEqual(code, 0)  # aborta en silencio
        self.assertEqual(self.pipeline_calls, [])
        self.assertFalse(self.exports.exists())
        self.assertEqual(len(self.db.runs()), 1)
        self.assertEqual([record.status for record in records], ["cancelled"])

    def test_interrupcion_por_sigterm_deja_failed(self):
        def killed(command, **kwargs):
            raise SystemExit(143)

        with mock.patch.object(subprocess, "run", side_effect=killed):
            code, _ = self.run_main()
        self.assertEqual(code, 143)
        [run] = self.db.runs()
        self.assertEqual((run["status"], run["error_message"]), ("failed", "SystemExit: 143"))

    def test_configuracion_invalida_no_crea_filas(self):
        with self.assertLogs(LOGGER_NAME, level="ERROR") as logs:
            code = nightly.main({"JOBS_DATABASE_URL": "sqlite://", "TARGET_DATE": "2026-13-01"}, today=TODAY)
        self.assertEqual(code, 2)
        self.assertEqual(self.db.runs(), [])
        self.assertEqual(self.pipeline_calls, [])
        self.assertIn("TARGET_DATE", logs.records[0].getMessage())

    def test_base_no_disponible_codigo_1_y_log(self):
        broken = create_engine("sqlite:////ruta/que/no/existe/x.db")
        with mock.patch.object(nightly, "create_jobs_engine", return_value=broken):
            code, records = self.run_main()
        self.assertEqual(code, 1)
        self.assertEqual(records[-1].status, "failed")
        self.assertIn("OperationalError", records[-1].getMessage())


# --- Independencia de la API (criterio 1) ---------------------------------------------------------


class IndependenceTests(unittest.TestCase):
    def test_no_importa_fastapi_ni_prefect_ni_la_api(self):
        code = (
            "import sys; sys.path.insert(0, 'scripts'); import nightly_export; "
            "print(sorted(m for m in ('fastapi', 'prefect', 'app', 'starlette') if m in sys.modules))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=nightly.REPO_ROOT, capture_output=True, text=True, check=True
        )
        self.assertEqual(result.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
