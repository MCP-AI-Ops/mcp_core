# app/models/model_user.py
# 사용자 모델 정의

from pydantic import BaseModel, EmailStr, HttpUrl
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    github_repo_url = Column(String)
    primary_usage_time = Column(String)
    expected_users = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    github_repo_url: HttpUrl
    primary_usage_time: str
    expected_users: int