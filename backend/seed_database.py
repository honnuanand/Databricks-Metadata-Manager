#!/usr/bin/env python3
"""
Seed Database Script for Metadata Manager
Creates initial admin user and sample data
"""

import sys
import os
from datetime import datetime, timezone
from uuid import uuid4

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from app.core.security import get_password_hash

def hash_password(password: str) -> str:
    return get_password_hash(password)

def seed_database(database_url: str):
    """Seed the database with initial data"""

    print("🌱 Seeding Metadata Manager Database")
    print("=" * 60)

    engine = create_engine(database_url)

    with engine.connect() as conn:
        # Check if users already exist
        result = conn.execute(text("SELECT COUNT(*) FROM users"))
        user_count = result.scalar()

        if user_count > 0:
            print(f"⚠️  Database already has {user_count} users.")
            print("🔄 Deleting existing users to re-seed with fixed UUIDs...")
            conn.execute(text("DELETE FROM users"))
            conn.commit()
            print("✅ Existing users deleted")

        print("👤 Creating admin user...")

        # Create admin user with FIXED UUID (consistent across re-seeds)
        admin_id = "00000000-0000-0000-0000-000000000001"
        admin_password = hash_password("admin123")

        conn.execute(text("""
            INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
            VALUES (:id, :email, :username, :full_name, :hashed_password, :role, :is_active, :is_superuser, :created_at, :updated_at)
        """), {
            "id": admin_id,
            "email": "admin@example.com",
            "username": "admin",
            "full_name": "Admin User",
            "hashed_password": admin_password,
            "role": "ADMIN",
            "is_active": True,
            "is_superuser": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        print("✅ Admin user created:")
        print("   Email: admin@example.com")
        print("   Username: admin")
        print("   Password: admin123")

        # Create an approver user with FIXED UUID
        print("\n👤 Creating approver user...")
        approver_id = "00000000-0000-0000-0000-000000000002"
        approver_password = hash_password("approver123")

        conn.execute(text("""
            INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
            VALUES (:id, :email, :username, :full_name, :hashed_password, :role, :is_active, :is_superuser, :created_at, :updated_at)
        """), {
            "id": approver_id,
            "email": "approver@example.com",
            "username": "approver",
            "full_name": "Approver User",
            "hashed_password": approver_password,
            "role": "APPROVER",
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        print("✅ Approver user created:")
        print("   Email: approver@example.com")
        print("   Username: approver")
        print("   Password: approver123")

        # Create a regular user with FIXED UUID
        print("\n👤 Creating regular user...")
        user_id = "00000000-0000-0000-0000-000000000003"
        user_password = hash_password("user123")

        conn.execute(text("""
            INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
            VALUES (:id, :email, :username, :full_name, :hashed_password, :role, :is_active, :is_superuser, :created_at, :updated_at)
        """), {
            "id": user_id,
            "email": "user@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "hashed_password": user_password,
            "role": "SUGGEST_ONLY",
            "is_active": True,
            "is_superuser": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        print("✅ Regular user created:")
        print("   Email: user@example.com")
        print("   Username: testuser")
        print("   Password: user123")

        conn.commit()

        print("\n🎉 Database seeded successfully!")
        print("\n📋 Login Credentials:")
        print("   Admin:    admin@example.com / admin123")
        print("   Approver: approver@example.com / approver123")
        print("   User:     user@example.com / user123")

if __name__ == "__main__":
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ DATABASE_URL environment variable not set!")
        print("Usage: DATABASE_URL='postgresql://...' python seed_database.py")
        sys.exit(1)

    seed_database(database_url)
