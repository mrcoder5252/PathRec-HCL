"""
API layer — wraps Person 1's skill_graph.py and Person 3's rag_pipeline.py
as HTTP endpoints so the frontend (Person 5) and LLM layer (Person 4) can
call them directly, instead of importing the Python functions locally.
 
Run it:
    pip install fastapi uvicorn networkx pandas scikit-learn python-multipart
    uvicorn api:app --reload --port 8000
 
Then open http://localhost:8000/docs for interactive testing (Swagger UI) —
send this link to Person 4 and Person 5, it's the easiest way for them to
try every endpoint by hand before wiring real frontend code to it.
"""
 
from typing import Optional
 
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
 
from skill_graph import build_graph, get_path, get_skills_for_domain
from rag_pipeline import load_courses, build_text_index, retrieve_courses
 
# ---------------------------------------------------------------------------
# Load everything once at startup (not per-request — CSVs are small, graph
# building and TF-IDF indexing are cheap, but no reason to redo it every call)
# ---------------------------------------------------------------------------
 
app = FastAPI(title="PathRec API", version="0.1")
 
# Allow the frontend (running on a different port, e.g. localhost:3000 / 5173)
# to call this API directly from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your real frontend URL before the demo
    allow_methods=["*"],
    allow_headers=["*"],
)
 
GRAPH = build_graph("skills_template.csv")
COURSES = load_courses("courses_template.csv")
VECTORIZER, MATRIX = build_text_index(COURSES)
 
 
# ---------------------------------------------------------------------------
# Request/response shapes
# ---------------------------------------------------------------------------
 
class PathRequest(BaseModel):
    known_skills: list[str]
    goal_skill: str
 
 
class RoadmapRequest(BaseModel):
    known_skills: list[str]
    goal_skill: str
    courses_per_skill: int = 1
 
 
class CompareRequest(BaseModel):
    known_skills: list[str]
    goal_a: str
    goal_b: str
 
 
class CoursesRequest(BaseModel):
    skill_id: str
    skill_name: Optional[str] = None
    top_k: int = 3
 
 
class ProfileRequest(BaseModel):
    """
    Stores a learner's confidence scores + goal so /feedback can look them
    up and re-route later. This mirrors Person 2's build_learner_profile()
    output, simplified to what the feedback loop actually needs.
    """
    learner_id: str
    confidence: dict[str, float]  # {skill_id: confidence_0_to_1}
    goal_skill: str
 
 
class FeedbackRequest(BaseModel):
    """Matches the FeedbackEvent shape from the shared data contract."""
    learner_id: str
    skill_id: str
    event_type: str  # "quiz_score" | "completion" | "skip"
    score: Optional[float] = None  # required for "quiz_score", ignored otherwise
 
 
# In-memory store for the hackathon demo — swap for a real DB later.
# {learner_id: {"confidence": {...}, "goal_skill": "..."}}
LEARNER_PROFILES: dict[str, dict] = {}
 
CONFIDENCE_THRESHOLD = 0.5  # a skill counts as "known" at/above this confidence
 
 
def _apply_feedback(confidence_dict: dict, skill_id: str, event_type: str,
                     score: Optional[float] = None) -> dict:
    """
    Mirrors Person 2's apply_feedback() in quiz_engine.py — duplicated here
    (rather than imported) so this API server doesn't require a Gemini API
    key just to start up. Keep both in sync if the scoring logic changes.
    """
    updated = dict(confidence_dict)
    existing = updated.get(skill_id, 0.3)
 
    if event_type == "quiz_score" and score is not None:
        updated[skill_id] = round((existing * 0.4) + (score * 0.6), 2)
    elif event_type == "completion":
        updated[skill_id] = round(min(existing + 0.2, 1.0), 2)
    elif event_type == "skip":
        updated[skill_id] = round(max(existing - 0.15, 0.0), 2)
 
    return updated
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
def _skill_or_404(skill_id: str):
    if skill_id not in GRAPH:
        raise HTTPException(status_code=404, detail=f"Unknown skill_id: {skill_id}")
    return GRAPH.nodes[skill_id]
 
 
def _path_with_names(known_skills: list[str], goal_skill: str) -> list[dict]:
    _skill_or_404(goal_skill)
    ordered_ids = get_path(GRAPH, known_skills, goal_skill)
    return [{"skill_id": sid, "name": GRAPH.nodes[sid]["name"]} for sid in ordered_ids]
 
 
# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
 
@app.get("/")
def root():
    return {
        "status": "ok",
        "skills_loaded": GRAPH.number_of_nodes(),
        "courses_loaded": len(COURSES),
    }
 
 
