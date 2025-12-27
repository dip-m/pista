#!/usr/bin/env python3
"""
Migration script to migrate data from one PostgreSQL database to another.
Run this script to migrate your existing PostgreSQL database to a new PostgreSQL instance (e.g., Supabase).

Usage:
    python update_utils/migrate_postgres_to_postgres.py --source-url postgresql://user:pass@host:5432/db --target-url postgresql://user:pass@host:5432/db
"""

import argparse
import psycopg2
import psycopg2.errors
import sys
from typing import List, Tuple, Any

def migrate_table(source_conn: psycopg2.extensions.connection,
                  target_conn: psycopg2.extensions.connection,
                  table_name: str, columns: List[str], batch_size: int = 1000,
                  skip_foreign_key_errors: bool = True):
    """Migrate a single table from source PostgreSQL to target PostgreSQL."""
    print(f"Migrating table: {table_name}")

    # Check if table already has data in target (safety check for reruns)
    target_cur = target_conn.cursor()
    try:
        target_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        target_count = target_cur.fetchone()[0]
    except Exception:
        # Table might not exist yet, that's okay
        target_count = 0
    target_cur.close()

    # Read from source PostgreSQL
    source_cur = source_conn.cursor()
    col_list = ", ".join(columns)
    source_cur.execute(f"SELECT {col_list} FROM {table_name}")

    # Get all rows
    rows = source_cur.fetchall()
    total_rows = len(rows)
    source_cur.close()

    if total_rows == 0:
        print(f"  Table {table_name} is empty in source, skipping")
        return

    # If target already has all rows (or more), skip migration
    if target_count >= total_rows:
        print(f"  Table {table_name} already migrated ({target_count} rows in target, {total_rows} in source), skipping")
        return
    elif target_count > 0:
        print(f"  Table {table_name} partially migrated ({target_count}/{total_rows} rows), continuing...")

    print(f"  Migrating {total_rows} rows...")

    # Insert into target PostgreSQL
    target_cur = target_conn.cursor()
    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    insert_sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

    inserted_count = 0
    skipped_count = 0
    error_count = 0

    # Insert rows one by one to handle foreign key violations gracefully
    commit_each = skip_foreign_key_errors

    for i, row in enumerate(rows):
        try:
            target_cur.execute(insert_sql, row)
            inserted_count += 1
            if commit_each:
                target_conn.commit()
            elif (i + 1) % batch_size == 0 or (i + 1) == total_rows:
                target_conn.commit()

            if (i + 1) % batch_size == 0:
                print(f"  Processed {i + 1}/{total_rows} rows (inserted: {inserted_count}, skipped: {skipped_count}, errors: {error_count})")
        except (psycopg2.errors.ForeignKeyViolation, psycopg2.IntegrityError) as e:
            error_str = str(e).lower()
            if "foreign key" in error_str and skip_foreign_key_errors:
                skipped_count += 1
                try:
                    target_conn.rollback()
                except:
                    pass
            else:
                try:
                    target_conn.rollback()
                except:
                    pass
                if not skip_foreign_key_errors:
                    raise
        except psycopg2.errors.InFailedSqlTransaction as e:
            error_count += 1
            try:
                target_conn.rollback()
            except:
                pass
        except Exception as e:
            error_count += 1
            error_str = str(e).lower()
            if "current transaction is aborted" in error_str:
                try:
                    target_conn.rollback()
                except:
                    pass
            else:
                print(f"  Warning: Error inserting row {i + 1}: {e}")
                try:
                    target_conn.rollback()
                except:
                    pass

    # Final commit if not committing each
    if not commit_each:
        try:
            target_conn.commit()
        except:
            target_conn.rollback()
    target_cur.close()

    print(f"  Completed {table_name}: {inserted_count} inserted, {skipped_count} skipped (FK violations), {error_count} errors")

