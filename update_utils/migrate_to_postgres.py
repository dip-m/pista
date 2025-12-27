#!/usr/bin/env python3
"""
Migration script to migrate data from SQLite to PostgreSQL.
Run this script to migrate your existing SQLite database to PostgreSQL.

Usage:
    python update_utils/migrate_to_postgres.py --sqlite-db gen/bgg_semantic.db --postgres-url postgresql://user:pass@host:5432/dbname
"""

import argparse
import sqlite3
import psycopg2
import psycopg2.errors
import sys
from psycopg2.extras import execute_values
from typing import List, Tuple, Any

def migrate_table(sqlite_conn: sqlite3.Connection, pg_conn: psycopg2.extensions.connection,
                  table_name: str, columns: List[str], batch_size: int = 1000,
                  skip_foreign_key_errors: bool = True):
    """Migrate a single table from SQLite to PostgreSQL."""
    print(f"Migrating table: {table_name}")

    # Read from SQLite
    sqlite_cur = sqlite_conn.execute(f"SELECT {', '.join(columns)} FROM {table_name}")

    # Get all rows
    rows = sqlite_cur.fetchall()
    total_rows = len(rows)

    if total_rows == 0:
        print(f"  Table {table_name} is empty, skipping")
        return

    print(f"  Migrating {total_rows} rows...")

    # Identify boolean columns (SQLite stores as integers, PostgreSQL expects booleans)
    boolean_columns = {'is_active', 'is_admin'}  # Add more boolean column names as needed
    boolean_indices = [i for i, col in enumerate(columns) if col in boolean_columns]

    # Convert boolean values from SQLite (int) to PostgreSQL (bool)
    def convert_row(row):
        row_list = list(row)
        for idx in boolean_indices:
            if row_list[idx] is not None:
                # Convert 0/1 to False/True
                row_list[idx] = bool(row_list[idx]) if isinstance(row_list[idx], int) else row_list[idx]
        return tuple(row_list)

    # Insert into PostgreSQL
    pg_cur = pg_conn.cursor()
    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    inserted_count = 0
    skipped_count = 0
    error_count = 0

    # Insert rows one by one to handle foreign key violations gracefully
    # When skipping FK errors, commit after each insert to avoid rollback issues
    commit_each = skip_foreign_key_errors

    for i, row in enumerate(rows):
        try:
            # Convert row data (especially booleans)
            converted_row = convert_row(row)
            pg_cur.execute(insert_sql, converted_row)
            inserted_count += 1
            if commit_each:
                pg_conn.commit()
            elif (i + 1) % batch_size == 0 or (i + 1) == total_rows:
                pg_conn.commit()

            if (i + 1) % batch_size == 0:
                print(f"  Processed {i + 1}/{total_rows} rows (inserted: {inserted_count}, skipped: {skipped_count}, errors: {error_count})")
        except (psycopg2.errors.ForeignKeyViolation, psycopg2.IntegrityError) as e:
            error_str = str(e).lower()
            if "foreign key" in error_str and skip_foreign_key_errors:
                skipped_count += 1
                # Rollback the failed insert and reset transaction
                try:
                    pg_conn.rollback()
                except:
                    pass  # If already rolled back, that's fine
            else:
                # For other integrity errors, rollback and continue
                try:
                    pg_conn.rollback()
                except:
                    pass
                if not skip_foreign_key_errors:
                    raise
        except psycopg2.errors.InFailedSqlTransaction as e:
            # Transaction is already aborted, rollback and continue
            error_count += 1
            try:
                pg_conn.rollback()
            except:
                pass
        except Exception as e:
            error_count += 1
            error_str = str(e).lower()
            # Check if it's a transaction abort error
            if "current transaction is aborted" in error_str:
                try:
                    pg_conn.rollback()
                except:
                    pass
            else:
                print(f"  Warning: Error inserting row {i + 1}: {e}")
                try:
                    pg_conn.rollback()
                except:
                    pass

    # Final commit if not committing each
    if not commit_each:
        try:
            pg_conn.commit()
        except:
            pg_conn.rollback()
    pg_cur.close()

    print(f"  Completed {table_name}: {inserted_count} inserted, {skipped_count} skipped (FK violations), {error_count} errors")

