from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class ResumeOut(BaseModel):
    id: int
    filename: str
    uploaded_at: datetime
    class Config:
        from_attributes = True


class JobRoleCreate(BaseModel):
    title: str
    description: Optional[str] = None


class JobRoleOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    resume_id: int
    job_role_id: int


class SessionOut(BaseModel):
    id: int
    status: str
    started_at: datetime
    class Config:
        from_attributes = True


class QuestionOut(BaseModel):
    id: int
    question_text: str
    source_context: Optional[str] = None
    question_type: Optional[str] = None
    difficulty: str
    order_index: int
    class Config:
        from_attributes = True
