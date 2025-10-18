import logging
import time

from sqlalchemy import text

from database import engine
from logging_config import configure_logging
from models import Base

logger = logging.getLogger("prestart")


def wait_for_db(max_tries=30, delay=2):
    for i in range(1, max_tries + 1):
        try:
            with engine.begin() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("DB conectada")
            return
        except Exception as e:
            logger.warning(
                "DB no disponible (try %s/%s): %s", i, max_tries, e.__class__.__name__
            )
            time.sleep(delay)
    raise RuntimeError("❌ DB no disponible después de varios intentos.")


if __name__ == "__main__":
    configure_logging()
    logger.info("Esperando a la BD…")
    wait_for_db()
    logger.info("Creando tablas si no existen…")
    Base.metadata.create_all(bind=engine)
    logger.info("Tablas listas ✅")
