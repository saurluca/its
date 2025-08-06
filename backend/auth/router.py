from fastapi import Depends, HTTPException, status, Response
from auth.service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_by_id,
    update_user,
    delete_user,
    get_users,
    get_user_by_email,
)
from auth.models import (
    UserResponse,
    UserCreate,
    UserUpdate,
    UserListResponse,
)
from typing import Annotated
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import APIRouter
from auth.constants import ACCESS_TOKEN_EXPIRE_MINUTES
from dependencies import get_db_session
from auth.dependencies import get_current_user_from_request
from sqlmodel import Session
from uuid import UUID


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token")
async def login_for_access_token(
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db_session),
) -> dict:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    # Set HTTP-only cookie with the access token
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert minutes to seconds
        path="/",
    )

    return {"message": "Login successful"}


@router.post("/logout")
async def logout(
    response: Response,
    current_user: Annotated[UserResponse, Depends(get_current_user_from_request)],
):
    """Logout by clearing the access token cookie"""
    response.delete_cookie(key="access_token", path="/")
    return {"message": "Logout successful"}


@router.get("/users/me/", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[UserResponse, Depends(get_current_user_from_request)],
    db: Session = Depends(get_db_session),
):
    """Get current user information"""
    user = await get_user_by_email(current_user.email, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.post(
    "/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user_endpoint(
    user_data: UserCreate,
    db: Session = Depends(get_db_session),
):
    """Create a new user"""
    return await create_user(user_data, db)


@router.get("/users/", response_model=UserListResponse)
async def get_users_endpoint(
    current_user: Annotated[UserResponse, Depends(get_current_user_from_request)],
    db: Session = Depends(get_db_session),
    skip: int = 0,
    limit: int = 100,
):
    """Get all users with pagination"""
    users = await get_users(skip=skip, limit=limit, session=db)
    total = len(users)  # In a real app, you'd want to get total count from DB
    return UserListResponse(users=users, total=total)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_endpoint(
    user_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user_from_request)],
    db: Session = Depends(get_db_session),
):
    """Get user by ID"""
    user = await get_user_by_id(user_id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_endpoint(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user_from_request)],
    db: Session = Depends(get_db_session),
):
    """Update user by ID"""
    user = await update_user(user_id, user_data, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user_from_request)],
    db: Session = Depends(get_db_session),
):
    """Delete user by ID"""
    success = await delete_user(user_id, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return None
