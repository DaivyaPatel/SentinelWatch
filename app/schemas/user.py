"""
User-related Pydantic schemas for request validation and response serialization.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    """POST /auth/register request body."""
    username: str = Field(..., min_length=3, max_length=50, examples=["operator_john"])
    email: EmailStr = Field(..., examples=["john@urbansafety.com"])
    password: str = Field(..., min_length=6, max_length=128, examples=["SecurePass123!"])
    role: str = Field(default="operator", pattern="^(admin|operator)$", examples=["operator"])


class UserLogin(BaseModel):
    """POST /auth/login request body."""
    username: str = Field(..., examples=["operator_john"])
    password: str = Field(..., examples=["SecurePass123!"])


class UserUpdate(BaseModel):
    """PATCH /users/{id} request body."""
    email: Optional[EmailStr] = None
    role: Optional[str] = Field(default=None, pattern="^(admin|operator)$")
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class UserResponse(BaseModel):
    """Standard user response (password excluded)."""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """POST /auth/login response."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
