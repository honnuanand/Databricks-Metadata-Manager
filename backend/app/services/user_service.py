"""
User Service - Business logic for user management and authentication
"""
import os
from typing import List, Optional
from app.dal.application_data_dal import application_data_dal
from app.schemas.user import User, UserCreate
from sqlalchemy import create_engine, text, event
from sqlalchemy.pool import NullPool
from passlib.context import CryptContext
from app.core.config import settings
from app.db.lakebase_oauth import get_lakebase_oauth_manager
import logging

logger = logging.getLogger(__name__)

# Create a single database engine for the application (connection pooling)
_engine = None

def get_engine():
    """Get or create the database engine singleton with Lakebase OAuth support"""
    global _engine
    if _engine is None:
        try:
            oauth_mgr = get_lakebase_oauth_manager()

            # Get schema from environment
            schema = os.environ.get('LAKEBASE_SCHEMA', 'metadata_manager')

            if oauth_mgr:
                # Use Lakebase with OAuth token refresh
                logger.info(f"Creating database engine with Lakebase OAuth (schema: {schema})")
                _engine = create_engine(
                    oauth_mgr.get_database_url(schema=schema),
                    poolclass=NullPool,  # Each connection gets fresh token
                    connect_args={"connect_timeout": 10}
                )

                # Refresh token on each connection
                @event.listens_for(_engine, "do_connect")
                def provide_token_on_connect(dialect, conn_rec, cargs, cparams):
                    fresh_mgr = get_lakebase_oauth_manager()
                    if fresh_mgr:
                        params = fresh_mgr.get_connection_params()
                        cparams['user'] = params['user']
                        cparams['password'] = params['password']
                        logger.debug("Refreshed OAuth token for database connection")

                logger.info("Database engine created with Lakebase OAuth")
            elif settings.DATABASE_URL:
                # Fall back to static DATABASE_URL
                logger.info("Creating database engine with static DATABASE_URL")
                _engine = create_engine(
                    settings.DATABASE_URL,
                    poolclass=NullPool,
                    connect_args={"connect_timeout": 10}
                )
                logger.info("Database engine created with static URL")
            else:
                raise ValueError("No database configuration available (set LAKEBASE_* or DATABASE_URL)")

        except Exception as e:
            logger.error(f"Failed to create database engine: {e}")
            raise
    return _engine

