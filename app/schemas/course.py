from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime

class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_published: bool = False
    is_free: bool = False
    price: int = 0

class CourseCreate(CourseBase):
    pass

class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_published: Optional[bool] = None
    is_free: Optional[bool] = None
    price: Optional[int] = None

class CourseInDB(CourseBase):
    id: int
    author_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CourseResponse(CourseInDB):
    lesson_count: int = 0
    author_name: Optional[str] = None

class CourseEnrollmentBase(BaseModel):
    course_id: int

class CourseEnrollmentResponse(BaseModel):
    id: int
    course_id: int
    student_id: int
    enrolled_at: datetime
    completed_at: Optional[datetime]
    progress: int
    
    class Config:
        from_attributes = True