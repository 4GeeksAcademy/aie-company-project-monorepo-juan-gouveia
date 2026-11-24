"""`brasaland_tasks.celery_app` crea la aplicación al importarse y exige `REDIS_URL`.

Las pruebas no se conectan a Redis: crear la aplicación no abre ninguna conexión. Se fija una URL antes
de cualquier importación del paquete (base 15, para no tocar la 0 si algún día se conectaran).
"""

import os

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
