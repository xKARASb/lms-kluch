from fastapi import HTTPException, status

class CustomHTTPException(HTTPException):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)

class UserNotFoundException(CustomHTTPException):
    def __init__(self, user_id: int = None):
        detail = f"User with id {user_id} not found" if user_id else "User not found"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class CourseNotFoundException(CustomHTTPException):
    def __init__(self, course_id: int = None):
        detail = f"Course with id {course_id} not found" if course_id else "Course not found"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class LessonNotFoundException(CustomHTTPException):
    def __init__(self, lesson_id: int = None):
        detail = f"Lesson with id {lesson_id} not found" if lesson_id else "Lesson not found"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class UnauthorizedException(CustomHTTPException):
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)