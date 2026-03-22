"""
Authentication service — user registration, login, and token management.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token


async def register_user(db: AsyncSession, data: UserCreate) -> UserResponse:
    """
    Register a new user.

    Raises:
        ValueError: If username or email already exists.
    """
    # Check for duplicates
    existing = await db.execute(
        select(User).where(
            (User.username == data.username) | (User.email == data.email)
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Username or email already registered")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=UserRole(data.role),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    logger.info("User registered: id={} username='{}'", user.id, user.username)
    return UserResponse.model_validate(user)


async def authenticate_user(db: AsyncSession, data: UserLogin) -> TokenResponse:
    """
    Authenticate a user and return a JWT token.

    Raises:
        ValueError: If credentials are invalid.
    """
    result = await db.execute(
        select(User).where(User.username == data.username)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.hashed_password):
        raise ValueError("Invalid username or password")

    if not user.is_active:
        raise ValueError("User account is deactivated")

    # Create JWT with user ID as subject
    token = create_access_token(data={"sub": str(user.id), "role": user.role.value})

    logger.info("User logged in: id={} username='{}'", user.id, user.username)
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[UserResponse]:
    """Retrieve a paginated list of users."""
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.id)
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


async def get_user_by_id(db: AsyncSession, user_id: int) -> UserResponse:
    """
    Retrieve a single user by ID.

    Raises:
        ValueError: If user not found.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise ValueError(f"User with id {user_id} not found")
    return UserResponse.model_validate(user)
