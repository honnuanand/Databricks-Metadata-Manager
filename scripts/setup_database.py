#!/usr/bin/env python3
"""
Database Setup Script for Metadata Manager
Sets up Neon database, runs migrations, and seeds initial data
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a shell command and return success status"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running command: {e}", file=sys.stderr)
        return False

def main():
    print("🗄️  Metadata Manager - Database Setup")
    print("=" * 60)

    # Get database URL
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("\n❌ DATABASE_URL environment variable not set!")
        print("\nPlease set it with your Neon connection string:")
        print('  export DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"')
        print("\nOr provide it as an argument:")
        print('  python3 setup_database.py "postgresql://..."')

        if len(sys.argv) > 1:
            db_url = sys.argv[1]
        else:
            return 1

    os.environ['DATABASE_URL'] = db_url
    print(f"✅ Database URL configured: {db_url[:30]}...")

    backend_dir = Path(__file__).parent / "backend"

    # Step 1: Generate migration if needed
    print("\n📝 Step 1: Checking for existing migrations...")
    versions_dir = backend_dir / "alembic" / "versions"
    migration_files = list(versions_dir.glob("*.py"))

    if not migration_files or input("\n🔄 Generate new migration? (y/N): ").lower() == 'y':
        print("Generating migration from models...")
        if run_command(
            f'cd backend && alembic revision --autogenerate -m "Initial schema"',
            cwd=backend_dir.parent
        ):
            print("✅ Migration generated successfully")
        else:
            print("⚠️  Migration generation failed or no changes detected")
    else:
        print(f"✅ Found {len(migration_files)} existing migration(s)")

    # Step 2: Run migrations
    print("\n🔄 Step 2: Running migrations...")
    if run_command("alembic upgrade head", cwd=backend_dir):
        print("✅ Migrations applied successfully")
    else:
        print("❌ Migration failed!")
        return 1

    # Step 3: Seed initial data (optional)
    print("\n🌱 Step 3: Seed initial data?")
    if input("Seed test users and sample comments? (Y/n): ").lower() != 'n':
        print("Seeding database...")
        seed_script = backend_dir / "seed_database.py"
        if seed_script.exists():
            if run_command(f"python3 {seed_script}", cwd=backend_dir.parent):
                print("✅ Database seeded successfully")
            else:
                print("⚠️  Seeding failed or script not found")
        else:
            print("⚠️  Seed script not found - skipping")

    # Step 4: Verify tables
    print("\n✅ Step 4: Verifying database setup...")
    verify_cmd = f"""python3 -c "
import sys
sys.path.insert(0, 'backend')
from sqlalchemy import create_engine, inspect
engine = create_engine('{db_url}')
inspector = inspect(engine)
tables = inspector.get_table_names()
print(f'📊 Found {{len(tables)}} tables: {{tables}}')
if len(tables) > 0:
    print('✅ Database is ready!')
else:
    print('⚠️  No tables found')
"
"""
    run_command(verify_cmd, cwd=backend_dir.parent)

    print("\n🎉 Database setup complete!")
    print("\n📋 Next steps:")
    print("  1. Add DATABASE_URL to Databricks secrets:")
    print(f'     databricks secrets put-secret metadata-manager-secrets database-url --string-value "{db_url}"')
    print("  2. Deploy the application:")
    print("     python3 deploy_to_databricks.py --skip-secrets --hard-redeploy")

    return 0

if __name__ == "__main__":
    sys.exit(main())
