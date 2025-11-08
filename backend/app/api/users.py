"""
User management API endpoints
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, require_admin, get_current_user
from app.models.user import User, UserCreate, UserResponse, UserUpdate, PasswordChange, ProfileUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user_profile(
    profile_update: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile information"""
    # Update profile fields
    if profile_update.first_name is not None:
        current_user.first_name = profile_update.first_name

    if profile_update.last_name is not None:
        current_user.last_name = profile_update.last_name

    if profile_update.email is not None:
        current_user.email = profile_update.email

    db.commit()
    db.refresh(current_user)

    logger.info(f"User '{current_user.username}' updated their profile")

    return current_user


@router.post("/me/change-password")
def change_own_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change current user's password"""
    # OIDC users cannot change password
    if current_user.is_oidc_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="OIDC users cannot change password. Please use your identity provider.",
        )

    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    db.commit()

    logger.info(f"User '{current_user.username}' changed their password")

    return {"message": "Password changed successfully"}


@router.get("", response_model=List[UserResponse])
def list_users(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List all users (admin only)"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_create: UserCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new user (admin only)"""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_create.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Create new user
    hashed_password = get_password_hash(user_create.password)
    new_user = User(
        username=user_create.username,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
        is_oidc_user=False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Admin '{admin_user.username}' created user '{new_user.username}'")

    return new_user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent modifying the default admin account's role
    if user.username == "admin" and user_update.is_superuser is not None:
        if not user_update.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot remove admin privileges from default admin account",
            )

    # Update fields
    if user_update.first_name is not None:
        user.first_name = user_update.first_name

    if user_update.last_name is not None:
        user.last_name = user_update.last_name

    if user_update.email is not None:
        user.email = user_update.email

    if user_update.password is not None:
        # OIDC users cannot have password changed this way
        if user.is_oidc_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot set password for OIDC users",
            )
        user.hashed_password = get_password_hash(user_update.password)

    if user_update.is_active is not None:
        # Prevent deactivating the default admin account
        if user.username == "admin" and not user_update.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot deactivate default admin account",
            )
        user.is_active = user_update.is_active

    if user_update.is_superuser is not None:
        user.is_superuser = user_update.is_superuser

    db.commit()
    db.refresh(user)

    logger.info(f"Admin '{admin_user.username}' updated user '{user.username}'")

    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Delete user (admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent deleting the default admin account
    if user.username == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete default admin account",
        )

    # Prevent self-deletion
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own account",
        )

    username = user.username
    db.delete(user)
    db.commit()

    logger.info(f"Admin '{admin_user.username}' deleted user '{username}'")

    return {"message": f"User '{username}' deleted successfully"}
