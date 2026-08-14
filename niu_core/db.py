"""Database helpers shared by the Niu Secretary platform."""

from __future__ import annotations

from contextlib import contextmanager
from sqlite3 import Connection

from server import store


connect = store.connect
database_path = store.database_path
now_iso = store.now_iso
new_id = store.new_id


@contextmanager
def transaction() -> Connection:
    connection = connect()
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def migrate() -> None:
    with connect() as connection:
        store.initialize(connection)

