from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    resumes = relationship("Resume", back_populates="owner")
    sessions = relationship("InterviewSession", back_populates="user")


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    parsed_data = Column(JSON, nullable=True)  # skills/projects/experience, filled in later
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="resumes")


class JobRole(Base):
    """A target role the candidate wants to practice for, e.g. 'Data Analyst'."""
    __tablename__ = "job_roles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    required_skills = Column(JSON, nullable=True)


class InterviewSession(Base):
    """One full mock interview attempt: resume + job role + a series of questions."""
    __tablename__ = "interview_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    job_role_id = Column(Integer, ForeignKey("job_roles.id"))
    status = Column(String, default="in_progress")  # in_progress / completed
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")
    questions = relationship("Question", back_populates="session")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"))
    question_text = Column(Text, nullable=False)
    source_context = Column(Text, nullable=True)  # which resume snippet this came from
    question_type = Column(String, nullable=True)  # technical / behavioral
    difficulty = Column(String, default="medium")   # easy / medium / hard
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("InterviewSession", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False)


class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    answer_text = Column(Text, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())

    question = relationship("Question", back_populates="answer")
    score = relationship("Score", back_populates="answer", uselist=False)


class Score(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("answers.id"))
    similarity_score = Column(Float, nullable=True)  # Sentence-BERT number
    llm_score = Column(Float, nullable=True)          # LLM judge number
    final_score = Column(Float, nullable=True)        # combined
    explanation = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    answer = relationship("Answer", back_populates="score")
