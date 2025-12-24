#!/usr/bin/env python3
"""
Manual script to fix SQLite database OAuth schema migration.
Run this if automatic migration fails.

Usage:
    python update_utils/fix_sqlite_oauth_schema.py --db-path gen/bgg_semantic.db
"""

import argparse
import sqlite3
import sys

def fix_schema(db_path: str):
    """Fix SQLite users table schema to include OAuth columns."""
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Check if users table exists
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if not cur.fetchone():
            print("ERROR: users table does not exist. Cannot migrate.")
            return False
        
        # Check current schema
        cur = conn.execute("PRAGMA table_info(users)")
        columns = {row[1]: row[2] for row in cur.fetchall()}
        print(f"Current columns: {list(columns.keys())}")
        
        # Check if migration is needed
        if 'email' in columns and 'oauth_provider' in columns:
            print("Schema already has OAuth columns. No migration needed.")
            return True
        
        print("\nStarting migration...")
        
        # Clean up any leftover users_new table
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users_new'")
        if cur.fetchone():
            print("Cleaning up leftover users_new table...")
            conn.execute("DROP TABLE IF EXISTS users_new")
            conn.commit()
        
        # Create new table with OAuth columns
        print("Creating new users table with OAuth columns...")
        conn.execute("""
            CREATE TABLE users_new (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                email          TEXT UNIQUE,
                username       TEXT,
                oauth_provider TEXT,
                oauth_id       TEXT,
                password_hash  TEXT,
                bgg_id         TEXT,
                is_admin       INTEGER DEFAULT 0,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create unique index
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_users_oauth_unique 
            ON users_new(oauth_provider, oauth_id) 
            WHERE oauth_provider IS NOT NULL AND oauth_id IS NOT NULL
        """)
        
        # Migrate existing users
        if 'username' in columns and 'password_hash' in columns:
            print("Migrating existing users...")
            conn.execute("""
                INSERT INTO users_new (id, email, username, oauth_provider, password_hash, bgg_id, is_admin, created_at)
                SELECT 
                    id,
                    CASE 
                        WHEN username LIKE '%@%' THEN username 
                        ELSE username || '@migrated.local' 
                    END as email,
                    username,
                    'email' as oauth_provider,
                    password_hash,
                    bgg_id,
                    COALESCE(is_admin, 0) as is_admin,
                    COALESCE(created_at, CURRENT_TIMESTAMP) as created_at
                FROM users
            """)
            user_count = conn.execute("SELECT COUNT(*) FROM users_new").fetchone()[0]
            print(f"Migrated {user_count} users")
        else:
            print("No existing users to migrate")
        
        # Drop old table and rename new one
        print("Replacing old table...")
        conn.execute("DROP TABLE users")
        conn.execute("ALTER TABLE users_new RENAME TO users")
        conn.commit()
        
        # Verify
        cur = conn.execute("PRAGMA table_info(users)")
        new_columns = {row[1]: row[2] for row in cur.fetchall()}
        print(f"\nMigration complete! New columns: {list(new_columns.keys())}")
        
        if 'email' in new_columns and 'oauth_provider' in new_columns:
            print("[SUCCESS] Migration successful!")
            return True
        else:
            print("[ERROR] Migration failed - columns still missing")
            return False
            
    except sqlite3.Error as e:
        print(f"ERROR: Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Fix SQLite OAuth schema migration")
    parser.add_argument("--db-path", default="gen/bgg_semantic.db", help="Path to SQLite database")
    args = parser.parse_args()
    
    print("=" * 60)
    print("SQLite OAuth Schema Migration Fix")
    print("=" * 60)
    
    success = fix_schema(args.db_path)
    
    if success:
        print("\n[SUCCESS] Database schema fixed successfully!")
        print("You can now restart your backend server.")
        sys.exit(0)
    else:
        print("\n[ERROR] Migration failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
