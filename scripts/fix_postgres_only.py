#!/usr/bin/env python3
"""
Script to replace all SQLite references with PostgreSQL-only code in main.py
Run this after manual review to complete the migration.
"""
import re

def fix_main_py():
    """Replace SQLite patterns with PostgreSQL-only code."""
    file_path = "backend/main.py"

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace ? with %s in queries (PostgreSQL uses %s)
    # But be careful - only replace in SQL query strings
    # Pattern: query = "... ? ..." -> query = "... %s ..."
    content = re.sub(r'query\s*=\s*"([^"]*)\?"', r'query = "\1%s"', content)
    content = re.sub(r"query\s*=\s*'([^']*)\?'", r"query = '\1%s'", content)

    # Remove DB_TYPE checks - always use PostgreSQL
    content = re.sub(r'\s*if\s+DB_TYPE\s*==\s*["\']postgres["\']:\s*\n\s*query\s*=\s*query\.replace\(["\']\?["\'],\s*["\']%s["\']\)', '', content)

    # Remove SQLite-specific error handling
    content = re.sub(r',\s*sqlite3\.Error', '', content)
    content = re.sub(r'except\s+sqlite3\.Error', 'except psycopg2.Error', content)

    # Remove SQLite migration code blocks
    # This is complex and should be done manually

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Updated {file_path}")
    print("NOTE: Review the file manually - some complex patterns may need manual fixes")

if __name__ == '__main__':
    fix_main_py()
