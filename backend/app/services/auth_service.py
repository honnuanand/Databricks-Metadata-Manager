"""
Authentication Service - JWT token management and user authentication
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
from app.services.user_service import user_service
from app.schemas.user import User
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication and JWT token management"""

    def __init__(self):
        self.user_service = user_service
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

        # Log initialization for debugging
        logger.info("=" * 80)
        logger.info("AuthService initialized")
        logger.info(f"SECRET_KEY starts with: {self.secret_key[:20]}...")
        logger.info(f"SECRET_KEY length: {len(self.secret_key)}")
        logger.info(f"ALGORITHM: {self.algorithm}")
        logger.info(f"ACCESS_TOKEN_EXPIRE_MINUTES: {self.access_token_expire_minutes}")
        logger.info("=" * 80)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user and return user object if valid"""
        try:
            user = await self.user_service.authenticate_user(username, password)
            return user
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire, "type": "access"})
        logger.info(f"create_access_token: Creating token with payload keys: {list(to_encode.keys())}")
        logger.info(f"create_access_token: Token will expire at: {expire}")
        logger.info(f"create_access_token: Using SECRET_KEY starting with: {self.secret_key[:20]}...")

        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        logger.info(f"create_access_token: Generated token starts with: {encoded_jwt[:30]}...")
        logger.info(f"create_access_token: Token length: {len(encoded_jwt)}")

        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify a JWT token and return payload if valid"""
        try:
            logger.info(f"verify_token: Attempting to verify token type={token_type}")
            logger.info(f"verify_token: Token starts with: {token[:30]}...")
            logger.info(f"verify_token: Using algorithm: {self.algorithm}")
            logger.info(f"verify_token: SECRET_KEY starts with: {self.secret_key[:20]}...")

            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            logger.info(f"verify_token: Token decoded successfully, payload keys: {list(payload.keys())}")

            # Check token type
            if payload.get("type") != token_type:
                logger.warning(f"verify_token: Token type mismatch. Expected {token_type}, got {payload.get('type')}")
                return None

            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                logger.warning(f"verify_token: Token has no expiration")
                return None

            exp_time = datetime.fromtimestamp(exp)
            now = datetime.utcnow()
            logger.info(f"verify_token: Token expires at {exp_time}, current time {now}")

            if exp_time < now:
                logger.warning(f"verify_token: Token expired")
                return None

            logger.info(f"verify_token: Token verified successfully for user {payload.get('sub')}")
            return payload
        except JWTError as e:
            logger.error(f"verify_token: JWT verification failed: {e}", exc_info=True)
            return None
    
    async def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT token"""
        try:
            logger.info(f"get_current_user: Verifying token...")
            payload = self.verify_token(token, "access")

            if payload is None:
                logger.warning(f"get_current_user: verify_token returned None")
                return None

            logger.info(f"get_current_user: Token verified, payload={payload}")

            user_id: str = payload.get("sub")
            if user_id is None:
                logger.warning(f"get_current_user: No 'sub' field in payload")
                return None

            logger.info(f"get_current_user: Extracted user_id={user_id} from token, calling user_service.get_user_by_id()")
            user = await self.user_service.get_user_by_id(user_id)

            if user is None:
                logger.warning(f"get_current_user: user_service.get_user_by_id returned None for user_id={user_id}")
                return None

            logger.info(f"get_current_user: Successfully retrieved user {user.username}")
            return user
        except Exception as e:
            logger.error(f"get_current_user: Exception occurred: {e}", exc_info=True)
            return None
    
    async def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """Create new access token from valid refresh token"""
        try:
            payload = self.verify_token(refresh_token, "refresh")
            if payload is None:
                return None
            
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            
            # Verify user still exists and is active
            user = await self.user_service.get_user_by_id(user_id)
            if not user or not user.is_active:
                return None
            
            # Create new access token
            token_data = {"sub": user.user_id, "username": user.username, "role": user.role}
            new_access_token = self.create_access_token(data=token_data)
            
            return new_access_token
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            return None
    
    async def login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Complete login process - authenticate and return tokens"""
        try:
            user = await self.authenticate_user(username, password)
            if not user:
                return None
            
            # Create token data
            token_data = {"sub": user.user_id, "username": user.username, "role": user.role}
            
            # Create tokens
            access_token = self.create_access_token(data=token_data)
            refresh_token = self.create_refresh_token(data=token_data)
            
            # Get user permissions
            permissions = await self.user_service.get_user_permissions(user)
            
            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.access_token_expire_minutes * 60,
                "user": {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                    "permissions": permissions
                }
            }
        except Exception as e:
            logger.error(f"Login error: {e}")
            return None
    
    def has_permission(self, user: User, permission: str) -> bool:
        """Check if user has a specific permission"""
        role_permissions = {
            "suggest_only": [
                "create_suggestions",
                "view_own_suggestions",
                "edit_own_draft_suggestions"
            ],
            "approver": [
                "create_suggestions",
                "view_own_suggestions",
                "edit_own_draft_suggestions",
                "view_all_suggestions",
                "approve_suggestions",
                "apply_suggestions"
            ],
            "admin": [
                "create_suggestions",
                "view_own_suggestions",
                "edit_own_draft_suggestions",
                "view_all_suggestions",
                "approve_suggestions",
                "apply_suggestions",
                "manage_users",
                "view_audit_logs",
                "admin_override"
            ]
        }
        
        user_permissions = role_permissions.get(user.role, [])
        return permission in user_permissions


# Singleton instance
auth_service = AuthService()