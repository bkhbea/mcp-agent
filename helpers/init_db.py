import sqlite3

#import os
#os.makedirs("servers", exist_ok=True)

conn = sqlite3.connect("servers/users.db")
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

#c.executemany("INSERT INTO users (name, email) VALUES (?, ?)", [
#    ("Alice", "alice@example.com"),
#    ("Bob", "bob@example.com"),
#    ("Charlie", "charlie@example.com")
#])

#conn.commit()
#conn.close()
#print("Database initialized with sample users.")
message = """
Database initialized, no users were created\n
If you to create users, uncommet the create users in this file
if you want to check the database:
sqlite3 users.db "SELECT * FROM users" 


"""
print(message)

