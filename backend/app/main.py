from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.api.endpoints.auth import router as auth_router
from app.api.endpoints.catalogs import router as catalogs_router
from app.api.dependencies.auth import get_current_active_user
from app.core.databricks_client import databricks_manager
from app.schemas.user import User
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    description="Clean API-driven Databricks Metadata Manager"
)

# Log configuration on startup
logger.info(f"SECRET_KEY configured: {settings.SECRET_KEY[:16]}...")
logger.info(f"DATABRICKS_HOST: {settings.DATABRICKS_HOST}")
logger.info(f"CORS_ORIGINS: {settings.CORS_ORIGINS}")

# Database initialization on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database with seed data if needed"""
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} starting up...")
    try:
        from sqlalchemy import create_engine, text
        from sqlalchemy.pool import NullPool
        from app.core.security import get_password_hash
        from datetime import datetime, timezone

        logger.info("Checking database initialization...")

        engine = create_engine(
            settings.DATABASE_URL,
            poolclass=NullPool,
            connect_args={"connect_timeout": 10}
        )

        with engine.connect() as conn:
            # Check if users exist
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()

            if user_count == 0:
                logger.info("Database is empty. Seeding with initial users...")

                # Create admin user with FIXED UUID
                admin_id = "00000000-0000-0000-0000-000000000001"
                admin_password = get_password_hash("admin123")

                conn.execute(text("""
                    INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
                    VALUES (:id, :email, :username, :full_name, :hashed_password, :role, :is_active, :is_superuser, :created_at, :updated_at)
                """), {
                    "id": admin_id,
                    "email": "admin@example.com",
                    "username": "admin",
                    "full_name": "Admin User",
                    "hashed_password": admin_password,
                    "role": "ADMIN",
                    "is_active": True,
                    "is_superuser": True,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })

                # Create approver user with FIXED UUID
                approver_id = "00000000-0000-0000-0000-000000000002"
                approver_password = get_password_hash("approver123")

                conn.execute(text("""
                    INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
                    VALUES (:id, :email, :username, :full_name, :hashed_password, :role, :is_active, :is_superuser, :created_at, :updated_at)
                """), {
                    "id": approver_id,
                    "email": "approver@example.com",
                    "username": "approver",
                    "full_name": "Approver User",
                    "hashed_password": approver_password,
                    "role": "APPROVER",
                    "is_active": True,
                    "is_superuser": False,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })

                # Create regular user with FIXED UUID
                user_id = "00000000-0000-0000-0000-000000000003"
                user_password = get_password_hash("user123")

                conn.execute(text("""
                    INSERT INTO users (id, email, username, full_name, hashed_password, role, is_active, is_superuser, created_at, updated_at)
                    VALUES (:id, :email, :username, :full_name, :hashed_password, :role, :is_active, :is_superuser, :created_at, :updated_at)
                """), {
                    "id": user_id,
                    "email": "user@example.com",
                    "username": "testuser",
                    "full_name": "Test User",
                    "hashed_password": user_password,
                    "role": "SUGGEST_ONLY",
                    "is_active": True,
                    "is_superuser": False,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                })

                conn.commit()
                logger.info("✅ Database seeded with 3 users (fixed UUIDs)")
            else:
                logger.info(f"Database already has {user_count} users. Skipping seed.")

    except Exception as e:
        logger.error(f"Error during database initialization: {e}", exc_info=True)

