from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from app.db.session import get_db
from app.models import Comment, CommentStatus, Approval, ApprovalAction, User, UserRole
from app.schemas.approval import (
    ApprovalCreate,
    ApprovalBatch,
    Approval as ApprovalSchema,
    ApprovalResponse,
    ApprovalBatchResponse
)
from app.schemas.comment import Comment as CommentSchema
from app.api.dependencies.auth import get_approver_user
from app.services.databricks_service import databricks_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


async def apply_comment_to_databricks(comment: Comment):
    """Apply approved comment to Databricks (background task)."""
    try:
        entity_path = {
            "catalog": comment.entity_catalog,
            "schema": comment.entity_schema,
            "table": comment.entity_table,
            "column": comment.entity_column
        }
        
        success = await databricks_service.update_comment(
            entity_type=comment.entity_type.value,
            entity_path=entity_path,
            comment=comment.suggested_comment
        )
        
        if success:
            logger.info(f"Successfully applied comment {comment.id} to Databricks")
        else:
            logger.error(f"Failed to apply comment {comment.id} to Databricks")
            
    except Exception as e:
        logger.error(f"Error applying comment {comment.id}: {e}")


@router.get("/pending", response_model=List[CommentSchema])
async def list_pending_approvals(
    entity_catalog: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_approver_user),
    db: Session = Depends(get_db)
):
    """List all comments pending approval."""
    query = db.query(Comment).filter(Comment.status == CommentStatus.PENDING)
    
    if entity_catalog:
        query = query.filter(Comment.entity_catalog == entity_catalog)
    
    comments = query.order_by(Comment.submitted_at).offset(skip).limit(limit).all()
    return comments


@router.get("/history", response_model=List[ApprovalSchema])
async def list_approval_history(
    approver_id: Optional[uuid.UUID] = Query(None),
    comment_id: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_approver_user),
    db: Session = Depends(get_db)
):
    """List approval history."""
    query = db.query(Approval)
    
    if approver_id:
        query = query.filter(Approval.approver_id == approver_id)
    if comment_id:
        query = query.filter(Approval.comment_id == comment_id)
    
    approvals = query.order_by(Approval.created_at.desc()).offset(skip).limit(limit).all()
    return approvals


@router.post("/{comment_id}/approve", response_model=ApprovalResponse)
async def approve_comment(
    comment_id: uuid.UUID,
    feedback: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_approver_user),
    db: Session = Depends(get_db)
):
    """Approve a comment and apply it to Databricks."""
    # Get the comment
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.status != CommentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Comment is not in pending status"
        )
    
    # Create approval record
    approval = Approval(
        comment_id=comment.id,
        approver_id=current_user.id,
        action=ApprovalAction.APPROVED,
        feedback=feedback
    )
    
    # Update comment status
    comment.status = CommentStatus.APPROVED
    comment.approved_by = current_user.id
    comment.approved_at = datetime.utcnow()
    
    db.add(approval)
    db.commit()
    
    # Apply to Databricks in background
    background_tasks.add_task(apply_comment_to_databricks, comment)
    
    # Mark as applied (will be updated async if successful)
    comment.status = CommentStatus.APPLIED
    comment.applied_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Comment {comment_id} approved by {current_user.username}")
    
    return ApprovalResponse(
        message="Comment approved and being applied to Databricks",
        status="approved",
        comment_id=comment.id,
        approval_id=approval.id
    )


@router.post("/{comment_id}/reject", response_model=ApprovalResponse)
async def reject_comment(
    comment_id: uuid.UUID,
    feedback: str,
    current_user: User = Depends(get_approver_user),
    db: Session = Depends(get_db)
):
    """Reject a comment with feedback."""
    # Get the comment
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.status != CommentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Comment is not in pending status"
        )
    
    # Create approval record
    approval = Approval(
        comment_id=comment.id,
        approver_id=current_user.id,
        action=ApprovalAction.REJECTED,
        feedback=feedback
    )
    
    # Update comment status back to draft
    comment.status = CommentStatus.DRAFT
    comment.submitted_at = None
    
    db.add(approval)
    db.commit()
    
    logger.info(f"Comment {comment_id} rejected by {current_user.username}")
    
    return ApprovalResponse(
        message="Comment rejected and returned to draft",
        status="rejected",
        comment_id=comment.id,
        approval_id=approval.id
    )


@router.post("/{comment_id}/request-changes", response_model=ApprovalResponse)
async def request_changes(
    comment_id: uuid.UUID,
    feedback: str,
    current_user: User = Depends(get_approver_user),
    db: Session = Depends(get_db)
):
    """Request changes on a comment."""
    # Get the comment
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.status != CommentStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail="Comment is not in pending status"
        )
    
    # Create approval record
    approval = Approval(
        comment_id=comment.id,
        approver_id=current_user.id,
        action=ApprovalAction.REQUEST_CHANGES,
        feedback=feedback
    )
    
    # Update comment status back to draft
    comment.status = CommentStatus.DRAFT
    comment.submitted_at = None
    
    db.add(approval)
    db.commit()
    
    logger.info(f"Changes requested for comment {comment_id} by {current_user.username}")
    
    return ApprovalResponse(
        message="Changes requested, comment returned to draft",
        status="changes_requested",
        comment_id=comment.id,
        approval_id=approval.id
    )


@router.post("/batch", response_model=ApprovalBatchResponse)
async def batch_approve(
    batch: ApprovalBatch,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_approver_user),
    db: Session = Depends(get_db)
):
    """Batch approve or reject multiple comments."""
    processed = 0
    failed = 0
    messages = []
    
    for comment_id in batch.comment_ids:
        try:
            comment = db.query(Comment).filter(Comment.id == comment_id).first()
            
            if not comment or comment.status != CommentStatus.PENDING:
                failed += 1
                messages.append(ApprovalResponse(
                    message=f"Comment {comment_id} not found or not pending",
                    status="failed",
                    comment_id=comment_id
                ))
                continue
            
            # Create approval record
            approval = Approval(
                comment_id=comment.id,
                approver_id=current_user.id,
                action=batch.action,
                feedback=batch.feedback
            )
            
            if batch.action == ApprovalAction.APPROVED:
                comment.status = CommentStatus.APPROVED
                comment.approved_by = current_user.id
                comment.approved_at = datetime.utcnow()
                
                # Apply to Databricks in background
                background_tasks.add_task(apply_comment_to_databricks, comment)
                comment.status = CommentStatus.APPLIED
                comment.applied_at = datetime.utcnow()
            else:
                comment.status = CommentStatus.DRAFT
                comment.submitted_at = None
            
            db.add(approval)
            processed += 1
            
            messages.append(ApprovalResponse(
                message=f"Comment {comment_id} {batch.action.value}",
                status=batch.action.value,
                comment_id=comment.id,
                approval_id=approval.id
            ))
            
        except Exception as e:
            failed += 1
            messages.append(ApprovalResponse(
                message=f"Error processing comment {comment_id}: {str(e)}",
                status="error",
                comment_id=comment_id
            ))
    
    db.commit()
    
    return ApprovalBatchResponse(
        processed=processed,
        failed=failed,
        messages=messages
    )