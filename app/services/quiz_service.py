from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from typing import List, Dict, Optional
from sqlalchemy import and_

from app.models.quiz import Quiz, Question, Answer, QuizAttempt
from app.models.user import User
from app.schemas.quiz import QuizCreate, QuizUpdate, QuizSubmit

class QuizService:
    def __init__(self, db: Session):
        self.db = db
    
    # === Создание теста ===
    def create_quiz(self, lesson_id: int, quiz_data: QuizCreate, author_id: int) -> Quiz:
        """Создание теста для урока"""
        quiz = Quiz(
            title=quiz_data.title,
            lesson_id=lesson_id,
            author_id=author_id
        )
        
        self.db.add(quiz)
        self.db.flush()
        
        for question_data in quiz_data.questions:
            question = Question(
                quiz_id=quiz.id,
                question_text=question_data.question_text,
                question_type=question_data.question_type
            )
            self.db.add(question)
            self.db.flush()
            
            for answer_data in question_data.answers:
                answer = Answer(
                    question_id=question.id,
                    answer_text=answer_data.answer_text,
                    is_correct=answer_data.is_correct
                )
                self.db.add(answer)
        
        self.db.commit()
        self.db.refresh(quiz)
        return quiz
    
    # === Получение теста ===
    def get_quiz(self, quiz_id: int, include_answers: bool = True) -> Optional[Quiz]:
        """Получение теста по ID"""
        query = self.db.query(Quiz).filter(Quiz.id == quiz_id)
        
        if include_answers:
            # Используем joinedload для загрузки всех связанных данных
            query = query.options(
                joinedload(Quiz.questions).joinedload(Question.answers)
            )
        
        quiz = query.first()
        
        if not quiz:
            return None
        
        return quiz
    
    def get_quiz_by_lesson(self, lesson_id: int) -> Optional[Quiz]:
        """Получение теста для урока"""
        return self.db.query(Quiz).filter(Quiz.lesson_id == lesson_id).first()
    
    # === Обновление теста ===
    def update_quiz(self, quiz_id: int, update_data: QuizUpdate, user_id: int) -> Quiz:
        """Обновление теста - ПРАВИЛЬНОЕ УДАЛЕНИЕ СТАРЫХ ВОПРОСОВ И ОТВЕТОВ"""
        quiz = self.get_quiz(quiz_id, include_answers=True)
        
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Проверяем права
        if quiz.author_id != user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_admin:
                raise HTTPException(status_code=403, detail="Not authorized")
        
        # Обновляем заголовок
        if update_data.title is not None:
            quiz.title = update_data.title
        
        # Обновляем вопросы, если они переданы
        if update_data.questions is not None:
            # ПРАВИЛЬНЫЙ СПОСОБ: удаляем старые вопросы и ответы
            # Это сработает благодаря cascade="all, delete-orphan"
            
            # 1. Очищаем все вопросы (ответы удалятся каскадно)
            for question in list(quiz.questions):  # Создаем копию списка
                self.db.delete(question)
            
            self.db.flush()  # Выполняем удаление
            
            # 2. Создаем новые вопросы
            for question_data in update_data.questions:
                if question_data.question_text is None:
                    continue
                    
                question = Question(
                    quiz_id=quiz.id,
                    question_text=question_data.question_text,
                    question_type=question_data.question_type or "single_choice"
                )
                self.db.add(question)
                self.db.flush()  # Получаем ID вопроса
                
                # 3. Создаем новые ответы
                if question_data.answers:
                    for answer_data in question_data.answers:
                        if answer_data.answer_text is None:
                            continue
                            
                        answer = Answer(
                            question_id=question.id,
                            answer_text=answer_data.answer_text,
                            is_correct=answer_data.is_correct or False
                        )
                        self.db.add(answer)
        
        self.db.commit()
        self.db.refresh(quiz)
        return quiz
    
    # === Удаление теста ===
    def delete_quiz(self, quiz_id: int, user_id: int) -> bool:
        """Удаление теста - СРАБОТАЕТ КАСКАДНОЕ УДАЛЕНИЕ"""
        quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Проверяем права
        if quiz.author_id != user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_admin:
                raise HTTPException(status_code=403, detail="Not authorized")
        
        # Удаляем тест (вопросы и ответы удалятся каскадно)
        self.db.delete(quiz)
        self.db.commit()
        return True
    
    # === Частичное обновление (альтернативный метод) ===
    def update_quiz_partial(self, quiz_id: int, update_data: QuizUpdate, user_id: int) -> Quiz:
        """Частичное обновление теста (только измененные поля)"""
        quiz = self.get_quiz(quiz_id, include_answers=True)
        
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        if quiz.author_id != user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_admin:
                raise HTTPException(status_code=403, detail="Not authorized")
        
        # Обновляем заголовок
        if update_data.title is not None:
            quiz.title = update_data.title
        
        # Если переданы вопросы - полное обновление
        if update_data.questions is not None:
            return self.update_quiz(quiz_id, update_data, user_id)
        
        self.db.commit()
        self.db.refresh(quiz)
        return quiz
    
    # === Удаление отдельных ответов ===
    def delete_answer(self, answer_id: int, user_id: int) -> bool:
        """Удаление конкретного ответа"""
        answer = self.db.query(Answer).filter(Answer.id == answer_id).first()
        
        if not answer:
            raise HTTPException(status_code=404, detail="Answer not found")
        
        # Получаем вопрос и тест для проверки прав
        question = self.db.query(Question).filter(Question.id == answer.question_id).first()
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        quiz = self.get_quiz(question.quiz_id, include_answers=False)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Проверяем права
        if quiz.author_id != user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_admin:
                raise HTTPException(status_code=403, detail="Not authorized")
        
        # Удаляем ответ
        self.db.delete(answer)
        self.db.commit()
        return True
    
    # === Удаление отдельных вопросов ===
    def delete_question(self, question_id: int, user_id: int) -> bool:
        """Удаление вопроса (с ответами удалятся каскадно)"""
        question = self.db.query(Question).filter(Question.id == question_id).first()
        
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")
        
        # Получаем тест для проверки прав
        quiz = self.get_quiz(question.quiz_id, include_answers=False)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        # Проверяем права
        if quiz.author_id != user_id:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.is_admin:
                raise HTTPException(status_code=403, detail="Not authorized")
        
        # Удаляем вопрос (ответы удалятся каскадно)
        self.db.delete(question)
        self.db.commit()
        return True
    
    # === Проверка ответов ===
    def submit_quiz(self, quiz_id: int, submit_data: QuizSubmit, user_id: int) -> Dict:
        """Проверка ответов пользователя"""
        quiz = self.get_quiz(quiz_id, include_answers=True)
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found")
        
        questions = quiz.questions
        
        # Подготавливаем словарь правильных ответов
        correct_answers = {}
        for question in questions:
            correct_answers[question.id] = []
            for answer in question.answers:
                if answer.is_correct:
                    correct_answers[question.id].append(answer.id)
        
        # Проверяем ответы пользователя
        total_questions = len(questions)
        correct_count = 0
        
        for user_answer in submit_data.answers:
            question_id = user_answer.question_id
            selected_ids = set(user_answer.selected_answer_ids)
            correct_ids = set(correct_answers.get(question_id, []))
            question = next((q for q in questions if q.id == question_id), None)
            if not question:
                continue
            if question.question_type == "single":
                if len(selected_ids) == 1 and selected_ids.issubset(correct_ids):
                    correct_count += 1
            
            elif question.question_type == "multiple":
                if selected_ids == correct_ids:
                    correct_count += 1
        # Вычисляем результат
        score = correct_count / total_questions if total_questions > 0 else 0
        is_passed = score >= 0.7
        
        # Сохраняем попытку
        attempt = QuizAttempt(
            quiz_id=quiz_id,
            user_id=user_id,
            score=score,
            is_passed=is_passed
        )
        self.db.add(attempt)
        self.db.commit()
        
        return {
            "score": score,
            "is_passed": is_passed,
            "total_questions": total_questions,
            "correct_answers": correct_count
        }
    
    def get_user_result(self, quiz_id: int, user_id: int) -> Dict:
        """Получение результата пользователя"""
        attempt = self.db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.user_id == user_id
        ).order_by(QuizAttempt.created_at.desc()).first()
        
        if not attempt:
            return {"message": "No attempts found"}
        
        return {
            "score": attempt.score,
            "is_passed": attempt.is_passed,
            "attempted_at": attempt.created_at
        }
