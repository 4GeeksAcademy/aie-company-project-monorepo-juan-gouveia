"""Pruebas de los endpoints de incidentes."""

import csv
import io

import pytest

ANALYZE_URL = "/api/v1/incidents/analyze"
EXPORT_URL = "/api/v1/incidents/results/export"


def by_key(items, key):
    return {item[key]: item for item in items}


def test_analyze_returns_briefing_summary(client, sample_upload):
    response = client.post(ANALYZE_URL, files=sample_upload)

    assert response.status_code == 200
    body = response.json()
    assert body["source_file"] == "incidents-brasaland.csv"
    assert (body["total_records"], body["valid_records"], body["invalid_records"]) == (100, 96, 4)

    categories = by_key(body["categories"], "code")
    assert [item["code"] for item in body["categories"]] == [
        "CUSTOMER_COMPLAINT", "EQUIPMENT", "SUPPLY", "FOOD_QUALITY", "STAFF",
    ]
    assert {code: item["count"] for code, item in categories.items()} == {
        "CUSTOMER_COMPLAINT": 29, "EQUIPMENT": 17, "SUPPLY": 22, "FOOD_QUALITY": 19, "STAFF": 9,
    }
    assert categories["CUSTOMER_COMPLAINT"]["percentage"] == 30.2
    assert categories["STAFF"]["percentage"] == 9.4

    statuses = by_key(body["statuses"], "code")
    assert {code: item["count"] for code, item in statuses.items()} == {"OPEN": 32, "CLOSED": 50, "DISCARDED": 14}
    assert statuses["CLOSED"]["percentage"] == 52.1

    satisfaction = body["satisfaction"]
    assert (satisfaction["closed_cases"], satisfaction["scored_cases"], satisfaction["average"]) == (50, 50, 3.46)
    assert [item["count"] for item in satisfaction["distribution"]] == [4, 6, 12, 19, 9]


def test_analyze_reports_invalid_records(client, sample_upload):
    body = client.post(ANALYZE_URL, files=sample_upload).json()

    breakdown = {item["rule"]: item["count"] for item in body["invalid_breakdown"]}
    assert len(breakdown) == 7
    assert breakdown == {
        "missing_location": 1,
        "invalid_category": 1,
        "empty_description": 1,
        "missing_reporter": 0,
        "invalid_status": 0,
        "closed_without_score": 1,
        "score_out_of_range": 0,
    }
    assert body["invalid_records_detail"][0] == {
        "incident_id": "BRS-000044", "row": 45, "rules": ["missing_location"],
    }
    assert len(body["invalid_records_detail"]) == 4


def test_analyze_numbers_are_json_numbers(client, sample_upload):
    body = client.post(ANALYZE_URL, files=sample_upload).json()
    assert isinstance(body["satisfaction"]["average"], float)
    assert isinstance(body["categories"][0]["percentage"], float)


def test_export_without_analysis_returns_404(client):
    response = client.get(EXPORT_URL)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_analysis"


def test_export_returns_last_analysis_as_csv(client, sample_upload):
    client.post(ANALYZE_URL, files=sample_upload)
    response = client.get(EXPORT_URL)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="results.csv"'

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert list(rows[0].keys()) == ["metric", "value", "percentage"]
    by_metric = {row["metric"]: row for row in rows}
    # 3 totales + 7 reglas + 5 categorías + 3 estados + 3 de satisfacción + 5 puntajes.
    assert len(by_metric) == len(rows) == 26
    assert by_metric["valid_records"]["value"] == "96"
    assert by_metric["category.STAFF"] == {"metric": "category.STAFF", "value": "9", "percentage": "9.4"}
    assert by_metric["satisfaction.average"]["value"] == "3.46"
    assert by_metric["invalid.missing_reporter"]["value"] == "0"


def test_export_uses_the_latest_analysis(client, sample_upload):
    client.post(ANALYZE_URL, files=sample_upload)
    header = sample_upload["file"][1].decode("utf-8").splitlines()[0]
    single = f"{header}\nBRS-000001,2024-01-01,COL-01,STAFF,Una sola fila,OPEN,,,MGR-01\n"
    client.post(ANALYZE_URL, files={"file": ("one.csv", single.encode(), "text/csv")})

    rows = {row["metric"]: row["value"] for row in csv.DictReader(io.StringIO(client.get(EXPORT_URL).text))}
    assert rows["total_records"] == "1"


HEADER = "incident_id,date,location_id,category,description,status,customer_id,satisfaction_score,reporter_id"


def assert_error(response, status, code):
    assert response.status_code == status
    body = response.json()
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    return body["error"]["message"]


@pytest.mark.parametrize(
    ("upload", "status", "code"),
    [
        (("notas.txt", b"hola", "text/plain"), 415, "unsupported_file_type"),
        (("vacio.csv", b"", "text/csv"), 400, "empty_file"),
        (("latin1.csv", f"{HEADER}\nBRS-000001,2024-01-01,COL-01,STAFF,Calefacción,OPEN,,,MGR-01\n".encode("latin-1"),
          "text/csv"), 422, "invalid_encoding"),
        (("encabezado.csv", f"{HEADER}\n".encode(), "text/csv"), 422, "no_records"),
    ],
)
def test_analyze_input_errors(client, upload, status, code):
    assert_error(client.post(ANALYZE_URL, files={"file": upload}), status, code)


def test_analyze_without_file(client):
    assert_error(client.post(ANALYZE_URL), 400, "missing_file")


def test_analyze_missing_columns_lists_them(client):
    upload = ("pocas.csv", b"incident_id,date\nBRS-000001,2024-01-01\n", "text/csv")
    message = assert_error(client.post(ANALYZE_URL, files={"file": upload}), 422, "missing_columns")
    assert "location_id" in message and "reporter_id" in message


def test_analyze_malformed_csv_is_a_file_error(client):
    # Una comilla sin cerrar convierte el resto del archivo en un único campo que supera el límite del
    # módulo csv (131 072 caracteres): debe ser un 422 del archivo, no un 500.
    good = "BRS-{n:06d},2024-01-01,COL-01,STAFF,Retraso en el turno,OPEN,,,MGR-01\n"
    text = HEADER + "\n" + good.format(n=1) + 'BRS-000002,2024-01-01,COL-01,STAFF,"Sin cerrar,OPEN,,,MGR-01\n'
    text +="".join(good.format(n=n) for n in range(3, 2500))
    upload = ("comilla.csv", text.encode(), "text/csv")
    message = assert_error(client.post(ANALYZE_URL, files={"file": upload}), 422, "malformed_csv")
    assert "línea 3" in message


def test_analyze_file_too_large(client, monkeypatch):
    monkeypatch.setattr("app.domains.incidents.router.MAX_UPLOAD_BYTES", 100)
    upload = ("grande.csv", b"x" * 101, "text/csv")
    assert_error(client.post(ANALYZE_URL, files={"file": upload}), 413, "file_too_large")


def test_analyze_accepts_windows_csv_content_type(client, sample_upload):
    name, data, _ = sample_upload["file"]
    response = client.post(ANALYZE_URL, files={"file": (name, data, "application/vnd.ms-excel")})
    assert response.status_code == 200


def test_failed_analysis_keeps_previous_result(client, sample_upload):
    client.post(ANALYZE_URL, files=sample_upload)
    client.post(ANALYZE_URL, files={"file": ("vacio.csv", b"", "text/csv")})
    assert client.get(EXPORT_URL).status_code == 200
