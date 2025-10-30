from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import auth_service
from app.schemas.user import User
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class CustomTokenAuth:
    """
    Custom authentication scheme that reads from X-Auth-Token header
    instead of Authorization header (which is stripped by Databricks SSO)
    """
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        # Try X-Auth-Token header first (for production with Databricks SSO)
        token = request.headers.get('X-Auth-Token')

        if not token:
            # Fallback to Authorization header (for local development)
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove 'Bearer ' prefix

        if not token:
            logger.warning(f"CustomTokenAuth: No token found in X-Auth-Token or Authorization headers")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(f"CustomTokenAuth: Token found, starts with: {token[:30]}...")
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

security = CustomTokenAuth()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Dependency to get the current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        logger.info(f"get_current_user: Received token starting with: {token[:30]}...")
        logger.info(f"get_current_user: Token length: {len(token)}")

        user = await auth_service.get_current_user(token)

        if user is None:
            logger.warning(f"get_current_user: auth_service.get_current_user returned None")
            raise credentials_exception

        logger.info(f"get_current_user: Successfully authenticated user {user.username}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_current_user: Exception occurred: {e}", exc_info=True)
        raise credentials_exception


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get current active user
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_role(*allowed_roles: str):
    """
    Dependency factory to require specific roles
    """
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted for your role"
            )
        return current_user
    return role_checker


def require_permission(permission: str):
    """
    Dependency factory to require specific permissions
    """
    def permission_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if not auth_service.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    return permission_checker


# Common role dependencies
require_approver = require_role("approver", "admin")
require_admin = require_role("admin")

# Common permission dependencies
require_suggest_permission = require_permission("create_suggestions")
require_approve_permission = require_permission("approve_suggestions")
require_apply_permission = require_permission("apply_suggestions")
require_admin_permission = require_permission("admin_override")