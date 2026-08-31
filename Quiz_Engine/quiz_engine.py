"""
Person 2 — Diagnostic Quiz + Profiling Engine
Day 1 deliverable: staircase quiz logic + skill-mention extractor
Day 2 will add: domain filtering + merge into final {skill_id: confidence} dict
"""
 
import os
import json
import random
import requests
from dotenv import load_dotenv

load_dotenv()

_genai_client = None
def _get_genai_client():
    global _genai_client
    if _genai_client is None and os.getenv("GEMINI_API_KEY"):
        from google import genai
        _genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _genai_client
 
# ---------------------------------------------------------------------------
# 1. Load the question bank
# ---------------------------------------------------------------------------
 
with open(os.path.join(os.path.dirname(__file__), "quiz_questions.json")) as f:
    QUESTION_BANK = json.load(f)
 
DIFFICULTY_ORDER = ["easy", "medium", "hard"]
 
 
def get_questions_by_difficulty(difficulty, skill_id=None, exclude_ids=None):
    """Return questions matching a difficulty (and optional skill_id filter)."""
    exclude_ids = exclude_ids or set()
    pool = [
        q for q in QUESTION_BANK
        if q["difficulty"] == difficulty
        and q["id"] not in exclude_ids
        and (skill_id is None or q["skill_id"] == skill_id)
    ]
    return pool
 
 
# ---------------------------------------------------------------------------
# 2. The staircase engine
# ---------------------------------------------------------------------------
 
class StaircaseQuiz:
    """
    Adaptive difficulty quiz:
    - starts at 'medium'
    - correct answer -> next question is one tier harder
    - wrong answer -> next question is one tier easier
    - stops after max_questions (default 6, tune 5-8)
    """
 
    def __init__(self, allowed_skill_ids=None, max_questions=6):
        self.allowed_skill_ids = allowed_skill_ids  # None = no domain filter yet (Day 1)
        self.max_questions = max_questions
        self.current_difficulty_index = 1  # start at 'medium'
        self.asked_ids = set()
        self.history = []  # list of {question_id, skill_id, difficulty, correct: bool}
 
    def _pick_next_question(self):
        difficulty = DIFFICULTY_ORDER[self.current_difficulty_index]
        candidates = []
        for skill in (self.allowed_skill_ids or [None]):
            candidates += get_questions_by_difficulty(difficulty, skill, self.asked_ids)
        if not candidates:
            # fallback: relax difficulty constraint if we've run out at this tier
            candidates = [q for q in QUESTION_BANK if q["id"] not in self.asked_ids]
        return random.choice(candidates) if candidates else None
 
    def next_question(self):
        if len(self.history) >= self.max_questions:
            return None
        q = self._pick_next_question()
        if q is None:
            return None
        self.asked_ids.add(q["id"])
        return {"id": q["id"], "skill_id": q["skill_id"], "difficulty": q["difficulty"],
                "question": q["question"], "options": q["options"]}
 
    def submit_answer(self, question_id, selected_option):
        q = next(item for item in QUESTION_BANK if item["id"] == question_id)
        is_correct = selected_option == q["correct"]
        self.history.append({
            "question_id": question_id,
            "skill_id": q["skill_id"],
            "difficulty": q["difficulty"],
            "correct": is_correct,
        })
        # move the staircase
        if is_correct and self.current_difficulty_index < len(DIFFICULTY_ORDER) - 1:
            self.current_difficulty_index += 1
        elif not is_correct and self.current_difficulty_index > 0:
            self.current_difficulty_index -= 1
        return is_correct
 
    def compute_confidence(self):
        """
        Turns quiz history into {skill_id: confidence_0_to_1}.
        Simple version: weighted by difficulty (harder correct answers count more).
        """
        weights = {"easy": 0.3, "medium": 0.6, "hard": 1.0}
        skill_scores = {}
        skill_counts = {}
 
        for entry in self.history:
            sid = entry["skill_id"]
            score = weights[entry["difficulty"]] if entry["correct"] else 0.0
            skill_scores[sid] = skill_scores.get(sid, 0.0) + score
            skill_counts[sid] = skill_counts.get(sid, 0) + 1
 
        confidence = {}
        for sid, total in skill_scores.items():
            count = skill_counts[sid]
            confidence[sid] = round(min(total / count, 1.0), 2)
        return confidence
 
 
