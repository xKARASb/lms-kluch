from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Настройки приложения
    APP_NAME: str = "LMS Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Настройки базы данных
    DATABASE_URL: str = "sqlite:///./lms.db"
    
    # Настройки безопасности
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Настройки загрузки файлов
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "./uploads"
    
    # Настройки CORS
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"

settings = Settings()