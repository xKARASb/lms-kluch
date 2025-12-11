import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import json
import shutil
from typing import Dict, Any, Optional, List, Tuple
import os
import re
import logging
import hashlib
from urllib.parse import urlparse, unquote

logger = logging.getLogger(__name__)

class SCORMParser:
    def __init__(self, upload_dir: str = "./uploads/scorm"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_manifest(self, manifest_path: Path) -> Dict[str, Any]:
        """Парсит файл imsmanifest.xml"""
        try:
            # Пробуем разные кодировки для чтения XML
            encodings = ['utf-8', 'utf-8-sig', 'cp1251', 'windows-1251', 
                        'iso-8859-1', 'latin-1', 'koi8-r', 'cp866', 'maccyrillic']
            
            root = None
            used_encoding = 'utf-8'
            
            for encoding in encodings:
                try:
                    with open(manifest_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    
                    # Парсим XML
                    root = ET.fromstring(content)
                    used_encoding = encoding
                    logger.info(f"Manifest прочитан в кодировке: {encoding}")
                    break
                except (UnicodeDecodeError, ET.ParseError) as e:
                    logger.debug(f"Не удалось прочитать манифест в кодировке {encoding}: {e}")
                    continue
            
            if root is None:
                # Если ни одна кодировка не подошла, читаем как бинарный и игнорируем ошибки
                with open(manifest_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                root = ET.fromstring(content)
                used_encoding = 'utf-8 (ignore errors)'
            
            # Namespace для SCORM
            ns = {
                'imscp': 'http://www.imsglobal.org/xsd/imscp_v1p1',
                'adlcp': 'http://www.adlnet.org/xsd/adlcp_v1p3',
                'imsmd': 'http://www.imsglobal.org/xsd/imsmd_v1p2'
            }
            
            # Извлекаем метаданные
            metadata = {
                'encoding_used': used_encoding,
                'manifest_path': str(manifest_path)
            }
            
            # Заголовок
            title_elem = root.find('.//imsmd:title', ns)
            if title_elem is not None and title_elem.text:
                metadata['title'] = title_elem.text.strip()
            
            # Описание
            description_elem = root.find('.//imsmd:description', ns)
            if description_elem is not None and description_elem.text:
                metadata['description'] = description_elem.text.strip()
            
            # Организация
            organizations = []
            for org_elem in root.findall('.//imscp:organizations/imscp:organization', ns):
                org_data = {
                    'identifier': org_elem.get('identifier', ''),
                    'title': ''
                }
                
                title_elem = org_elem.find('imscp:title', ns)
                if title_elem is not None and title_elem.text:
                    org_data['title'] = title_elem.text.strip()
                
                organizations.append(org_data)
            
            metadata['organizations'] = organizations
            
            # Ресурсы
            resources = []
            for resource_elem in root.findall('.//imscp:resources/imscp:resource', ns):
                resource = {
                    'identifier': resource_elem.get('identifier', ''),
                    'type': resource_elem.get('type', ''),
                    'href': resource_elem.get('href', ''),
                    'files': []
                }
                
                # Файлы ресурса
                for file_elem in resource_elem.findall('imscp:file', ns):
                    file_href = file_elem.get('href')
                    if file_href:
                        resource['files'].append(file_href)
                
                resources.append(resource)
            
            metadata['resources'] = resources
            
            return metadata
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге манифеста {manifest_path}: {str(e)}")
            raise Exception(f"Ошибка при парсинге манифеста: {str(e)}")
    
    def extract_scorm_package(self, scorm_file, extract_to: str) -> Dict[str, Any]:
        """Извлекает SCORM пакет и парсит его"""
        extract_path = Path(extract_to)
        
        # Очищаем папку для извлечения
        if extract_path.exists():
            shutil.rmtree(extract_path)
        extract_path.mkdir(parents=True)
        
        try:
            logger.info(f"Извлечение SCORM пакета в {extract_path}")
            
            # Извлекаем ZIP
            with zipfile.ZipFile(scorm_file, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            if (extract_path / "__MACOSX").exists():
                shutil.rmtree(extract_path / "__MACOSX")

            # Ищем манифест
            manifest_path = extract_path / "imsmanifest.xml"
            if not manifest_path.exists():
                # Пробуем найти в подпапках
                found = False
                for file in extract_path.rglob("imsmanifest.xml"):
                    manifest_path = file
                    found = True
                    logger.info(f"Найден манифест: {manifest_path}")
                    break
                
                if not found:
                    # Попробуем найти файлы с похожими именами
                    for file in extract_path.rglob("*manifest*.xml"):
                        manifest_path = file
                        found = True
                        logger.info(f"Найден альтернативный манифест: {manifest_path}")
                        break

            if not manifest_path.exists():
                raise Exception("Файл imsmanifest.xml не найден в пакете")
            
            # Парсим манифест
            metadata = self.parse_manifest(manifest_path)
            
            # Ищем HTML/файлы для конвертации
            html_files = []
            image_files = []
            other_files = []
            
            # Собираем все файлы из ресурсов
            for resource in metadata.get('resources', []):
                for file in resource.get('files', []):
                    if file:
                        full_path = extract_path / file
                        if full_path.exists():
                            # Классифицируем файлы
                            file_str = str(full_path)
                            file_lower = file.lower()
                            
                            if file_lower.endswith(('.html', '.htm')):
                                html_files.append(file_str)
                            elif file_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp')):
                                image_files.append(file_str)
                            else:
                                other_files.append(file_str)
            
            # Также ищем файлы в извлеченной папке
            for html_file in extract_path.rglob("*.html"):
                file_str = str(html_file)
                if file_str not in html_files:
                    html_files.append(file_str)
            
            for html_file in extract_path.rglob("*.htm"):
                file_str = str(html_file)
                if file_str not in html_files:
                    html_files.append(file_str)
            
            for img_file in extract_path.rglob("*.jpg"):
                file_str = str(img_file)
                if file_str not in image_files:
                    image_files.append(file_str)
            
            for img_file in extract_path.rglob("*.jpeg"):
                file_str = str(img_file)
                if file_str not in image_files:
                    image_files.append(file_str)
            
            for img_file in extract_path.rglob("*.png"):
                file_str = str(img_file)
                if file_str not in image_files:
                    image_files.append(file_str)
            
            for img_file in extract_path.rglob("*.gif"):
                file_str = str(img_file)
                if file_str not in image_files:
                    image_files.append(file_str)
            
            for img_file in extract_path.rglob("*.bmp"):
                file_str = str(img_file)
                if file_str not in image_files:
                    image_files.append(file_str)
            
            for img_file in extract_path.rglob("*.svg"):
                file_str = str(img_file)
                if file_str not in image_files:
                    image_files.append(file_str)
            
            metadata['extracted_path'] = str(extract_path)
            metadata['html_files'] = html_files
            metadata['image_files'] = image_files
            metadata['other_files'] = other_files
            metadata['total_files'] = len(html_files) + len(image_files) + len(other_files)
            metadata['html_files_count'] = len(html_files)
            metadata['image_files_count'] = len(image_files)
            
            logger.info(f"Найдено файлов: HTML={len(html_files)}, изображений={len(image_files)}, других={len(other_files)}")
            return metadata
            
        except Exception as e:
            # Очищаем в случае ошибки
            if extract_path.exists():
                try:
                    shutil.rmtree(extract_path)
                except:
                    pass
            
            logger.error(f"Ошибка при обработке SCORM пакета: {str(e)}")
            raise Exception(f"Ошибка при обработке SCORM пакета: {str(e)}")
    
    def detect_file_encoding(self, file_path: str) -> tuple:
        """Определяет кодировку файла"""
        # Список возможных кодировок для русских текстов
        encodings = [
            'utf-8', 'utf-8-sig',  # UTF-8 варианты
            'cp1251', 'windows-1251',  # Windows кириллица
            'koi8-r', 'koi8-u',  # KOI8
            'iso-8859-1', 'iso-8859-5', 'iso-8859-15',  # ISO
            'cp866', 'ibm866',  # DOS/OEM кириллица
            'maccyrillic',  # Mac кириллица
            'latin-1',  # Западноевропейская
        ]
        
        # Сначала читаем первые несколько байт для анализа
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read(4096)  # Читаем первые 4KB
            
            # Проверяем BOM для UTF-8
            if raw_data.startswith(b'\xef\xbb\xbf'):
                return 'utf-8-sig', "BOM detected"
            
            # Простая эвристика для определения кодировки
            for encoding in encodings:
                try:
                    # Пробуем декодировать
                    test_data = raw_data[:1000]  # Тестируем на первых 1000 байтах
                    decoded = test_data.decode(encoding)
                    
                    # Проверяем наличие кириллицы (опционально)
                    if any(ord('А') <= ord(c) <= ord('я') for c in decoded if c.isalpha()):
                        return encoding, "Cyrillic detected"
                    
                    return encoding, "Success"
                except UnicodeDecodeError:
                    continue
            
            return 'utf-8', "Fallback"
            
        except Exception as e:
            logger.warning(f"Не удалось определить кодировку для {file_path}: {e}")
            return 'utf-8', f"Error: {e}"
    
    def read_file_with_encoding(self, file_path: str) -> str:
        """Читает файл с правильной кодировкой"""
        encoding, reason = self.detect_file_encoding(file_path)
        logger.info(f"Чтение файла {file_path} в кодировке {encoding} ({reason})")
        
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
            
            # Удаляем BOM если есть
            if content.startswith('\ufeff'):
                content = content[1:]
            
            return content
            
        except Exception as e:
            logger.error(f"Ошибка чтения файла {file_path} в кодировке {encoding}: {e}")
            
            # Пробуем другие кодировки в случае ошибки
            fallback_encodings = ['utf-8', 'cp1251', 'windows-1251', 'iso-8859-1']
            
            for enc in fallback_encodings:
                if enc == encoding:
                    continue
                    
                try:
                    with open(file_path, 'r', encoding=enc, errors='replace') as f:
                        content = f.read()
                    
                    if content.startswith('\ufeff'):
                        content = content[1:]
                    
                    logger.info(f"Успешно прочитан с fallback кодировкой {enc}")
                    return content
                except:
                    continue
            
            # Если ничего не помогло, читаем с игнорированием ошибок
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                logger.warning(f"Файл прочитан с игнорированием ошибок")
                return content
            except Exception as final_error:
                raise Exception(f"Не удалось прочитать файл {file_path}: {final_error}")
    
    def extract_and_process_images(self, html_file_path: str, html_content: str, 
                                 extracted_path: str, upload_base_dir: str, 
                                 course_id: int, lesson_id: int) -> Tuple[str, List[Dict]]:
        """
        Извлекает изображения из HTML и сохраняет их локально.
        Возвращает обновленный HTML и информацию о изображениях.
        """
        processed_images = []
        
        # Папка для сохранения изображений этого урока
        images_dir = Path(upload_base_dir) / "courses" / str(course_id) / "lessons" / str(lesson_id) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        # Регулярное выражение для поиска изображений в HTML
        # Ищем теги img с src атрибутом
        img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
        
        def replace_image(match):
            img_tag = match.group(0)
            img_src = match.group(1)
            
            # Пропускаем data:image (встроенные изображения) и внешние URL
            if img_src.startswith('data:') or img_src.startswith(('http://', 'https://', '//')):
                return img_tag
            
            # Определяем полный путь к изображению
            img_path = None
            
            # Пробуем несколько вариантов:
            # 1. Относительный путь от HTML файла
            html_dir = Path(html_file_path).parent
            possible_paths = [
                html_dir / img_src,  # Относительный путь
                html_dir / unquote(img_src),  # URL decoded
                Path(extracted_path) / img_src.lstrip('/'),  # Абсолютный от корня SCORM
                Path(extracted_path) / unquote(img_src.lstrip('/')),  # URL decoded
            ]
            
            for path in possible_paths:
                if path.exists() and path.is_file():
                    img_path = path
                    break
            
            if not img_path:
                logger.warning(f"Изображение не найдено: {img_src} в файле {html_file_path}")
                return img_tag
            
            # Генерируем уникальное имя для изображения
            file_hash = hashlib.md5(str(img_path).encode()).hexdigest()[:8]
            original_name = img_path.name
            name_without_ext = img_path.stem
            extension = img_path.suffix.lower()
            
            # Если расширение не стандартное, используем .bin
            if extension not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
                extension = '.bin'
            
            new_filename = f"{name_without_ext}_{file_hash}{extension}"
            new_filepath = images_dir / new_filename
            
            # Копируем изображение
            try:
                shutil.copy2(img_path, new_filepath)
                logger.info(f"Скопировано изображение: {img_path} -> {new_filepath}")
                
                # Формируем новый URL для изображения
                new_url = f"/uploads/courses/{course_id}/lessons/{lesson_id}/images/{new_filename}"
                
                # Заменяем src в теге img
                new_img_tag = re.sub(
                    r'src=["\'][^"\']+["\']',
                    f'src="{new_url}"',
                    img_tag
                )
                
                # Добавляем информацию о изображении
                processed_images.append({
                    'original_path': str(img_path),
                    'original_src': img_src,
                    'new_path': str(new_filepath),
                    'new_url': new_url,
                    'filename': new_filename
                })
                
                return new_img_tag
                
            except Exception as e:
                logger.error(f"Ошибка при копировании изображения {img_path}: {e}")
                return img_tag
        
        # Заменяем все изображения в HTML
        updated_html = re.sub(img_pattern, replace_image, html_content)
        
        # Также обрабатываем CSS background-image
        bg_pattern = r'background-image:\s*url\(["\']?([^)"\']+)["\']?\)'
        
        def replace_background(match):
            bg_url = match.group(1)
            full_match = match.group(0)
            
            # Пропускаем внешние URL и data:image
            if bg_url.startswith('data:') or bg_url.startswith(('http://', 'https://', '//')):
                return full_match
            
            # Определяем путь к изображению
            img_path = None
            html_dir = Path(html_file_path).parent
            possible_paths = [
                html_dir / bg_url,
                html_dir / unquote(bg_url),
                Path(extracted_path) / bg_url.lstrip('/'),
                Path(extracted_path) / unquote(bg_url.lstrip('/')),
            ]
            
            for path in possible_paths:
                if path.exists() and path.is_file():
                    img_path = path
                    break
            
            if not img_path:
                return full_match
            
            # Генерируем уникальное имя
            file_hash = hashlib.md5(str(img_path).encode()).hexdigest()[:8]
            original_name = img_path.name
            name_without_ext = img_path.stem
            extension = img_path.suffix.lower()
            
            if extension not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp']:
                extension = '.bin'
            
            new_filename = f"{name_without_ext}_bg_{file_hash}{extension}"
            new_filepath = images_dir / new_filename
            
            # Копируем изображение
            try:
                shutil.copy2(img_path, new_filepath)
                logger.info(f"Скопировано фоновое изображение: {img_path} -> {new_filepath}")
                
                # Формируем новый URL
                new_url = f"/uploads/courses/{course_id}/lessons/{lesson_id}/images/{new_filename}"
                
                # Заменяем URL
                new_bg = f'background-image: url("{new_url}")'
                
                processed_images.append({
                    'original_path': str(img_path),
                    'original_src': bg_url,
                    'new_path': str(new_filepath),
                    'new_url': new_url,
                    'filename': new_filename,
                    'type': 'background'
                })
                
                return new_bg
                
            except Exception as e:
                logger.error(f"Ошибка при копировании фонового изображения {img_path}: {e}")
                return full_match
        
        # Заменяем background-image
        updated_html = re.sub(bg_pattern, replace_background, updated_html, flags=re.IGNORECASE)
        
        return updated_html, processed_images
    
    def convert_to_markdown_with_images(self, html_file_path: str, extracted_path: str,
                                      upload_base_dir: str, course_id: int, 
                                      lesson_id: int) -> Tuple[str, List[Dict]]:
        """
        Конвертирует HTML в Markdown, сохраняя изображения локально.
        Возвращает Markdown и информацию об изображениях.
        """
        try:
            # Читаем HTML файл
            html_content = self.read_file_with_encoding(html_file_path)
            
            # Извлекаем и обрабатываем изображения
            processed_html, images_info = self.extract_and_process_images(
                html_file_path, html_content, extracted_path, 
                upload_base_dir, course_id, lesson_id
            )
            
            # Конвертируем обработанный HTML в Markdown
            markdown_content = self._html_to_markdown(processed_html)
            
            # Добавляем информацию об изображениях в конец Markdown
            # if images_info:
            #     markdown_content += "\n\n---\n\n"
            #     markdown_content += "## Прикрепленные изображения\n\n"
            #     for img in images_info:
            #         if img.get('type') != 'background':
            #             markdown_content += f"![{img['filename']}]({img['new_url']})\n\n"
            
            return markdown_content, images_info
            
        except Exception as e:
            logger.error(f"Ошибка при конвертации HTML в Markdown с изображениями: {str(e)}")
            raise
    
    def _html_to_markdown(self, html_content: str) -> str:
        """Конвертирует HTML в Markdown"""
        # Упрощённая конвертация HTML в Markdown
        # Удаляем теги script и style
        html_content = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>', '', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Заменяем заголовки
        for i in range(6, 0, -1):
            tag = f'h{i}'
            html_content = re.sub(
                f'<{tag}[^>]*>(.*?)</{tag}>',
                f'{"#" * i} \\1\n\n',
                html_content,
                flags=re.IGNORECASE | re.DOTALL
            )
        
        # Заменяем жирный текст
        html_content = re.sub(r'<b\b[^>]*>(.*?)</b>', r'**\1**', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'<strong\b[^>]*>(.*?)</strong>', r'**\1**', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Заменяем курсив
        html_content = re.sub(r'<i\b[^>]*>(.*?)</i>', r'*\1*', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'<em\b[^>]*>(.*?)</em>', r'*\1*', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Заменяем подчеркнутый текст
        html_content = re.sub(r'<u\b[^>]*>(.*?)</u>', r'_\1_', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Заменяем ссылки
        html_content = re.sub(
            r'<a\b[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            r'[\2](\1)',
            html_content,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # Заменяем изображения (уже обработаны, но на всякий случай оставляем)
        html_content = re.sub(
            r'<img\b[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>',
            r'![\2](\1)',
            html_content,
            flags=re.IGNORECASE
        )
        html_content = re.sub(
            r'<img\b[^>]*src="([^"]*)"[^>]*>',
            r'![](\1)',
            html_content,
            flags=re.IGNORECASE
        )
        
        # Заменяем списки
        html_content = re.sub(r'<li\b[^>]*>(.*?)</li>', r'* \1\n', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'<ul\b[^>]*>|</ul>', r'', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<ol\b[^>]*>|</ol>', r'', html_content, flags=re.IGNORECASE)
        
        # Заменяем параграфы
        html_content = re.sub(r'<p\b[^>]*>(.*?)</p>', r'\1\n\n', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Заменяем переносы строк
        html_content = re.sub(r'<br\b[^>]*>', r'  \n', html_content, flags=re.IGNORECASE)
        
        # Заменяем горизонтальные линии
        html_content = re.sub(r'<hr\b[^>]*>', r'\n---\n', html_content, flags=re.IGNORECASE)
        
        # Обработка таблиц (упрощенная)
        html_content = re.sub(r'<table[^>]*>', r'\n', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</table>', r'\n', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<tr[^>]*>', r'\n', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'</tr>', r'', html_content, flags=re.IGNORECASE)
        html_content = re.sub(r'<td[^>]*>(.*?)</td>', r'| \1 ', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        html_content = re.sub(r'<th[^>]*>(.*?)</th>', r'| **\1** ', 
                             html_content, flags=re.IGNORECASE | re.DOTALL)
        
        # Удаляем оставшиеся теги
        html_content = re.sub(r'<[^>]*>', '', html_content)
        
        # Заменяем HTML entities
        html_entities = {
            '&nbsp;': ' ',
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&#39;': "'",
            '&apos;': "'",
            '&copy;': '(c)',
            '&reg;': '(r)',
            '&trade;': '(tm)',
            '&mdash;': '—',
            '&ndash;': '–',
            '&hellip;': '...',
            '&laquo;': '«',
            '&raquo;': '»',
        }
        
        for entity, replacement in html_entities.items():
            html_content = html_content.replace(entity, replacement)
        
        # Заменяем числовые HTML entities
        def replace_decimal_entity(match):
            try:
                return chr(int(match.group(1)))
            except:
                return match.group(0)
        
        def replace_hex_entity(match):
            try:
                return chr(int(match.group(1), 16))
            except:
                return match.group(0)
        
        html_content = re.sub(r'&#(\d+);', replace_decimal_entity, html_content)
        html_content = re.sub(r'&#x([0-9a-fA-F]+);', replace_hex_entity, html_content)
        
        # Очищаем лишние пробелы и переносы строк
        html_content = re.sub(r'[ \t]+', ' ', html_content)
        html_content = re.sub(r'\n[ \t]+\n', '\n\n', html_content)
        html_content = re.sub(r'\n\s*\n', '\n\n', html_content)
        
        # Удаляем пустые строки в начале и конце
        html_content = html_content.strip()
        
        return html_content
    
    def convert_to_markdown(self, html_file_path: str) -> str:
        """Конвертирует HTML в Markdown (старая версия без обработки изображений)"""
        try:
            html_content = self.read_file_with_encoding(html_file_path)
            return self._html_to_markdown(html_content)
        except Exception as e:
            logger.error(f"Ошибка при конвертации HTML в Markdown: {str(e)}")
            error_message = f"""# Ошибка конвертации

Не удалось конвертировать файл: `{html_file_path}`

**Ошибка:** {str(e)}
"""
            return error_message
    
    def cleanup_extracted_files(self, extracted_path: str):
        """Очищает извлеченные файлы"""
        try:
            path = Path(extracted_path)
            if path.exists():
                shutil.rmtree(path)
                logger.info(f"Очищена директория: {extracted_path}")
        except Exception as e:
            logger.error(f"Ошибка при очистке директории {extracted_path}: {e}")