# ---------------------------------------------------------------------------
# 3. Skill-mention extractor (from free text, e.g. chat messages)
# ---------------------------------------------------------------------------
 
def extract_skill_mentions(user_text, llm_call_fn):
    """
    Uses an LLM to pull skill mentions out of free text and estimate confidence.
    llm_call_fn: a function(prompt: str) -> str, wired to whatever LLM API you're using.
    Returns: {skill_id: confidence_0_to_1}
    Coordinate skill_id naming with Person 1's taxonomy so IDs match exactly.
    """
    prompt = f"""You are extracting skill signals from a learner's message.
Return ONLY valid JSON, no explanation, no markdown.
Format: {{"skill_id": confidence_float_0_to_1, ...}}
Only include skills the learner clearly claims to know. Use snake_case skill ids
matching this style: python_basics, dbms, rest_apis, auth, deployment, system_design_basics.
If they say "basic" or "a bit of", use a lower confidence (0.2-0.4).
If they sound experienced, use higher confidence (0.6-0.9).
 
Message: "{user_text}"
"""
    raw = llm_call_fn(prompt)
    try:
        cleaned = raw.strip().strip("`").replace("json\n", "").replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError):
        return {}  # fail safe — empty dict, never crash the pipeline
 
 
# ---------------------------------------------------------------------------
# 4. Merge quiz results + text-extracted mentions into final profile dict
# ---------------------------------------------------------------------------
 
def merge_confidence(quiz_confidence, text_confidence):
    """
    Combines quiz-derived confidence with chat-extracted confidence.
    If both exist for a skill, take the higher value (benefit of the doubt,
    but quiz result is more reliable so weight it slightly more).
    """
    merged = dict(quiz_confidence)
    for skill_id, conf in text_confidence.items():
        if skill_id in merged:
            merged[skill_id] = round(max(merged[skill_id], conf * 0.9), 2)
        else:
            merged[skill_id] = round(conf, 2)
    return merged
 
 
# ---------------------------------------------------------------------------
# 5. Real LLM call (Gemini)
# ---------------------------------------------------------------------------
 
def real_llm_call(prompt):
    client = _get_genai_client()
    if client:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text or "{}"
        except Exception:
            return "{}"
    return "{}"
 
 
# ---------------------------------------------------------------------------
# 6. Domain filtering (Day 2 -> now live, calls Person 1's API)
# ---------------------------------------------------------------------------
# Person 1's skill_graph API is the source of truth for domain -> skill_ids.
# We keep a small local fallback map (using their REAL skill_ids, confirmed
# against skills_template.csv) in case the API isn't reachable — e.g. testing
# offline, or Person 1's server isn't running yet.
 
PATHREC_API_BASE = os.getenv("PATHREC_API_BASE", "http://127.0.0.1:8000")
 
FALLBACK_DOMAIN_SKILL_MAP = {
    "backend": [
        "py_basics", "sql_basics", "rest_apis", "auth",
        "deployment", "system_design_basics",
    ],
}
 
 
def get_allowed_skills_for_domain(domain):
    """
    Returns the list of skill_ids relevant to a given domain, for use as
    StaircaseQuiz(allowed_skill_ids=...).
 
    Tries Person 1's live API first (GET /skills/domain/{domain}) so the quiz
    always matches their real, current skill graph. Falls back to a small
    local map if the API isn't reachable, so this function never breaks the
    pipeline even if their server is down.
    """
    try:
        resp = requests.get(f"{PATHREC_API_BASE}/skills/domain/{domain}", timeout=3)
        if resp.status_code == 200:
            return resp.json()["skill_ids"]
    except requests.exceptions.RequestException:
        pass  # API not reachable — fall through to local fallback
 
    return FALLBACK_DOMAIN_SKILL_MAP.get(domain)  # None if unknown -> no filter
 
 
