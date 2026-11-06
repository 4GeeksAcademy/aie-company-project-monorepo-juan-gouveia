"""Utilidades comunes de TinyDB."""

from tinydb.table import Document, Table


def insert_with_file_id(table: Table, record: dict) -> int:
    """Inserta `record` con un doc_id calculado a partir de lo que hay en el archivo.

    TinyDB recuerda en memoria el siguiente doc_id de cada tabla. Si otro proceso insertó después
    (por ejemplo, `uv run create-admin` con la API arrancada), la siguiente inserción de la API
    reutilizaría un ID ocupado y fallaría con ValueError (500). Leer el archivo lo evita, igual que
    hace suppliers/repository.py. Quien llama debe tener tomado el bloqueo de la tabla.
    """
    next_id = max((document.doc_id for document in table.all()), default=0) + 1
    table.insert(Document(record, doc_id=next_id))
    return next_id
