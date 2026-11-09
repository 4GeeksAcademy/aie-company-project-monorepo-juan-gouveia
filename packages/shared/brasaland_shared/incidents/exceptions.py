"""Errores del archivo de incidentes.

Heredan de ValueError para que los scripts los capturen como cualquier error de entrada;
la API los traduce a respuestas HTTP con mensajes en español.
"""


class IncidentFileError(ValueError):
    """Base de los errores de un archivo de incidentes que no se puede analizar."""


class EmptyFileError(IncidentFileError):
    def __init__(self):
        super().__init__("The file is empty")


class InvalidEncodingError(IncidentFileError):
    def __init__(self):
        super().__init__("The file is not valid UTF-8")


class MissingColumnsError(IncidentFileError):
    def __init__(self, missing, source_name=None):
        self.missing = missing
        where = f" in {source_name}" if source_name else ""
        super().__init__(f"Missing columns{where}: {', '.join(missing)}")


class MalformedCsvError(IncidentFileError):
    """El lector de CSV no puede seguir, por ejemplo por una comilla sin cerrar que convierte el
    resto del archivo en un campo más largo que el límite del módulo csv."""

    def __init__(self, line, reason, source_name=None):
        self.line = line
        where = f" in {source_name}" if source_name else ""
        super().__init__(f"Malformed CSV{where} near line {line}: {reason}")


class NoRecordsError(IncidentFileError):
    def __init__(self):
        super().__init__("The file has a header but no records")
