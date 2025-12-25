import os
import logging

# Remove all existing handlers (especially StreamHandler -> stdout)
# MCP stdio servers MUST own stdout exclusively
# DO NOT USE the print() command here. 

root = logging.getLogger()
for h in list(root.handlers):
    root.removeHandler(h)

root.propagate = False

file_handler = logging.FileHandler("example.log")
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
file_handler.setFormatter(formatter)

root.addHandler(file_handler)
root.setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
logger.debug("DB SERVER STARTED")

import sqlite3
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("SQLite3 DB Server" , log_level="CRITICAL")    
mcp.title = "Database MCP Server"
mcp.version = "0.1.0"

@mcp.tool()
def create_user(name: str, email: str) -> dict:
    """Create a new user and return their info."""
    logger.debug(f"Creating new user with name {name} and email: {email}")
    # Absolute path to users.db in the same folder as db_server.py
    db_path = os.path.join(os.path.dirname(__file__), "users.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", (name, email))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return {"id": user_id, "name": name, "email": email}

@mcp.tool()
def update_user(id: int, name: str | None = None, email: str | None = None) -> dict:
    """Update user fields by ID. Return updated user info."""
    db_path = os.path.join(os.path.dirname(__file__), "users.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if email is not None:
        updates.append("email = ?")
        params.append(email)
    if not updates:
        raise ValueError("No fields provided for update")
    params.append(id)
    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(sql, tuple(params))
    conn.commit()

    cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"User {id} not found")
    return {"id": row[0], "name": row[1], "email": row[2]}

@mcp.tool()
def delete_user(id: int) -> dict:
    """Delete user by ID. Return deleted user ID."""
    db_path = os.path.join(os.path.dirname(__file__), "users.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise ValueError(f"User {id} not found")
    cursor.execute("DELETE FROM users WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"deleted_id": row[0]}

@mcp.tool()
def list_users(name_filter: str | None = None, email_filter: str | None = None) -> list[dict]:
    """Return users optionally filtered by name or email."""
    db_path = os.path.join(os.path.dirname(__file__), "users.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    sql = "SELECT id, name, email FROM users WHERE 1=1"
    params = []
    if name_filter:
        sql += " AND name LIKE ?"
        params.append(f"%{name_filter}%")
    if email_filter:
        sql += " AND email LIKE ?"
        params.append(f"%{email_filter}%")
    cursor.execute(sql, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "email": r[2]} for r in rows]

@mcp.tool()
def get_user_by_id(id: int) -> dict:
    """Return a user by their ID."""
    db_path = os.path.join(os.path.dirname(__file__), "users.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email FROM users WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"User {id} not found")
    return {"id": row[0], "name": row[1], "email": row[2]}



if __name__ == "__main__":
    mcp.run(transport="stdio")

