from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import tempfile
import shutil
from pathlib import Path
from app.database import get_db
from app.api.dependencies import get_current_active_user, require_role
from app.models.user import User, UserRole
from app.crud import course as crud_course
from app.crud import lesson as crud_lesson
from app.services.scorm_parser import SCORMParser
from app.schemas.lesson import LessonCreate, LessonAttachmentCreate
from app.config import settings
import os
import logging

router = APIRouter()
scorm_parser = SCORMParser()
logger = logging.getLogger(__name__)

@router.post("/import/{course_id}")
async def import_scorm_package(
    course_id: int,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.AUTHOR))
):
    """Импортировать SCORM пакет в курс с сохранением изображений"""
    # Проверяем курс
    course = crud_course.get_course(db, course_id=course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    # Проверяем права
    if course.author_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Проверяем тип файла
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ['.zip', '.scorm', '.pif']:
        raise HTTPException(
            status_code=400, 
            detail="File must be a ZIP or SCORM package (.zip, .scorm, .pif)"
        )
    
    # Сохраняем временный файл
    temp_dir = tempfile.mkdtemp(prefix="scorm_import_")
    temp_file_path = Path(temp_dir) / (file.filename or "scorm_package.zip")
    
    try:
        logger.info(f"Начало импорта SCORM пакета для курса {course_id}")
        
        # Сохраняем загруженный файл
        with open(temp_file_path, 'wb') as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Файл сохранен: {temp_file_path}, размер: {temp_file_path.stat().st_size} байт")
        
        # Извлекаем и парсим SCORM пакет
        extract_dir = Path(scorm_parser.upload_dir) / f"course_{course_id}_{os.urandom(4).hex()}"
        logger.info(f"Извлечение в: {extract_dir}")
        
        metadata = scorm_parser.extract_scorm_package(temp_file_path, extract_dir)
        extracted_path = metadata['extracted_path']
        
        # Создаем уроки из SCORM контента
        lessons_created = []
        failed_conversions = []
        
        logger.info(f"Найдено HTML файлов: {len(metadata.get('html_files', []))}")
        logger.info(f"Найдено изображений: {len(metadata.get('image_files', []))}")
        
        for i, html_file in enumerate(metadata.get('html_files', [])):
            try:
                logger.info(f"Обработка файла {i+1}: {html_file}")
                
                # Сначала создаем урок с временным заголовком
                file_name = Path(html_file).stem
                temp_title = f"{file_name}"
                if len(metadata.get('html_files', [])) > 1:
                    temp_title = f"Урок {i+1}: {temp_title}"
                
                lesson_data = LessonCreate(
                    title=temp_title,
                    content="Конвертация...",
                    course_id=course_id,
                    order=i
                )
                
                lesson = crud_lesson.create_lesson(db, lesson_data)
                lesson_id = lesson.id
                
                # Конвертируем HTML в Markdown с обработкой изображений
                markdown_content, images_info = scorm_parser.convert_to_markdown_with_images(
                    html_file,
                    extracted_path,
                    settings.UPLOAD_DIR,
                    course_id,
                    lesson_id
                )
                
                # Обновляем урок с конвертированным контентом
                lesson.title = temp_title  # Можно улучшить, извлекая заголовок из HTML
                lesson.content = markdown_content
                
                # Сохраняем SCORM метаданные
                lesson.scorm_data = {
                    "source_file": html_file,
                    "scorm_metadata": {
                        'title': metadata.get('title'),
                        'description': metadata.get('description'),
                        'encoding_used': metadata.get('encoding_used')
                    },
                    "original_file_name": file_name,
                    "imported_from_scorm": True,
                    "images_count": len(images_info)
                }
                
                # Создаем записи для прикрепленных изображений
# В функции import_scorm_package, после обработки изображений добавьте:
                for img_info in images_info:
                    # Определяем MIME-тип по расширению
                    ext = Path(img_info['filename']).suffix.lower()
                    mime_types = {
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.gif': 'image/gif',
                        '.bmp': 'image/bmp',
                        '.svg': 'image/svg+xml',
                        '.webp': 'image/webp'
                    }
                    mime_type = mime_types.get(ext, 'application/octet-stream')
                    
                    # Проверяем размер файла
                    file_size = Path(img_info['new_path']).stat().st_size
                    
                    # Создаем запись вложения
                    attachment_data = LessonAttachmentCreate(
                        lesson_id=lesson_id,
                        file_name=img_info['filename'],
                        file_path=img_info['new_path'],
                        file_size=file_size,
                        mime_type=mime_type,
                        is_video=False
                    )
                    
                    # Создаем вложение в базе данных
                    crud_lesson.create_attachment(db, attachment_data)
                    logger.info(f"Создано вложение: {img_info['filename']}")

                db.commit()
                db.refresh(lesson)
                
                lessons_created.append({
                    'id': lesson.id,
                    'title': lesson.title,
                    'file': html_file,
                    'content_length': len(markdown_content),
                    'images_count': len(images_info)
                })
                
                logger.info(f"Создан урок {lesson.id}: {lesson.title}, изображений: {len(images_info)}")
                
            except Exception as e:
                logger.error(f"Ошибка при создании урока из файла {html_file}: {str(e)}")
                failed_conversions.append({
                    'file': html_file,
                    'error': str(e)
                })
                continue
        
        # Удаляем временный файл
        shutil.rmtree(temp_dir)
        
        # Очищаем извлеченные файлы через background task
        if background_tasks:
            background_tasks.add_task(scorm_parser.cleanup_extracted_files, extracted_path)
        
        response = {
            "message": f"SCORM пакет успешно обработан",
            "summary": {
                "total_files_found": len(metadata.get('html_files', [])),
                "lessons_created": len(lessons_created),
                "failed_conversions": len(failed_conversions),
                "total_images_found": len(metadata.get('image_files', [])),
                "images_processed": sum(lesson.get('images_count', 0) for lesson in lessons_created)
            },
            "lessons_created": lessons_created,
            "failed_conversions": failed_conversions if failed_conversions else None,
            "metadata": {
                "title": metadata.get('title'),
                "description": metadata.get('description'),
                "organizations": len(metadata.get('organizations', [])),
                "resources": len(metadata.get('resources', []))
            }
        }
        
        if failed_conversions:
            response["warning"] = f"Не удалось конвертировать {len(failed_conversions)} файлов"
        
        logger.info(f"Импорт завершен: создано {len(lessons_created)} уроков")
        return response
        
    except Exception as e:
        logger.error(f"Ошибка импорта SCORM пакета: {str(e)}")
        
        # Очищаем в случае ошибки
        if Path(temp_dir).exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Не удалось импортировать SCORM пакет: {str(e)}"
        )