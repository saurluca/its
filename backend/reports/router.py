from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlmodel import Session

from auth.dependencies import get_current_user_from_request
from dependencies import get_db_session
from reports.models import Report, ReportCreate, ReportRead
from auth.models import UserResponse


router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportRead, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    request: Request,
    db: Session = Depends(get_db_session),
    current_user: UserResponse = Depends(get_current_user_from_request),
):
    """Create a new user report.

    The frontend should send the current page URL. We also capture the user agent.
    """

    if not payload.url:
        raise HTTPException(status_code=400, detail="url is required")

    user_agent_header = request.headers.get("user-agent")

    report = Report(
        report_type=payload.report_type or "generic",
        url=payload.url,
        category_tags=payload.category_tags,
        message=payload.message,
        user_agent=payload.user_agent or user_agent_header,
        task_id=payload.task_id,
        unit_id=payload.unit_id,
        user_id=current_user.id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return ReportRead(
        id=report.id,
        report_type=report.report_type,
        url=report.url,
        category_tags=report.category_tags,
        message=report.message,
        user_agent=report.user_agent,
        task_id=report.task_id,
        unit_id=report.unit_id,
        user_id=report.user_id,
        created_at=report.created_at,
    )
