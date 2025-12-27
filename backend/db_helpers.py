"""
Helper functions for database operations that automatically manage connections.
"""
from typing import Callable
from contextlib import contextmanager
from backend.db import get_db_connection, put_connection


@contextmanager
def db_operation():
    """
    Context manager for database operations.
    Automatically gets a connection and returns it to the pool.

    Usage:
        with db_operation() as conn:
            cur = execute_query(conn, "SELECT ...", (...))
            result = cur.fetchone()
            conn.commit()
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        put_connection(conn)


def with_db_connection(func: Callable) -> Callable:
    """
    Decorator that automatically provides a database connection to a function.
    The function should accept 'conn' as its first parameter after self/request params.

    Usage:
        @with_db_connection
        def my_endpoint(current_user, conn):
            cur = execute_query(conn, "SELECT ...", (...))
    """

    def wrapper(*args, **kwargs):
        conn = get_db_connection()
        try:
            # Insert conn as the last positional argument before keyword args
            return func(*args, conn, **kwargs)
        finally:
            put_connection(conn)

    return wrapper
