# User Authentication Models
# Pydantic 모델을 사용한 사용자 인증 및 관리 스키마

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator
import re


CloudProvider = Literal["aws", "azure", "gcp", "alibaba", "oracle", "ibm", "other"]


class UserBase(BaseModel):
    """사용자 기본 정보"""
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    full_name: Optional[str] = Field(None, max_length=128)
    organization: Optional[str] = Field(None, max_length=128)
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('사용자명은 영문자, 숫자, 언더스코어, 하이픈만 사용 가능합니다.')
        return v


class UserCreate(UserBase):
    """사용자 생성 요청"""
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('비밀번호는 최소 8자 이상이어야 합니다.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('비밀번호는 최소 1개의 대문자를 포함해야 합니다.')
        if not re.search(r'[a-z]', v):
            raise ValueError('비밀번호는 최소 1개의 소문자를 포함해야 합니다.')
        if not re.search(r'[0-9]', v):
            raise ValueError('비밀번호는 최소 1개의 숫자를 포함해야 합니다.')
        return v


class UserUpdate(BaseModel):
    """사용자 정보 수정"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=128)
    organization: Optional[str] = Field(None, max_length=128)
    is_active: Optional[bool] = None


class UserCloudConfig(BaseModel):
    """클라우드 계정 설정"""
    cloud_provider: CloudProvider
    cloud_account_id: Optional[str] = Field(None, max_length=128)
    cloud_region: Optional[str] = Field(None, max_length=64)
    cloud_access_key: Optional[str] = Field(None, max_length=512)
    cloud_secret_key: Optional[str] = Field(None, max_length=512)
    cloud_tenant_id: Optional[str] = Field(None, max_length=128)  # Azure
    cloud_project_id: Optional[str] = Field(None, max_length=128)  # GCP
    cloud_config_json: Optional[dict] = None


class UserResponse(UserBase):
    """사용자 정보 응답"""
    id: int
    is_active: bool
    is_verified: bool
    email_verified_at: Optional[datetime] = None
    cloud_provider: Optional[CloudProvider] = None
    cloud_account_id: Optional[str] = None
    cloud_region: Optional[str] = None
    api_key: Optional[str] = None
    api_key_expires_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    two_factor_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """로그인 요청"""
    username: str
    password: str
    two_factor_code: Optional[str] = Field(None, min_length=6, max_length=6)


class UserLoginResponse(BaseModel):
    """로그인 응답"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class PasswordChange(BaseModel):
    """비밀번호 변경 요청"""
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('비밀번호는 최소 8자 이상이어야 합니다.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('비밀번호는 최소 1개의 대문자를 포함해야 합니다.')
        if not re.search(r'[a-z]', v):
            raise ValueError('비밀번호는 최소 1개의 소문자를 포함해야 합니다.')
        if not re.search(r'[0-9]', v):
            raise ValueError('비밀번호는 최소 1개의 숫자를 포함해야 합니다.')
        return v


class PasswordResetRequest(BaseModel):
    """비밀번호 재설정 요청"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """비밀번호 재설정 확인"""
    token: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('비밀번호는 최소 8자 이상이어야 합니다.')
        if not re.search(r'[A-Z]', v):
            raise ValueError('비밀번호는 최소 1개의 대문자를 포함해야 합니다.')
        if not re.search(r'[a-z]', v):
            raise ValueError('비밀번호는 최소 1개의 소문자를 포함해야 합니다.')
        if not re.search(r'[0-9]', v):
            raise ValueError('비밀번호는 최소 1개의 숫자를 포함해야 합니다.')
        return v


class EmailVerificationRequest(BaseModel):
    """이메일 인증 요청"""
    token: str


class ApiKeyResponse(BaseModel):
    """API 키 응답"""
    api_key: str
    expires_at: datetime


class UserSession(BaseModel):
    """사용자 세션"""
    id: int
    user_id: int
    session_token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime
    created_at: datetime
    last_activity_at: datetime
    
    class Config:
        from_attributes = True


class AuditLogEntry(BaseModel):
    """감사 로그 항목"""
    id: int
    user_id: Optional[int] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
