"""
Comments API endpoints using clean architecture
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.schemas.comment import (
    CommentSuggestion,
    CommentSuggestionCreate,
    CommentSuggestionUpdate
)
from app.schemas.approval import Approval
from app.services.comment_service import comment_service
from app.api.dependencies.auth import (
    get_current_active_user,
    require_suggest_permission,
    require_approve_permission,
    require_apply_permission
)
from app.schemas.user import User
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class SubmitSuggestionResponse(BaseModel):
    message: str
    suggestion: CommentSuggestion


class ApproveRequest(BaseModel):
    action: str  # "approve" or "reject"
    feedback: Optional[str] = None


class ApproveResponse(BaseModel):
    message: str
    suggestion: CommentSuggestion


class ApplyResponse(BaseModel):
    message: str
    suggestion: CommentSuggestion


@router.post("/suggestions", response_model=CommentSuggestion)
async def create_suggestion(
    suggestion_data: CommentSuggestionCreate,
    current_user: User = Depends(require_suggest_permission)
):
    """Create a new comment suggestion"""
    try:
        suggestion = await comment_service.create_suggestion(suggestion_data, current_user)
        logger.info(f"Created suggestion {suggestion.suggestion_id} by {current_user.username}")
        return suggestion
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating suggestion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create suggestion"
        )


@router.get("/suggestions", response_model=List[CommentSuggestion])
async def list_suggestions(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    created_by: Optional[str] = Query(None, description="Filter by creator"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to return"),
    current_user: User = Depends(get_current_active_user)
):
    """List comment suggestions with optional filtering"""
    try:
        suggestions = await comment_service.list_suggestions(
            user=current_user,
            status=status_filter,
            created_by=created_by
        )
        
        # Apply entity type filter if provided
        if entity_type:
            suggestions = [s for s in suggestions if s.entity_type == entity_type]
        
        # Apply pagination
        total = len(suggestions)
        suggestions = suggestions[skip:skip + limit]
        
        return suggestions
    except Exception as e:
        logger.error(f"Error listing suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list suggestions"
        )


@router.get("/suggestions/{suggestion_id}", response_model=CommentSuggestion)
async def get_suggestion(
    suggestion_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific comment suggestion"""
    try:
        suggestion = await comment_service.get_suggestion(suggestion_id, current_user)
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found or access denied"
            )
        return suggestion
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suggestion {suggestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get suggestion"
        )


@router.put("/suggestions/{suggestion_id}", response_model=CommentSuggestion)
async def update_suggestion(
    suggestion_id: str,
    update_data: CommentSuggestionUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update a comment suggestion"""
    try:
        suggestion = await comment_service.update_suggestion(suggestion_id, update_data, current_user)
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found"
            )
        return suggestion
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating suggestion {suggestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update suggestion"
        )


@router.post("/suggestions/{suggestion_id}/submit", response_model=SubmitSuggestionResponse)
async def submit_suggestion(
    suggestion_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Submit a suggestion for approval"""
    try:
        suggestion = await comment_service.submit_for_approval(suggestion_id, current_user)
        if not suggestion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggestion not found"
            )
        
        return SubmitSuggestionResponse(
            message="Suggestion submitted for approval",
            suggestion=suggestion
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting suggestion {suggestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit suggestion"
        )


@router.post("/suggestions/{suggestion_id}/approve", response_model=ApproveResponse)
async def approve_suggestion(
    suggestion_id: str,
    approve_data: ApproveRequest,
    current_user: User = Depends(require_approve_permission)
):
    """Approve or reject a suggestion"""
    try:
        if approve_data.action not in ["approve", "reject"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action must be 'approve' or 'reject'"
            )
        
        suggestion = await comment_service.approve_suggestion(
            suggestion_id=suggestion_id,
            approver=current_user,
            action=approve_data.action,
            feedback=approve_data.feedback
        )
        
        message = f"Suggestion {approve_data.action}d successfully"
        return ApproveResponse(message=message, suggestion=suggestion)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving suggestion {suggestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve suggestion"
        )


@router.post("/suggestions/{suggestion_id}/apply", response_model=ApplyResponse)
async def apply_suggestion(
    suggestion_id: str,
    current_user: User = Depends(require_apply_permission)
):
    """Apply an approved suggestion to Databricks"""
    try:
        suggestion = await comment_service.apply_suggestion(suggestion_id, current_user)
        
        return ApplyResponse(
            message="Suggestion applied to Databricks successfully",
            suggestion=suggestion
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying suggestion {suggestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply suggestion"
        )


@router.get("/suggestions/{suggestion_id}/approvals", response_model=List[Approval])
async def get_suggestion_approvals(
    suggestion_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get approval history for a suggestion"""
    try:
        approvals = await comment_service.get_suggestion_approvals(suggestion_id, current_user)
        return approvals
    except Exception as e:
        logger.error(f"Error getting approvals for suggestion {suggestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get approval history"
        )


@router.get("/my-suggestions", response_model=List[CommentSuggestion])
async def get_my_suggestions(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(get_current_active_user)
):
    """Get current user's suggestions"""
    try:
        suggestions = await comment_service.list_suggestions(
            user=current_user,
            status=status_filter,
            created_by=current_user.user_id
        )
        return suggestions
    except Exception as e:
        logger.error(f"Error getting user suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user suggestions"
        )