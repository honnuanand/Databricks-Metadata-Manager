from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel
from app.services.auth_service import auth_service
from app.services.user_service import user_service
from app.api.dependencies.auth import get_current_active_user
from app.schemas.user import User
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Login and get access token"""
    try:
        result = await auth_service.login(login_data.username, login_data.password)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"User {login_data.username} logged in successfully")
        return LoginResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(refresh_data: RefreshRequest):
    """Refresh access token using refresh token"""
    try:
        new_access_token = await auth_service.refresh_access_token(refresh_data.refresh_token)
        
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return RefreshResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=auth_service.access_token_expire_minutes * 60
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    try:
        permissions = await user_service.get_user_permissions(current_user)

        return {
            "user": {
                "user_id": current_user.user_id,
                "username": current_user.username,
                "email": current_user.email,
                "full_name": current_user.full_name,
                "role": current_user.role,
                "is_active": current_user.is_active,
                "permissions": permissions
            }
        }
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout endpoint - JWT tokens are stateless, so this just confirms the user is authenticated"""
    try:
        logger.info(f"User {current_user.username} logged out")
        return {
            "message": "Successfully logged out",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/debug-token")
async def debug_token_verification(token: str):
    """Debug endpoint to test token verification"""
    try:
        from app.services.auth_service import auth_service
        from app.services.user_service import user_service
        from jose import jwt

        debug_steps = []

        # Step 1: Decode WITHOUT verification
        try:
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            debug_steps.append({"step": "unverified_decode", "status": "success", "payload": unverified_payload})
        except Exception as e:
            debug_steps.append({"step": "unverified_decode", "status": "failed", "error": str(e)})
            unverified_payload = None

        # Step 2: Verify token signature
        verified_payload = auth_service.verify_token(token, "access")
        if verified_payload:
            debug_steps.append({"step": "verify_token", "status": "success", "payload": verified_payload})
        else:
            debug_steps.append({"step": "verify_token", "status": "failed"})

        # Step 3: Extract user_id
        if verified_payload:
            user_id = verified_payload.get("sub")
            debug_steps.append({"step": "extract_user_id", "status": "success", "user_id": user_id})

            # Step 4: Look up user in database
            try:
                user = await user_service.get_user_by_id(user_id)
                if user:
                    debug_steps.append({
                        "step": "get_user_by_id",
                        "status": "success",
                        "user": {
                            "user_id": user.user_id,
                            "username": user.username,
                            "email": user.email,
                            "role": user.role
                        }
                    })
                else:
                    debug_steps.append({"step": "get_user_by_id", "status": "failed", "error": "User not found in database"})
            except Exception as e:
                debug_steps.append({"step": "get_user_by_id", "status": "failed", "error": str(e)})

        return {
            "debug_steps": debug_steps,
            "token_valid": verified_payload is not None,
            "secret_key_prefix": auth_service.secret_key[:20]
        }

    except Exception as e:
        return {
            "error": str(e),
            "message": "Exception during debug"
        }


@router.get("/me-debug")
async def get_current_user_info_debug(request: Request):
    """Debug version of /me endpoint with explicit error handling"""
    try:
        from app.api.dependencies.auth import get_current_active_user, security

        logger.info("=== /me-debug called ===")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"X-Auth-Token header: {request.headers.get('X-Auth-Token', 'NOT SET')[:50]}...")
        logger.info(f"Authorization header: {request.headers.get('Authorization', 'NOT SET')[:50]}...")

        # Step 1: Extract credentials using security scheme
        try:
            credentials = await security(request)
            logger.info(f"✅ Step 1: Security extracted credentials, token starts with: {credentials.credentials[:30]}...")
        except Exception as e:
            logger.error(f"❌ Step 1 FAILED: Security could not extract credentials: {e}")
            return {"error": f"Step 1 failed: {str(e)}", "step": "security_extraction"}

        # Step 2: Get current user
        try:
            from app.services.auth_service import auth_service
            user = await auth_service.get_current_user(credentials.credentials)
            if user:
                logger.info(f"✅ Step 2: Got user: {user.username}")
            else:
                logger.error(f"❌ Step 2 FAILED: auth_service.get_current_user returned None")
                return {"error": "User not found", "step": "get_current_user"}
        except Exception as e:
            logger.error(f"❌ Step 2 FAILED: Exception in get_current_user: {e}", exc_info=True)
            return {"error": f"Step 2 failed: {str(e)}", "step": "get_current_user"}

        # Step 3: Check if user is active
        if not user.is_active:
            logger.error(f"❌ Step 3 FAILED: User {user.username} is not active")
            return {"error": "User is not active", "step": "check_active"}

        logger.info(f"✅ Step 3: User is active")

        # Step 4: Get permissions
        try:
            from app.services.user_service import user_service
            permissions = await user_service.get_user_permissions(user)
            logger.info(f"✅ Step 4: Got permissions: {permissions}")
        except Exception as e:
            logger.error(f"❌ Step 4 FAILED: Exception getting permissions: {e}", exc_info=True)
            return {"error": f"Step 4 failed: {str(e)}", "step": "get_permissions"}

        logger.info("✅ ALL STEPS PASSED!")

        return {
            "success": True,
            "user": {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "permissions": permissions
            }
        }

    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR in /me-debug: {e}", exc_info=True)
        return {"error": f"Unexpected error: {str(e)}", "step": "unknown"}


