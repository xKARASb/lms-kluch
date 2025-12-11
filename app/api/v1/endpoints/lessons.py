from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
import os
from app.database import get_db
from app.schemas.lesson import LessonCreate, LessonUpdate, LessonResponse, LessonAttachmentCreate, LessonAttachmentResponse
from app.crud import lesson as crud_lesson
from app.crud import course as crud_course
from app.api.dependencies import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.services.file_service import FileService
from app.services.markdown_service import MarkdownService
from app.config import settings

router = APIRouter()
file_service = FileService()
markdown_service = MarkdownService()

@router.get("/course/{course_id}", response_model=List[LessonResponse])
async def read_lessons(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить все уроки курса"""
    course = crud_course.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Проверяем доступ
    if not course.is_published and course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to view lessons")
    
    lessons = crud_lesson.get_lessons_by_course(db, course_id=course_id)
    return lessons

@router.get("/{lesson_id}", response_model=LessonResponse)
async def read_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить урок по ID"""
    lesson = crud_lesson.get_lesson_with_attachments(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем доступ к курсу
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if not course.is_published and course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to view this lesson")
    
    return lesson

@router.post("/", response_model=LessonResponse)
async def create_lesson(
    lesson: LessonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.AUTHOR))
):
    """Создать новый урок"""
    # Проверяем, что курс существует и пользователь автор
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to add lessons to this course")
    
    return crud_lesson.create_lesson(db=db, lesson=lesson)

