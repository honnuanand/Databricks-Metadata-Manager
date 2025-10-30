from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.orm import relationship
import enum
from app.db.base import BaseModel


class UserRole(str, enum.Enum):
    SUGGEST_ONLY = "suggest_only"  # Can only suggest comments
    APPROVER = "approver"  # Can suggest and approve comments
    ADMIN = "admin"  # Full access including user management


class User(BaseModel):
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255))
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.SUGGEST_ONLY, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    created_comments = relationship("Comment", back_populates="creator", foreign_keys="Comment.created_by")
    approved_comments = relationship("Comment", back_populates="approver", foreign_keys="Comment.approved_by")
    approvals = relationship("Approval", back_populates="approver")
    audit_logs = relationship("AuditLog", back_populates="user")