from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.db.base import BaseModel


class EntityType(str, enum.Enum):
    CATALOG = "catalog"
    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"


class CommentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class Comment(BaseModel):
    __tablename__ = "comments"
    
    # Entity identification
    entity_type = Column(Enum(EntityType), nullable=False)
    entity_catalog = Column(String(255), nullable=False, index=True)
    entity_schema = Column(String(255), index=True)
    entity_table = Column(String(255), index=True)
    entity_column = Column(String(255))
    
    # Comment content
    current_comment = Column(Text)
    suggested_comment = Column(Text, nullable=False)
    
    # Status tracking
    status = Column(Enum(CommentStatus), default=CommentStatus.DRAFT, nullable=False, index=True)
    
    # User relationships
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Timestamps
    submitted_at = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    applied_at = Column(DateTime(timezone=True))
    
    # Relationships
    creator = relationship("User", back_populates="created_comments", foreign_keys=[created_by])
    approver = relationship("User", back_populates="approved_comments", foreign_keys=[approved_by])
    approvals = relationship("Approval", back_populates="comment", cascade="all, delete-orphan")
    
    @property
    def entity_path(self):
        path = f"{self.entity_catalog}"
        if self.entity_schema:
            path += f".{self.entity_schema}"
        if self.entity_table:
            path += f".{self.entity_table}"
        if self.entity_column:
            path += f".{self.entity_column}"
        return path