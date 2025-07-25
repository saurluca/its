from typing import List
from uuid import UUID
from sqlmodel import select
from datetime import datetime
from sqlalchemy import desc

from courses.models import Course, CourseCreate, CourseUpdate
from exceptions import DocumentNotFoundError
from utils import get_session


def create_course(course_data: CourseCreate) -> Course:
    """
    Create a new course

    Args:
        course_data: Course creation data

    Returns:
        Created course
    """
    with get_session() as session:
        course = Course.model_validate(course_data.model_dump())
        session.add(course)
        session.commit()
        session.refresh(course)
        return course


def get_course_by_id(course_id: UUID) -> Course:
    """
    Get course by ID

    Args:
        course_id: Course UUID

    Returns:
        Course object

    Raises:
        DocumentNotFoundError: If course not found
    """
    with get_session() as session:
        statement = select(Course).where(Course.id == course_id)
        course = session.exec(statement).first()

        if not course:
            raise DocumentNotFoundError(f"Course not found with id: {course_id}")

        return course


def get_all_courses(limit: int = 100) -> List[Course]:
    """
    Get all courses with limit

    Args:
        limit: Maximum number of courses to return

    Returns:
        List of courses
    """
    with get_session() as session:
        statement = select(Course).order_by(desc(Course.created_at)).limit(limit)
        courses = session.exec(statement).all()
        return list(courses)


def update_course(course_id: UUID, course_update: CourseUpdate) -> Course:
    """
    Update course by ID

    Args:
        course_id: Course UUID
        course_update: Course update data

    Returns:
        Updated course

    Raises:
        DocumentNotFoundError: If course not found
    """
    with get_session() as session:
        statement = select(Course).where(Course.id == course_id)
        course = session.exec(statement).first()

        if not course:
            raise DocumentNotFoundError(f"Course not found with id: {course_id}")

        # Update fields that are not None
        update_data = course_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(course, field, value)

        course.updated_at = datetime.utcnow()
        session.add(course)
        session.commit()
        session.refresh(course)

        return course


def delete_course(course_id: UUID) -> Course:
    """
    Delete course by ID

    Args:
        course_id: Course UUID

    Returns:
        Deleted course

    Raises:
        DocumentNotFoundError: If course not found
    """
    with get_session() as session:
        statement = select(Course).where(Course.id == course_id)
        course = session.exec(statement).first()

        if not course:
            raise DocumentNotFoundError(f"Course not found with id: {course_id}")

        session.delete(course)
        session.commit()

        return course
