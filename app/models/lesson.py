from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.sqlite import JSON
from app.database import Base
from datetime import datetime

class Lesson(Base):
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text)  # Markdown контент
    order = Column(Integer, default=0)  # Порядок в курсе
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Метаданные для SCORM
    scorm_data = Column(JSON, nullable=True)
    quiz = relationship("Quiz", back_populates="lesson", uselist=False)
    
    # Отношения
    course = relationship("Course", back_populates="lessons")
    attachments = relationship("LessonAttachment", back_populates="lesson", cascade="all, delete-orphan")

class LessonAttachment(Base):
    __tablename__ = "lesson_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer)  # В байтах
    mime_type = Column(String)
    is_video = Column(Boolean, default=False)
    video_provider = Column(String)  # 'rutube', 'youtube', 'vimeo', 'uploaded'
    video_id = Column(String)  # ID видео на Rutube или другом сервисе
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    lesson = relationship("Lesson", back_populates="attachments")