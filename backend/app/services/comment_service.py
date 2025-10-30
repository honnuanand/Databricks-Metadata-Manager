"""
Comment Service - Business logic for comment suggestions and approval workflows
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.dal.application_data_dal import application_data_dal
from app.dal.databricks_metadata_dal import databricks_metadata_dal
from app.schemas.comment import CommentSuggestion, CommentSuggestionCreate, CommentSuggestionUpdate
from app.schemas.approval import Approval, ApprovalCreate
from app.schemas.user import User
import logging

logger = logging.getLogger(__name__)


class CommentService:
    """Service for comment suggestion and approval workflows"""
    
    def __init__(self):
        self.app_dal = application_data_dal
        self.metadata_dal = databricks_metadata_dal
    
    async def create_suggestion(self, suggestion_data: CommentSuggestionCreate, user: User) -> CommentSuggestion:
        """Create a new comment suggestion"""
        try:
            # Validate user has permission to create suggestions
            if user.role not in ["suggest_only", "approver", "admin"]:
                raise ValueError("User does not have permission to create suggestions")
            
            # Create the suggestion
            suggestion = await self.app_dal.create_comment_suggestion(suggestion_data, user.user_id)
            
            # Log the activity
            await self.app_dal.log_audit_event(
                user_id=user.user_id,
                action="create_suggestion",
                entity_type=suggestion.entity_type,
                entity_id=suggestion.suggestion_id,
                entity_path=suggestion.entity_full_path,
                details=f"Suggested comment for {suggestion.entity_full_path}"
            )
            
            logger.info(f"User {user.username} created suggestion {suggestion.suggestion_id}")
            return suggestion
        except Exception as e:
            logger.error(f"Error creating suggestion for user {user.username}: {e}")
            raise
    
    async def get_suggestion(self, suggestion_id: str, user: User) -> Optional[CommentSuggestion]:
        """Get a specific suggestion"""
        try:
            suggestion = await self.app_dal.get_comment_suggestion(suggestion_id)
            
            if suggestion:
                # Check if user has permission to view this suggestion
                if user.role == "suggest_only" and suggestion.created_by != user.user_id:
                    # Suggest-only users can only view their own suggestions
                    return None
                
                # Log access
                await self.app_dal.log_audit_event(
                    user_id=user.user_id,
                    action="view_suggestion",
                    entity_type=suggestion.entity_type,
                    entity_id=suggestion.suggestion_id,
                    entity_path=suggestion.entity_full_path
                )
            
            return suggestion
        except Exception as e:
            logger.error(f"Error getting suggestion {suggestion_id} for user {user.username}: {e}")
            raise
    
    async def list_suggestions(self, user: User, status: Optional[str] = None, 
                              created_by: Optional[str] = None) -> List[CommentSuggestion]:
        """List suggestions based on user permissions"""
        try:
            # Apply role-based filtering
            if user.role == "suggest_only":
                # Suggest-only users can only see their own suggestions
                created_by = user.user_id
            elif user.role in ["approver", "admin"]:
                # Approvers and admins can see all suggestions or filter by creator
                pass
            
            suggestions = await self.app_dal.list_comment_suggestions(status=status, created_by=created_by)
            
            # Log access
            await self.app_dal.log_audit_event(
                user_id=user.user_id,
                action="list_suggestions",
                details=f"Filters: status={status}, created_by={created_by}"
            )
            
            logger.info(f"User {user.username} listed {len(suggestions)} suggestions")
            return suggestions
        except Exception as e:
            logger.error(f"Error listing suggestions for user {user.username}: {e}")
            raise
    
    async def update_suggestion(self, suggestion_id: str, update_data: CommentSuggestionUpdate, 
                               user: User) -> Optional[CommentSuggestion]:
        """Update a suggestion (only by creator or admin)"""
        try:
            # Get the existing suggestion
            existing = await self.app_dal.get_comment_suggestion(suggestion_id)
            if not existing:
                return None
            
            # Check permissions
            if user.role == "suggest_only" and existing.created_by != user.user_id:
                raise ValueError("You can only edit your own suggestions")
            
            if existing.status in ["approved", "applied"] and user.role != "admin":
                raise ValueError("Cannot edit approved or applied suggestions")
            
            # Update the suggestion
            updated = await self.app_dal.update_comment_suggestion(suggestion_id, update_data)
            
            if updated:
                # Log the update
                await self.app_dal.log_audit_event(
                    user_id=user.user_id,
                    action="update_suggestion",
                    entity_type=updated.entity_type,
                    entity_id=suggestion_id,
                    entity_path=updated.entity_full_path,
                    details=f"Updated suggestion status: {updated.status}"
                )
            
            logger.info(f"User {user.username} updated suggestion {suggestion_id}")
            return updated
        except Exception as e:
            logger.error(f"Error updating suggestion {suggestion_id} for user {user.username}: {e}")
            raise
    
    async def submit_for_approval(self, suggestion_id: str, user: User) -> Optional[CommentSuggestion]:
        """Submit a suggestion for approval"""
        try:
            # Get the suggestion
            suggestion = await self.app_dal.get_comment_suggestion(suggestion_id)
            if not suggestion:
                return None
            
            # Check permissions
            if suggestion.created_by != user.user_id and user.role != "admin":
                raise ValueError("You can only submit your own suggestions")
            
            if suggestion.status != "draft":
                raise ValueError("Only draft suggestions can be submitted for approval")
            
            # Update status to pending
            update_data = CommentSuggestionUpdate(
                status="pending",
                submitted_at=datetime.utcnow()
            )
            
            updated = await self.app_dal.update_comment_suggestion(suggestion_id, update_data)
            
            if updated:
                # Log the submission
                await self.app_dal.log_audit_event(
                    user_id=user.user_id,
                    action="submit_suggestion",
                    entity_type=updated.entity_type,
                    entity_id=suggestion_id,
                    entity_path=updated.entity_full_path,
                    details="Submitted for approval"
                )
            
            logger.info(f"User {user.username} submitted suggestion {suggestion_id} for approval")
            return updated
        except Exception as e:
            logger.error(f"Error submitting suggestion {suggestion_id} for user {user.username}: {e}")
            raise
    
    async def approve_suggestion(self, suggestion_id: str, approver: User, 
                                action: str, feedback: Optional[str] = None) -> CommentSuggestion:
        """Approve or reject a suggestion"""
        try:
            # Check permissions
            if approver.role not in ["approver", "admin"]:
                raise ValueError("Only approvers and admins can approve suggestions")
            
            # Get the suggestion
            suggestion = await self.app_dal.get_comment_suggestion(suggestion_id)
            if not suggestion:
                raise ValueError("Suggestion not found")
            
            if suggestion.status != "pending":
                raise ValueError("Only pending suggestions can be approved or rejected")
            
            # Create approval record
            approval_data = ApprovalCreate(
                suggestion_id=suggestion_id,
                approver_id=approver.user_id,
                action=action,
                feedback=feedback
            )
            
            approval = await self.app_dal.create_approval(approval_data)
            
            # Update suggestion status
            now = datetime.utcnow()
            if action == "approve":
                update_data = CommentSuggestionUpdate(
                    status="approved",
                    approved_by=approver.user_id,
                    approved_at=now
                )
            else:  # reject
                update_data = CommentSuggestionUpdate(
                    status="rejected",
                    approved_by=approver.user_id,
                    approved_at=now
                )
            
            updated = await self.app_dal.update_comment_suggestion(suggestion_id, update_data)
            
            # Log the approval
            await self.app_dal.log_audit_event(
                user_id=approver.user_id,
                action=f"{action}_suggestion",
                entity_type=suggestion.entity_type,
                entity_id=suggestion_id,
                entity_path=suggestion.entity_full_path,
                details=f"Action: {action}, Feedback: {feedback}"
            )
            
            logger.info(f"User {approver.username} {action}ed suggestion {suggestion_id}")
            return updated
        except Exception as e:
            logger.error(f"Error approving suggestion {suggestion_id} for user {approver.username}: {e}")
            raise
    
    async def apply_suggestion(self, suggestion_id: str, applier: User) -> CommentSuggestion:
        """Apply an approved suggestion to Databricks"""
        try:
            # Check permissions
            if applier.role not in ["approver", "admin"]:
                raise ValueError("Only approvers and admins can apply suggestions")
            
            # Get the suggestion
            suggestion = await self.app_dal.get_comment_suggestion(suggestion_id)
            if not suggestion:
                raise ValueError("Suggestion not found")
            
            if suggestion.status != "approved":
                raise ValueError("Only approved suggestions can be applied")
            
            # Build entity path for Databricks
            entity_path = {}
            if suggestion.entity_catalog:
                entity_path["catalog"] = suggestion.entity_catalog
            if suggestion.entity_schema:
                entity_path["schema"] = suggestion.entity_schema
            if suggestion.entity_table:
                entity_path["table"] = suggestion.entity_table
            if suggestion.entity_column:
                entity_path["column"] = suggestion.entity_column
            
            # Apply the comment to Databricks
            success = await self.metadata_dal.update_comment(
                entity_type=suggestion.entity_type,
                entity_path=entity_path,
                comment=suggestion.suggested_comment
            )
            
            if success:
                # Update suggestion status to applied
                update_data = CommentSuggestionUpdate(
                    status="applied",
                    applied_at=datetime.utcnow()
                )
                
                updated = await self.app_dal.update_comment_suggestion(suggestion_id, update_data)
                
                # Log the application
                await self.app_dal.log_audit_event(
                    user_id=applier.user_id,
                    action="apply_suggestion",
                    entity_type=suggestion.entity_type,
                    entity_id=suggestion_id,
                    entity_path=suggestion.entity_full_path,
                    details=f"Applied comment: {suggestion.suggested_comment}"
                )
                
                logger.info(f"User {applier.username} applied suggestion {suggestion_id}")
                return updated
            else:
                raise ValueError("Failed to apply comment to Databricks")
        except Exception as e:
            logger.error(f"Error applying suggestion {suggestion_id} for user {applier.username}: {e}")
            raise
    
    async def get_suggestion_approvals(self, suggestion_id: str, user: User) -> List[Approval]:
        """Get approval history for a suggestion"""
        try:
            # Check if user can view this suggestion
            suggestion = await self.get_suggestion(suggestion_id, user)
            if not suggestion:
                return []
            
            approvals = await self.app_dal.list_approvals_for_suggestion(suggestion_id)
            
            # Log access
            await self.app_dal.log_audit_event(
                user_id=user.user_id,
                action="view_approvals",
                entity_id=suggestion_id,
                details=f"Viewed {len(approvals)} approvals"
            )
            
            return approvals
        except Exception as e:
            logger.error(f"Error getting approvals for suggestion {suggestion_id}: {e}")
            raise


# Singleton instance
comment_service = CommentService()