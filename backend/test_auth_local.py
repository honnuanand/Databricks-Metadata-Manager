#!/usr/bin/env python3
"""
Local Authentication Test Script
Tests the authentication flow without Databricks SSO
"""

import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Set environment variables
os.environ['DATABASE_URL'] = 'postgresql://neondb_owner:npg_SaRbXP4x6wtj@ep-lively-mud-a4u1i94u.us-east-1.aws.neon.tech/neondb?sslmode=require'
os.environ['SECRET_KEY'] = 'LrM0Shhrw0MhIzRtQhbUF30o4dTjE4d5m6PRDZhGUPM'

from app.services.auth_service import auth_service

async def test_authentication():
    """Test authentication with all seeded users"""

    print("=" * 70)
    print("AUTHENTICATION TEST - Neon Database")
    print("=" * 70)

    test_users = [
        {"email": "admin@example.com", "password": "admin123", "role": "admin"},
        {"email": "approver@example.com", "password": "approver123", "role": "approver"},
        {"email": "user@example.com", "password": "user123", "role": "suggest_only"},
    ]

    for user_data in test_users:
        print(f"\n{'='*70}")
        print(f"Testing: {user_data['email']}")
        print(f"{'='*70}")

        # Test authentication
        result = await auth_service.login(user_data['email'], user_data['password'])

        if result:
            print(f"✅ LOGIN SUCCESSFUL")
            print(f"   User ID: {result['user']['user_id']}")
            print(f"   Username: {result['user']['username']}")
            print(f"   Email: {result['user']['email']}")
            print(f"   Role: {result['user']['role']}")
            print(f"   Expected Role: {user_data['role']}")
            print(f"   Role Match: {'✅ YES' if result['user']['role'] == user_data['role'] else '❌ NO'}")
            print(f"   Access Token: {result['access_token'][:50]}...")
            print(f"   Token Type: {result['token_type']}")
            print(f"   Expires In: {result['expires_in']} seconds")
            print(f"\n   Permissions:")
            for perm, value in result['user']['permissions'].items():
                if value:
                    print(f"      ✓ {perm}")
        else:
            print(f"❌ LOGIN FAILED")
            print(f"   Could not authenticate user")

        # Test with wrong password
        print(f"\n   Testing wrong password...")
        wrong_result = await auth_service.login(user_data['email'], "wrongpassword")
        if not wrong_result:
            print(f"   ✅ Correctly rejected invalid password")
        else:
            print(f"   ❌ ERROR: Accepted invalid password!")

    print(f"\n{'='*70}")
    print("TEST COMPLETE")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    asyncio.run(test_authentication())
