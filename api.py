# api.py
from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
import json, io

# DB / SQLAlchemy (same as earlier)
from sqlalchemy import Column, Integer, String, Text, DateTime, create_engine, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# For PDF extraction (lightweight)
from PyPDF2 import PdfReader

SECRET_KEY = "replace_this_with_a_strong_secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DATABASE_URL = "sqlite:///./app.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    saves = relationship("SavedRecommendation", back_populates="owner")

class SavedRecommendation(Base):
    __tablename__ = "saved_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, index=True)
    data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User", back_populates="saves")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Career Advisor - Enhanced API")

# Simple career DB
career_db = {
    "Data Scientist": {"required_skills": ["Python","Machine Learning","Statistics","SQL","Data Visualization"],
                       "roadmap": ["Python basics","Statistics","SQL","ML algorithms","Projects"]},
    "Web Developer": {"required_skills": ["HTML","CSS","JavaScript","React","APIs"],
                      "roadmap": ["HTML/CSS","JS fundamentals","React","Backend basics","Full-stack projects"]},
    "AI Engineer": {"required_skills": ["Python","Deep Learning","NLP","PyTorch"],
                    "roadmap": ["Python","DL fundamentals","PyTorch","NLP projects","Research reading"]},
    "Product Manager": {"required_skills": ["Communication","Project Management","Leadership","Business Analysis"],
                        "roadmap": ["Communication","Agile & Scrum","Market research","Product cases"]}
}

# Auth utils
def get_password_hash(p): return pwd_context.hash(p)
def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_by_email(db, email: str):
    return db.query(User).filter(User.email == email).first()

def get_current_user(token: str = Depends(oauth2_scheme), db=Depends(get_db)):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user

# Schemas
class UserCreate(BaseModel):
    email: str
    password: str

class Skills(BaseModel):
    user_skills: str

class SavePayload(BaseModel):
    title: str
    payload: dict

# Core analyze function (same logic)
def analyze_skills(user_skills):
    user = {s.strip().capitalize() for s in user_skills.split(",") if s.strip()}
    results = []
    for career, details in career_db.items():
        req = {s.capitalize() for s in details["required_skills"]}
        matched = sorted(list(req & user))
        missing = sorted(list(req - user))
        score = round((len(matched) / len(req)) * 100, 2) if req else 0.0
        results.append({"career": career, "match_score": score, "matched_skills": matched, "missing_skills": missing, "roadmap": details["roadmap"]})
    return sorted(results, key=lambda x: x["match_score"], reverse=True)

