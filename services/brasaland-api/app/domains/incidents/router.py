"""Endpoints del dominio de incidentes. Solo traducen HTTP; las reglas están en service.py."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Response, UploadFile

from app.core.errors import ApiError
from app.domains.incidents import service
from app.domains.incidents.dependencies import get_repository
from app.domains.incidents.exceptions import (
    EmptyFileError,
    IncidentFileError,
    InvalidEncodingError,
    MissingColumnsError,
    NoRecordsError,
)
from app.domains.incidents.repository import LastAnalysisRepository, StoredAnalysis
from app.domains.incidents.schemas import AnalysisResponse

router = APIRouter(prefix="/incidents", tags=["incidents"])

# Un mes de incidentes de las 14 sedes ocupa decenas de KB; 5 MB deja margen de sobra.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def to_api_error(error: IncidentFileError) -> ApiError:
    """Traduce un error del archivo a su respuesta HTTP, con un mensaje para el usuario."""
    if isinstance(error, EmptyFileError):
        return ApiError(400, "empty_file", "El archivo está vacío.")
    if isinstance(error, InvalidEncodingError):
        return ApiError(
            422, "invalid_encoding", "El archivo no está en UTF-8. Expórtalo de nuevo como «CSV UTF-8»."
        )
    if isinstance(error, MissingColumnsError):
        return ApiError(422, "missing_columns", f"Faltan columnas obligatorias: {', '.join(error.missing)}.")
    if isinstance(error, NoRecordsError):
        return ApiError(422, "no_records", "El archivo solo tiene el encabezado; no hay incidentes que analizar.")
    return ApiError(422, "invalid_file", "No se pudo leer el archivo.")


async def read_csv_upload(file: UploadFile | None) -> bytes:
    """Comprueba que se haya enviado un CSV de tamaño razonable y devuelve su contenido."""
    if file is None:
        raise ApiError(400, "missing_file", "No se recibió ningún archivo. Envíalo en el campo «file».")
    # Se comprueba la extensión y no el Content-Type: Windows envía los CSV como application/vnd.ms-excel.
    if not (file.filename or "").lower().endswith(".csv"):
        raise ApiError(415, "unsupported_file_type", "El archivo debe tener extensión .csv.")
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(413, "file_too_large", "El archivo supera el tamaño máximo de 5 MB.")
    return data


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_incidents(
    file: UploadFile | None = File(None, description="CSV de incidentes en UTF-8"),
    repository: LastAnalysisRepository = Depends(get_repository),
) -> AnalysisResponse:
    """Valida y resume el CSV de incidentes, y lo guarda como el último análisis."""
    data = await read_csv_upload(file)
    try:
        records = service.parse_upload(data)
    except IncidentFileError as error:
        raise to_api_error(error) from None
    summary = service.analyze(records)

    result = AnalysisResponse.from_summary(summary, file.filename or "", datetime.now(timezone.utc))
    export_csv = service.export_csv_text(service.build_export_rows(summary))
    repository.save(StoredAnalysis(result=result, export_csv=export_csv))
    return result


@router.get(
    "/results/export",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}, "description": "CSV con una fila por métrica"}},
)
def export_results(repository: LastAnalysisRepository = Depends(get_repository)) -> Response:
    """Descarga el último análisis como results.csv (columnas metric, value y percentage)."""
    stored = repository.get()
    if stored is None:
        raise ApiError(404, "no_analysis", "Todavía no hay ningún análisis. Sube un archivo primero.")
    return Response(
        content=stored.export_csv,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="results.csv"'},
    )
