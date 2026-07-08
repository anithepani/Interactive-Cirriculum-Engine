import sqlite3

# Connect to the database (looks in the current directory)
conn = sqlite3.connect('ice.db')
cursor = conn.cursor()

# Check if users table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
result = cursor.fetchone()

if result:
    print("✅ users table exists")
else:
    print("❌ users table missing – creating it now")
    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255) NOT NULL,
            password_hash VARCHAR(255),
            oauth_provider VARCHAR(50),
            oauth_id VARCHAR(255),
            role VARCHAR(50) DEFAULT 'learner',
            is_verified BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME,
            FOREIGN KEY (tenant_id) REFERENCES tenants(id)
        )
    ''')
    # Create verification_codes table
    cursor.execute('''
        CREATE TABLE verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR(255) NOT NULL,
            code VARCHAR(6) NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_used BOOLEAN DEFAULT 0
        )
    ''')
    cursor.execute('CREATE INDEX idx_users_email ON users(email)')
    cursor.execute('CREATE INDEX idx_verification_codes_email ON verification_codes(email)')
    conn.commit()
    print("✅ Tables created")

# Show columns to confirm
cursor.execute("PRAGMA table_info(users)")
columns = [row[1] for row in cursor.fetchall()]
print("✅ users columns:", columns)

conn.close()