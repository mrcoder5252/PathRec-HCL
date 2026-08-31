"""
PathRec API & Nexora Backend
=============================
Combines:
- JWT User Authentication (Register, Login, Session)
- Skill Dependency Graph (NetworkX)
- Course Retrieval & RAG Pipeline (TF-IDF + Cosine Similarity)
- Adaptive Staircase Diagnostic Quiz Engine
- Live Adaptive Feedback Loop & Re-routing
- "Why Not X?" Goal Comparison & Path Narration
- AI Career Copilot & LLM Intake
"""

import os
import uuid
import hashlib
import json
from typing import Optional, List, Dict
from datetime import datetime, timedelta

import jwt
from fastapi import FastAPI, HTTPException, Header, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from skill_graph import build_graph, get_path, get_skills_for_domain
from rag_pipeline import load_courses, build_text_index, retrieve_courses
from llm_layer import narrate_path, explain_why_not, intake_extract

# ---------------------------------------------------------------------------
# App Initialization & Data Loading
# ---------------------------------------------------------------------------

app = FastAPI(title="PathRec & Nexora API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GRAPH = build_graph("skills_template.csv")
COURSES = load_courses("courses_template.csv")
VECTORIZER, MATRIX = build_text_index(COURSES)

# Load quiz question bank
QUIZ_FILE = os.path.join("Quiz_Engine", "quiz_questions.json")
if os.path.exists(QUIZ_FILE):
    with open(QUIZ_FILE, "r", encoding="utf-8") as f:
        QUESTION_BANK = json.load(f)
else:
    QUESTION_BANK = []

# ---------------------------------------------------------------------------
# Auth Config & In-Memory Stores
# ---------------------------------------------------------------------------

JWT_SECRET = os.getenv("JWT_SECRET", "nexora-super-secret-jwt-key-2026")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 72

USERS_DB: Dict[str, dict] = {
    "alex@example.com": {
        "id": "user_alex_001",
        "email": "alex@example.com",
        "name": "Alex Morgan",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "target_role": "Backend Developer",
        "domain": "backend",
        "goal_skill": "deployment",
        "confidence": {"py_basics": 0.8, "sql_basics": 0.6, "rest_apis": 0.5},
        "created_at": datetime.utcnow().isoformat()
    }
}

LEARNER_PROFILES: Dict[str, dict] = {
    "user_alex_001": {
        "confidence": {"py_basics": 0.8, "sql_basics": 0.6, "rest_apis": 0.5},
        "goal_skill": "deployment"
    }
}

QUIZ_SESSIONS: Dict[str, dict] = {}

CONFIDENCE_THRESHOLD = 0.5
DIFFICULTY_ORDER = ["easy", "medium", "hard"]


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    name: str
    target_role: Optional[str] = "Backend Developer"
    domain: Optional[str] = "backend"
    goal_skill: Optional[str] = "deployment"


class UserLoginRequest(BaseModel):
    email: str
    password: str


class PathRequest(BaseModel):
    known_skills: List[str]
    goal_skill: str


class RoadmapRequest(BaseModel):
    known_skills: List[str]
    goal_skill: str
    courses_per_skill: int = 1


class CompareRequest(BaseModel):
    known_skills: List[str]
    goal_a: str
    goal_b: str


class CoursesRequest(BaseModel):
    skill_id: str
    skill_name: Optional[str] = None
    top_k: int = 3


class ProfileRequest(BaseModel):
    learner_id: str
    confidence: Dict[str, float]
    goal_skill: str


class FeedbackRequest(BaseModel):
    learner_id: str
    skill_id: str
    event_type: str  # "quiz_score" | "completion" | "skip"
    score: Optional[float] = None


class QuizStartRequest(BaseModel):
    learner_id: Optional[str] = "guest"
    domain: Optional[str] = "backend"
    max_questions: Optional[int] = 6


class QuizSubmitRequest(BaseModel):
    session_id: str
    question_id: str
    selected_option: str


class CopilotRequest(BaseModel):
    message: str
    learner_id: Optional[str] = None
    history: Optional[List[dict]] = None


# ---------------------------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def create_jwt_token(email: str, user_id: str) -> str:
    payload = {
        "sub": email,
        "uid": user_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user_from_token(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        return USERS_DB.get(email)
    except Exception:
        return None


def require_current_user(authorization: Optional[str] = Header(None)) -> dict:
    user = get_current_user_from_token(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token."
        )
    return user


# ---------------------------------------------------------------------------
# Core Helpers
# ---------------------------------------------------------------------------

def _skill_or_404(skill_id: str):
    if skill_id not in GRAPH:
        raise HTTPException(status_code=404, detail=f"Unknown skill_id: {skill_id}")
    return GRAPH.nodes[skill_id]


def _path_with_names(known_skills: List[str], goal_skill: str) -> List[dict]:
    _skill_or_404(goal_skill)
    ordered_ids = get_path(GRAPH, known_skills, goal_skill)
    return [{"skill_id": sid, "name": GRAPH.nodes[sid]["name"], "domain": GRAPH.nodes[sid].get("domain", "backend")} for sid in ordered_ids]


def _apply_feedback(confidence_dict: dict, skill_id: str, event_type: str, score: Optional[float] = None) -> dict:
    updated = dict(confidence_dict)
    existing = updated.get(skill_id, 0.3)

    if event_type == "quiz_score" and score is not None:
        updated[skill_id] = round((existing * 0.4) + (score * 0.6), 2)
    elif event_type == "completion":
        updated[skill_id] = round(min(existing + 0.3, 1.0), 2)
    elif event_type == "skip":
        updated[skill_id] = round(max(existing - 0.2, 0.0), 2)

    return updated


# ---------------------------------------------------------------------------
# Auth Endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/register")
def register_user(req: UserRegisterRequest):
    email_clean = req.email.strip().lower()
    if email_clean in USERS_DB:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user_id = f"user_{uuid.uuid4().hex[:8]}"
    new_user = {
        "id": user_id,
        "email": email_clean,
        "name": req.name.strip(),
        "password_hash": hash_password(req.password),
        "target_role": req.target_role or "Backend Developer",
        "domain": req.domain or "backend",
        "goal_skill": req.goal_skill or "deployment",
        "confidence": {},
        "created_at": datetime.utcnow().isoformat()
    }
    USERS_DB[email_clean] = new_user
    LEARNER_PROFILES[user_id] = {
        "confidence": {},
        "goal_skill": new_user["goal_skill"]
    }

    token = create_jwt_token(email_clean, user_id)
    return {
        "token": token,
        "user": {
            "id": user_id,
            "email": email_clean,
            "name": new_user["name"],
            "target_role": new_user["target_role"],
            "domain": new_user["domain"],
            "goal_skill": new_user["goal_skill"],
            "confidence": new_user["confidence"]
        }
    }


@app.post("/auth/login")
def login_user(req: UserLoginRequest):
    email_clean = req.email.strip().lower()
    user = USERS_DB.get(email_clean)
    if not user or user["password_hash"] != hash_password(req.password):
        raise HTTPException(status_code=400, detail="Invalid email or password.")

    token = create_jwt_token(email_clean, user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "target_role": user["target_role"],
            "domain": user["domain"],
            "goal_skill": user["goal_skill"],
            "confidence": user.get("confidence", {})
        }
    }


@app.get("/auth/me")
def get_current_user_profile(user: dict = Depends(require_current_user)):
    profile = LEARNER_PROFILES.get(user["id"], {})
    user_confidence = profile.get("confidence", user.get("confidence", {}))
    known_skills = [s for s, c in user_confidence.items() if c >= CONFIDENCE_THRESHOLD]

    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "target_role": user["target_role"],
        "domain": user["domain"],
        "goal_skill": user["goal_skill"],
        "confidence": user_confidence,
        "known_skills": known_skills
    }


# ---------------------------------------------------------------------------
# General & Domain Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "PathRec & Nexora API",
        "skills_loaded": GRAPH.number_of_nodes(),
        "courses_loaded": len(COURSES),
        "questions_loaded": len(QUESTION_BANK),
    }


