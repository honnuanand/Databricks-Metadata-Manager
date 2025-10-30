from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import relationship
from app.db.base import BaseModel


class AuditLog(BaseModel):
    __tablename__ = "audit_logs"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    details = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")