# In-memory storage for comments (for development/testing)
comments_storage = [
    {
        "id": "comment_001",
        "entity_type": "column",
        "entity_catalog": "arao",
        "entity_schema": "metadata_test",
        "entity_table": "users",
        "entity_column": "email",
        "entity_path": "arao.metadata_test.users.email",
        "current_comment": "User email address",
        "suggested_comment": "Primary email address for user communication and authentication",
        "status": "pending",
        "created_by": "john_suggest",
        "created_at": "2024-01-15T10:30:00Z"
    },
    {
        "id": "comment_002",
        "entity_type": "table",
        "entity_catalog": "arao",
        "entity_schema": "metadata_test", 
        "entity_table": "users",
        "entity_path": "arao.metadata_test.users",
        "current_comment": None,
        "suggested_comment": "Core user information table containing authentication and profile data",
        "status": "draft",
        "created_by": "alice_suggest",
        "created_at": "2024-01-15T11:15:00Z"
    },
    {
        "id": "comment_003",
        "entity_type": "column",
        "entity_catalog": "arao",
        "entity_schema": "metadata_test",
        "entity_table": "products",
        "entity_column": "price",
        "entity_path": "arao.metadata_test.products.price",
        "current_comment": "Product price",
        "suggested_comment": "Product price in USD with 2 decimal precision",
        "status": "pending",
        "created_by": "john_suggest",
        "created_at": "2024-01-15T12:00:00Z"
    },
    {
        "id": "comment_004",
        "entity_type": "schema",
        "entity_catalog": "arao",
        "entity_schema": "metadata_test",
        "entity_path": "arao.metadata_test",
        "current_comment": "Test schema with sample tables and comprehensive metadata",
        "suggested_comment": "Comprehensive test environment with sample business data for metadata management development and testing",
        "status": "pending",
        "created_by": "john_suggest",
        "created_at": "2024-01-15T13:00:00Z"
    },
    {
        "id": "comment_005",
        "entity_type": "schema", 
        "entity_catalog": "arao",
        "entity_schema": "metadata_manager",
        "entity_path": "arao.metadata_manager",
        "current_comment": "Central repository for Databricks metadata management",
        "suggested_comment": "Production schema for Databricks Unity Catalog metadata management with audit trails and approval workflows",
        "status": "approved",
        "created_by": "alice_suggest",
        "created_at": "2024-01-15T14:00:00Z",
        "approved_by": "jane_approver",
        "approved_at": "2024-01-15T15:00:00Z"
    }
]

# Helper function to get user role from username
def get_user_role_from_username(username: str) -> str:
    """Get the role for a given username"""
    role_map = {
        "john_suggest": "suggest_only",
        "alice_suggest": "suggest_only",
        "jane_approver": "approver",
        "bob_approver": "approver",
        "admin_user": "admin",
        "admin": "admin",
        "approver": "approver",
        "testuser": "suggest_only"
    }
    return role_map.get(username, "suggest_only")


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

# Mount static files if the directory exists
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")
    logger.info(f"Mounted static files from {STATIC_DIR}")
else:
    logger.warning(f"Static directory not found at {STATIC_DIR}")

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(catalogs_router, prefix="/api/v1/catalogs", tags=["Catalogs"])

# Add users endpoint for frontend compatibility  
@app.get("/api/v1/users/me")
async def get_current_user_info_compat(current_user: User = Depends(get_current_active_user)):
    """Get current user information - compatibility endpoint"""
    from app.services.user_service import user_service
    
    try:
        permissions = await user_service.get_user_permissions(current_user)
        
        return {
            "id": current_user.user_id,
            "email": current_user.email,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "is_active": current_user.is_active,
            "permissions": permissions
        }
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

# Add comments endpoints
@app.get("/api/v1/comments")
async def get_all_comments(
    status: str = None,
    current_user: User = Depends(get_current_active_user)
):
    """Get all comments (for audit log and admin views)

    Optional query parameters:
    - status: Filter by comment status (pending, approved, rejected, draft, applied)
    """
    # Filter by status if provided
    filtered_comments = comments_storage
    if status:
        filtered_comments = [c for c in comments_storage if c.get("status") == status]

    # Enhance each comment with user role information
    enhanced_comments = []
    for comment in filtered_comments:
        enhanced_comment = comment.copy()
        # Add the role/authorization level of the user who created/approved/applied the comment
        enhanced_comment["created_by_role"] = get_user_role_from_username(comment.get("created_by", ""))
        if comment.get("approved_by"):
            enhanced_comment["approved_by_role"] = get_user_role_from_username(comment.get("approved_by"))
        if comment.get("applied_by"):
            enhanced_comment["applied_by_role"] = get_user_role_from_username(comment.get("applied_by"))
        enhanced_comments.append(enhanced_comment)
    return enhanced_comments

@app.get("/api/v1/comments/my")
async def get_my_comments():
    """Get current user's comment suggestions"""
    # TODO: Filter by current user when authentication is implemented
    # For now, return all comments for development
    return comments_storage

