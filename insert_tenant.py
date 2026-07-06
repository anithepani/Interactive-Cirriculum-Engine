import sqlite3

conn = sqlite3.connect('apps/api/ice.db')
conn.execute("INSERT OR IGNORE INTO tenants (id, name, slug) VALUES ('default-tenant', 'Default Tenant', 'default')")
conn.commit()
conn.close()

print("Tenant inserted successfully!")