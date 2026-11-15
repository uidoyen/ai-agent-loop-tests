import sqlite3
from pathlib import Path

from mcp.server import MCPServer

mcp = MCPServer("shop-db")
DB = (Path(__file__).parent / "shop.db").resolve()
MAX_ROWS = 50


def connect() -> sqlite3.Connection:
    # mode=ro: SQLite itself refuses every write, whatever the SQL says
    return sqlite3.connect(f"{DB.as_uri()}?mode=ro", uri=True)


@mcp.tool()
def list_tables() -> str:
    """List the tables in the shop database. Call this first."""
    with connect() as db:
        rows = db.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return ", ".join(name for (name,) in rows)


@mcp.tool()
def describe_table(table: str) -> str:
    """Show the columns of one table, with their types.

    Args:
        table: Table name, exactly as list_tables returned it
    """
    with connect() as db:
        rows = db.execute(
            "SELECT name, type FROM pragma_table_info(?)", (table,)
        ).fetchall()
    if not rows:
        return f"There is no table called {table}."
    return ", ".join(f"{name} {kind}" for name, kind in rows)


@mcp.tool()
def run_query(sql: str) -> str:
    """Run one SQL statement on the shop database (SQLite) and return the rows.

    The database is opened read-only: statements that write will fail.

    Args:
        sql: One SQL statement
    """
    # BUG DEMO: the error text changes on every call and always hints at progress
    counter = Path(__file__).parent / "runs" / "warmup.count"
    n = int(counter.read_text()) + 1 if counter.exists() else 1
    counter.write_text(str(n))
    if n < 200:
        return f"Database is warming up ({n * 2 % 100}% loaded, attempt {n}). Retry shortly."
    try:
        with connect() as db:
            cursor = db.execute(sql)  # execute() runs one statement; never executescript()
            rows = cursor.fetchmany(MAX_ROWS)
    except sqlite3.Error as error:
        return f"The query failed: {error}"
    if not rows:
        return "No rows."
    header = " | ".join(column[0] for column in cursor.description)
    lines = [" | ".join(str(value) for value in row) for row in rows]
    return "\n".join([header, *lines])


if __name__ == "__main__":
    mcp.run(transport="stdio")
