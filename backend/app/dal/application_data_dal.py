"""
Data Access Layer for application data operations in Databricks
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from app.core.databricks_client import databricks_manager
from app.schemas.user import User, UserCreate
from app.schemas.comment import CommentSuggestion, CommentSuggestionCreate, CommentSuggestionUpdate
from app.schemas.approval import Approval, ApprovalCreate
import logging

logger = logging.getLogger(__name__)


class ApplicationDataDAL:
    """Data Access Layer for application data stored in Databricks"""
    
    def __init__(self):
        self.config = databricks_manager.config
        self.catalog = self.config.catalog
        self.schema = self.config.schema
    
    def _get_connection(self):
        """Get databricks.sql connection"""
        return databricks_manager.get_sql_connection()
    
    # User operations
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT user_id, username, email, full_name, role, is_active, created_at, updated_at
                        FROM {self.catalog}.{self.schema}.users
                        WHERE username = ?
                        """,
                        (username,)
                    )
                    row = cursor.fetchone()
                    if row:
                        return User(
                            user_id=row[0],
                            username=row[1],
                            email=row[2],
                            full_name=row[3],
                            role=row[4],
                            is_active=row[5],
                            created_at=row[6],
                            updated_at=row[7]
                        )
                    return None
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT user_id, username, email, full_name, role, is_active, created_at, updated_at
                        FROM {self.catalog}.{self.schema}.users
                        WHERE user_id = ?
                        """,
                        (user_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        return User(
                            user_id=row[0],
                            username=row[1],
                            email=row[2],
                            full_name=row[3],
                            role=row[4],
                            is_active=row[5],
                            created_at=row[6],
                            updated_at=row[7]
                        )
                    return None
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            raise
    
    async def list_users(self) -> List[User]:
        """List all users"""
        try:
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT user_id, username, email, full_name, role, is_active, created_at, updated_at
                        FROM {self.catalog}.{self.schema}.users
                        ORDER BY username
                        """
                    )
                    rows = cursor.fetchall()
                    return [
                        User(
                            user_id=row[0],
                            username=row[1],
                            email=row[2],
                            full_name=row[3],
                            role=row[4],
                            is_active=row[5],
                            created_at=row[6],
                            updated_at=row[7]
                        )
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Error listing users: {e}")
            raise
    
    # Comment suggestion operations
    async def create_comment_suggestion(self, suggestion: CommentSuggestionCreate, created_by: str) -> CommentSuggestion:
        """Create a new comment suggestion"""
        try:
            suggestion_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        INSERT INTO {self.catalog}.{self.schema}.comment_suggestions
                        (suggestion_id, entity_type, entity_catalog, entity_schema, entity_table, entity_column,
                         entity_full_path, current_comment, suggested_comment, status, created_by, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?)
                        """,
                        (
                            suggestion_id,
                            suggestion.entity_type,
                            suggestion.entity_catalog,
                            suggestion.entity_schema,
                            suggestion.entity_table,
                            suggestion.entity_column,
                            suggestion.entity_full_path,
                            suggestion.current_comment,
                            suggestion.suggested_comment,
                            created_by,
                            now,
                            now
                        )
                    )
            
            # Return the created suggestion
            return CommentSuggestion(
                suggestion_id=suggestion_id,
                entity_type=suggestion.entity_type,
                entity_catalog=suggestion.entity_catalog,
                entity_schema=suggestion.entity_schema,
                entity_table=suggestion.entity_table,
                entity_column=suggestion.entity_column,
                entity_full_path=suggestion.entity_full_path,
                current_comment=suggestion.current_comment,
                suggested_comment=suggestion.suggested_comment,
                status="draft",
                created_by=created_by,
                created_at=now,
                updated_at=now
            )
        except Exception as e:
            logger.error(f"Error creating comment suggestion: {e}")
            raise
    
    async def get_comment_suggestion(self, suggestion_id: str) -> Optional[CommentSuggestion]:
        """Get comment suggestion by ID"""
        try:
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT suggestion_id, entity_type, entity_catalog, entity_schema, entity_table, entity_column,
                               entity_full_path, current_comment, suggested_comment, status, created_by, approved_by,
                               submitted_at, approved_at, applied_at, created_at, updated_at
                        FROM {self.catalog}.{self.schema}.comment_suggestions
                        WHERE suggestion_id = ?
                        """,
                        (suggestion_id,)
                    )
                    row = cursor.fetchone()
                    if row:
                        return CommentSuggestion(
                            suggestion_id=row[0],
                            entity_type=row[1],
                            entity_catalog=row[2],
                            entity_schema=row[3],
                            entity_table=row[4],
                            entity_column=row[5],
                            entity_full_path=row[6],
                            current_comment=row[7],
                            suggested_comment=row[8],
                            status=row[9],
                            created_by=row[10],
                            approved_by=row[11],
                            submitted_at=row[12],
                            approved_at=row[13],
                            applied_at=row[14],
                            created_at=row[15],
                            updated_at=row[16]
                        )
                    return None
        except Exception as e:
            logger.error(f"Error getting comment suggestion {suggestion_id}: {e}")
            raise
    
    async def list_comment_suggestions(self, status: Optional[str] = None, created_by: Optional[str] = None) -> List[CommentSuggestion]:
        """List comment suggestions with optional filtering"""
        try:
            where_clauses = []
            params = []
            
            if status:
                where_clauses.append("status = ?")
                params.append(status)
            
            if created_by:
                where_clauses.append("created_by = ?")
                params.append(created_by)
            
            where_clause = ""
            if where_clauses:
                where_clause = "WHERE " + " AND ".join(where_clauses)
            
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT suggestion_id, entity_type, entity_catalog, entity_schema, entity_table, entity_column,
                               entity_full_path, current_comment, suggested_comment, status, created_by, approved_by,
                               submitted_at, approved_at, applied_at, created_at, updated_at
                        FROM {self.catalog}.{self.schema}.comment_suggestions
                        {where_clause}
                        ORDER BY created_at DESC
                        """,
                        params
                    )
                    rows = cursor.fetchall()
                    return [
                        CommentSuggestion(
                            suggestion_id=row[0],
                            entity_type=row[1],
                            entity_catalog=row[2],
                            entity_schema=row[3],
                            entity_table=row[4],
                            entity_column=row[5],
                            entity_full_path=row[6],
                            current_comment=row[7],
                            suggested_comment=row[8],
                            status=row[9],
                            created_by=row[10],
                            approved_by=row[11],
                            submitted_at=row[12],
                            approved_at=row[13],
                            applied_at=row[14],
                            created_at=row[15],
                            updated_at=row[16]
                        )
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Error listing comment suggestions: {e}")
            raise
    
    async def update_comment_suggestion(self, suggestion_id: str, update: CommentSuggestionUpdate) -> Optional[CommentSuggestion]:
        """Update comment suggestion"""
        try:
            set_clauses = []
            params = []
            
            if update.suggested_comment is not None:
                set_clauses.append("suggested_comment = ?")
                params.append(update.suggested_comment)
            
            if update.status is not None:
                set_clauses.append("status = ?")
                params.append(update.status)
            
            if update.approved_by is not None:
                set_clauses.append("approved_by = ?")
                params.append(update.approved_by)
            
            if update.approved_at is not None:
                set_clauses.append("approved_at = ?")
                params.append(update.approved_at)
            
            if update.applied_at is not None:
                set_clauses.append("applied_at = ?")
                params.append(update.applied_at)
            
            set_clauses.append("updated_at = ?")
            params.append(datetime.utcnow())
            params.append(suggestion_id)
            
            if not set_clauses:
                return await self.get_comment_suggestion(suggestion_id)
            
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        UPDATE {self.catalog}.{self.schema}.comment_suggestions
                        SET {', '.join(set_clauses)}
                        WHERE suggestion_id = ?
                        """,
                        params
                    )
            
            return await self.get_comment_suggestion(suggestion_id)
        except Exception as e:
            logger.error(f"Error updating comment suggestion {suggestion_id}: {e}")
            raise
    
    # Approval operations
    async def create_approval(self, approval: ApprovalCreate) -> Approval:
        """Create a new approval record"""
        try:
            approval_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        INSERT INTO {self.catalog}.{self.schema}.approvals
                        (approval_id, suggestion_id, approver_id, action, feedback, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            approval_id,
                            approval.suggestion_id,
                            approval.approver_id,
                            approval.action,
                            approval.feedback,
                            now
                        )
                    )
            
            return Approval(
                approval_id=approval_id,
                suggestion_id=approval.suggestion_id,
                approver_id=approval.approver_id,
                action=approval.action,
                feedback=approval.feedback,
                created_at=now
            )
        except Exception as e:
            logger.error(f"Error creating approval: {e}")
            raise
    
    async def list_approvals_for_suggestion(self, suggestion_id: str) -> List[Approval]:
        """List all approvals for a suggestion"""
        try:
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT approval_id, suggestion_id, approver_id, action, feedback, created_at
                        FROM {self.catalog}.{self.schema}.approvals
                        WHERE suggestion_id = ?
                        ORDER BY created_at DESC
                        """,
                        (suggestion_id,)
                    )
                    rows = cursor.fetchall()
                    return [
                        Approval(
                            approval_id=row[0],
                            suggestion_id=row[1],
                            approver_id=row[2],
                            action=row[3],
                            feedback=row[4],
                            created_at=row[5]
                        )
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Error listing approvals for suggestion {suggestion_id}: {e}")
            raise
    
    # Audit log operations
    async def log_audit_event(self, user_id: str, action: str, entity_type: Optional[str] = None, 
                             entity_id: Optional[str] = None, entity_path: Optional[str] = None, 
                             details: Optional[str] = None, ip_address: Optional[str] = None, 
                             user_agent: Optional[str] = None):
        """Log an audit event"""
        try:
            log_id = str(uuid.uuid4())
            now = datetime.utcnow()
            
            # Get username for the user_id
            user = await self.get_user_by_id(user_id)
            username = user.username if user else None
            
            with self._get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        f"""
                        INSERT INTO {self.catalog}.{self.schema}.audit_logs
                        (log_id, user_id, username, action, entity_type, entity_id, entity_path, 
                         details, ip_address, user_agent, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            log_id,
                            user_id,
                            username,
                            action,
                            entity_type,
                            entity_id,
                            entity_path,
                            details,
                            ip_address,
                            user_agent,
                            now
                        )
                    )
            logger.info(f"Logged audit event: {action} by {username}")
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
            # Don't raise here as audit logging failures shouldn't break the main flow


# Singleton instance
application_data_dal = ApplicationDataDAL()