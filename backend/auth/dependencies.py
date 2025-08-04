from fastapi import Request, Depends, HTTPException, status
import jwt
from jwt.exceptions import InvalidTokenError
from auth.schemas import TokenData, User
from dependencies import get_db_session
from sqlmodel import Session, select
from auth.models import User as UserModel
import os


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


def get_user_from_db(db: Session, username: str):
    """Get user from database by username"""
    user = db.exec(select(UserModel).where(UserModel.username == username)).first()
    if not user:
        return None
    return User(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def get_current_user_from_request(
    request: Request, db: Session = Depends(get_db_session)
):
    """Get current user from HTTP-only cookie"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Get token from cookie
    token = request.cookies.get("access_token")
    if not token:
        raise credentials_exception

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
