from fastapi import APIRouter
from app.api.v1.endpoints import auth, courses, lessons, scorm, users, quiz

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses"])
api_router.include_router(lessons.router, prefix="/lessons", tags=["Lessons"])
api_router.include_router(scorm.router, prefix="/scorm", tags=["SCORM"])
api_router.include_router(quiz.router, prefix="/api/v1", tags=["quizzes"])