import sqlite3
from contextlib import contextmanager
from database.schema import get_db_path

@contextmanager
def get_connection():
    """Provides a context-managed connection to the SQLite database.
    Ensures the connection is always closed and transactions committed.
    """
    db_file = get_db_path()
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row  # Enables returning dictionary-like rows
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
