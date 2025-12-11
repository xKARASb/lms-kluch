from sqlalchemy import Boolean, Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    AUTHOR = "author"
    STUDENT = "student"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    courses_authored = relationship("Course", back_populates="author", foreign_keys="Course.author_id")
    enrolled_courses = relationship("CourseEnrollment", back_populates="student")