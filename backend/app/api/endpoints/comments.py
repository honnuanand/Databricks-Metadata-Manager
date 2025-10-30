from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from app.db.session import get_db
from app.models import Comment, CommentStatus, User, UserRole
from app.schemas.comment import (
    CommentCreate,
    CommentUpdate,
    Comment as CommentSchema,
    CommentFilter,
    CommentSubmit
)
from app.api.dependencies.auth import get_current_active_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[CommentSchema])
async def list_comments(
    status: Optional[CommentStatus] = Query(None),
    entity_catalog: Optional[str] = Query(None),
    entity_schema: Optional[str] = Query(None),
    entity_table: Optional[str] = Query(None),
    created_by: Optional[uuid.UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List comments with optional filters."""
    query = db.query(Comment)
    
    # Apply filters
    if status:
        query = query.filter(Comment.status == status)
    if entity_catalog:
        query = query.filter(Comment.entity_catalog == entity_catalog)
    if entity_schema:
        query = query.filter(Comment.entity_schema == entity_schema)
    if entity_table:
        query = query.filter(Comment.entity_table == entity_table)
    if created_by:
        query = query.filter(Comment.created_by == created_by)
    
    # For non-admin users, only show their own drafts
    if current_user.role != UserRole.ADMIN and status == CommentStatus.DRAFT:
        query = query.filter(Comment.created_by == current_user.id)
    
    # Pagination
    comments = query.offset(skip).limit(limit).all()
    return comments


@router.get("/my", response_model=List[CommentSchema])
async def list_my_comments(
    status: Optional[CommentStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List current user's comments."""
    query = db.query(Comment).filter(Comment.created_by == current_user.id)
    
    if status:
        query = query.filter(Comment.status == status)
    
    comments = query.order_by(Comment.created_at.desc()).offset(skip).limit(limit).all()
    return comments


@router.get("/{comment_id}", response_model=CommentSchema)
async def get_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific comment."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check permissions for draft comments
    if comment.status == CommentStatus.DRAFT and comment.created_by != current_user.id:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return comment


@router.post("/", response_model=CommentSchema)
async def create_comment(
    comment_data: CommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new comment suggestion."""
    # Create comment
    db_comment = Comment(
        entity_type=comment_data.entity_type,
        entity_catalog=comment_data.entity_catalog,
        entity_schema=comment_data.entity_schema,
        entity_table=comment_data.entity_table,
        entity_column=comment_data.entity_column,
        current_comment=comment_data.current_comment,
        suggested_comment=comment_data.suggested_comment,
        status=CommentStatus.DRAFT,
        created_by=current_user.id
    )
    
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    
    logger.info(f"Comment created by {current_user.username}: {db_comment.id}")
    return db_comment


@router.put("/{comment_id}", response_model=CommentSchema)
async def update_comment(
    comment_id: uuid.UUID,
    comment_update: CommentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update a comment (only if in draft status)."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check permissions
    if comment.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this comment")
    
    # Only allow updates to draft comments
    if comment.status != CommentStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Can only update comments in draft status"
        )
    
    # Update fields
    if comment_update.suggested_comment is not None:
        comment.suggested_comment = comment_update.suggested_comment
    
    comment.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(comment)
    
    return comment


@router.post("/submit", response_model=dict)
async def submit_comments(
    submission: CommentSubmit,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Submit draft comments for approval."""
    # Get all specified comments
    comments = db.query(Comment).filter(
        Comment.id.in_(submission.comment_ids),
        Comment.created_by == current_user.id,
        Comment.status == CommentStatus.DRAFT
    ).all()
    
    if len(comments) != len(submission.comment_ids):
        raise HTTPException(
            status_code=400,
            detail="Some comments not found or not in draft status"
        )
    
    # Update status to pending
    for comment in comments:
        comment.status = CommentStatus.PENDING
        comment.submitted_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": f"Successfully submitted {len(comments)} comments for approval",
        "submitted_count": len(comments)
    }


@router.delete("/{comment_id}")
async def delete_comment(
    comment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a comment (only if in draft status)."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check permissions
    if comment.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    
    # Only allow deletion of draft comments
    if comment.status != CommentStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail="Can only delete comments in draft status"
        )
    
    db.delete(comment)
    db.commit()
    
    return {"message": "Comment deleted successfully"}