@app.post("/api/v1/comments")
async def create_comment(comment_data: dict):
    """Create a new comment suggestion"""
    import uuid
    from datetime import datetime
    
    comment_id = str(uuid.uuid4())
    current_time = datetime.now().isoformat() + "Z"
    
    # Build entity path
    entity_parts = []
    if comment_data.get("entity_catalog"):
        entity_parts.append(comment_data.get("entity_catalog"))
    if comment_data.get("entity_schema"):
        entity_parts.append(comment_data.get("entity_schema"))
    if comment_data.get("entity_table"):
        entity_parts.append(comment_data.get("entity_table"))
    if comment_data.get("entity_column"):
        entity_parts.append(comment_data.get("entity_column"))
    
    entity_path = ".".join(entity_parts)
    
    # Create comment object
    comment = {
        "id": comment_id,
        "entity_type": comment_data.get("entity_type", "column"),
        "entity_catalog": comment_data.get("entity_catalog"),
        "entity_schema": comment_data.get("entity_schema"),
        "entity_table": comment_data.get("entity_table"),
        "entity_column": comment_data.get("entity_column"),
        "current_comment": comment_data.get("current_comment"),
        "suggested_comment": comment_data.get("suggested_comment"),
        "status": "draft",
        "created_by": "john_suggest",  # TODO: Get from current user
        "created_at": current_time,
        "updated_at": current_time,
        "entity_path": entity_path
    }
    
    # Store the comment
    comments_storage.append(comment)
    
    logger.info(f"Created comment {comment_id} for {entity_path}")
    return comment

@app.get("/api/v1/comments/table/{catalog}/{schema}/{table}")
async def get_table_comments(catalog: str, schema: str, table: str):
    """Get pending comments for a specific table"""
    # Filter comments for this specific table
    table_comments = []
    for comment in comments_storage:
        # Match by entity path for table and column level comments
        entity_path = f"{catalog}.{schema}.{table}"
        if (comment.get("entity_catalog") == catalog and 
            comment.get("entity_schema") == schema and 
            comment.get("entity_table") == table) or \
           (comment.get("entity_path", "").startswith(entity_path)):
            table_comments.append(comment)
    
    return table_comments


@app.get("/api/v1/approvals/pending")
async def get_pending_approvals():
    """Get pending approvals for approvers"""
    # Return comments that are pending approval
    pending_comments = [comment for comment in comments_storage if comment.get("status") == "pending"]
    return pending_comments

@app.post("/api/v1/approvals/{comment_id}/approve")
async def approve_comment(comment_id: str, feedback: str = None):
    """Approve a comment suggestion"""
    # Find the comment
    comment = None
    for c in comments_storage:
        if c.get("id") == comment_id:
            comment = c
            break
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Update comment status
    comment["status"] = "approved"
    comment["approved_at"] = "2024-01-15T14:00:00Z"
    comment["approved_by"] = "jane_approver"  # In real app, get from current user
    if feedback:
        comment["approval_feedback"] = feedback
    
    logger.info(f"Approved comment {comment_id}")
    return {"message": "Comment approved successfully", "comment": comment}

@app.post("/api/v1/approvals/{comment_id}/reject")
async def reject_comment(comment_id: str, feedback: str):
    """Reject a comment suggestion"""
    if not feedback:
        raise HTTPException(status_code=400, detail="Feedback is required for rejection")
    
    # Find the comment
    comment = None
    for c in comments_storage:
        if c.get("id") == comment_id:
            comment = c
            break
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Update comment status
    comment["status"] = "rejected"
    comment["rejected_at"] = "2024-01-15T14:00:00Z"
    comment["rejected_by"] = "jane_approver"  # In real app, get from current user
    comment["rejection_feedback"] = feedback
    
    logger.info(f"Rejected comment {comment_id}")
    return {"message": "Comment rejected successfully", "comment": comment}

@app.post("/api/v1/approvals/{comment_id}/apply")
async def apply_comment(comment_id: str):
    """Apply an approved comment to Databricks"""
    # Find the comment
    comment = None
    for c in comments_storage:
        if c.get("id") == comment_id:
            comment = c
            break
    
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Comment must be approved before applying")
    
    # Update comment status
    comment["status"] = "applied"
    comment["applied_at"] = "2024-01-15T15:00:00Z"
    comment["applied_by"] = "admin_user"  # In real app, get from current user
    
    # In a real implementation, this would update the Databricks catalog metadata
    logger.info(f"Applied comment {comment_id} to Databricks")
    return {"message": "Comment applied to Databricks successfully", "comment": comment}


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"{settings.APP_NAME} shutting down...")


