import sqlite3

conn = sqlite3.connect("users.db")
c = conn.cursor()

# Create table
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL
)
""")

# Insert sample rows
c.executemany("INSERT INTO users (name, email) VALUES (?, ?)", [
    ("Alice", "alice@example.com"),
    ("Bob", "bob@example.com"),
    ("Charlie", "charlie@example.com")
])

conn.commit()
conn.close()
print("Database initialized with sample users.")
