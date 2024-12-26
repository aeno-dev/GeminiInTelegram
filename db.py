from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, func
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime
from typing import List, Dict
from sqlalchemy import select
import logging
import os

# Настройка базового логгера
logger = logging.getLogger("db")
logger.setLevel(logging.DEBUG)
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
file_handler = logging.FileHandler(os.path.join(LOG_DIR, "db.log"), encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


Base = declarative_base()

class UserHistory(Base):
    __tablename__ = 'user_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    query = Column(String)
    response = Column(Text)
    image_ids = Column(String)
    model_type = Column(String, default='gemini-2.0-flash-exp')  # Добавлено поле model_type
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'UserHistory(id={self.id}, user_id={self.user_id}, query="{self.query}", response="{self.response}", image_ids="{self.image_ids}", model_type="{self.model_type}", timestamp="{self.timestamp}")'


class Database:
    def __init__(self, db_url='sqlite:///bot_history.db'):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        logger.debug("Database initialized")

    def add_record(self, user_id, query, response, image_ids: List[str] = None, model_type: str = 'gemini-2.0-flash-exp'):
        session = self.Session()
        if image_ids:
            image_ids_str = ",".join(image_ids)
        else:
            image_ids_str = None
        record = UserHistory(user_id=user_id, query=query, response=response, image_ids=image_ids_str, model_type = model_type)
        session.add(record)
        session.commit()
        session.close()
        logger.debug(
            f"DB: Record added - User ID: {user_id}, Query: {query}, Response: {response}, Model: {model_type}, Image IDs: {image_ids}")

    def clear_history(self, user_id):
        session = self.Session()
        session.query(UserHistory).filter(UserHistory.user_id == user_id).delete()
        session.commit()
        session.close()
        logger.info(f"DB: History cleared for user {user_id}")

    def get_history(self, user_id) -> List[Dict[str, str]]:
        session = self.Session()
        history_records = session.query(UserHistory).filter(UserHistory.user_id == user_id).order_by(
            UserHistory.timestamp.asc()).all()
        session.close()

        history = []
        for record in history_records:
            history.append({
                "query": record.query,
                "response": record.response,
                "image_ids": record.image_ids,
                "model_type": record.model_type
            })
        logger.debug(f"DB: History retrieved for user {user_id}: {history}")
        return history

    def set_model(self, user_id, model_type):
        session = self.Session()

        if model_type == 'Gemini 2.0 Flash':
            model_type_db = 'gemini-2.0-flash-exp'
        elif model_type == 'Gemini 2.0 Flash Thinking':
            model_type_db = 'gemini-2.0-flash-thinking-exp-1219'
        else:
            model_type_db = 'gemini-2.0-flash-exp'

        # Записываем в базу модель
        session.add(UserHistory(user_id=user_id, query='model change', response=f'Выбрана модель: {model_type}',
                                image_ids=None,
                                model_type=model_type_db))  # Костыль, чтобы модель сохранялась сразу
        # Обновляем модель в истории
        session.query(UserHistory).filter(UserHistory.user_id == user_id).update(
            {UserHistory.model_type: model_type_db})
        session.commit()
        session.close()
        logger.info(f"DB: Model set for user {user_id} to {model_type}")

    def get_current_model(self, user_id):
        session = self.Session()
        last_record = session.query(UserHistory).filter(UserHistory.user_id == user_id).order_by(
            UserHistory.timestamp.desc()).first()
        session.close()
        if last_record:
            return last_record.model_type
        return 'gemini-2.0-flash-exp'