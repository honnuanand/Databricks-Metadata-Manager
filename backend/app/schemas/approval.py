from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class ApprovalCreate(BaseModel):
    suggestion_id: str
    approver_id: str
    action: str  # "approve" or "reject"
    feedback: Optional[str] = None


class Approval(BaseModel):
    approval_id: str
    suggestion_id: str
    approver_id: str
    action: str
    feedback: Optional[str] = None
    created_at: Optional[datetime] = None