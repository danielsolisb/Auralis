import pymysql
import threading
from typing import Iterable, Optional, Tuple, Any

class DB:
    """
    Gestor de conexiones MySQL con el enfoque: **una conexión por hilo**.
    - Cada hilo obtiene y reutiliza su propia conexión (thread-local).
    - Evita colisiones de protocolo ('Packet sequence number wrong') de PyMySQL
      al compartir una sola conexión entre múltiples hilos.
    """
    def __init__(self, host: str, port: int, user: str, password: str, dbname: str):
        self._conn_params = dict(
            host=host,
            port=port,
            user=user,
            password=password,
            database=dbname,
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
            charset="utf8mb4",
        )
        self._local = threading.local()

    def _get_conn(self) -> pymysql.connections.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = pymysql.connect(**self._conn_params)
            self._local.conn = conn
            return conn
        try:
            conn.ping(reconnect=True)
        except Exception:
            conn = pymysql.connect(**self._conn_params)
            self._local.conn = conn
        return conn

    def _commit(self, conn):
        try:
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

    def executemany(self, sql: str, rows: Iterable[Tuple[Any, ...]]):
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.executemany(sql, rows)
            self._commit(conn)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

    def execute(self, sql: str, params: Optional[Tuple[Any, ...]] = None):
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, params)
            try:
                res = cur.fetchall()
            except Exception:
                res = []
        self._commit(conn)
        return res

    def close_thread(self):
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            finally:
                self._local.conn = None