@router.post("/migrate-user-ids")
async def migrate_user_ids():
    """
    One-time migration endpoint to update existing users to use fixed UUIDs
    This fixes the issue where JWT tokens contain old random UUIDs
    """
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool
        from app.core.config import settings
        from app.core.security import get_password_hash

        logger.info("Starting user ID migration...")

        engine = create_engine(
            settings.DATABASE_URL,
            poolclass=NullPool,
            connect_args={"connect_timeout": 10}
        )

        with engine.connect() as conn:
            # Get existing users
            result = conn.execute(text("""
                SELECT id, email, username FROM users ORDER BY email
            """))
            existing_users = result.fetchall()
            logger.info(f"Found {len(existing_users)} existing users")

            # Delete ALL existing users
            conn.execute(text("DELETE FROM users"))
            logger.info("Deleted all existing users")

            # Recreate with fixed UUIDs
            from datetime import datetime, timezone

            users_to_create = [
                {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "email": "admin@example.com",
                    "username": "admin",
                    "full_name": "Admin User",
                    "hashed_password": get_password_hash("admin123"),
                    "role": "ADMIN",
                    "is_active": True,
                    "is_superuser": True,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000002",
                    "email": "approver@example.com",
                    "username": "approver",
                    "full_name": "Approver User",
                    "hashed_password": get_password_hash("approver123"),
                    "role": "APPROVER",
                    "is_active": True,
                    "is_superuser": False,
                },
                {
                    "id": "00000000-0000-0000-0000-000000000003",
                    "email": "user@example.com",
                    "username": "testuser",
                    "full_name": "Test User",
                    "hashed_password": get_password_hash("user123"),
                    "role": "SUGGEST_ONLY",
                    "is_active": True,
                    "is_superuser": False,
                },
            ]

            for user in users_to_create:
                conn.execute(text("""
                    INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
                    VALUES (:id, :email, :username, :full_name, :hashed_password, :role, :is_active, :is_superuser, :created_at, :updated_at)
                """), {
                    **user,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })
                logger.info(f"Created user: {user['email']} with ID {user['id']}")

            conn.commit()
            logger.info("Migration committed successfully")

            return {
                "status": "success",
                "message": "User IDs migrated to fixed UUIDs",
                "old_users": [{"id": str(u[0]), "email": u[1], "username": u[2]} for u in existing_users],
                "new_users": [{"id": u["id"], "email": u["email"], "username": u["username"]} for u in users_to_create]
            }

    except Exception as e:
        logger.error(f"Error during user ID migration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Migration failed: {str(e)}"
        )


@router.get("/test-users")
async def list_test_users():
    """List available test users for development"""
    test_users = [
        {
            "username": "john_suggest",
            "password": "suggest123",
            "role": "suggest_only",
            "description": "John Doe - Can create and view own suggestions"
        },
        {
            "username": "alice_suggest", 
            "password": "suggest123",
            "role": "suggest_only",
            "description": "Alice Johnson - Can create and view own suggestions"
        },
        {
            "username": "jane_approver",
            "password": "approve123", 
            "role": "approver",
            "description": "Jane Smith - Can approve and apply suggestions"
        },
        {
            "username": "bob_approver",
            "password": "approve123",
            "role": "approver", 
            "description": "Bob Williams - Can approve and apply suggestions"
        },
        {
            "username": "admin_user",
            "password": "admin123",
            "role": "admin",
            "description": "Admin User - Full access to all features"
        }
    ]
    
    return {
        "message": "Test users available in the system",
        "users": test_users,
        "note": "These users are created in the Databricks schema and ready for use"
    }


@router.post("/dev/switch-user")
async def switch_dev_user(user_id: str = Query(...)):
    """Switch to a different test user for development (simulates login)"""
    # Map user IDs to test users
    test_user_map = {
        "u001": {"username": "john_suggest", "password": "suggest123"},
        "u002": {"username": "alice_suggest", "password": "suggest123"},
        "u003": {"username": "jane_approver", "password": "approve123"},
        "u004": {"username": "bob_approver", "password": "approve123"},
        "u005": {"username": "admin_user", "password": "admin123"}
    }
    
    if user_id not in test_user_map:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test user not found"
        )
    
    # Get the user credentials and perform login
    user_creds = test_user_map[user_id]
    
    try:
        result = await auth_service.login(user_creds["username"], user_creds["password"])
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to switch user",
            )
        
        logger.info(f"Dev switch to user {user_creds['username']} successful")
        return LoginResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dev user switch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during user switch"
        )


@router.post("/dev/create-test-users")
async def create_test_users():
    """Create test users in the system for development"""
    # This endpoint would normally create users in the database
    # For now, we'll just return a success message since the users
    # are already created in the Databricks schema
    
    created_users = [
        {
            "user_id": "u001",
            "username": "john_suggest",
            "role": "suggest_only",
            "full_name": "John Doe",
            "email": "john.suggest@example.com"
        },
        {
            "user_id": "u002", 
            "username": "alice_suggest",
            "role": "suggest_only",
            "full_name": "Alice Johnson",
            "email": "alice.suggest@example.com"
        },
        {
            "user_id": "u003",
            "username": "jane_approver", 
            "role": "approver",
            "full_name": "Jane Smith",
            "email": "jane.approver@example.com"
        },
        {
            "user_id": "u004",
            "username": "bob_approver",
            "role": "approver", 
            "full_name": "Bob Williams",
            "email": "bob.approver@example.com"
        },
        {
            "user_id": "u005",
            "username": "admin_user",
            "role": "admin",
            "full_name": "Admin User", 
            "email": "admin@example.com"
        }
    ]
    
    return {
        "message": "Test users created successfully",
        "users": created_users,
        "note": "These test users are now available for login and user switching"
    }