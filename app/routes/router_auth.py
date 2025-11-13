# app/routes/router_auth.py
# 회원가입, 로그인, 탈퇴 API

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.model_user import User, UserCreate
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.db import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    new_user = User(
        email=user.email,
        password_hash=hash_password(user.password),
        github_repo_url=user.github_repo_url,
        # primary_usage_time=user.primary_usage_time or "",  # None이면 빈 문자열
        expected_users=user.expected_users
    )
    db.add(new_user)
    db.commit()
    return {"message": "Signup successful"}

@router.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": db_user.email})
    return {"access_token": token, "token_type": "bearer"}

@router.put("/profile")
def update_profile(
    projectData: dict,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 프로필 정보 업데이트 (GitHub URL, 예상 사용자 수)"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 프로젝트 정보 업데이트
    if "github_repo_url" in projectData:
        user.github_repo_url = projectData["github_repo_url"]
    if "expected_users" in projectData:
        user.expected_users = projectData["expected_users"]
    
    db.commit()
    return {"message": "Profile updated successfully"}

@router.delete("/delete")
def delete_account(email: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}