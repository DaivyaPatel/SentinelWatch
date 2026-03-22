"""
Authentication router — registration, login, and user management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse, UserUpdate,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        201: {
            "description": "User registered successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "username": "operator_john",
                        "email": "john@urbansafety.com",
                        "role": "operator",
                        "is_active": True,
                        "created_at": "2026-03-21T16:30:00Z",
                        "updated_at": "2026-03-21T16:30:00Z",
                    }
                }
            },
        },
        400: {"description": "Username or email already exists"},
    },
)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new operator or admin user."""
    try:
        return await auth_service.register_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and get JWT token",
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIs...",
                        "token_type": "bearer",
                        "user": {
                            "id": 1,
                            "username": "operator_john",
                            "email": "john@urbansafety.com",
                            "role": "operator",
                            "is_active": True,
                            "created_at": "2026-03-21T16:30:00Z",
                            "updated_at": "2026-03-21T16:30:00Z",
                        },
                    }
                }
            },
        },
        400: {"description": "Invalid credentials"},
    },
)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with username and password, receive a JWT token."""
    try:
        return await auth_service.authenticate_user(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users (admin only)",
    dependencies=[Depends(get_current_admin)],
)
async def list_users(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to list all registered users."""
    return await auth_service.get_all_users(db, skip, limit)
