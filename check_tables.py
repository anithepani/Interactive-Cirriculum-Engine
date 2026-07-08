import sqlite3
conn = sqlite3.connect('ice.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('users', 'verification_codes')").fetchall()
print(tables)
conn.close()