# ---------------------------------------------------------------------------
# 7. Clean LearnerProfile output for Person 1 (Day 2 deliverable)
# ---------------------------------------------------------------------------
# Converts our confidence dict into the current_skills shape from the shared
# data contract: [{skill_id, level: beginner|intermediate|advanced}]
 
def confidence_to_level(confidence):
    """Buckets a 0-1 confidence float into a level label."""
    if confidence >= 0.7:
        return "advanced"
    elif confidence >= 0.4:
        return "intermediate"
    else:
        return "beginner"
 
 
def build_learner_profile(learner_id, goal_text, target_domain, timeframe_weeks,
                           merged_confidence, completed_courses=None):
    """
    Assembles the final LearnerProfile-shaped dict (minus profile_embedding,
    which isn't Person 2's job) ready to hand to Person 1 / the backend.
    merged_confidence: output of merge_confidence() — {skill_id: confidence_0_to_1}
    """
    current_skills = [
        {"skill_id": skill_id, "level": confidence_to_level(conf)}
        for skill_id, conf in merged_confidence.items()
    ]
    return {
        "id": learner_id,
        "goal_text": goal_text,
        "target_domain": target_domain,
        "timeframe_weeks": timeframe_weeks,
        "current_skills": current_skills,
        "completed_courses": completed_courses or [],
    }
 
 
# ---------------------------------------------------------------------------
# 8. Feedback-based confidence updates (Day 3)
# ---------------------------------------------------------------------------
# Takes a FeedbackEvent (quiz_score | completion | skip) and adjusts that
# skill's confidence, so the updated dict can be re-passed into get_path()
# for re-routing. This is the "confidence needs to feed back into known_skills"
# piece Person 1's roadmap describes.
 
def apply_feedback(confidence_dict, skill_id, event_type, score=None):
    """
    Mutates a copy of confidence_dict based on a single FeedbackEvent and
    returns the updated dict. Never errors out on unknown skill_ids —
    just adds them fresh at a sensible default.
 
    event_type "quiz_score": score is 0-1, blended with existing confidence
    event_type "completion": bumps confidence up (module finished successfully)
    event_type "skip": drops confidence — treat similarly to "too easy/too hard"
                        signal (learner skipped, so we don't trust this skill yet)
    """
    updated = dict(confidence_dict)
    existing = updated.get(skill_id, 0.3)  # default starting point if unseen
 
    if event_type == "quiz_score" and score is not None:
        # Weighted blend: new signal counts more than old, but doesn't fully overwrite
        updated[skill_id] = round((existing * 0.4) + (score * 0.6), 2)
    elif event_type == "completion":
        updated[skill_id] = round(min(existing + 0.2, 1.0), 2)
    elif event_type == "skip":
        updated[skill_id] = round(max(existing - 0.15, 0.0), 2)
 
    return updated
 
 