@app.get("/domains")
def get_domains():
    domains = list({data.get("domain", "backend") for _, data in GRAPH.nodes(data=True)})
    return {"domains": sorted(domains)}


@app.get("/skills/domain/{domain}")
def skills_for_domain(domain: str):
    skill_ids = get_skills_for_domain(GRAPH, domain)
    if not skill_ids:
        raise HTTPException(status_code=404, detail=f"No skills found for domain: {domain}")
    return {
        "domain": domain,
        "skill_ids": skill_ids,
        "skills": [{"skill_id": sid, "name": GRAPH.nodes[sid]["name"]} for sid in skill_ids],
    }


# ---------------------------------------------------------------------------
# Staircase Diagnostic Quiz Endpoints
# ---------------------------------------------------------------------------

def _pick_next_question(domain: str, difficulty_idx: int, asked_ids: set, allowed_skills: Optional[List[str]] = None) -> Optional[dict]:
    difficulty = DIFFICULTY_ORDER[difficulty_idx]
    candidates = [
        q for q in QUESTION_BANK
        if q["id"] not in asked_ids
        and q["difficulty"] == difficulty
        and (allowed_skills is None or q["skill_id"] in allowed_skills)
    ]
    if not candidates:
        candidates = [
            q for q in QUESTION_BANK
            if q["id"] not in asked_ids
            and (allowed_skills is None or q["skill_id"] in allowed_skills)
        ]
    if not candidates:
        candidates = [q for q in QUESTION_BANK if q["id"] not in asked_ids]

    if not candidates:
        return None

    return candidates[0]


