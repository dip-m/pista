#!/usr/bin/env python3
"""
Verification script to test PostgreSQL connection and schema.
Run this after migration to ensure everything is set up correctly.

Usage:
    python update_utils/verify_postgres.py --postgres-url postgresql://user:pass@host:5432/db
"""

import argparse
import psycopg2
import sys
from psycopg2.extras import RealDictCursor

def verify_connection(postgres_url: str):
    """Verify PostgreSQL connection and schema."""
    print("=" * 60)
    print("PostgreSQL Connection Verification")
    print("=" * 60)
    
    try:
        # Test connection
        print("\n1. Testing connection...")
        conn = psycopg2.connect(postgres_url)
        print("   ✅ Connection successful!")
        
        # Check tables
        print("\n2. Checking tables...")
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [row['table_name'] for row in cur.fetchall()]
        print(f"   Found {len(tables)} tables:")
        for table in tables:
            print(f"     - {table}")
        
        # Required tables
        required_tables = [
            'users', 'games', 'mechanics', 'categories', 'designers',
            'artists', 'publishers', 'families', 'game_mechanics',
            'game_categories', 'user_collections', 'chat_threads',
            'chat_messages'
        ]
        missing_tables = [t for t in required_tables if t not in tables]
        if missing_tables:
            print(f"   ⚠️  Missing tables: {missing_tables}")
        else:
            print("   ✅ All required tables exist")
        
        # Check users table schema
        print("\n3. Checking users table schema...")
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        user_columns = {row['column_name']: row['data_type'] for row in cur.fetchall()}
        print(f"   Columns: {list(user_columns.keys())}")
        
        required_user_columns = ['id', 'email', 'username', 'oauth_provider', 'oauth_id', 'password_hash']
        missing_columns = [c for c in required_user_columns if c not in user_columns]
        if missing_columns:
            print(f"   ⚠️  Missing columns: {missing_columns}")
        else:
            print("   ✅ All required OAuth columns exist")
        
        # Check data counts
        print("\n4. Checking data counts...")
        
        # Users
        cur.execute("SELECT COUNT(*) as count FROM users")
        user_count = cur.fetchone()['count']
        print(f"   Users: {user_count}")
        
        # Games
        cur.execute("SELECT COUNT(*) as count FROM games")
        game_count = cur.fetchone()['count']
        print(f"   Games: {game_count}")
        
        # Collections
        cur.execute("SELECT COUNT(*) as count FROM user_collections")
        collection_count = cur.fetchone()['count']
        print(f"   User Collections: {collection_count}")
        
        # Chat threads
        cur.execute("SELECT COUNT(*) as count FROM chat_threads")
        thread_count = cur.fetchone()['count']
        print(f"   Chat Threads: {thread_count}")
        
        # Check indexes
        print("\n5. Checking indexes...")
        cur.execute("""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            AND tablename = 'users'
        """)
        indexes = [row['indexname'] for row in cur.fetchall()]
        print(f"   User table indexes: {indexes}")
        
        # Check foreign keys
        print("\n6. Checking foreign key constraints...")
        cur.execute("""
            SELECT
                tc.table_name, 
                kcu.column_name, 
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
            LIMIT 10
        """)
        fks = cur.fetchall()
        print(f"   Found {len(fks)} foreign key constraints (showing first 10)")
        
        # Test a query
        print("\n7. Testing sample queries...")
        
        # Test user query
        cur.execute("SELECT id, email, username, oauth_provider FROM users LIMIT 1")
        sample_user = cur.fetchone()
        if sample_user:
            print(f"   ✅ Sample user query works: {sample_user}")
        else:
            print("   ⚠️  No users found (this is OK if database is empty)")
        
        # Test game query
        cur.execute("SELECT id, name FROM games LIMIT 1")
        sample_game = cur.fetchone()
        if sample_game:
            print(f"   ✅ Sample game query works: {sample_game}")
        else:
            print("   ⚠️  No games found (this is OK if database is empty)")
        
        cur.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Verification Complete!")
        print("=" * 60)
        print("\nYour PostgreSQL database is ready to use.")
        print("Update your .env file with:")
        print(f"  DB_TYPE=postgres")
        print(f"  DATABASE_URL={postgres_url}")
        print("\nThen restart your backend server.")
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed: {e}")
        print("\nPlease check:")
        print("  - PostgreSQL server is running")
        print("  - Connection string is correct")
        print("  - Database exists")
        print("  - User has proper permissions")
        return False
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    parser = argparse.ArgumentParser(description="Verify PostgreSQL connection and schema")
    parser.add_argument("--postgres-url", required=True, help="PostgreSQL connection URL")
    args = parser.parse_args()
    
    success = verify_connection(args.postgres_url)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
