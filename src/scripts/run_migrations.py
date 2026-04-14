#!/usr/bin/env python3
"""
run_migrations.py — Apply SQL migrations to Supabase.

Usage:
    # Via psql (recommended — needs DATABASE_URL)
    python scripts/run_migrations.py --psql

    # Via Supabase Python client (needs SUPABASE_URL + SUPABASE_SERVICE_KEY)
    python scripts/run_migrations.py --supabase

    # Preview SQL without executing
    python scripts/run_migrations.py --dry-run

    # Single file
    python scripts/run_migrations.py --psql --file sql/sources.sql

DATABASE_URL format:
    postgresql://postgres.[project-ref]:[password]@aws-0-eu-west-2.pooler.supabase.com:6543/postgres

Or set individual vars:
    SUPABASE_URL=https://nxlerszckdzvilqxwjfj.supabase.co
    SUPABASE_SERVICE_KEY=eyJ...
"""

import os
import subprocess
import sys
from pathlib import Path

# Order matters: FKs require referenced tables to exist first
MIGRATION_ORDER = [
    "sql/sources.sql",
    "sql/lex_provisions.sql",
    "sql/legal_nodes.sql",
    "sql/area_metrics.sql",
    "sql/citizen_actions.sql",
]

ROOT = Path(__file__).parent.parent


def run_psql(sql_file: Path, database_url: str) -> bool:
    """Execute a SQL file via psql."""
    try:
        result = subprocess.run(
            ["psql", database_url, "-f", str(sql_file), "--set", "ON_ERROR_STOP=on"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            # Count statements executed (rough)
            lines = result.stdout.strip().split("\n") if result.stdout else []
            print(f"    OK ({len(lines)} output lines)")
            return True
        else:
            print(f"    ERROR: {result.stderr[:300]}")
            return False
    except FileNotFoundError:
        print("    ERROR: psql not found. Install postgresql-client.")
        return False
    except subprocess.TimeoutExpired:
        print("    ERROR: psql timed out")
        return False


def run_supabase(sql_file: Path, url: str, key: str) -> bool:
    """Execute SQL via Supabase Python client."""
    try:
        from supabase import create_client
    except ImportError:
        print("    ERROR: pip install supabase")
        return False

    client = create_client(url, key)
    sql = sql_file.read_text()

    # Split into statements and execute each
    # (Supabase rpc doesn't support multi-statement well)
    statements = [s.strip() for s in sql.split(";") if s.strip()
                  and not s.strip().startswith("--")]

    errors = 0
    for i, stmt in enumerate(statements):
        try:
            client.rpc("exec_sql", {"query": stmt + ";"}).execute()
        except Exception as e:
            err_str = str(e)
            # Ignore "already exists" errors (idempotent migrations)
            if "already exists" in err_str or "duplicate" in err_str.lower():
                continue
            print(f"    Statement {i+1} error: {err_str[:150]}")
            errors += 1

    if errors:
        print(f"    {errors} error(s)")
        return False
    print(f"    OK ({len(statements)} statements)")
    return True


def main():
    dry_run = "--dry-run" in sys.argv
    use_psql = "--psql" in sys.argv
    use_supabase = "--supabase" in sys.argv
    single_file = None

    for i, arg in enumerate(sys.argv):
        if arg == "--file" and i + 1 < len(sys.argv):
            single_file = sys.argv[i + 1]

    if not dry_run and not use_psql and not use_supabase:
        print("Specify --psql, --supabase, or --dry-run")
        print(__doc__)
        sys.exit(1)

    files = [single_file] if single_file else MIGRATION_ORDER

    print("BASIS SQL Migrations")
    print("=" * 60)

    # Resolve credentials
    database_url = os.environ.get("DATABASE_URL", "")
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

    if use_psql and not database_url:
        print("ERROR: Set DATABASE_URL env var")
        print("  postgresql://postgres.[ref]:[pw]@aws-0-eu-west-2.pooler.supabase.com:6543/postgres")
        sys.exit(1)

    if use_supabase and (not supabase_url or not supabase_key):
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars")
        sys.exit(1)

    ok_count = 0
    fail_count = 0

    for migration_path in files:
        full_path = ROOT / migration_path
        if not full_path.exists():
            print(f"\n  SKIP: {migration_path} (not found)")
            continue

        sql = full_path.read_text()
        stmt_count = sql.count(";")
        print(f"\n  Applying: {migration_path} ({stmt_count} statements)")

        if dry_run:
            preview = sql[:300].replace("\n", "\n    ")
            print(f"    {preview}...")
            ok_count += 1
            continue

        if use_psql:
            success = run_psql(full_path, database_url)
        else:
            success = run_supabase(full_path, supabase_url, supabase_key)

        if success:
            ok_count += 1
        else:
            fail_count += 1

    print(f"\n{'=' * 60}")
    print(f"Done: {ok_count} ok, {fail_count} failed")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
