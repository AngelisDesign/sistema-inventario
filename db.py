import mysql.connector
from contextlib import contextmanager

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",          # <-- tu contraseña de MySQL
    "database": "inventario",
    "charset": "utf8mb4",
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def query(sql, params=None):
    """Ejecuta un SELECT y devuelve lista de diccionarios."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(sql, params or ())
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def execute(sql, params=None):
    """Ejecuta INSERT/UPDATE/DELETE simple (sin transacción)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params or ())
    conn.commit()
    last_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return last_id


@contextmanager
def transaction():
    """
    Uso:
        with transaction() as cursor:
            cursor.execute("INSERT ...")
            cursor.execute("UPDATE ...")
    Si algo falla, se deshace todo automáticamente.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()