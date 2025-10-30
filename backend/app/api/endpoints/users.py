from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import uuid
from app.db.session import get_db
from app.models import User, UserRole
from app.schemas.user import User as UserSchema, UserUpdate
from app.api.dependencies.auth import get_current_active_user, get_admin_user
from app.core.security import get_password_hash

router = APIRouter()


@router.get("/", response_model=List[UserSchema])
async def list_users(
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    return current_user


@router.get("/{user_id}", response_model=UserSchema)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get a specific user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: uuid.UUID,
    user_update: UserUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields if provided
    if user_update.email is not None:
        # Check if email is already taken
        existing = db.query(User).filter(
            User.email == user_update.email,
            User.id != user_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = user_update.email
    
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    
    if user_update.role is not None:
        user.role = user_update.role
    
    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    
    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Delete a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}


@router.get("/roles/summary", response_model=dict)
async def get_roles_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get summary of users by role."""
    summary = {}
    
    for role in UserRole:
        count = db.query(User).filter(User.role == role, User.is_active == True).count()
        summary[role.value] = count
    
    total = db.query(User).filter(User.is_active == True).count()
    summary["total_active"] = total
    
    return summary