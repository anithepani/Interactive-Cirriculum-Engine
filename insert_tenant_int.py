import sqlite3

conn = sqlite3.connect('ice.db')
conn.execute("INSERT OR IGNORE INTO tenants (id, name, slug) VALUES (1, 'Default Tenant', 'default')")
conn.commit()
conn.close()

print("Tenant inserted into root ice.db")