@app.post("/quiz/start")
def start_quiz_session(req: QuizStartRequest):
    session_id = f"quiz_{uuid.uuid4().hex[:10]}"
    allowed_skills = get_skills_for_domain(GRAPH, req.domain) if req.domain else None

    q = _pick_next_question(req.domain or "backend", 1, set(), allowed_skills)
    if not q:
        raise HTTPException(status_code=500, detail="No quiz questions available.")

    QUIZ_SESSIONS[session_id] = {
        "learner_id": req.learner_id or "guest",
        "domain": req.domain or "backend",
        "difficulty_idx": 1,
        "history": [],
        "asked_ids": [q["id"]],
        "max_questions": req.max_questions or 6,
        "allowed_skills": allowed_skills
    }

    return {
        "session_id": session_id,
        "question_number": 1,
        "total_questions": req.max_questions or 6,
        "question": {
            "id": q["id"],
            "skill_id": q["skill_id"],
            "difficulty": q["difficulty"],
            "question": q["question"],
            "options": q["options"]
        }
    }


@app.post("/quiz/submit")
def submit_quiz_answer(req: QuizSubmitRequest):
    session = QUIZ_SESSIONS.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Quiz session not found or expired.")

    q = next((item for item in QUESTION_BANK if item["id"] == req.question_id), None)
    if not q:
        raise HTTPException(status_code=404, detail=f"Question id {req.question_id} not found.")

    is_correct = req.selected_option == q["correct"]
    session["history"].append({
        "question_id": q["id"],
        "skill_id": q["skill_id"],
        "difficulty": q["difficulty"],
        "correct": is_correct,
        "selected": req.selected_option,
        "correct_answer": q["correct"]
    })

    if is_correct and session["difficulty_idx"] < len(DIFFICULTY_ORDER) - 1:
        session["difficulty_idx"] += 1
    elif not is_correct and session["difficulty_idx"] > 0:
        session["difficulty_idx"] -= 1

    if len(session["history"]) >= session["max_questions"]:
        weights = {"easy": 0.3, "medium": 0.6, "hard": 1.0}
        skill_scores: Dict[str, float] = {}
        skill_counts: Dict[str, int] = {}

        for entry in session["history"]:
            sid = entry["skill_id"]
            score = weights[entry["difficulty"]] if entry["correct"] else 0.0
            skill_scores[sid] = skill_scores.get(sid, 0.0) + score
            skill_counts[sid] = skill_counts.get(sid, 0) + 1

        confidence = {}
        for sid, total in skill_scores.items():
            count = skill_counts[sid]
            confidence[sid] = round(min(total / count, 1.0), 2)

        learner_id = session["learner_id"]
        if learner_id in LEARNER_PROFILES:
            LEARNER_PROFILES[learner_id]["confidence"] = dict(confidence)

        return {
            "completed": True,
            "is_correct": is_correct,
            "correct_answer": q["correct"],
            "explanation": f"{'Correct!' if is_correct else 'Incorrect.'} The answer is: {q['correct']}",
            "confidence": confidence,
            "total_answered": len(session["history"]),
            "correct_count": sum(1 for h in session["history"] if h["correct"]),
        }

    next_q = _pick_next_question(session["domain"], session["difficulty_idx"], set(session["asked_ids"]), session["allowed_skills"])
    if not next_q:
        confidence = {}
        return {
            "completed": True,
            "is_correct": is_correct,
            "correct_answer": q["correct"],
            "confidence": confidence,
            "total_answered": len(session["history"]),
            "correct_count": sum(1 for h in session["history"] if h["correct"]),
        }

    session["asked_ids"].append(next_q["id"])

    return {
        "completed": False,
        "is_correct": is_correct,
        "correct_answer": q["correct"],
        "question_number": len(session["history"]) + 1,
        "total_questions": session["max_questions"],
        "next_question": {
            "id": next_q["id"],
            "skill_id": next_q["skill_id"],
            "difficulty": next_q["difficulty"],
            "question": next_q["question"],
            "options": next_q["options"]
        }
    }


