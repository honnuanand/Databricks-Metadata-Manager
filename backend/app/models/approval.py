from sqlalchemy import Column, String, Text, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from app.db.base import BaseModel


class ApprovalAction(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUEST_CHANGES = "request_changes"


class Approval(BaseModel):
    __tablename__ = "approvals"
    
    comment_id = Column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=False)
    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(Enum(ApprovalAction), nullable=False)
    feedback = Column(Text)
    
    # Relationships
    comment = relationship("Comment", back_populates="approvals")
    approver = relationship("User", back_populates="approvals")