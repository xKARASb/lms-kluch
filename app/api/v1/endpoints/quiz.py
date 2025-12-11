from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.quiz import (
    QuizCreate, QuizCreateResponse,
    QuizUpdate, QuizUpdateResponse,
    QuizDeleteResponse,
    QuizResponse,
    QuizSubmit, QuizResult
)
from app.services.quiz_service import QuizService
from app.api.dependencies import get_current_user
from app.models.user import User

router = APIRouter()

# === Создание ===
@router.post("/lessons/{lesson_id}/quiz", response_model=QuizCreateResponse)
def create_quiz_for_lesson(
    lesson_id: int,
    quiz_data: QuizCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создание теста для урока"""
    quiz_service = QuizService(db)
    
    existing_quiz = quiz_service.get_quiz_by_lesson(lesson_id)
    if existing_quiz:
        raise HTTPException(
            status_code=400,
            detail="Quiz already exists for this lesson"
        )
    
    quiz = quiz_service.create_quiz(lesson_id, quiz_data, current_user.id)
    return QuizCreateResponse(message="Quiz created", quiz_id=quiz.id)

# === Получение ===
@router.get("/quizzes/{quiz_id}", response_model=QuizResponse)
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение теста по ID"""
    quiz_service = QuizService(db)
    quiz = quiz_service.get_quiz(quiz_id, include_answers=True)
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    
    # Для студентов скрываем правильные ответы
    if quiz.author_id != current_user.id and not current_user.is_admin:
        for question in quiz.questions:
            for answer in question.answers:
                answer.is_correct = None
    
    return quiz

@router.get("/lessons/{lesson_id}/quiz", response_model=QuizResponse)
def get_lesson_quiz(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение теста для урока"""
    quiz_service = QuizService(db)
    quiz = quiz_service.get_quiz_by_lesson(lesson_id)
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found for this lesson")
    
    # Для студентов скрываем правильные ответы
    quiz_with_answers = quiz_service.get_quiz(quiz.id, include_answers=True)
    if quiz_with_answers.author_id != current_user.id:
        for question in quiz_with_answers.questions:
            for answer in question.answers:
                answer.is_correct = None
    
    return quiz_with_answers

# === Обновление (ПОЛНОЕ - заменяет все вопросы) ===
@router.put("/quizzes/{quiz_id}", response_model=QuizUpdateResponse)
def update_quiz(
    quiz_id: int,
    update_data: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Полное обновление теста - заменяет ВСЕ вопросы и ответы"""
    quiz_service = QuizService(db)
    
    quiz = quiz_service.update_quiz(quiz_id, update_data, current_user.id)
    return QuizUpdateResponse(message="Quiz updated", quiz_id=quiz.id)

# === Частичное обновление ===
@router.patch("/quizzes/{quiz_id}", response_model=QuizUpdateResponse)
def update_quiz_partial(
    quiz_id: int,
    update_data: QuizUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Частичное обновление теста (только измененные поля)"""
    quiz_service = QuizService(db)
    
    quiz = quiz_service.update_quiz_partial(quiz_id, update_data, current_user.id)
    return QuizUpdateResponse(message="Quiz updated", quiz_id=quiz.id)

# === Удаление теста ===
@router.delete("/quizzes/{quiz_id}", response_model=QuizDeleteResponse)
def delete_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаление теста (удалит все вопросы и ответы каскадно)"""
    quiz_service = QuizService(db)
    
    quiz_service.delete_quiz(quiz_id, current_user.id)
    return QuizDeleteResponse(message="Quiz deleted")

# === Удаление вопроса ===
@router.delete("/questions/{question_id}", response_model=QuizDeleteResponse)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаление вопроса (удалит все ответы каскадно)"""
    quiz_service = QuizService(db)
    
    quiz_service.delete_question(question_id, current_user.id)
    return QuizDeleteResponse(message="Question deleted")

# === Удаление ответа ===
@router.delete("/answers/{answer_id}", response_model=QuizDeleteResponse)
def delete_answer(
    answer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удаление конкретного ответа"""
    quiz_service = QuizService(db)
    
    quiz_service.delete_answer(answer_id, current_user.id)
    return QuizDeleteResponse(message="Answer deleted")

# === Проверка ответов ===
@router.post("/quizzes/{quiz_id}/submit", response_model=QuizResult)
def submit_quiz_answers(
    quiz_id: int,
    submit_data: QuizSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отправка ответов на тест"""
    quiz_service = QuizService(db)
    result = quiz_service.submit_quiz(quiz_id, submit_data, current_user.id)
    return result

@router.get("/quizzes/{quiz_id}/result")
def get_quiz_result(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получение результата теста пользователя"""
    quiz_service = QuizService(db)
    result = quiz_service.get_user_result(quiz_id, current_user.id)
    return result