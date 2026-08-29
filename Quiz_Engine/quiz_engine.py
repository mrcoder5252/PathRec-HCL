"""
Person 2 — Diagnostic Quiz + Profiling Engine
Day 1 deliverable: staircase quiz logic + skill-mention extractor
Day 2 will add: domain filtering + merge into final {skill_id: confidence} dict
"""
 
import os
import json
import random
from dotenv import load_dotenv
import google.generativeai as genai
 
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")
 
# ---------------------------------------------------------------------------
# 1. Load the question bank
# ---------------------------------------------------------------------------
 
with open("quiz_questions.json") as f:
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
    response = model.generate_content(prompt)
    return response.text
 
 
# ---------------------------------------------------------------------------
# 6. Quick manual test — run this file directly to see it work
# ---------------------------------------------------------------------------
 
if __name__ == "__main__":
    quiz = StaircaseQuiz(
    allowed_skill_ids={"python_basics", "dbms", "rest_apis", "auth", "deployment"},
    max_questions=6
)
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
 
    profile_message = """
        I want to become a backend developer.
        I have built REST APIs using Flask and know basic JWT authentication.
        I have also worked with SQL databases.
        """

    print("\n=== Learner Profile ===")

    text_conf = extract_skill_mentions(profile_message, real_llm_call)
    final_profile = merge_confidence(quiz_confidence, text_conf)

    print("Profile skill signals:", text_conf)
    print("FINAL LEARNER PROFILE:", final_profile)
        