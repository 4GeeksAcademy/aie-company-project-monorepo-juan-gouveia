"""Loggers propios de la API que deben salir por consola junto a los de Uvicorn."""

import logging


def console_logger(name: str) -> logging.Logger:
    """Devuelve el logger `name` con un handler de consola en nivel INFO.

    Uvicorn solo configura sus propios loggers: sin un handler, las líneas de INFO de un logger propio
    no saldrían por consola. El handler se añade una sola vez, aunque se llame varias veces.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
