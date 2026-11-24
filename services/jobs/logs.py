"""Formato de log de los jobs: cada línea con timestamp (UTC), nivel, nombre del job y estado resultante.

```
2026-11-25T08:00:01Z | INFO | nightly_export | processing | target_date=2026-11-24 | Exportando telemetry_events
```

El job y el estado llegan en `extra={"job": ..., "status": ...}`. Una línea sin ellos (de otra librería)
se escribe con `-` en su lugar, en vez de romper el formato.
"""

from __future__ import annotations

import logging
import sys
import time

LOGGER_NAME = "brasaland.jobs"
FORMAT = "%(asctime)s | %(levelname)s | %(job)s | %(status)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class _JobFieldsDefaults(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.job = getattr(record, "job", "-")
        record.status = getattr(record, "status", "-")
        return True


def formatter() -> logging.Formatter:
    fmt = logging.Formatter(FORMAT, datefmt=DATE_FORMAT)
    fmt.converter = time.gmtime
    return fmt


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Logger de los jobs hacia stderr (en Docker, el log del contenedor). Idempotente."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    if not any(getattr(h, "_brasaland_jobs", False) for h in logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter())
        handler.addFilter(_JobFieldsDefaults())
        handler._brasaland_jobs = True  # type: ignore[attr-defined]
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