@app.get("/api")
async def api_root():
    """API information endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "description": "Clean API-driven Databricks Metadata Manager",
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with database connectivity test"""
    from app.db.session import is_using_oauth
    from app.db.lakebase_oauth import get_lakebase_oauth_manager

    # Check if OAuth is being used for the database URL
    db_url_info = "not_configured"
    try:
        oauth_mgr = get_lakebase_oauth_manager()
        if oauth_mgr:
            schema = os.environ.get('LAKEBASE_SCHEMA', 'metadata_manager')
            effective_url = oauth_mgr.get_database_url(schema=schema)
            from urllib.parse import urlparse
            parsed = urlparse(effective_url)
            db_url_info = f"{parsed.scheme}://***:***@{parsed.hostname}/{parsed.path.lstrip('/')}"
        else:
            effective_url = settings.effective_database_url
            default_url = "postgresql://user:pass@localhost/dbname"
            if effective_url and effective_url != default_url:
                from urllib.parse import urlparse
                parsed = urlparse(effective_url)
                db_url_info = f"{parsed.scheme}://***:***@{parsed.hostname}/{parsed.path.lstrip('/')}"
    except Exception as e:
        db_url_info = f"error_getting_url: {str(e)}"

    # Get Lakebase env vars for debugging
    lakebase_env = {
        "LAKEBASE_INSTANCE": os.environ.get("LAKEBASE_INSTANCE"),
        "LAKEBASE_HOST": os.environ.get("LAKEBASE_HOST"),
        "LAKEBASE_SCHEMA": os.environ.get("LAKEBASE_SCHEMA"),
        "DATABRICKS_HOST": os.environ.get("DATABRICKS_HOST"),
        "DATABRICKS_CLIENT_ID": "***" if os.environ.get("DATABRICKS_CLIENT_ID") else None,
        "DATABRICKS_CLIENT_SECRET": "***" if os.environ.get("DATABRICKS_CLIENT_SECRET") else None,
        "DATABRICKS_TOKEN": "***" if os.environ.get("DATABRICKS_TOKEN") else None,
    }

    # Check OAuth status
    using_oauth = False
    oauth_token_expires_in = None
    oauth_username = None
    oauth_error = None
    try:
        using_oauth = is_using_oauth()
        if using_oauth:
            oauth_mgr = get_lakebase_oauth_manager()
            if oauth_mgr:
                oauth_token_expires_in = oauth_mgr.token_expires_in
                oauth_username = oauth_mgr.get_username()
    except Exception as e:
        oauth_error = str(e)
        logger.warning(f"Could not get OAuth status: {e}")

    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "services": {
            "auth_service": "available",
            "database": "unknown"
        },
        "database_url_configured": db_url_info != "not_configured",
        "database_url_info": db_url_info,
        "using_lakebase": settings.is_using_lakebase,
        "using_oauth": using_oauth,
        "lakebase_env": lakebase_env,
    }

    # Add OAuth details if using OAuth
    if using_oauth:
        health_status["oauth_token_expires_in"] = oauth_token_expires_in
        health_status["oauth_username"] = oauth_username

    if oauth_error:
        health_status["oauth_error"] = oauth_error

    # Test database connectivity using the session engine (which handles OAuth)
    try:
        from sqlalchemy import text
        from app.db.session import get_engine as get_session_engine

        # Use the session engine which handles OAuth token refresh
        engine = get_session_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            health_status["services"]["database"] = "connected"
            health_status["database_user_count"] = user_count
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")

    return health_status

@app.get("/")
async def serve_react_app():
    """Serve the React application"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    else:
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "message": "Frontend not built. Run 'npm run build' in the front-end directory.",
            "documentation": "/docs"
        }

# Catch-all route for React Router (must be last)
@app.get("/{full_path:path}")
async def serve_react_router(full_path: str):
    """Catch-all route to serve React app for client-side routing"""
    # Don't catch API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    # Serve index.html for all other routes (React Router will handle them)
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    else:
        raise HTTPException(status_code=404, detail="Frontend not found")