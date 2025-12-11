import re

def validate_email(email: str) -> bool:
    """Проверяет валидность email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_username(username: str) -> bool:
    """Проверяет валидность имени пользователя"""
    # Только буквы, цифры и подчеркивание, от 3 до 20 символов
    pattern = r'^[a-zA-Z0-9_]{3,20}$'
    return bool(re.match(pattern, username))

def validate_password(password: str) -> bool:
    """Проверяет сложность пароля"""
    # Минимум 8 символов, хотя бы одна цифра, одна буква в верхнем и нижнем регистре
    if len(password) < 8:
        return False
    
    if not re.search(r'\d', password):
        return False
    
    if not re.search(r'[A-Z]', password):
        return False
    
    if not re.search(r'[a-z]', password):
        return False
    
    return True
