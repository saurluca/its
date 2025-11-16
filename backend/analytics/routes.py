# analytics/routes.py
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, func

from tasks.models import Task
from auth.models import User
from auth.dependencies import get_current_user_from_request, get_db_session
from analytics.models import PageType, UserPageSession
from analytics.queries import get_page_usage_stats



router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/pages/{page}/stats")
def page_stats(
    page: PageType,
    limit_users: int = Query(10, ge=1, le=50),
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request)
):
    """Get usage statistics for a specific page"""
    return get_page_usage_stats(session, page, limit_users)


@router.post("/pages/{page}/enter")
def enter_page(
    page: PageType,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request),
):
    # Close any existing "open" session for this user + page
    open_session = session.exec(
        select(UserPageSession)
        .where(UserPageSession.user_id == current_user.id)
        .where(UserPageSession.page == page)
        .where(UserPageSession.left_at.is_(None))
    ).first()

    if open_session:
        open_session.left_at = datetime.utcnow()
        open_session.duration_seconds = int(
            (open_session.left_at - open_session.entered_at).total_seconds()
        )
        session.add(open_session)

    # Create new session
    new_session = UserPageSession(
        user_id=current_user.id,
        page=page,
        entered_at=datetime.utcnow(),
    )
    session.add(new_session)
    session.commit()
    session.refresh(new_session)

    return {"status": "entered", "page": page, "session_id": new_session.id}


@router.post("/pages/{page}/leave")
def leave_page(
    page: PageType,
    session: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user_from_request),
):
    # Find open session
    open_session = session.exec(
        select(UserPageSession)
        .where(UserPageSession.user_id == current_user.id)
        .where(UserPageSession.page == page)
        .where(UserPageSession.left_at.is_(None))
    ).first()

    if not open_session:
        raise HTTPException(status_code=404, detail="No active session found")

    open_session.left_at = datetime.utcnow()
    open_session.duration_seconds = int(
        (open_session.left_at - open_session.entered_at).total_seconds()
    )

    session.add(open_session)
    session.commit()
    session.refresh(open_session)

    return {
        "status": "left",
        "page": page,
        "duration_seconds": open_session.duration_seconds,
    }