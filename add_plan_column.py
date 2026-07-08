import sqlite3

conn = sqlite3.connect('ice.db')
try:
    conn.execute('ALTER TABLE tenants ADD COLUMN plan TEXT DEFAULT "free"')
    conn.commit()
    print('✅ plan column added to tenants table')
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print('⚠️ plan column already exists')
    else:
        print(f'❌ Error: {e}')
conn.close()