@app.get("/skills/domain/{domain}")
def skills_for_domain(domain: str):
    """
    Used by Person 2 to filter the diagnostic quiz down to one domain's
    skill_ids. Matches DOMAIN_SKILL_MAP in quiz_engine.py — call this
    instead of hardcoding the map once both sides are wired together.
    """
    skill_ids = get_skills_for_domain(GRAPH, domain)
    if not skill_ids:
        raise HTTPException(status_code=404, detail=f"No skills found for domain: {domain}")
    return {
        "domain": domain,
        "skill_ids": skill_ids,
        "skills": [{"skill_id": sid, "name": GRAPH.nodes[sid]["name"]} for sid in skill_ids],
    }
 
 
@app.post("/path")
def compute_path(req: PathRequest):
    """
    Core gap-path endpoint. Given what the learner knows + their goal,
    returns the ordered list of missing skills (prerequisites first).
    """
    path = _path_with_names(req.known_skills, req.goal_skill)
    return {"goal_skill": req.goal_skill, "path": path}
 
 
@app.post("/courses")
def get_courses(req: CoursesRequest):
    """Returns real courses for a single skill_id."""
    node = _skill_or_404(req.skill_id)
    skill_name = req.skill_name or node["name"]
    results = retrieve_courses(req.skill_id, skill_name, COURSES, VECTORIZER, MATRIX, top_k=req.top_k)
    return {"skill_id": req.skill_id, "courses": results}
 
 
@app.post("/roadmap")
def full_roadmap(req: RoadmapRequest):
    """
    The main endpoint the frontend should call: gap-path + a real course
    attached to every step, in one response. This is what should drive
    the roadmap timeline UI directly — each item below maps to one
    PathMilestone-shaped card.
    """
    path = _path_with_names(req.known_skills, req.goal_skill)
    milestones = []
    for order, step in enumerate(path, start=1):
        courses = retrieve_courses(
            step["skill_id"], step["name"], COURSES, VECTORIZER, MATRIX,
            top_k=req.courses_per_skill,
        )
        milestones.append({
            "order": order,
            "skill_id": step["skill_id"],
            "skill_name": step["name"],
            "courses": courses,
            "status": "not_started",
        })
    return {"goal_skill": req.goal_skill, "milestones": milestones}
 
 
@app.post("/compare")
def compare_paths(req: CompareRequest):
    """
    Powers the "why not X?" feature: computes the path to two different
    goals from the same known_skills, and returns both plus what's
    shared/unique — Person 4's LLM layer can turn this into a sentence.
    """
    path_a = _path_with_names(req.known_skills, req.goal_a)
    path_b = _path_with_names(req.known_skills, req.goal_b)
 
    ids_a = {s["skill_id"] for s in path_a}
    ids_b = {s["skill_id"] for s in path_b}
 
    return {
        "goal_a": {"goal": req.goal_a, "path": path_a, "length": len(path_a)},
        "goal_b": {"goal": req.goal_b, "path": path_b, "length": len(path_b)},
        "shared_skills": sorted(ids_a & ids_b),
        "only_in_a": sorted(ids_a - ids_b),
        "only_in_b": sorted(ids_b - ids_a),
    }
 
 
@app.post("/profile")
def save_profile(req: ProfileRequest):
    """
    Stores a learner's confidence dict + goal so /feedback can look it up
    later and re-route. Call this once, right after the diagnostic quiz
    finishes (Person 2's build_learner_profile() output feeds this).
    """
    LEARNER_PROFILES[req.learner_id] = {
        "confidence": dict(req.confidence),
        "goal_skill": req.goal_skill,
    }
    known_skills = [s for s, c in req.confidence.items() if c >= CONFIDENCE_THRESHOLD]
    return {"learner_id": req.learner_id, "stored": True, "known_skills": known_skills}
 
 
@app.get("/profile/{learner_id}")
def get_profile(learner_id: str):
    """Debug helper — see what's currently stored for a learner."""
    if learner_id not in LEARNER_PROFILES:
        raise HTTPException(status_code=404, detail=f"No profile found for learner_id: {learner_id}")
    return LEARNER_PROFILES[learner_id]
 
 
@app.post("/feedback")
def submit_feedback(req: FeedbackRequest):
    """
    The adaptive-loop endpoint: a learner does badly (or well) on a skill,
    their confidence updates, and the roadmap is recomputed live using the
    new known_skills. This is the "demo-winning moment" from the persona
    flow — call /profile first, then this, and watch the returned roadmap
    change shape.
    """
    if req.learner_id not in LEARNER_PROFILES:
        raise HTTPException(
            status_code=404,
            detail=f"No profile found for learner_id: {req.learner_id}. Call POST /profile first.",
        )
 
    profile = LEARNER_PROFILES[req.learner_id]
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
        "re_routed_roadmap": {"goal_skill": profile["goal_skill"], "milestones": milestones},
    }
 