#!/usr/bin/env python3
"""
Database synchronization script: Sync local PostgreSQL database with production.

This script:
1. Connects to production database
2. Exports data (excluding sensitive info if needed)
3. Imports into local database
4. Can be run manually or scheduled via cron

Usage:
    python scripts/sync_db_production.py --dry-run
    python scripts/sync_db_production.py --full-sync
    python scripts/sync_db_production.py --tables games,users --incremental
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    print("ERROR: psycopg2-binary is required. Install with: pip install psycopg2-binary")
    sys.exit(1)


def get_db_connection(database_url):
    """Create a database connection."""
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"ERROR: Failed to connect to database: {e}")
        sys.exit(1)


def export_table_data(conn, table_name, output_file=None):
    """Export data from a table."""
    cur = conn.cursor()

    # Get column names
    cur.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))

    columns = [row[0] for row in cur.fetchall()]

    # Get data
    cur.execute(f"SELECT * FROM {table_name}")
    rows = cur.fetchall()

    if output_file:
        import csv
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)
        print(f"Exported {len(rows)} rows from {table_name} to {output_file}")

    return columns, rows


def import_table_data(conn, table_name, columns, rows, truncate=False):
    """Import data into a table."""
    cur = conn.cursor()

    if truncate:
        cur.execute(f"TRUNCATE TABLE {table_name} CASCADE")
        print(f"Truncated {table_name}")

    if not rows:
        print(f"No data to import for {table_name}")
        return

    # Build INSERT statement
    placeholders = ','.join(['%s'] * len(columns))
    columns_str = ','.join(columns)

    query = f"""
        INSERT INTO {table_name} ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT DO NOTHING
    """

    execute_values(cur, query, rows)
    conn.commit()

    print(f"Imported {len(rows)} rows into {table_name}")


def sync_table(prod_conn, local_conn, table_name, incremental=False):
    """Sync a single table from production to local."""
    print(f"\n{'='*60}")
    print(f"Syncing table: {table_name}")
    print(f"{'='*60}")

    # Export from production
    columns, rows = export_table_data(prod_conn, table_name)

    if incremental:
        # For incremental sync, only sync recent records
        # This is a simplified version - adjust based on your schema
        if 'created_at' in columns or 'updated_at' in columns:
            # Filter by date (last 7 days)
            date_col = 'updated_at' if 'updated_at' in columns else 'created_at'
            date_idx = columns.index(date_col)

            cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            from datetime import timedelta
            cutoff_date -= timedelta(days=7)

            rows = [row for row in rows if row[date_idx] and row[date_idx] >= cutoff_date]
            print(f"Filtered to {len(rows)} recent rows (last 7 days)")

    # Import to local
    import_table_data(local_conn, table_name, columns, rows, truncate=not incremental)

    print(f"✓ Completed sync for {table_name}")


def main():
    parser = argparse.ArgumentParser(description='Sync local PostgreSQL database with production')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be synced without actually syncing')
    parser.add_argument('--full-sync', action='store_true', help='Sync all tables (full sync)')
    parser.add_argument('--tables', type=str, help='Comma-separated list of tables to sync (e.g., games,users)')
    parser.add_argument('--incremental', action='store_true', help='Only sync recent records (last 7 days)')
    parser.add_argument('--prod-url', type=str, help='Production database URL (overrides PROD_DATABASE_URL env var)')
    parser.add_argument('--local-url', type=str, help='Local database URL (overrides DATABASE_URL env var)')

    args = parser.parse_args()

    # Get database URLs
    prod_url = args.prod_url or os.getenv('PROD_DATABASE_URL')
    local_url = args.local_url or os.getenv('DATABASE_URL')

    if not prod_url:
        print("ERROR: Production database URL not provided.")
        print("Set PROD_DATABASE_URL environment variable or use --prod-url")
        sys.exit(1)

    if not local_url:
        print("ERROR: Local database URL not provided.")
        print("Set DATABASE_URL environment variable or use --local-url")
        sys.exit(1)

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        print(f"Production URL: {prod_url[:20]}...")
        print(f"Local URL: {local_url[:20]}...")
        return

    # Connect to databases
    print("Connecting to production database...")
    prod_conn = get_db_connection(prod_url)

    print("Connecting to local database...")
    local_conn = get_db_connection(local_url)

    try:
        # Get list of tables
        cur = prod_conn.cursor()
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        all_tables = [row[0] for row in cur.fetchall()]

        # Determine which tables to sync
        if args.full_sync:
            tables_to_sync = all_tables
        elif args.tables:
            tables_to_sync = [t.strip() for t in args.tables.split(',')]
            # Validate tables exist
            invalid_tables = [t for t in tables_to_sync if t not in all_tables]
            if invalid_tables:
                print(f"WARNING: Tables not found: {', '.join(invalid_tables)}")
                tables_to_sync = [t for t in tables_to_sync if t in all_tables]
        else:
            # Default: sync common tables
            default_tables = ['games', 'users', 'game_features', 'user_collections']
            tables_to_sync = [t for t in default_tables if t in all_tables]

        print(f"\nTables to sync: {', '.join(tables_to_sync)}")
        print(f"Mode: {'Incremental' if args.incremental else 'Full'}")

        # Sync each table
        for table in tables_to_sync:
            try:
                sync_table(prod_conn, local_conn, table, incremental=args.incremental)
            except Exception as e:
                print(f"ERROR: Failed to sync {table}: {e}")
                continue

        print(f"\n{'='*60}")
        print("✓ Database sync completed!")
        print(f"{'='*60}")

    finally:
        prod_conn.close()
        local_conn.close()


if __name__ == '__main__':
    main()
