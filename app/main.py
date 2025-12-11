from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.v1.router import api_router
from app.config import settings
from app.database import Base, engine
import os
import logging

logger = logging.getLogger(__name__)

# Создаем таблицы в базе данных
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Создаем необходимые директории
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "courses"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "lessons"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "scorm"), exist_ok=True)

# Подключаем статические файлы
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Подключаем роутеры
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Welcome to LMS Platform API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}