# ---------------------------------------------------------------------------
# Roadmap & Course Endpoints
# ---------------------------------------------------------------------------

@app.post("/path")
def compute_path(req: PathRequest):
    path = _path_with_names(req.known_skills, req.goal_skill)
    return {"goal_skill": req.goal_skill, "path": path}


@app.post("/courses")
def get_courses(req: CoursesRequest):
    node = _skill_or_404(req.skill_id)
    skill_name = req.skill_name or node["name"]
    results = retrieve_courses(req.skill_id, skill_name, COURSES, VECTORIZER, MATRIX, top_k=req.top_k)
    return {"skill_id": req.skill_id, "courses": results}


@app.post("/roadmap")
def full_roadmap(req: RoadmapRequest):
    path = _path_with_names(req.known_skills, req.goal_skill)
    milestones = []
    retrieved_map = {}

    for order, step in enumerate(path, start=1):
        courses = retrieve_courses(
            step["skill_id"], step["name"], COURSES, VECTORIZER, MATRIX,
            top_k=req.courses_per_skill,
        )
        retrieved_map[step["skill_id"]] = courses
        milestones.append({
            "order": order,
            "skill_id": step["skill_id"],
            "skill_name": step["name"],
            "domain": step.get("domain", "backend"),
            "courses": courses,
            "status": "not_started",
        })

    narration = narrate_path(path, retrieved_map)

    return {
        "goal_skill": req.goal_skill,
        "total_milestones": len(milestones),
        "narration": narration,
        "milestones": milestones
    }


@app.post("/compare")
def compare_paths(req: CompareRequest):
    path_a = _path_with_names(req.known_skills, req.goal_a)
    path_b = _path_with_names(req.known_skills, req.goal_b)

    ids_a = {s["skill_id"] for s in path_a}
    ids_b = {s["skill_id"] for s in path_b}

    shared_ids = sorted(ids_a & ids_b)
    only_a_ids = sorted(ids_a - ids_b)
    only_b_ids = sorted(ids_b - ids_a)

    explanation = explain_why_not(path_a, path_b, req.goal_a, req.goal_b)

    return {
        "goal_a": {"goal": req.goal_a, "path": path_a, "length": len(path_a)},
        "goal_b": {"goal": req.goal_b, "path": path_b, "length": len(path_b)},
        "shared_skills": [{"skill_id": sid, "name": GRAPH.nodes[sid]["name"]} for sid in shared_ids],
        "only_in_a": [{"skill_id": sid, "name": GRAPH.nodes[sid]["name"]} for sid in only_a_ids],
        "only_in_b": [{"skill_id": sid, "name": GRAPH.nodes[sid]["name"]} for sid in only_b_ids],
        "explanation": explanation
    }


