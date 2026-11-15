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


# --- WRONG-TOOL TEST: six narrow tools next to the three real ones (the last one has a vague docstring on purpose) ---
def _rows(sql: str, args=()) -> str:
    with connect() as db:
        rows = db.execute(sql, args).fetchall()
    return "\n".join(" | ".join(str(v) for v in r) for r in rows) or "No rows."


@mcp.tool()
def count_orders() -> str:
    """Count all orders in the shop."""
    return _rows("SELECT COUNT(*) FROM orders")


@mcp.tool()
def recent_orders(limit: int = 3) -> str:
    """Show the most recent orders (id, item, total in EUR, date)."""
    return _rows("SELECT id, item, total_eur, ordered_on FROM orders ORDER BY ordered_on DESC LIMIT ?", (limit,))


@mcp.tool()
def get_customer(name: str) -> str:
    """Look up one customer by name (id, name, city)."""
    return _rows("SELECT id, name, city FROM customers WHERE name LIKE ?", (f"%{name}%",))


@mcp.tool()
def orders_for_customer(customer_id: int) -> str:
    """List the orders of one customer (id, item, total in EUR, date)."""
    return _rows("SELECT id, item, total_eur, ordered_on FROM orders WHERE customer_id = ?", (customer_id,))


@mcp.tool()
def order_total(order_id: int) -> str:
    """Total in EUR of one order."""
    return _rows("SELECT total_eur FROM orders WHERE id = ?", (order_id,))


@mcp.tool()
def top_customers() -> str:
    """Top customers."""
    return _rows("SELECT c.name, COUNT(*) FROM orders o JOIN customers c ON c.id = o.customer_id GROUP BY c.name ORDER BY COUNT(*) DESC, c.name LIMIT 3")


if __name__ == "__main__":
    mcp.run(transport="stdio")
