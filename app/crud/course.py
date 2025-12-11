from sqlalchemy.orm import Session, joinedload
from app.models.course import Course, CourseEnrollment
from app.schemas.course import CourseCreate, CourseUpdate
from typing import List, Optional

def get_course(db: Session, course_id: int):
    return db.query(Course).filter(Course.id == course_id).first()

def get_courses(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    author_id: Optional[int] = None,
    published_only: bool = True
):
    query = db.query(Course)
    
    if author_id:
        query = query.filter(Course.author_id == author_id)
    
    if published_only:
        query = query.filter(Course.is_published == True)
    
    return query.offset(skip).limit(limit).all()

def create_course(db: Session, course: CourseCreate, author_id: int):
    db_course = Course(**course.dict(), author_id=author_id)
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

def update_course(db: Session, course_id: int, course_update: CourseUpdate):
    db_course = get_course(db, course_id)
    if not db_course:
        return None
    
    update_data = course_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_course, field, value)
    
    db.commit()
    db.refresh(db_course)
    return db_course

def delete_course(db: Session, course_id: int):
    db_course = get_course(db, course_id)
    if db_course:
        db.delete(db_course)
        db.commit()
    return db_course

def enroll_student(db: Session, course_id: int, student_id: int):
    # Проверяем, не записан ли уже студент
    existing = db.query(CourseEnrollment).filter(
        CourseEnrollment.course_id == course_id,
        CourseEnrollment.student_id == student_id
    ).first()
    
    if existing:
        return existing
    
    enrollment = CourseEnrollment(course_id=course_id, student_id=student_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment

def get_user_enrollments(db: Session, user_id: int):
    return db.query(CourseEnrollment).filter(
        CourseEnrollment.student_id == user_id
    ).options(joinedload(CourseEnrollment.course)).all()