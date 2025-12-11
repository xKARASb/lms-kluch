from sqlalchemy.orm import Session, joinedload
from app.models.lesson import Lesson, LessonAttachment
from app.schemas.lesson import LessonCreate, LessonUpdate, LessonAttachmentCreate
from typing import List, Optional

def get_lesson(db: Session, lesson_id: int):
    return db.query(Lesson).filter(Lesson.id == lesson_id).first()

def get_lesson_with_attachments(db: Session, lesson_id: int):
    return db.query(Lesson).options(
        joinedload(Lesson.attachments)
    ).filter(Lesson.id == lesson_id).first()

def get_lessons_by_course(db: Session, course_id: int):
    return db.query(Lesson).filter(
        Lesson.course_id == course_id
    ).order_by(Lesson.order).all()

def create_lesson(db: Session, lesson: LessonCreate):
    db_lesson = Lesson(**lesson.dict())
    db.add(db_lesson)
    db.commit()
    db.refresh(db_lesson)
    return db_lesson

def update_lesson(db: Session, lesson_id: int, lesson_update: LessonUpdate):
    db_lesson = get_lesson(db, lesson_id)
    if not db_lesson:
        return None
    
    update_data = lesson_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_lesson, field, value)
    
    db.commit()
    db.refresh(db_lesson)
    return db_lesson

def delete_lesson(db: Session, lesson_id: int):
    db_lesson = get_lesson(db, lesson_id)
    if db_lesson:
        db.delete(db_lesson)
        db.commit()
    return db_lesson

def create_attachment(db: Session, attachment: LessonAttachmentCreate):
    db_attachment = LessonAttachment(**attachment.dict())
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment

def get_attachment(db: Session, attachment_id: int):
    return db.query(LessonAttachment).filter(LessonAttachment.id == attachment_id).first()

def get_attachments(db: Session, lesson_id: int):
    return db.query(LessonAttachment).filter(
        LessonAttachment.lesson_id == lesson_id
    ).all()

def get_attachments_by_type(db: Session, lesson_id: int, file_type: str = None):
    """Получить вложения по типу файла"""
    query = db.query(LessonAttachment).filter(LessonAttachment.lesson_id == lesson_id)
    
    if file_type == 'image':
        query = query.filter(LessonAttachment.mime_type.like('image/%'))
    elif file_type == 'video':
        query = query.filter(LessonAttachment.is_video == True)
    elif file_type == 'document':
        query = query.filter(
            LessonAttachment.mime_type.like('application/%') | 
            LessonAttachment.mime_type.like('text/%')
        ).filter(LessonAttachment.is_video == False)
    
    return query.all()

def delete_attachment(db: Session, attachment_id: int):
    db_attachment = db.query(LessonAttachment).filter(
        LessonAttachment.id == attachment_id
    ).first()
    
    if db_attachment:
        db.delete(db_attachment)
        db.commit()
    
    return db_attachment

def get_attachment_by_filename(db: Session, lesson_id: int, filename: str):
    """Получить вложение по имени файла"""
    return db.query(LessonAttachment).filter(
        LessonAttachment.lesson_id == lesson_id,
        LessonAttachment.file_name == filename
    ).first()