# ---------------------------------------------------------------------------
# 9. Quick manual test — run this file directly to see it work
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    quiz = StaircaseQuiz(max_questions=6)  # no domain filter yet, Day 1 only
 
    print("=== Simulated quiz run ===")
    while True:
        q = quiz.next_question()
        if q is None:
            break
        # Simulate a learner who's decent at python/rest but weak at deployment/system design
        good_skills = {"python_basics", "rest_apis"}
        pretend_correct = q["skill_id"] in good_skills or random.random() > 0.5
        real_q = next(item for item in QUESTION_BANK if item["id"] == q["id"])
        selected = real_q["correct"] if pretend_correct else "WRONG_OPTION_PLACEHOLDER"
        is_correct = quiz.submit_answer(q["id"], selected)
        print(f"{q['id']} [{q['skill_id']}/{q['difficulty']}] -> {'✓' if is_correct else '✗'}")
 
    quiz_confidence = quiz.compute_confidence()
    print("\nQuiz-derived confidence:", quiz_confidence)
 
    test_messages = [
        "I've built REST APIs with Flask and know some JWT auth basics",
        "I've deployed apps using Docker before",
        "I'm comfortable writing SQL queries and database schemas",
    ]
 
    print("\n=== Testing skill-mention extraction (REAL Gemini API) ===")
    final_merged = dict(quiz_confidence)
    for msg in test_messages:
        text_conf = extract_skill_mentions(msg, real_llm_call)
        final_merged = merge_confidence(final_merged, text_conf)
        print(f"\nMessage: {msg}")
        print("Extracted:", text_conf)
        print("Merged with quiz confidence:", final_merged)
 
    # -----------------------------------------------------------------
    # Demo: domain filtering (Day 2)
    # -----------------------------------------------------------------
    print("\n=== Domain filtering demo ===")
    domain = "backend"  # must match Person 1's real domain name in skills_template.csv
    allowed = get_allowed_skills_for_domain(domain)
    print(f"Allowed skill_ids for '{domain}':", allowed)
    filtered_quiz = StaircaseQuiz(allowed_skill_ids=allowed, max_questions=6)
    print("(A new StaircaseQuiz(allowed_skill_ids=...) instance is now scoped to this domain)")
 
    # -----------------------------------------------------------------
    # Demo: clean LearnerProfile output for Person 1
    # -----------------------------------------------------------------
    print("\n=== LearnerProfile output for Person 1 ===")
    profile = build_learner_profile(
        learner_id="learner_001",
        goal_text="I want to become a backend developer and land an internship in 4 months",
        target_domain=domain,
        timeframe_weeks=16,
        merged_confidence=final_merged,
    )
    print(json.dumps(profile, indent=2))
 
    # -----------------------------------------------------------------
    # Demo: feedback-based confidence update (Day 3)
    # -----------------------------------------------------------------
    print("\n=== Feedback loop demo ===")
    print("Before feedback:", final_merged.get("sql_basics"))
    updated_confidence = apply_feedback(final_merged, "sql_basics", "quiz_score", score=0.9)
    print("After a strong SQL Basics quiz_score (0.9):", updated_confidence.get("sql_basics"))
    updated_confidence = apply_feedback(updated_confidence, "auth", "skip")
    print("After skipping the 'auth' module:", updated_confidence.get("auth"))
    updated_confidence = apply_feedback(updated_confidence, "deployment", "completion")
    print("After completing the 'deployment' module:", updated_confidence.get("deployment"))
    print("\nFull updated confidence dict (this is what gets passed back to Person 1's get_path()):")
    print(json.dumps(updated_confidence, indent=2))
 
    # -----------------------------------------------------------------
    # Demo: full end-to-end chain -> real call to Person 1's /roadmap API
    # -----------------------------------------------------------------
    # Requires Person 1's server running: uvicorn api:app --port 8000
    print("\n=== End-to-end: calling Person 1's live /roadmap API ===")
 
    CONFIDENCE_THRESHOLD = 0.5  # treat a skill as "known" above this confidence
 
    known_skills = [
        skill_id for skill_id, conf in updated_confidence.items()
        if conf >= CONFIDENCE_THRESHOLD
    ]
    print(f"known_skills (confidence >= {CONFIDENCE_THRESHOLD}):", known_skills)
 
    goal_skill = "deployment"  # placeholder — normally comes from Person 4's intake extraction
    try:
        resp = requests.post(
            f"{PATHREC_API_BASE}/roadmap",
            json={"known_skills": known_skills, "goal_skill": goal_skill},
            timeout=5,
        )
        if resp.status_code == 200:
            roadmap = resp.json()
            print(f"\nRoadmap for goal '{goal_skill}':")
            for m in roadmap["milestones"]:
                course_title = m["courses"][0]["title"] if m["courses"] else "no course found"
                print(f"  {m['order']}. {m['skill_name']} -> {course_title}")
        else:
            print(f"API returned status {resp.status_code}: {resp.text}")
    except requests.exceptions.RequestException as e:
        print(f"Could not reach Person 1's API at {PATHREC_API_BASE} — is their server running?")
        print(f"(error: {e})")
 