def main():
    parser = argparse.ArgumentParser(description="Migrate SQLite database to PostgreSQL")
    parser.add_argument("--sqlite-db", required=True, help="Path to SQLite database")
    parser.add_argument("--postgres-url", required=True, help="PostgreSQL connection URL")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts")
    args = parser.parse_args()

    # Connect to databases
    print("Connecting to SQLite database...")
    sqlite_conn = sqlite3.connect(args.sqlite_db)

    print("Connecting to PostgreSQL database...")
    pg_conn = psycopg2.connect(args.postgres_url)
    pg_conn.autocommit = False

    try:
        # Ensure PostgreSQL schema exists
        print("Ensuring PostgreSQL schema exists...")
        import os
        schema_path = os.path.join(os.path.dirname(__file__), "schema_postgres.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()

        # Execute schema creation
        # Use autocommit mode to avoid transaction abort issues
        old_autocommit = pg_conn.autocommit
        pg_conn.autocommit = True
        pg_cur = pg_conn.cursor()

        # Split SQL into statements by semicolon
        # Remove inline comments (-- to end of line) and clean up
        import re
        # Remove comments (-- to end of line)
        sql_no_comments = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        # Split by semicolon and clean up
        statements = [s.strip() for s in sql_no_comments.split(';') if s.strip()]

        for i, statement in enumerate(statements, 1):
            try:
                pg_cur.execute(statement)
            except Exception as e:
                error_str = str(e).lower()
                # Ignore "already exists" errors for tables, indexes, constraints
                if "already exists" not in error_str and "duplicate" not in error_str:
                    print(f"  Error executing statement {i}: {e}")
                    print(f"  Statement: {statement[:150]}...")
                    # Don't fail completely, but log the error

        pg_cur.close()
        pg_conn.autocommit = old_autocommit
        print("Schema ensured")

        # Verify key tables exist
        pg_cur = pg_conn.cursor()
        required_tables = ['games', 'users', 'mechanics', 'categories']
        missing_tables = []

        for table_name in required_tables:
            pg_cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """, (table_name,))
            table_exists = pg_cur.fetchone()[0]
            if not table_exists:
                missing_tables.append(table_name)

        pg_cur.close()

        if missing_tables:
            raise Exception(f"Required tables were not created: {', '.join(missing_tables)}. Please check schema_postgres.sql and database permissions.")

        # Tables to migrate (in order due to foreign keys)
        tables = [
            ("games", ["id", "name", "description", "year_published", "min_players", "max_players",
                      "playing_time", "min_playtime", "max_playtime", "min_age", "thumbnail", "image",
                      "average_rating", "bayes_rating", "avg_weight", "num_ratings", "num_comments",
                      "ranks_json", "polls_json"]),
            ("mechanics", ["id", "name"]),
            ("categories", ["id", "name"]),
            ("families", ["id", "name"]),
            ("designers", ["id", "name"]),
            ("artists", ["id", "name"]),
            ("publishers", ["id", "name"]),
            ("game_mechanics", ["game_id", "mechanic_id"]),
            ("game_categories", ["game_id", "category_id"]),
            ("game_families", ["game_id", "family_id"]),
            ("game_designers", ["game_id", "designer_id"]),
            ("game_artists", ["game_id", "artist_id"]),
            ("game_publishers", ["game_id", "publisher_id"]),
            ("game_profiles", ["game_id", "profile_text"]),
            ("game_embeddings", ["game_id", "vector_json", "dim", "model_name"]),
        ]

        # Migrate main tables first
        print("\nMigrating main tables...")
        for table_name, columns in tables:
            try:
                migrate_table(sqlite_conn, pg_conn, table_name, columns, args.batch_size)
            except Exception as e:
                print(f"  Error migrating {table_name}: {e}")
                continue

        # Migrate user-related tables (may need special handling for OAuth columns)
        print("\nMigrating user tables (with OAuth migration)...")

        # Migrate users - handle both old and new OAuth schema
        print("Checking users table schema...")
        sqlite_cur = sqlite_conn.execute("PRAGMA table_info(users)")
        user_columns = {row[1]: row[2] for row in sqlite_cur.fetchall()}

        # Determine which columns exist
        has_email = 'email' in user_columns
        has_oauth_provider = 'oauth_provider' in user_columns

        if has_email and has_oauth_provider:
            # Already migrated to OAuth schema
            print("Users table already has OAuth schema, migrating directly...")
            sqlite_cur = sqlite_conn.execute("""
                SELECT id, email, username, oauth_provider, oauth_id, password_hash, bgg_id, is_admin, created_at
                FROM users
            """)
        else:
            # Old schema - need to convert
            print("Users table has old schema, converting to OAuth format...")
            sqlite_cur = sqlite_conn.execute("SELECT id, username, password_hash, bgg_id, is_admin, created_at FROM users")

        users = sqlite_cur.fetchall()

        if users:
            print(f"Migrating {len(users)} users...")
            pg_cur = pg_conn.cursor()

            for user in users:
                if has_email and has_oauth_provider:
                    # New OAuth schema
                    user_id, email, username, oauth_provider, oauth_id, password_hash, bgg_id, is_admin, created_at = user
                else:
                    # Old schema - convert
                    user_id, username, password_hash, bgg_id, is_admin, created_at = user
                    email = username if "@" in str(username) else f"{username}@migrated.local"
                    oauth_provider = 'email'
                    oauth_id = None

                pg_cur.execute("""
                    INSERT INTO users (id, email, username, oauth_provider, oauth_id, password_hash, bgg_id, is_admin, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (user_id, email, username, oauth_provider, oauth_id, password_hash, bgg_id,
                      bool(is_admin) if is_admin else False, created_at))

            pg_conn.commit()
            pg_cur.close()
            print("Users migrated")

        # Migrate other user-related tables
        user_tables = [
            ("user_collections", ["user_id", "game_id", "added_at", "personal_rating"]),
            ("chat_threads", ["id", "user_id", "title", "created_at", "updated_at"]),
            ("chat_messages", ["id", "thread_id", "role", "message", "metadata", "created_at"]),
            ("feature_mods", ["id", "game_id", "feature_type", "feature_id", "action", "created_at"]),
            ("feedback_questions", ["id", "question_text", "question_type", "is_active", "created_at"]),
            ("feedback_question_options", ["id", "question_id", "option_text", "display_order", "created_at"]),
            ("user_feedback_responses", ["id", "user_id", "question_id", "option_id", "response", "context", "thread_id", "created_at"]),
            ("ab_test_configs", ["id", "config_key", "config_value", "is_active", "created_at", "updated_at"]),
        ]

        for table_name, columns in user_tables:
            try:
                migrate_table(sqlite_conn, pg_conn, table_name, columns, args.batch_size)
            except Exception as e:
                print(f"  Error migrating {table_name}: {e}")
                continue

        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    main()