# --- Auth endpoints ---
@app.post("/register", status_code=201)
def register(u: UserCreate, db=Depends(get_db)):
    if get_user_by_email(db, u.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=u.email, hashed_password=get_password_hash(u.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"msg":"user_created","email":user.email}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    user = get_user_by_email(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": user.email}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"access_token": token, "token_type": "bearer"}

# --- Advice / Save / History ---
@app.post("/advise")
def advise(sk: Skills, current_user: Optional[User] = Depends(get_current_user) or None):
    out = analyze_skills(sk.user_skills)
    tips = "Focus on missing skills, build 2 projects, and network."
    return {"top_careers": out, "personalized_tips": tips, "timestamp": datetime.utcnow().isoformat()}

@app.post("/save", status_code=201)
def save_recommendation(body: SavePayload, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    rec = SavedRecommendation(user_id=current_user.id, title=body.title, data=json.dumps(body.payload))
    db.add(rec); db.commit(); db.refresh(rec)
    return {"id": rec.id, "title": rec.title, "created_at": rec.created_at.isoformat()}

@app.get("/history")
def get_history(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    items = db.query(SavedRecommendation).filter(SavedRecommendation.user_id == current_user.id).order_by(SavedRecommendation.created_at.desc()).all()
    out = []
    for it in items:
        out.append({"id": it.id, "title": it.title, "data": json.loads(it.data), "created_at": it.created_at.isoformat()})
    return {"history": out}

# --- Resume Upload & Parse ---
@app.post("/upload_resume")
async def upload_resume(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes supported")
    contents = await file.read()
    try:
        reader = PdfReader(io.BytesIO(contents))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception:
        # fallback: return raw bytes length
        text = ""
    # naive skill extraction: match career_db skills
    found = set()
    for skills in (d["required_skills"] for d in career_db.values()):
        for s in skills:
            if s.lower() in text.lower():
                found.add(s.capitalize())
    return {"extracted_text_snippet": text[:200], "extracted_skills": sorted(list(found))}

# --- Badges (simple rules) ---
@app.get("/badges")
def badges(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    earned = []

    # --- Career Recommendation Badges ---
    items = db.query(SavedRecommendation).filter(SavedRecommendation.user_id == current_user.id).all()
    if items:
        earned.append({
            "id": "first_save",
            "name": "💾 First Save",
            "earned_at": items[0].created_at.isoformat()
        })
    for it in items:
        try:
            d = json.loads(it.data)
            top0 = d.get("top_careers", [])[0] if d.get("top_careers") else None
            if top0 and top0.get("match_score", 0) >= 80:
                earned.append({
                    "id": "top_match",
                    "name": "🌟 High Match (>=80%)",
                    "earned_at": it.created_at.isoformat()
                })
                break
        except Exception:
            continue

    # --- Quiz Badges ---
    quiz_items = db.query(QuizScore).filter(QuizScore.user_id == current_user.id).all()
    for q in quiz_items:
        if q.score == len(quiz_bank.get(q.career, [])):  # perfect score
            earned.append({
                "id": f"quiz_master_{q.career.lower()}",
                "name": f"🎓 Quiz Master ({q.career})",
                "earned_at": q.created_at.isoformat()
            })
            break
    if len(quiz_items) >= 5:
        earned.append({
            "id": "quiz_fanatic",
            "name": "🔥 Quiz Fanatic (5+ quizzes taken)",
            "earned_at": quiz_items[-1].created_at.isoformat()
        })

    # --- Resume Badges (simple rules) ---
    # idea: award when user uploads/enhances resume successfully
    resume_flag = db.query(SavedRecommendation).filter(
        SavedRecommendation.user_id == current_user.id,
        SavedRecommendation.title.like("%Resume%")
    ).first()

    if resume_flag:
        earned.append({
            "id": "resume_ready",
            "name": "📄 Resume Ready (uploaded & enhanced)",
            "earned_at": resume_flag.created_at.isoformat()
        })

    return {"badges": earned}

# --- Job trends (mock) ---
@app.get("/job_trends")
def job_trends(q: Optional[str] = None):
    # return mock time series
    labels = ["2024-01","2024-04","2024-07","2024-10","2025-01","2025-04","2025-07","2025-09"]
    base = [40,45,48,52,55,58,60,63]
    return {"query": q or "all", "trend": [{"date":d,"demand_index":base[i%len(base)] + (i%3)*2} for i,d in enumerate(labels)]}

# --- Export recommendation to PDF (simple) ---
# --- Export recommendation or resume to PDF ---
@app.post("/export_pdf")
def export_pdf(payload: dict, current_user: User = Depends(get_current_user)):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        textobject = c.beginText(40, 750)
        textobject.setFont("Helvetica", 12)

        # Common header
        textobject.textLine("AI Career Advisor Report")
        textobject.moveCursor(0, 18)
        textobject.textLine(f"Generated: {datetime.utcnow().isoformat()}")
        textobject.moveCursor(0, 24)

        # --- Case 1: Career Recommendation ---
        if "top_careers" in payload:
            textobject.textLine("=== Career Recommendations ===")
            for idx, cobj in enumerate(payload.get("top_careers", []), start=1):
                textobject.moveCursor(0, 16)
                textobject.textLine(f"{idx}. {cobj.get('career')} - Match: {cobj.get('match_score')}%")
                if cobj.get("matched_skills"):
                    textobject.moveCursor(0, 14)
                    textobject.textLine(f"   Matched: {', '.join(cobj['matched_skills'])}")
                if cobj.get("missing_skills"):
                    textobject.moveCursor(0, 14)
                    textobject.textLine(f"   Missing: {', '.join(cobj['missing_skills'])}")

        # --- Case 2: Resume Enhancement ---
        elif "suggestions" in payload or "skills" in payload:
            textobject.textLine("=== Resume Enhancement Report ===")
            skills = payload.get("skills", [])
            suggestions = payload.get("suggestions", [])
            if skills:
                textobject.moveCursor(0, 16)
                textobject.textLine(f"Extracted Skills: {', '.join(skills)}")
            if suggestions:
                textobject.moveCursor(0, 20)
                textobject.textLine("Improvement Suggestions:")
                for s in suggestions:
                    textobject.moveCursor(0, 14)
                    textobject.textLine(f"- {s}")

        else:
            textobject.textLine("No data provided.")

        c.drawText(textobject)
        c.showPage()
        c.save()
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=advisor_report.pdf"}
        )

    except Exception:
        # fallback: send plain text JSON
        b = io.BytesIO(json.dumps(payload, indent=2).encode("utf-8"))
        return StreamingResponse(
            b,
            media_type="application/octet-stream",
            headers={"Content-Disposition": "attachment; filename=advisor_report.json"}
        )

class QuizScore(Base):
    __tablename__ = "quiz_scores"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    career = Column(String, index=True)
    score = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner = relationship("User")

Base.metadata.create_all(bind=engine)

# --- Mock Quiz Questions ---
quiz_bank = {
    "Python": [
        {"q": "What is the output of len([1,2,3])?", "options": ["2","3","4"], "a": "3"},
        {"q": "Which keyword defines a function?", "options": ["func","def","lambda"], "a": "def"},
    ],
    "SQL": [
        {"q": "Which SQL keyword retrieves data?", "options": ["SELECT","UPDATE","INSERT"], "a": "SELECT"},
        {"q": "What does PRIMARY KEY ensure?", "options": ["Uniqueness","Speed","Null values"], "a": "Uniqueness"},
    ]
}
class QuizSubmission(BaseModel):
    career: str
    answers: dict

import random

@app.get("/quiz_questions")
def quiz_questions(career: str = "Python", limit: int = 2):
    questions = quiz_bank.get(career, [])
    if not questions:
        raise HTTPException(status_code=404, detail="No quiz available for this career")
    # Randomly select questions (default = 2)
    selected = random.sample(questions, min(limit, len(questions)))
    return {"career": career, "questions": selected}

@app.post("/submit_quiz")
def submit_quiz(body: QuizSubmission, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    questions = quiz_bank.get(body.career, [])
    score = sum(1 for i, q in enumerate(questions) if body.answers.get(str(i)) == q["a"])
    rec = QuizScore(user_id=current_user.id, career=body.career, score=score)
    db.add(rec); db.commit()
    return {"career": body.career, "score": score, "total": len(questions)}

# --- Mock Interview ---
@app.get("/interview_questions")
def interview_questions(career: str = "Data Scientist"):
    base_qs = {
        "Data Scientist": [
            "Explain overfitting in ML.",
            "What is p-value in statistics?",
            "How would you handle missing data?"
        ],
        "Web Developer": [
            "Explain the difference between GET and POST.",
            "What is a REST API?",
            "How does React manage state?"
        ]
    }
    return {"career": career, "questions": base_qs.get(career, ["Tell me about yourself."])}

@app.post("/interview_feedback")
def interview_feedback(career: str, answers: List[str]):
    # Simple keyword check
    feedback = []
    keywords = {
        "overfitting": ["overfit","generalization","train","test"],
        "GET vs POST": ["idempotent","data","body","url"],
    }
    for ans in answers:
        matched = [k for k,v in keywords.items() if any(word in ans.lower() for word in v)]
        feedback.append({"answer": ans, "keywords_matched": matched})
    return {"career": career, "feedback": feedback}

# --- Resume Enhancer ---
@app.post("/resume_enhance")
async def resume_enhance(file: UploadFile = File(...)):
    contents = await file.read()
    reader = PdfReader(io.BytesIO(contents))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    suggestions = []
    if "team" not in text.lower():
        suggestions.append("Add teamwork/leadership examples.")
    if "project" not in text.lower():
        suggestions.append("Mention 1-2 key projects with impact metrics.")
    return {"suggestions": suggestions}

# --- Career Comparison ---
@app.get("/compare_careers")
def compare_careers(c1: str, c2: str):
    d1, d2 = career_db.get(c1), career_db.get(c2)
    return {
        "career1": {"name": c1, **(d1 or {})},
        "career2": {"name": c2, **(d2 or {})},
        "salary_estimates": {c1: "₹12 LPA", c2: "₹10 LPA"},
    }
# --- Quiz Scores History ---
@app.get("/quiz_scores")
def quiz_scores(current_user: User = Depends(get_current_user), db=Depends(get_db)):
    items = db.query(QuizScore).filter(QuizScore.user_id == current_user.id).order_by(QuizScore.created_at.desc()).all()
    out = []
    for it in items:
        out.append({
            "career": it.career,
            "score": it.score,
            "created_at": it.created_at.isoformat()
        })
    return {"scores": out}
