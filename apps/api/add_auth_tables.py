"""Create auth tables (users, verification_codes) if they don't exist.

Run from repo root:
    python apps/api/add_auth_tables.py
"""
from __future__ import annotations

import os
import sqlite3

# Resolve DB path: prefer DATABASE_URL sqlite file, else repo-root ice.db
DB_PATH = os.environ.get("AUTH_DB_PATH")
if not DB_PATH:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    DB_PATH = os.path.join(repo_root, "ice.db")

print(f"Using database: {DB_PATH}")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Ensure tenants table exists (required FK target)
cursor.execute("""
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    slug VARCHAR UNIQUE NOT NULL,
    plan VARCHAR DEFAULT 'free',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

# Create or migrate users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL DEFAULT 'User',
    password_hash VARCHAR(255),
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255),
    role VARCHAR DEFAULT 'learner',
    is_verified BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    UNIQUE(oauth_provider, oauth_id)
)
""")

# Add missing columns to existing users table (safe no-op if already present)
_auth_columns = {
    "name": "VARCHAR(255) NOT NULL DEFAULT 'User'",
    "password_hash": "VARCHAR(255)",
    "oauth_id": "VARCHAR(255)",
    "is_verified": "BOOLEAN DEFAULT 0",
    "is_active": "BOOLEAN DEFAULT 1",
    "last_login": "DATETIME",
    "role": "VARCHAR DEFAULT 'learner'",
}
cursor.execute("PRAGMA table_info(users)")
existing_cols = {row[1] for row in cursor.fetchall()}
for col, col_type in _auth_columns.items():
    if col not in existing_cols:
        cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
        print(f"  Added column users.{col}")

cursor.execute("""
CREATE TABLE IF NOT EXISTS verification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) NOT NULL,
    code VARCHAR(6) NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_used BOOLEAN DEFAULT 0
)
""")

cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
cursor.execute(
    "CREATE INDEX IF NOT EXISTS idx_verification_codes_email ON verification_codes(email)"
)
cursor.execute("CREATE INDEX IF NOT EXISTS ix_users_tenant ON users(tenant_id)")

conn.commit()
conn.close()

print("Auth tables created / migrated successfully!")
