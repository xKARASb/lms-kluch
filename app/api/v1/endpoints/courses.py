from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.course import CourseCreate, CourseUpdate, CourseResponse, CourseEnrollmentResponse
from app.crud import course as crud_course
from app.api.dependencies import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.services.file_service import FileService

router = APIRouter()
file_service = FileService()

@router.get("/", response_model=List[CourseResponse])
async def read_courses(
    skip: int = 0,
    limit: int = 100,
    author_id: Optional[int] = None,
    published_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить список курсов"""
    courses = crud_course.get_courses(
        db, 
        skip=skip, 
        limit=limit, 
        author_id=author_id,
        published_only=published_only
    )
    
    # Преобразуем в response с дополнительными полями
    response_courses = []
    for course in courses:
        course_dict = CourseResponse.from_orm(course)
        course_dict.lesson_count = len(course.lessons)
        course_dict.author_name = course.author.full_name
        response_courses.append(course_dict)
    
    return response_courses

@router.get("/my-courses", response_model=List[CourseResponse])
async def read_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить курсы текущего пользователя (как автор или студент)"""
    if current_user.role == UserRole.AUTHOR or current_user.role == UserRole.ADMIN:
        # Курсы, где пользователь автор
        courses = crud_course.get_courses(db, author_id=current_user.id, published_only=False)
    else:
        # Курсы, на которые записан студент
        enrollments = crud_course.get_user_enrollments(db, current_user.id)
        courses = [enrollment.course for enrollment in enrollments]
    
    response_courses = []
    for course in courses:
        course_dict = CourseResponse.from_orm(course)
        course_dict.lesson_count = len(course.lessons)
        course_dict.author_name = course.author.full_name
        response_courses.append(course_dict)
    
    return response_courses

@router.get("/{course_id}", response_model=CourseResponse)
async def read_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить курс по ID"""
    course = crud_course.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Проверяем доступ
    if not course.is_published and course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to view this course")
    
    course_dict = CourseResponse.from_orm(course)
    course_dict.lesson_count = len(course.lessons)
    course_dict.author_name = course.author.full_name
    
    return course_dict

@router.post("/", response_model=CourseResponse)
async def create_course(
    course: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.AUTHOR))
):
    """Создать новый курс (только для авторов)"""
    return crud_course.create_course(db=db, course=course, author_id=current_user.id)

@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: int,
    course_update: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Обновить курс"""
    course = crud_course.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Проверяем права
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this course")
    
    updated_course = crud_course.update_course(db, course_id=course_id, course_update=course_update)
    if not updated_course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    return updated_course

@router.delete("/{course_id}")
async def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Удалить курс"""
    course = crud_course.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Проверяем права
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this course")
    
    crud_course.delete_course(db, course_id=course_id)
    return {"message": "Course deleted successfully"}

@router.post("/{course_id}/enroll", response_model=CourseEnrollmentResponse)
async def enroll_in_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Записаться на курс"""
    course = crud_course.get_course(db, course_id=course_id)
    if not course or not course.is_published:
        raise HTTPException(status_code=404, detail="Course not found or not published")
    
    # Проверяем, не является ли пользователь автором курса
    if course.author_id == current_user.id:
        raise HTTPException(status_code=400, detail="Author cannot enroll in their own course")
    
    enrollment = crud_course.enroll_student(db, course_id=course_id, student_id=current_user.id)
    return enrollment

@router.post("/{course_id}/upload-thumbnail")
async def upload_thumbnail(
    course_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Загрузить обложку для курса"""
    course = crud_course.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Проверяем права
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Сохраняем файл
    file_path = await file_service.save_upload_file(file, subdir="courses/thumbnails")
    if not file_path:
        raise HTTPException(status_code=500, detail="Failed to save file")
    
    # Обновляем курс
    course.thumbnail_url = str(file_path)
    db.commit()
    db.refresh(course)
    
    return {"thumbnail_url": str(file_path)}