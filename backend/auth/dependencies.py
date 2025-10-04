from fastapi import Request, Depends, HTTPException, status, WebSocket
import jwt
from jwt.exceptions import InvalidTokenError
from auth.models import TokenData, UserResponse
from dependencies import get_db_session
from sqlmodel import Session, select
from auth.models import User
from constants import SECRET_KEY, ALGORITHM
from starlette.websockets import WebSocketDisconnect


def get_user_from_db(db: Session, email: str):
    """Get user from database by email"""
    user = db.exec(select(User).where(User.email == email)).first()
    if not user:
        return None
    return UserResponse(
        id=str(user.id),
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
        email = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except InvalidTokenError:
        raise credentials_exception

    # Narrow Optional[str] to str for type-checker and safety
    email_value = token_data.email
    if email_value is None:
        raise credentials_exception
    user = get_user_from_db(db, email=email_value)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_from_websocket(
    websocket: WebSocket, db: Session = Depends(get_db_session)
):
    """Authenticate a websocket connection via the HTTP-only access token."""

    token = websocket.cookies.get("access_token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise InvalidTokenError()
        token_data = TokenData(email=email)
    except InvalidTokenError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

    email_value = token_data.email
    if email_value is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

    user = get_user_from_db(db, email=email_value)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION)

    return user
