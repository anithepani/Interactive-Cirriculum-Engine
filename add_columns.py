import sqlite3
conn = sqlite3.connect('ice.db')
cursor = conn.cursor()

# Add missing columns if they don't exist
cursor.execute("PRAGMA table_info(users)")
existing = [row[1] for row in cursor.fetchall()]

if 'oauth_provider' not in existing:
    cursor.execute("ALTER TABLE users ADD COLUMN oauth_provider VARCHAR(50)")
    print("✅ Added oauth_provider")
if 'oauth_id' not in existing:
    cursor.execute("ALTER TABLE users ADD COLUMN oauth_id VARCHAR(255)")
    print("✅ Added oauth_id")
if 'role' not in existing:
    cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'learner'")
    print("✅ Added role")
if 'is_verified' not in existing:
    cursor.execute("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0")
    print("✅ Added is_verified")
if 'is_active' not in existing:
    cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
    print("✅ Added is_active")

conn.commit()
conn.close()
print("✅ All columns added")