#!/usr/bin/env python3
"""
Test script to verify Supabase PostgreSQL connection.
"""

import psycopg2
import sys

# In update_utils/test_supabase_connection.py, change line 9 to:
CONNECTION_STRING = "postgresql://postgres.azejopggiscyfjyaiosi:Pista_01123@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"
print("Testing Supabase connection...")
print(f"Connection string: postgresql://postgres:***@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres")

try:
    print("\n1. Attempting connection...")
    conn = psycopg2.connect(CONNECTION_STRING)
    print("   ✅ Connection successful!")
    
    print("\n2. Testing query...")
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"   ✅ PostgreSQL version: {version[:50]}...")
    
    print("\n3. Checking database...")
    cur.execute("SELECT current_database();")
    db_name = cur.fetchone()[0]
    print(f"   ✅ Connected to database: {db_name}")
    
    print("\n4. Checking tables...")
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
        LIMIT 10
    """)
    tables = cur.fetchall()
    if tables:
        print(f"   ✅ Found {len(tables)} tables:")
        for table in tables:
            print(f"      - {table[0]}")
    else:
        print("   ℹ️  No tables found (database is empty)")
    
    cur.close()
    conn.close()
    
    print("\n[SUCCESS] All tests passed! Supabase connection is working.")
    print("\nYou can now run the migration:")
    print('python update_utils/migrate_to_postgres.py --sqlite-db gen/bgg_semantic.db --postgres-url "postgresql://postgres:Pista_01123@db.azejopggiscyfjyaiosi.supabase.co:5432/postgres"')
    sys.exit(0)
    
except psycopg2.OperationalError as e:
    print(f"\n❌ Connection failed: {e}")
    print("\nTroubleshooting:")
    print("1. Check your internet connection")
    print("2. Verify the Supabase project is active (not paused)")
    print("3. Check if the hostname is correct in Supabase dashboard")
    print("4. Verify firewall/network settings allow outbound connections")
    print("5. Try accessing Supabase dashboard to verify project status")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