# Password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service for user management and authentication"""

    def __init__(self):
        self.app_dal = application_data_dal
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password from PostgreSQL database"""
        try:
            # Get database engine
            engine = get_engine()

            with engine.connect() as conn:
                # Query user by email or username
                result = conn.execute(text("""
                    SELECT id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at
                    FROM users
                    WHERE email = :identifier OR username = :identifier
                """), {"identifier": username})

                row = result.fetchone()

                if not row:
                    logger.warning(f"User {username} not found")
                    return None

                # Verify password
                if not pwd_context.verify(password, row[4]):  # row[4] is hashed_password
                    logger.warning(f"Invalid password for user {username}")
                    return None

                # Check if user is active
                if not row[6]:  # row[6] is is_active
                    logger.warning(f"User {username} is inactive")
                    return None

                # Create User object (normalize role to lowercase for permission checks)
                role = row[5].lower() if row[5] else None
                # Map SUGGEST_ONLY to suggest_only for consistency
                if role == 'suggest_only':
                    role = 'suggest_only'

                user = User(
                    user_id=str(row[0]),
                    email=row[1],
                    username=row[2],
                    full_name=row[3],
                    role=role,
                    is_active=row[6],
                    created_at=row[8],
                    updated_at=row[9]
                )

                logger.info(f"User {username} authenticated successfully with role {role}")
                return user

        except Exception as e:
            logger.error(f"Error authenticating user {username}: {e}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID from PostgreSQL database"""
        try:
            logger.info(f"get_user_by_id: Looking up user_id={user_id}, type={type(user_id)}")

            # Get database engine
            engine = get_engine()

            with engine.connect() as conn:
                # Query user by ID
                result = conn.execute(text("""
                    SELECT id, email, username, full_name, role, is_active, created_at, updated_at
                    FROM users
                    WHERE id = :user_id
                """), {"user_id": user_id})

                row = result.fetchone()

                if not row:
                    logger.warning(f"get_user_by_id: User with ID {user_id} not found in database")
                    # Try to list all user IDs to debug
                    all_ids = conn.execute(text("SELECT id, email FROM users")).fetchall()
                    logger.info(f"get_user_by_id: Available user IDs in database: {[(str(r[0]), r[1]) for r in all_ids]}")
                    return None

                logger.info(f"get_user_by_id: Found user - id={row[0]}, email={row[1]}, username={row[2]}")

                # Create User object (normalize role to lowercase for permission checks)
                role = row[4].lower() if row[4] else None

                user = User(
                    user_id=str(row[0]),
                    email=row[1],
                    username=row[2],
                    full_name=row[3],
                    role=role,
                    is_active=row[5],
                    created_at=row[6],
                    updated_at=row[7]
                )

                return user

        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            return await self.app_dal.get_user_by_username(username)
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            raise
    
    async def list_users(self, requesting_user: User) -> List[User]:
        """List all users (admin only)"""
        try:
            if requesting_user.role != "admin":
                raise ValueError("Only admins can list all users")
            
            users = await self.app_dal.list_users()
            
            # Log access
            await self.app_dal.log_audit_event(
                user_id=requesting_user.user_id,
                action="list_users",
                details=f"Listed {len(users)} users"
            )
            
            logger.info(f"Admin {requesting_user.username} listed {len(users)} users")
            return users
        except Exception as e:
            logger.error(f"Error listing users for {requesting_user.username}: {e}")
            raise
    
    async def get_user_permissions(self, user: User) -> dict:
        """Get user permissions based on role"""
        try:
            permissions = {
                "can_create_suggestions": False,
                "can_view_all_suggestions": False,
                "can_approve_suggestions": False,
                "can_apply_suggestions": False,
                "can_manage_users": False,
                "can_view_audit_logs": False
            }
            
            if user.role == "suggest_only":
                permissions.update({
                    "can_create_suggestions": True,
                })
            elif user.role == "approver":
                permissions.update({
                    "can_create_suggestions": True,
                    "can_view_all_suggestions": True,
                    "can_approve_suggestions": True,
                    "can_apply_suggestions": True,
                })
            elif user.role == "admin":
                permissions.update({
                    "can_create_suggestions": True,
                    "can_view_all_suggestions": True,
                    "can_approve_suggestions": True,
                    "can_apply_suggestions": True,
                    "can_manage_users": True,
                    "can_view_audit_logs": True,
                })
            
            return permissions
        except Exception as e:
            logger.error(f"Error getting permissions for user {user.username}: {e}")
            raise
    
    async def get_user_activity_summary(self, user: User, target_user_id: Optional[str] = None) -> dict:
        """Get user activity summary"""
        try:
            # If target_user_id is provided, check permissions
            if target_user_id and target_user_id != user.user_id:
                if user.role not in ["approver", "admin"]:
                    raise ValueError("Insufficient permissions to view other users' activity")
                target_user = await self.get_user_by_id(target_user_id)
                if not target_user:
                    raise ValueError("Target user not found")
            else:
                target_user_id = user.user_id
                target_user = user
            
            # Get comment suggestions by this user
            suggestions = await self.app_dal.list_comment_suggestions(created_by=target_user_id)
            
            # Count by status
            status_counts = {}
            for suggestion in suggestions:
                status = suggestion.status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Get approvals made by this user (if they're an approver)
            approvals_given = 0
            if target_user.role in ["approver", "admin"]:
                # This would require a method to count approvals by approver
                # For now, set to 0
                approvals_given = 0
            
            activity_summary = {
                "user": {
                    "user_id": target_user.user_id,
                    "username": target_user.username,
                    "role": target_user.role
                },
                "suggestions": {
                    "total": len(suggestions),
                    "by_status": status_counts
                },
                "approvals_given": approvals_given,
                "recent_suggestions": suggestions[:5]  # Last 5 suggestions
            }
            
            # Log access
            await self.app_dal.log_audit_event(
                user_id=user.user_id,
                action="view_user_activity",
                details=f"Viewed activity for user {target_user.username}"
            )
            
            return activity_summary
        except Exception as e:
            logger.error(f"Error getting user activity summary: {e}")
            raise


# Singleton instance
user_service = UserService()