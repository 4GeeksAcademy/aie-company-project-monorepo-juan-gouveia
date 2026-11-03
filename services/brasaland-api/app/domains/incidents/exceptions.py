"""Errores del archivo de incidentes. Solo librería estándar: los usa también el script de consola.

Heredan de ValueError para que el script los capture como cualquier error de entrada;
el router de la API los traduce a respuestas HTTP con mensajes en español.
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


class NoRecordsError(IncidentFileError):
    def __init__(self):
        super().__init__("The file has a header but no records")
