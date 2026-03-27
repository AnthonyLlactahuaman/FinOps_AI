"""
Gestión de memoria conversacional - Persistente con PostgreSQL
"""
import os
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver


def get_memory() -> PostgresSaver:
    """
    Crea y retorna una memoria conversacional persistente
    usando PostgreSQL como backend.
    """
    DB_URI = os.environ.get("POSTGRES_DB_URI")
    if not DB_URI:
        raise ValueError("POSTGRES_DB_URI no encontrada en variables de entorno")

    connection_kwargs = {
        "autocommit": True,
        "prepare_threshold": 0,
    }

    pool = ConnectionPool(
        conninfo=DB_URI,
        max_size=20,
        kwargs=connection_kwargs,
    )

    checkpointer = PostgresSaver(pool)
    checkpointer.setup()
    return checkpointer
