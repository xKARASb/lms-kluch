from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Создание
class AnswerCreate(BaseModel):
    answer_text: str
    is_correct: bool

class QuestionCreate(BaseModel):
    question_text: str
    question_type: str  # "single_choice" или "multiple_choice"
    answers: List[AnswerCreate]

class QuizCreate(BaseModel):
    title: str
    questions: List[QuestionCreate]

# Получение (детальная информация)
class AnswerResponse(BaseModel):
    id: int
    answer_text: str
    is_correct: bool
    
    class Config:
        from_attributes = True

class QuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: str
    answers: List[AnswerResponse]
    
    class Config:
        from_attributes = True

class QuizResponse(BaseModel):
    id: int
    title: str
    lesson_id: int
    author_id: int
    created_at: datetime
    questions: List[QuestionResponse]
    
    class Config:
        from_attributes = True

# Обновление
class AnswerUpdate(BaseModel):
    id: Optional[int] = None  # Если None - новый ответ
    answer_text: Optional[str] = None
    is_correct: Optional[bool] = None

class QuestionUpdate(BaseModel):
    id: Optional[int] = None  # Если None - новый вопрос
    question_text: Optional[str] = None
    question_type: Optional[str] = None
    answers: Optional[List[AnswerUpdate]] = None

class QuizUpdate(BaseModel):
    title: Optional[str] = None
    questions: Optional[List[QuestionUpdate]] = None

# Ответы при операциях
class QuizCreateResponse(BaseModel):
    message: str
    quiz_id: int
    
    class Config:
        from_attributes = True

class QuizUpdateResponse(BaseModel):
    message: str
    quiz_id: int
    
    class Config:
        from_attributes = True

class QuizDeleteResponse(BaseModel):
    message: str
    
    class Config:
        from_attributes = True

# Для отправки ответов
class UserAnswer(BaseModel):
    question_id: int
    selected_answer_ids: List[int]

class QuizSubmit(BaseModel):
    answers: List[UserAnswer]

class QuizResult(BaseModel):
    score: float
    is_passed: bool
    total_questions: int
    correct_answers: int