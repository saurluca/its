from fastapi import APIRouter, HTTPException, status
from uuid import UUID

from courses.schemas import (
    CourseCreateRequest,
    CourseUpdateRequest,
    CourseResponse,
    CoursesListResponse,
    CourseDeleteResponse,
)
from courses.service import (
    create_course,
    get_course_by_id,
    get_all_courses,
    update_course,
    delete_course,
)
from courses.models import CourseCreate, CourseUpdate
from exceptions import DocumentNotFoundError

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("/", response_model=CoursesListResponse)
def get_courses():
    """
    Retrieve all courses with a limit of 100.
    Returns a list of courses ordered by creation date.
    """
    try:
        courses = get_all_courses(limit=100)
        course_responses = [
            CourseResponse(
                id=course.id,
                name=course.name,
                created_at=course.created_at,
                updated_at=course.updated_at,
            )
            for course in courses
        ]
        return CoursesListResponse(courses=course_responses)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_new_course(
    course_request: CourseCreateRequest,
):
    """
    Create a new course.
    Requires a course name in the request body.
    """
    try:
        course_data = CourseCreate(name=course_request.name)
        course = create_course(course_data)

        return CourseResponse(
            id=course.id,
            name=course.name,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{course_id}", response_model=CourseResponse)
def get_course(
    course_id: UUID,
):
    """
    Retrieve a specific course by its ID.
    Returns course details if found.
    """
    try:
        course = get_course_by_id(course_id)
        return CourseResponse(
            id=course.id,
            name=course.name,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )
    except DocumentNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{course_id}", response_model=CourseResponse)
def update_existing_course(
    course_id: UUID,
    course_request: CourseUpdateRequest,
):
    """
    Update an existing course by ID.
    Only provided fields will be updated.
    """
    try:
        course_update_data = CourseUpdate(
            **course_request.model_dump(exclude_unset=True)
        )
        course = update_course(course_id, course_update_data)

        return CourseResponse(
            id=course.id,
            name=course.name,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )
    except DocumentNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{course_id}", response_model=CourseDeleteResponse)
def delete_existing_course(
    course_id: UUID,
):
    """
    Delete a course by ID.
    Returns success status and the deleted course ID.
    """
    try:
        course = delete_course(course_id)
        return CourseDeleteResponse(success=True, id=course.id)
    except DocumentNotFoundError:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
