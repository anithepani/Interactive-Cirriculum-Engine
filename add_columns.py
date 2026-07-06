import sqlite3

conn = sqlite3.connect('ice.db')
conn.execute("ALTER TABLE curricula ADD COLUMN status TEXT DEFAULT 'queued'")
conn.execute("ALTER TABLE curricula ADD COLUMN ready_at DATETIME")
conn.commit()
conn.close()
print("Columns added successfully")