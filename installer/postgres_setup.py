"""
PostgreSQL/Neon database setup for Metadata Manager installer.

Handles:
- Database connectivity testing
- Alembic migrations
- User seeding
"""

import os
import subprocess
import sys
from typing import Tuple, List, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone


@dataclass
class MigrationResult:
    """Result of migration operation"""
    success: bool
    message: str
    current_revision: Optional[str] = None


class PostgresSetup:
    """Manages PostgreSQL database setup and migrations"""

    # Fixed UUIDs for seed users (consistent across re-seeds)
    SEED_USERS = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "email": "admin@example.com",
            "username": "admin",
            "full_name": "Admin User",
            "password": "admin123",
            "role": "ADMIN",
            "is_superuser": True,
        },
        {
            "id": "00000000-0000-0000-0000-000000000002",
            "email": "approver@example.com",
            "username": "approver",
            "full_name": "Approver User",
            "password": "approver123",
            "role": "APPROVER",
            "is_superuser": False,
        },
        {
            "id": "00000000-0000-0000-0000-000000000003",
            "email": "user@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "user123",
            "role": "SUGGEST_ONLY",
            "is_superuser": False,
        },
    ]

    def __init__(self, database_url: str, backend_path: str = None, verbose: bool = False):
        self.database_url = database_url
        self.backend_path = backend_path or str(Path(__file__).parent.parent / "backend")
        self.verbose = verbose
        self._engine = None

    def get_engine(self):
        """Get or create SQLAlchemy engine"""
        if self._engine is None:
            from sqlalchemy import create_engine
            from sqlalchemy.pool import NullPool

            self._engine = create_engine(
                self.database_url,
                poolclass=NullPool,
                connect_args={"connect_timeout": 10}
            )
        return self._engine

    def test_connection(self) -> Tuple[bool, str]:
        """Test database connectivity"""
        try:
            from sqlalchemy import text

            engine = self.get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            return True, "Connected to PostgreSQL successfully"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def get_current_revision(self) -> Optional[str]:
        """Get current Alembic revision"""
        try:
            from sqlalchemy import text

            engine = self.get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def run_migrations(self) -> MigrationResult:
        """Run Alembic migrations"""
        alembic_dir = Path(self.backend_path) / "alembic"

        if not alembic_dir.exists():
            return MigrationResult(
                success=False,
                message=f"Alembic directory not found: {alembic_dir}"
            )

        try:
            # Set DATABASE_URL environment variable for Alembic
            env = os.environ.copy()
            env["DATABASE_URL"] = self.database_url

            # Run alembic upgrade head
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd=self.backend_path,
                env=env,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                return MigrationResult(
                    success=False,
                    message=f"Migration failed: {result.stderr}"
                )

            current_rev = self.get_current_revision()
            return MigrationResult(
                success=True,
                message="Migrations completed successfully",
                current_revision=current_rev
            )

        except subprocess.TimeoutExpired:
            return MigrationResult(
                success=False,
                message="Migration timed out"
            )
        except Exception as e:
            return MigrationResult(
                success=False,
                message=f"Migration error: {str(e)}"
            )

    def verify_tables_exist(self) -> Tuple[bool, List[str]]:
        """Verify required tables exist"""
        required_tables = ["users", "comments", "approvals", "audit_logs"]
        missing = []

        try:
            from sqlalchemy import text

            engine = self.get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public'
                """))
                existing = [row[0] for row in result.fetchall()]

            for table in required_tables:
                if table not in existing:
                    missing.append(table)

            return len(missing) == 0, missing

        except Exception as e:
            return False, [f"Error: {str(e)}"]

    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return pwd_context.hash(password)
        except ImportError:
            # Fallback if passlib not available in this context
            import bcrypt
            return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def seed_users(self, force: bool = False) -> Tuple[bool, str]:
        """Seed initial users into the database"""
        try:
            from sqlalchemy import text

            engine = self.get_engine()
            with engine.connect() as conn:
                # Check if users already exist
                result = conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()

                if user_count > 0 and not force:
                    return True, f"Users table already has {user_count} records (skipped)"

                if user_count > 0 and force:
                    # Delete existing users for re-seed
                    conn.execute(text("DELETE FROM users"))
                    conn.commit()

                # Insert seed users
                for user in self.SEED_USERS:
                    hashed_password = self.hash_password(user["password"])
                    now = datetime.now(timezone.utc)

                    conn.execute(text("""
                        INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
                        VALUES (:id, :email, :username, :full_name, :hashed_password, :role, :is_active, :is_superuser, :created_at, :updated_at)
                    """), {
                        "id": user["id"],
                        "email": user["email"],
                        "username": user["username"],
                        "full_name": user["full_name"],
                        "hashed_password": hashed_password,
                        "role": user["role"],
                        "is_active": True,
                        "is_superuser": user["is_superuser"],
                        "created_at": now,
                        "updated_at": now,
                    })

                conn.commit()

            return True, f"Seeded {len(self.SEED_USERS)} users"

        except Exception as e:
            return False, f"Seeding failed: {str(e)}"

    def setup_database(
        self,
        run_migrations: bool = True,
        seed_data: bool = True,
        dry_run: bool = False
    ) -> Tuple[bool, List[str]]:
        """
        Complete database setup.

        Returns:
            Tuple of (success, list of messages)
        """
        messages = []

        if dry_run:
            messages.append("[DRY RUN] Would test database connection")
            messages.append("[DRY RUN] Would run Alembic migrations")
            messages.append("[DRY RUN] Would seed initial users")
            return True, messages

        # Test connection
        success, msg = self.test_connection()
        messages.append(msg)
        if not success:
            return False, messages

        # Run migrations
        if run_migrations:
            result = self.run_migrations()
            messages.append(result.message)
            if result.current_revision:
                messages.append(f"Current revision: {result.current_revision}")
            if not result.success:
                return False, messages

        # Verify tables
        tables_ok, missing = self.verify_tables_exist()
        if not tables_ok:
            messages.append(f"Missing tables: {', '.join(missing)}")
            return False, messages
        messages.append("All required tables exist")

        # Seed users
        if seed_data:
            success, msg = self.seed_users()
            messages.append(msg)
            if not success:
                return False, messages

        return True, messages

    def get_user_credentials(self) -> List[dict]:
        """Get list of seed user credentials for display"""
        return [
            {"email": u["email"], "password": u["password"], "role": u["role"]}
            for u in self.SEED_USERS
        ]

    def dispose(self):
        """Dispose of database engine"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