def main():
    parser = argparse.ArgumentParser(description="Migrate PostgreSQL database to another PostgreSQL instance")
    parser.add_argument("--source-url", required=True, help="Source PostgreSQL connection URL")
    parser.add_argument("--target-url", required=True, help="Target PostgreSQL connection URL")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts")
    args = parser.parse_args()

    # Connect to databases
    print("Connecting to source PostgreSQL database...")
    source_conn = psycopg2.connect(args.source_url)
    source_conn.autocommit = False

    print("Connecting to target PostgreSQL database...")
    target_conn = psycopg2.connect(args.target_url)
    target_conn.autocommit = False

    try:
        # Ensure target PostgreSQL schema exists
        print("Ensuring target PostgreSQL schema exists...")
        import os
        schema_path = os.path.join(os.path.dirname(__file__), "schema_postgres.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            sql = f.read()

        # Execute schema creation
        old_autocommit = target_conn.autocommit
        target_conn.autocommit = True
        target_cur = target_conn.cursor()

        # Split SQL into statements by semicolon
        import re
        sql_no_comments = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        statements = [s.strip() for s in sql_no_comments.split(';') if s.strip()]

        for i, statement in enumerate(statements, 1):
            try:
                target_cur.execute(statement)
            except Exception as e:
                error_str = str(e).lower()
                if "already exists" not in error_str and "duplicate" not in error_str:
                    print(f"  Warning executing statement {i}: {e}")

        target_cur.close()
        target_conn.autocommit = old_autocommit
        print("Schema ensured")

        # Verify key tables exist
        target_cur = target_conn.cursor()
        required_tables = ['games', 'users', 'mechanics', 'categories']
        missing_tables = []

        for table_name in required_tables:
            target_cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """, (table_name,))
            table_exists = target_cur.fetchone()[0]
            if not table_exists:
                missing_tables.append(table_name)

        target_cur.close()

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
                migrate_table(source_conn, target_conn, table_name, columns, args.batch_size)
            except Exception as e:
                print(f"  Error migrating {table_name}: {e}")
                continue

        # Migrate user-related tables
        print("\nMigrating user tables...")

        # Migrate users
        print("Migrating users...")
        source_cur = source_conn.cursor()
        source_cur.execute("""
            SELECT id, email, username, oauth_provider, oauth_id, password_hash, bgg_id, is_admin, created_at
            FROM users
        """)
        users = source_cur.fetchall()
        source_cur.close()

        if users:
            print(f"Migrating {len(users)} users...")
            target_cur = target_conn.cursor()

            for user in users:
                user_id, email, username, oauth_provider, oauth_id, password_hash, bgg_id, is_admin, created_at = user
                target_cur.execute("""
                    INSERT INTO users (id, email, username, oauth_provider, oauth_id, password_hash, bgg_id, is_admin, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, (user_id, email, username, oauth_provider, oauth_id, password_hash, bgg_id,
                      bool(is_admin) if is_admin else False, created_at))

            target_conn.commit()
            target_cur.close()
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
                migrate_table(source_conn, target_conn, table_name, columns, args.batch_size)
            except Exception as e:
                print(f"  Error migrating {table_name}: {e}")
                continue

        # Fix sequences after migration
        print("\nFixing sequences...")
        target_cur = target_conn.cursor()
        sequences_to_fix = [
            'chat_threads_id_seq',
            'chat_messages_id_seq',
            'feature_mods_id_seq',
            'feedback_questions_id_seq',
            'feedback_question_options_id_seq',
            'user_feedback_responses_id_seq',
            'ab_test_configs_id_seq',
        ]

        for seq_name in sequences_to_fix:
            # Extract table name from sequence name
            table_name = seq_name.replace('_id_seq', '')
            try:
                target_cur.execute(f"""
                    SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1, false)
                """)
                target_conn.commit()
                print(f"  Fixed {seq_name}")
            except Exception as e:
                print(f"  Warning: Could not fix {seq_name}: {e}")
                target_conn.rollback()

        target_cur.close()

        print("\nMigration completed successfully!")

    except Exception as e:
        print(f"Migration failed: {e}", file=sys.stderr)
        target_conn.rollback()
        raise
    finally:
        source_conn.close()
        target_conn.close()

if __name__ == "__main__":
    main()
