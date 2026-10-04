import os
import shutil
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import models, schemas, auth
import resume_parser
import llm_service
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Intelligence Hire - Starter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploaded_resumes"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/api/ping")
def ping():
    return {"message": "pong - backend is alive"}


# ---------- AUTH (same as before) ----------

@app.post("/signup", response_model=schemas.UserOut)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(email=user.email, hashed_password=auth.hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/me", response_model=schemas.UserOut)
def read_current_user(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


# ---------- RESUME UPLOAD (same as before) ----------

@app.post("/resumes/upload", response_model=schemas.ResumeOut)
def upload_resume(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are allowed")

    safe_filename = f"user{current_user.id}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, safe_filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    resume = models.Resume(owner_id=current_user.id, filename=file.filename, filepath=filepath)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


@app.get("/resumes/mine", response_model=list[schemas.ResumeOut])
def my_resumes(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(models.Resume).filter(models.Resume.owner_id == current_user.id).all()


# ---------- JOB ROLES (new) ----------
# For now these are added manually/by an admin. Later you can let an LLM
# generate "required_skills" automatically from a job title.

@app.post("/job-roles", response_model=schemas.JobRoleOut)
def create_job_role(role: schemas.JobRoleCreate, db: Session = Depends(get_db)):
    new_role = models.JobRole(title=role.title, description=role.description)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role


@app.get("/job-roles", response_model=list[schemas.JobRoleOut])
def list_job_roles(db: Session = Depends(get_db)):
    return db.query(models.JobRole).all()


# ---------- INTERVIEW SESSIONS (new) ----------
# This is the "Select Target Job Role" -> session-starts step in your flowchart.

@app.post("/sessions/start", response_model=schemas.SessionOut)
def start_session(
    payload: schemas.SessionCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    # make sure the resume actually belongs to this user
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.id == payload.resume_id, models.Resume.owner_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    job_role = db.query(models.JobRole).filter(models.JobRole.id == payload.job_role_id).first()
    if not job_role:
        raise HTTPException(status_code=404, detail="Job role not found")

    session = models.InterviewSession(
        user_id=current_user.id,
        resume_id=resume.id,
        job_role_id=job_role.id,
        status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@app.get("/sessions/mine", response_model=list[schemas.SessionOut])
def my_sessions(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.InterviewSession)
        .filter(models.InterviewSession.user_id == current_user.id)
        .all()
    )


# ---------- RESUME PARSING + QUESTION GENERATION ----------

@app.post("/resumes/{resume_id}/parse")
def parse_resume(
    resume_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    resume = (
        db.query(models.Resume)
        .filter(models.Resume.id == resume_id, models.Resume.owner_id == current_user.id)
        .first()
    )
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    raw_text = resume_parser.extract_text_from_pdf(resume.filepath)
    structured = llm_service.structure_resume(raw_text)

    resume.parsed_data = structured
    db.commit()
    db.refresh(resume)
    return {"resume_id": resume.id, "parsed_data": structured}


@app.post("/sessions/{session_id}/generate-questions", response_model=list[schemas.QuestionOut])
def generate_session_questions(
    session_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    session = (
        db.query(models.InterviewSession)
        .filter(models.InterviewSession.id == session_id, models.InterviewSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    resume = db.query(models.Resume).filter(models.Resume.id == session.resume_id).first()
    if not resume.parsed_data:
        raise HTTPException(status_code=400, detail="Parse the resume first via /resumes/{id}/parse")

    job_role = db.query(models.JobRole).filter(models.JobRole.id == session.job_role_id).first()

    generated = llm_service.generate_questions(resume.parsed_data, job_role.title)

    questions = []
    for i, q in enumerate(generated):
        question = models.Question(
            session_id=session.id,
            question_text=q["question_text"],
            source_context=q.get("source_context"),
            question_type=q.get("question_type"),
            difficulty=q.get("difficulty", "medium"),
            order_index=i,
        )
        db.add(question)
        questions.append(question)

    db.commit()
    for q in questions:
        db.refresh(q)
    return questions


@app.get("/sessions/{session_id}/questions", response_model=list[schemas.QuestionOut])
def get_session_questions(
    session_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Question)
        .filter(models.Question.session_id == session_id)
        .order_by(models.Question.order_index)
        .all()
    )
