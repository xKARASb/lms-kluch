import os
from pathlib import Path
from typing import Optional
from app.config import settings

def get_file_url(file_path: str) -> str:
    """
    Преобразует локальный путь в URL для доступа через /uploads
    """
    if not file_path:
        return ""
    
    # Если это уже URL, возвращаем как есть
    if file_path.startswith(('http://', 'https://', '//')):
        return file_path
    
    # Если путь абсолютный и находится внутри UPLOAD_DIR
    abs_path = Path(file_path).absolute()
    upload_dir = Path(settings.UPLOAD_DIR).absolute()
    
    try:
        # Пробуем получить относительный путь
        rel_path = abs_path.relative_to(upload_dir)
        return f"/uploads/{rel_path.as_posix()}"
    except ValueError:
        # Если путь не внутри UPLOAD_DIR, возвращаем как есть
        return file_path

def get_absolute_path(file_url: str) -> Optional[Path]:
    """
    Преобразует URL вида /uploads/... в абсолютный путь к файлу
    """
    if not file_url:
        return None
    
    # Если это не uploads URL, возвращаем None
    if not file_url.startswith('/uploads/'):
        return None
    
    # Убираем /uploads/ и добавляем к базовому пути
    rel_path = file_url[9:]  # Убираем '/uploads/'
    abs_path = Path(settings.UPLOAD_DIR) / rel_path
    
    return abs_path.absolute()

def ensure_directory_exists(file_path: str) -> bool:
    """
    Создает директорию для файла, если она не существует
    """
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False

def is_safe_path(base_path: str, target_path: str) -> bool:
    """
    Проверяет, что target_path находится внутри base_path
    (защита от path traversal)
    """
    try:
        base = Path(base_path).resolve()
        target = Path(target_path).resolve()
        return base in target.parents or base == target
    except Exception:
        return False