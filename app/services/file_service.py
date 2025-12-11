import os
import shutil
from pathlib import Path
from typing import Optional
import aiofiles
from fastapi import UploadFile
import magic

class FileService:
    def __init__(self, base_upload_dir: str = "./uploads"):
        self.base_upload_dir = Path(base_upload_dir)
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_upload_file(self, upload_file: UploadFile, subdir: str = "") -> Optional[Path]:
        """Сохраняет загруженный файл"""
        try:
            # Создаем поддиректорию
            upload_dir = self.base_upload_dir / subdir
            upload_dir.mkdir(parents=True, exist_ok=True)
            
            # Генерируем уникальное имя файла
            file_ext = Path(upload_file.filename).suffix if upload_file.filename else ""
            unique_filename = f"{os.urandom(8).hex()}{file_ext}"
            file_path = upload_dir / unique_filename
            
            # Сохраняем файл
            async with aiofiles.open(file_path, 'wb') as out_file:
                content = await upload_file.read()
                await out_file.write(content)
            
            return file_path
            
        except Exception as e:
            print(f"Ошибка при сохранении файла: {e}")
            return None
    
    def get_file_mime_type(self, file_path: Path) -> str:
        """Определяет MIME тип файла"""
        mime = magic.Magic(mime=True)
        return mime.from_file(str(file_path))
    
    def get_file_size(self, file_path: Path) -> int:
        """Возвращает размер файла в байтах"""
        return file_path.stat().st_size
    
    def delete_file(self, file_path: str) -> bool:
        """Удаляет файл"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def extract_rutube_id(self, url: str) -> Optional[str]:
        """Извлекает ID видео из ссылки Rutube"""
        import re
        
        # Паттерны для Rutube
        patterns = [
            r'rutube\.ru/video/([a-f0-9]+)/',
            r'rutube\.ru/play/embed/([a-f0-9]+)',
            r'rutube\.ru/video/embed/([a-f0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None