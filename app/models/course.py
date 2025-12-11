from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON
from app.database import Base
from datetime import datetime

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text)
    short_description = Column(String(500))
    thumbnail_url = Column(String)
    is_published = Column(Boolean, default=False)
    is_free = Column(Boolean, default=False)
    price = Column(Integer, default=0)  # В копейках/центах
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    author = relationship("User", back_populates="courses_authored", foreign_keys=[author_id])
    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", back_populates="course", cascade="all, delete-orphan")

class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    progress = Column(Integer, default=0)  # Процент завершения
    
    # Отношения
    course = relationship("Course", back_populates="enrollments")
    student = relationship("User", back_populates="enrolled_courses")