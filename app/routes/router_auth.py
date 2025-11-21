# app/routes/router_auth.py
# 회원가입, 로그인, 탈퇴 API

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.model_user import User, UserCreate
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.core.db_sqlalchemy import get_db

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

@router.get("/profile")
def get_profile(
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """현재 로그인한 사용자의 기본 프로필 정보를 반환합니다."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "email": user.email,
        "github_repo_url": user.github_repo_url,
        "expected_users": user.expected_users,
        "created_at": user.created_at,
    }

@router.put("/profile")
def update_profile(
    projectData: dict,
    email: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """사용자 프로필 정보 업데이트 (GitHub URL, 요청사항)"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 프로젝트 정보 업데이트
    if "github_repo_url" in projectData:
        user.github_repo_url = projectData["github_repo_url"]
    # requirements는 자연어이므로 DB에 저장하지 않고 MCP로만 전송
    # expected_users는 더 이상 사용하지 않음 (자연어 요청사항으로 대체)
    
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