# ---------------------------------------------------------------------------
# Profile & Adaptive Feedback Loop Endpoints
# ---------------------------------------------------------------------------

@app.post("/profile")
def save_profile(req: ProfileRequest):
    LEARNER_PROFILES[req.learner_id] = {
        "confidence": dict(req.confidence),
        "goal_skill": req.goal_skill,
    }
    known_skills = [s for s, c in req.confidence.items() if c >= CONFIDENCE_THRESHOLD]
    return {
        "learner_id": req.learner_id,
        "stored": True,
        "known_skills": known_skills
    }


@app.get("/profile/{learner_id}")
def get_profile(learner_id: str):
    if learner_id not in LEARNER_PROFILES:
        return {
            "learner_id": learner_id,
            "confidence": {"py_basics": 0.8, "sql_basics": 0.6},
            "goal_skill": "deployment"
        }
    return LEARNER_PROFILES[learner_id]


@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    profile = LEARNER_PROFILES.get(req.learner_id, {
        "confidence": {"py_basics": 0.8, "sql_basics": 0.6},
        "goal_skill": "deployment"
    })

    updated_confidence = _apply_feedback(profile["confidence"], req.skill_id, req.event_type, req.score)
    profile["confidence"] = updated_confidence
    LEARNER_PROFILES[req.learner_id] = profile

    known_skills = [s for s, c in updated_confidence.items() if c >= CONFIDENCE_THRESHOLD]
    new_path = _path_with_names(known_skills, profile["goal_skill"])

    milestones = []
    for order, step in enumerate(new_path, start=1):
        courses = retrieve_courses(step["skill_id"], step["name"], COURSES, VECTORIZER, MATRIX, top_k=1)
        milestones.append({
            "order": order,
            "skill_id": step["skill_id"],
            "skill_name": step["name"],
            "courses": courses,
            "status": "not_started",
        })

    return {
        "learner_id": req.learner_id,
        "updated_confidence": updated_confidence,
        "known_skills": known_skills,
        "re_routed_roadmap": {
            "goal_skill": profile["goal_skill"],
            "milestones": milestones,
            "total_milestones": len(milestones)
        },
    }


# ---------------------------------------------------------------------------
# AI Copilot & Natural Language Intake Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/copilot")
def copilot_chat(req: CopilotRequest):
    user_text = req.message.strip()

    extracted = None
    try:
        if any(keyword in user_text.lower() for keyword in ["want to", "learn", "goal", "become", "know", "study", "path"]):
            extracted = intake_extract(user_text)
    except Exception:
        extracted = None

    if extracted and extracted.get("goal_skill"):
        goal = extracted.get("goal_skill")
        claimed = extracted.get("claimed_skills", [])
        timeframe = extracted.get("timeframe") or "your target timeline"
        goal_name = GRAPH.nodes.get(goal, {}).get('name', goal)
        reply = (
            f"🎯 I understand your goal is **{goal_name}** "
            f"({extracted.get('domain', 'backend')}) within **{timeframe}**.\n\n"
            f"You mentioned knowing: **{', '.join(claimed) if claimed else 'starting fresh'}**.\n"
            f"I have initialized your tailored roadmap with prerequisite milestones and curated courses!"
        )
    elif "resume" in user_text.lower():
        reply = "📄 For your resume, ensure you quantify your impact with metrics (e.g., 'Designed REST APIs handling 500+ requests/sec'). Check the Resume tab to see tailored ATS keyword suggestions."
    elif "interview" in user_text.lower():
        reply = "🎙️ To prepare for backend technical interviews, practice system design trade-offs (caching, database indexing) and explaining your code clearly."
    elif "priority" in user_text.lower() or "focus" in user_text.lower():
        reply = "⚡ Top priority: Complete the diagnostic assessment to identify your key skill gaps and start your recommended courses."
    else:
        reply = f"I'm here to guide your career growth! You can ask me to evaluate your goal, review your skills, or explain specific course prerequisites."

    return {
        "reply": reply,
        "extracted_data": extracted
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)

 