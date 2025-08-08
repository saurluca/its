from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
import jwt
from auth.models import UserCreate, UserUpdate, UserResponse, User
import os
from typing import Annotated, List
from fastapi import Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from auth.models import TokenData
from sqlmodel import Session, select
from dependencies import get_db_session
from auth.dependencies import get_current_user_from_request
from uuid import UUID

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")
if len(SECRET_KEY) < 32:
    raise ValueError("SECRET_KEY must be at least 32 characters long")
if not ALGORITHM:
    raise ValueError("ALGORITHM environment variable is required")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user_model_from_db(session: Session, email: str) -> User:
    """Get user model from database by email"""
    user = session.exec(select(User).where(User.email == email)).first()
    return user


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    """Authenticate user with database"""
    user = get_user_model_from_db(session, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Session = Depends(get_db_session),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception
    # Narrow Optional[str] to str for type-checker
    email_value = token_data.email
    if email_value is None:
        raise credentials_exception
    user = get_user_model_from_db(session, email=email_value)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


async def get_current_active_user_from_cookie(
    current_user: Annotated[UserResponse, Depends(get_current_user_from_request)],
):
    """Get current active user from cookie"""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Database CRUD operations
async def create_user(user_data: UserCreate, session: Session) -> User:
    """Create a new user"""
    # Check if email already exists
    existing_user = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if email already exists (if provided)
    if user_data.email:
        existing_email = session.exec(
            select(User).where(User.email == user_data.email)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        disabled=False,
    )

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


async def get_user_by_id(user_id: UUID, session: Session) -> User | None:
    """Get user by ID"""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        return None
    return user


async def get_user_by_email(email: str, session: Session) -> User | None:
    """Get user by email"""
    user = session.exec(select(User).where(User.email == email)).first()
    if not user:
        return None
    return user


async def update_user(
    user_id: UUID, user_data: UserUpdate, session: Session
) -> User | None:
    """Update user by ID"""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        return None

    # Check if new email already exists (if being updated)
    if user_data.email and user_data.email != user.email:
        existing_user = session.exec(
            select(User).where(User.email == user_data.email)
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists",
            )

    # Check if new email already exists (if being updated)
    if user_data.email and user_data.email != user.email:
        existing_email = session.exec(
            select(User).where(User.email == user_data.email)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
            )

    # Update fields
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.password is not None:
        user.hashed_password = get_password_hash(user_data.password)
    if user_data.disabled is not None:
        user.disabled = user_data.disabled

    user.updated_at = datetime.now()

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


async def delete_user(user_id: UUID, session: Session) -> bool:
    """Delete user by ID"""
    user = session.exec(select(User).where(User.id == user_id)).first()
    if not user:
        return False

    session.delete(user)
    session.commit()
    return True


async def get_users(
    skip: int = 0, limit: int = 100, session: Session = Depends(get_db_session)
) -> List[UserResponse]:
    """Get all users with pagination"""
    users = session.exec(select(User).offset(skip).limit(limit)).all()
    return users
