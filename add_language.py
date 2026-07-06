import sqlite3
conn = sqlite3.connect('ice.db')
try:
    conn.execute("ALTER TABLE curricula ADD COLUMN language TEXT DEFAULT 'en'")
    conn.commit()
    print("✅ language column added")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("⚠️ language column already exists")
    else:
        print(f"❌ Error: {e}")
conn.close()