@router.put("/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: int,
    lesson_update: LessonUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Обновить урок"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем права
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this lesson")
    
    updated_lesson = crud_lesson.update_lesson(db, lesson_id=lesson_id, lesson_update=lesson_update)
    if not updated_lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    return updated_lesson

@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Удалить урок"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем права
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete this lesson")
    
    crud_lesson.delete_lesson(db, lesson_id=lesson_id)
    return {"message": "Lesson deleted successfully"}

@router.post("/{lesson_id}/upload-attachment", response_model=LessonAttachmentResponse)
async def upload_attachment(
    lesson_id: int,
    file: UploadFile = File(...),
    is_video: bool = Form(False),
    video_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Загрузить вложение для урока"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем права
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    attachment_data = {}
    
    if is_video and video_url:
        # Обработка видео из Rutube
        video_id = file_service.extract_rutube_id(video_url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid Rutube URL")
        
        attachment_data = {
            "file_name": f"rutube_video_{video_id}",
            "file_path": video_url,
            "is_video": True,
            "video_provider": "rutube",
            "video_id": video_id,
            "mime_type": "video/rutube"
        }
    else:
        # Загрузка обычного файла
        file_path = await file_service.save_upload_file(file, subdir=f"lessons/{lesson_id}")
        if not file_path:
            raise HTTPException(status_code=500, detail="Failed to save file")
        
        mime_type = file_service.get_file_mime_type(file_path)
        file_size = file_service.get_file_size(file_path)
        
        attachment_data = {
            "file_name": file.filename or str(file_path.name),
            "file_path": str(file_path),
            "file_size": file_size,
            "mime_type": mime_type,
            "is_video": mime_type.startswith('video/') if not is_video else is_video,
            "video_provider": "uploaded" if mime_type.startswith('video/') else None
        }
    
    # Создаем запись вложения
    attachment_create = LessonAttachmentCreate(
        lesson_id=lesson_id,
        **attachment_data
    )
    
    return crud_lesson.create_attachment(db, attachment_create)

@router.post("/{lesson_id}/markdown-preview")
async def preview_markdown(
    lesson_id: int,
    markdown_content: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Предпросмотр Markdown контента"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем права
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Конвертируем Markdown в HTML
    html_content = markdown_service.convert_to_html(markdown_content)
    
    return {"html_content": html_content}

@router.get("/{lesson_id}/attachments", response_model=List[LessonAttachmentResponse])
async def get_lesson_attachments(
    lesson_id: int,
    file_type: Optional[str] = None,  # 'image', 'video', 'document'
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить все вложения урока"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем доступ к курсу
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if not course.is_published and course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to view attachments")
    
    if file_type:
        attachments = crud_lesson.get_attachments_by_type(db, lesson_id=lesson_id, file_type=file_type)
    else:
        attachments = crud_lesson.get_attachments(db, lesson_id=lesson_id)
    
    # Преобразуем пути в URL
    response_attachments = []
    for attachment in attachments:
        attachment_dict = LessonAttachmentResponse.from_orm(attachment)
        
        # Преобразуем локальный путь в URL
        if attachment.file_path and not attachment.file_path.startswith(('http://', 'https://')):
            # Если это локальный файл, преобразуем путь в URL
            try:
                # Относительный путь от базовой директории загрузок
                rel_path = os.path.relpath(attachment.file_path, settings.UPLOAD_DIR)
                attachment_dict.file_url = f"/uploads/{rel_path.replace(os.path.sep, '/')}"
            except ValueError:
                # Если путь не внутри UPLOAD_DIR, оставляем как есть
                attachment_dict.file_url = attachment.file_path
        else:
            # Если это URL (например, Rutube), оставляем как есть
            attachment_dict.file_url = attachment.file_path
        
        response_attachments.append(attachment_dict)
    
    return response_attachments

@router.get("/{lesson_id}/attachments/{attachment_id}", response_model=LessonAttachmentResponse)
async def get_lesson_attachment(
    lesson_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить информацию о конкретном вложении"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем доступ к курсу
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if not course.is_published and course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to view attachment")
    
    attachment = crud_lesson.get_attachment(db, attachment_id=attachment_id)
    if not attachment or attachment.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Преобразуем путь в URL
    attachment_dict = LessonAttachmentResponse.from_orm(attachment)
    
    if attachment.file_path and not attachment.file_path.startswith(('http://', 'https://')):
        try:
            rel_path = os.path.relpath(attachment.file_path, settings.UPLOAD_DIR)
            attachment_dict.file_url = f"/uploads/{rel_path.replace(os.path.sep, '/')}"
        except ValueError:
            attachment_dict.file_url = attachment.file_path
    else:
        attachment_dict.file_url = attachment.file_path
    
    return attachment_dict

@router.get("/{lesson_id}/attachments/{attachment_id}/download")
async def download_lesson_attachment(
    lesson_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Скачать файл вложения"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем доступ к курсу
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if not course.is_published and course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to download attachment")
    
    attachment = crud_lesson.get_attachment(db, attachment_id=attachment_id)
    if not attachment or attachment.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Проверяем тип файла
    if attachment.file_path.startswith(('http://', 'https://')):
        # Если это внешний URL (например, Rutube), перенаправляем
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=attachment.file_path)
    
    # Проверяем существование файла
    file_path = Path(attachment.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Определяем Content-Type
    media_type = attachment.mime_type or "application/octet-stream"
    
    # Отправляем файл
    from fastapi.responses import FileResponse
    return FileResponse(
        path=file_path,
        filename=attachment.file_name,
        media_type=media_type,
        headers={
            "Content-Disposition": f"attachment; filename={attachment.file_name}"
        }
    )

@router.get("/{lesson_id}/attachments/{attachment_id}/preview")
async def preview_lesson_attachment(
    lesson_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Предпросмотр файла вложения (для изображений, PDF и т.д.)"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем доступ к курсу
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if not course.is_published and course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to preview attachment")
    
    attachment = crud_lesson.get_attachment(db, attachment_id=attachment_id)
    if not attachment or attachment.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Проверяем, можно ли предпросматривать этот тип файла
    previewable_types = [
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp', 'image/svg+xml',
        'application/pdf',
        'text/plain', 'text/html', 'text/markdown', 'text/css', 'application/javascript',
        'application/json', 'application/xml'
    ]
    
    if attachment.mime_type not in previewable_types:
        raise HTTPException(
            status_code=400, 
            detail="This file type cannot be previewed. Please download it instead."
        )
    
    if attachment.file_path.startswith(('http://', 'https://')):
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=attachment.file_path)
    
    file_path = Path(attachment.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Для текстовых файлов читаем содержимое
    if attachment.mime_type.startswith('text/') or attachment.mime_type in [
        'application/json', 'application/xml'
    ]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "filename": attachment.file_name,
                "mime_type": attachment.mime_type,
                "content": content,
                "size": file_path.stat().st_size
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cannot read file: {str(e)}")
    
    # Для изображений и PDF возвращаем файл с inline content-disposition
    from fastapi.responses import FileResponse
    
    # Определяем, inline или attachment
    content_disposition = "inline"
    if attachment.mime_type == 'application/pdf':
        content_disposition = "inline; filename=\"{}\"".format(attachment.file_name)
    
    return FileResponse(
        path=file_path,
        filename=attachment.file_name,
        media_type=attachment.mime_type,
        headers={"Content-Disposition": content_disposition}
    )

@router.delete("/{lesson_id}/attachments/{attachment_id}")
async def delete_lesson_attachment(
    lesson_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Удалить вложение урока"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем права (только автор курса или админ)
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to delete attachment")
    
    attachment = crud_lesson.get_attachment(db, attachment_id=attachment_id)
    if not attachment or attachment.lesson_id != lesson_id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Удаляем физический файл если он локальный
    if attachment.file_path and not attachment.file_path.startswith(('http://', 'https://')):
        try:
            file_path = Path(attachment.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"Error deleting file {attachment.file_path}: {e}")
    
    # Удаляем запись из БД
    crud_lesson.delete_attachment(db, attachment_id=attachment_id)
    
    return {"message": "Attachment deleted successfully"}

@router.get("/{lesson_id}/attachments/stats")
async def get_lesson_attachments_stats(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Получить статистику по вложениям урока"""
    lesson = crud_lesson.get_lesson(db, lesson_id=lesson_id)
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Проверяем доступ к курсу
    course = crud_course.get_course(db, course_id=lesson.course_id)
    if not course.is_published and course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    attachments = crud_lesson.get_attachments(db, lesson_id=lesson_id)
    
    # Собираем статистику
    stats = {
        "total": len(attachments),
        "by_type": {
            "images": 0,
            "videos": 0,
            "documents": 0,
            "other": 0
        },
        "total_size": 0,
        "external_links": 0
    }
    
    for attachment in attachments:
        # Размер (только для локальных файлов)
        if attachment.file_path and not attachment.file_path.startswith(('http://', 'https://')):
            try:
                file_path = Path(attachment.file_path)
                if file_path.exists():
                    stats["total_size"] += file_path.stat().st_size
            except:
                pass
        else:
            stats["external_links"] += 1
        
        # Типы файлов
        if attachment.is_video:
            stats["by_type"]["videos"] += 1
        elif attachment.mime_type and attachment.mime_type.startswith('image/'):
            stats["by_type"]["images"] += 1
        elif attachment.mime_type and (
            attachment.mime_type.startswith('text/') or 
            attachment.mime_type.startswith('application/') and 
            not attachment.mime_type.startswith('application/octet-stream')
        ):
            stats["by_type"]["documents"] += 1
        else:
            stats["by_type"]["other"] += 1
    
    # Форматируем размер
    def format_size(size_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0 or unit == 'GB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
    
    stats["formatted_size"] = format_size(stats["total_size"])
    
    return stats