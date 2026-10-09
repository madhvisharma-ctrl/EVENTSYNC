"""
EventSync Database Connection Layer

This module provides:
- SQLite database connection
- Row-based query results
- Read helpers
- Write helpers
- Transaction helpers
- Database utility functions
"""

from pathlib import Path
import sqlite3
from typing import Any, Iterable, Optional


# ================================================================
# PATH CONFIGURATION
# ================================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_DIR = BASE_DIR / "database"

DATABASE_PATH = DATABASE_DIR / "eventsync.db"


# Make sure the database directory exists.
DATABASE_DIR.mkdir(parents=True, exist_ok=True)


def init_database_directory() -> None:
    """Ensure the SQLite database directory exists."""
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)


# ================================================================
# DATABASE CONNECTION
# ================================================================

def get_connection() -> sqlite3.Connection:
    """
    Create and return a new SQLite connection.

    Every connection:
    - uses sqlite3.Row
    - enables foreign keys
    - uses WAL mode
    - has a reasonable timeout
    """

    connection = sqlite3.connect(
        str(DATABASE_PATH),
        timeout=30,
        check_same_thread=False
    )

    # Allows:
    # row["name"]
    # instead of:
    # row[1]
    connection.row_factory = sqlite3.Row

    # Enforce FOREIGN KEY relationships.
    connection.execute("PRAGMA foreign_keys = ON")

    # Improve SQLite reliability when multiple operations happen.
    connection.execute("PRAGMA journal_mode = WAL")

    # Reduce unnecessary disk synchronization overhead.
    connection.execute("PRAGMA synchronous = NORMAL")

    return connection


# ================================================================
# SELECT HELPERS
# ================================================================

def fetch_one(
    query: str,
    parameters: Iterable[Any] = ()
) -> Optional[sqlite3.Row]:
    """
    Execute a SELECT query and return one row.

    Returns:
        sqlite3.Row if found
        None if no row exists
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            query,
            tuple(parameters)
        )

        return cursor.fetchone()

    finally:
        connection.close()


def fetch_all(
    query: str,
    parameters: Iterable[Any] = ()
) -> list[sqlite3.Row]:
    """
    Execute a SELECT query and return all rows.
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            query,
            tuple(parameters)
        )

        return cursor.fetchall()

    finally:
        connection.close()


def fetch_value(
    query: str,
    parameters: Iterable[Any] = ()
) -> Any:
    """
    Execute a SELECT query and return the first column
    of the first row.

    Returns None if no result exists.
    """

    row = fetch_one(query, parameters)

    if row is None:
        return None

    return row[0]


# ================================================================
# WRITE HELPERS
# ================================================================

def execute_write(
    query: str,
    parameters: Iterable[Any] = ()
) -> int:
    """
    Execute INSERT / UPDATE / DELETE.

    For INSERT statements, returns the generated row ID.

    For UPDATE / DELETE statements, the returned value may be
    zero when there is no generated row ID.
    """

    connection = get_connection()

    try:
        cursor = connection.execute(
            query,
            tuple(parameters)
        )

        connection.commit()

        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def execute_many(
    query: str,
    parameters_list: Iterable[Iterable[Any]]
) -> None:
    """
    Execute the same INSERT / UPDATE statement for multiple rows.
    """

    connection = get_connection()

    try:
        connection.executemany(
            query,
            [tuple(parameters) for parameters in parameters_list]
        )

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


def execute_script(script: str) -> None:
    """
    Execute multiple SQL statements as one transaction.
    """

    connection = get_connection()

    try:
        connection.executescript(script)
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ================================================================
# TRANSACTION HELPER
# ================================================================

def run_transaction(callback, *args, **kwargs):
    """
    Run a custom database operation inside a transaction.

    The callback receives the active SQLite connection.

    Example:

        def save_data(connection):
            connection.execute(...)

        run_transaction(save_data)
    """

    connection = get_connection()

    try:
        result = callback(connection, *args, **kwargs)

        connection.commit()

        return result

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ================================================================
# DATABASE INFORMATION HELPERS
# ================================================================

def database_exists() -> bool:
    """
    Return True when the SQLite database file exists.
    """

    return DATABASE_PATH.exists()


def get_database_path() -> str:
    """
    Return the absolute database path as a string.
    """

    return str(DATABASE_PATH)


def table_exists(table_name: str) -> bool:
    """
    Check whether a specific table exists.
    """

    connection = get_connection()

    try:
        row = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table_name,)
        ).fetchone()

        return row is not None

    finally:
        connection.close()


def get_table_names() -> list[str]:
    """
    Return all user-created SQLite table names.
    """

    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        return [row["name"] for row in rows]

    finally:
        connection.close()


# ================================================================
# CONNECTION TEST
# ================================================================

def test_connection() -> bool:
    """
    Verify that SQLite can be opened successfully.
    """

    connection = get_connection()

    try:
        connection.execute("SELECT 1")
        return True

    finally:
        connection.close()


# ================================================================
# MODULE TEST
# ================================================================

if __name__ == "__main__":
    print("=" * 60)
    print(" EventSync Database Connection Test")
    print("=" * 60)

    print(f"Database path : {DATABASE_PATH}")
    print(f"Database exists: {database_exists()}")

    try:
        if test_connection():
            print("SQLite connection: OK")

        print("Existing tables:")

        tables = get_table_names()

        if tables:
            for table in tables:
                print(f"  - {table}")
        else:
            print("  No tables yet.")

    except Exception as error:
        print("Database connection failed.")
        print(f"Error: {error}")

    print("=" * 60)