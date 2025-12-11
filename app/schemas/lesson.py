from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class LessonBase(BaseModel):
    title: str
    content: Optional[str] = None
    order: int = 0
    is_published: bool = False

class LessonCreate(LessonBase):
    course_id: int

class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None
    is_published: Optional[bool] = None

class LessonAttachmentBase(BaseModel):
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    is_video: bool = False
    video_provider: Optional[str] = None
    video_id: Optional[str] = None

class LessonAttachmentCreate(LessonAttachmentBase):
    lesson_id: int

class LessonAttachmentResponse(LessonAttachmentBase):
    id: int
    lesson_id: int
    created_at: datetime
    file_url: Optional[str] = None  # Добавлено поле для URL
    
    class Config:
        from_attributes = True

class LessonInDB(LessonBase):
    id: int
    course_id: int
    created_at: datetime
    updated_at: datetime
    scorm_data: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class LessonResponse(LessonInDB):
    attachments: List[LessonAttachmentResponse] = []
    attachment_count: int = 0
    
    @validator('attachment_count', always=True)
    def compute_attachment_count(cls, v, values):
        if 'attachments' in values:
            return len(values['attachments'])
        return 0