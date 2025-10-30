from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class EntityType(str, Enum):
    CATALOG = "catalog"
    SCHEMA = "schema"
    TABLE = "table"
    COLUMN = "column"


class CommentStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class CommentSuggestionCreate(BaseModel):
    entity_type: EntityType
    entity_catalog: str
    entity_schema: Optional[str] = None
    entity_table: Optional[str] = None
    entity_column: Optional[str] = None
    entity_full_path: str
    current_comment: Optional[str] = None
    suggested_comment: str = Field(..., min_length=1)


class CommentSuggestionUpdate(BaseModel):
    suggested_comment: Optional[str] = Field(None, min_length=1)
    status: Optional[CommentStatus] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None


class CommentSuggestion(BaseModel):
    suggestion_id: str
    entity_type: str
    entity_catalog: str
    entity_schema: Optional[str] = None
    entity_table: Optional[str] = None
    entity_column: Optional[str] = None
    entity_full_path: str
    current_comment: Optional[str] = None
    suggested_comment: str
    status: str
    created_by: str
    approved_by: Optional[str] = None
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None