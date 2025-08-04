from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
import jwt
from auth.schemas import UserInDB, UserCreate, UserUpdate, UserResponse
import os
from typing import Annotated, List, Optional
from fastapi import Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from auth.schemas import TokenData, User
from sqlmodel import Session, select
from auth.models import User as UserModel
from dependencies import get_db_session


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user_from_db(db: Session, username: str):
    """Get user from database by username"""
    user = db.exec(select(UserModel).where(UserModel.username == username)).first()
    if not user:
        return None
    return UserInDB(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        hashed_password=user.hashed_password,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user with database"""
    user = get_user_from_db(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db_session)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user_from_db(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Database CRUD operations
async def create_user(user_data: UserCreate, db: Session) -> UserResponse:
    """Create a new user"""
    # Check if username already exists
    existing_user = db.exec(
        select(UserModel).where(UserModel.username == user_data.username)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email already exists (if provided)
    if user_data.email:
        existing_email = db.exec(
            select(UserModel).where(UserModel.email == user_data.email)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = UserModel(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hashed_password,
        disabled=False,
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return UserResponse(
        id=str(db_user.id),
        username=db_user.username,
        email=db_user.email,
        full_name=db_user.full_name,
        disabled=db_user.disabled,
        created_at=db_user.created_at,
        updated_at=db_user.updated_at,
    )


async def get_user_by_id(user_id: str, db: Session) -> Optional[UserResponse]:
    """Get user by ID"""
    user = db.exec(select(UserModel).where(UserModel.id == user_id)).first()
    if not user:
        return None

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def get_user_by_username(username: str, db: Session) -> Optional[UserResponse]:
    """Get user by username"""
    user = db.exec(select(UserModel).where(UserModel.username == username)).first()
    if not user:
        return None

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def update_user(
    user_id: str, user_data: UserUpdate, db: Session
) -> Optional[UserResponse]:
    """Update user by ID"""
    user = db.exec(select(UserModel).where(UserModel.id == user_id)).first()
    if not user:
        return None

    # Check if new username already exists (if being updated)
    if user_data.username and user_data.username != user.username:
        existing_user = db.exec(
            select(UserModel).where(UserModel.username == user_data.username)
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    # Check if new email already exists (if being updated)
    if user_data.email and user_data.email != user.email:
        existing_email = db.exec(
            select(UserModel).where(UserModel.email == user_data.email)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
            )

    # Update fields
    if user_data.username is not None:
        user.username = user_data.username
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.password is not None:
        user.hashed_password = get_password_hash(user_data.password)
    if user_data.disabled is not None:
        user.disabled = user_data.disabled

    user.updated_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def delete_user(user_id: str, db: Session) -> bool:
    """Delete user by ID"""
    user = db.exec(select(UserModel).where(UserModel.id == user_id)).first()
    if not user:
        return False

    db.delete(user)
    db.commit()
    return True


async def get_users(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db_session)
) -> List[UserResponse]:
    """Get all users with pagination"""
    users = db.exec(select(UserModel).offset(skip).limit(limit)).all()

    return [
        UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]
