"""
Person 2 <-> Person 1 integration — clean demo script
Shows the full flow in one place, no unrelated quiz/text-extraction noise:
 
    1. Take a learner's {skill_id: confidence} profile (from quiz_engine.py)
    2. Send it to Person 1's API (POST /profile)
    3. Get back their initial roadmap
    4. Simulate a feedback event (learner fails a quiz on one skill)
    5. Show the roadmap automatically re-routing
 
Run Person 1's server first, in its own terminal:
    uvicorn api:app --reload --port 8000
 
Then run this file in a second terminal:
    python integration_demo.py
"""
 
import os
import requests
 
PATHREC_API_BASE = os.getenv("PATHREC_API_BASE", "http://127.0.0.1:8000")
 
 
def check_server_is_up():
    try:
        resp = requests.get(f"{PATHREC_API_BASE}/", timeout=3)
        resp.raise_for_status()
        info = resp.json()
        print(f"Connected to Person 1's API — {info['skills_loaded']} skills, {info['courses_loaded']} courses loaded.\n")
        return True
    except requests.exceptions.RequestException:
        print(f"Could not reach {PATHREC_API_BASE} — is `uvicorn api:app --port 8000` running in another terminal?")
        return False
 
 
def save_profile(learner_id, confidence, goal_skill):
    resp = requests.post(
        f"{PATHREC_API_BASE}/profile",
        json={"learner_id": learner_id, "confidence": confidence, "goal_skill": goal_skill},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
 
 
def get_roadmap(known_skills, goal_skill):
    resp = requests.post(
        f"{PATHREC_API_BASE}/roadmap",
        json={"known_skills": known_skills, "goal_skill": goal_skill},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
 
 
def submit_feedback(learner_id, skill_id, event_type, score=None):
    resp = requests.post(
        f"{PATHREC_API_BASE}/feedback",
        json={"learner_id": learner_id, "skill_id": skill_id, "event_type": event_type, "score": score},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
 
 
def print_roadmap(title, milestones):
    print(title)
    for m in milestones:
        course = m["courses"][0]["title"] if m.get("courses") else "no course found"
        print(f"  {m['order']}. {m['skill_name']} -> {course}")
    print()
 
 
if __name__ == "__main__":
    if not check_server_is_up():
        exit(1)
 
    # This is exactly the shape quiz_engine.py's merge_confidence() produces —
    # swap this for the real output of your quiz run whenever you like.
    learner_id = "demo_learner"
    confidence = {
        "py_basics": 0.8,
        "rest_apis": 0.6,
        "sql_basics": 0.3,
        "auth": 0.2,
    }
    goal_skill = "deployment"
 
    print("=== Step 1: Save learner profile ===")
    print(f"Confidence dict: {confidence}")
    save_result = save_profile(learner_id, confidence, goal_skill)
    print(f"Known skills (>= 0.5 confidence): {save_result['known_skills']}\n")
 
    print("=== Step 2: Initial roadmap ===")
    initial = get_roadmap(save_result["known_skills"], goal_skill)
    print_roadmap(f"Roadmap to '{goal_skill}' ({len(initial['milestones'])} steps):", initial["milestones"])
 
    print("=== Step 3: Learner fails a quiz on 'rest_apis' (score 0.1) ===")
    feedback_result = submit_feedback(learner_id, "rest_apis", "quiz_score", score=0.1)
    print(f"Updated confidence: {feedback_result['updated_confidence']}")
    print(f"Known skills now: {feedback_result['known_skills']}\n")
 
    print("=== Step 4: Re-routed roadmap (automatic) ===")
    new_milestones = feedback_result["re_routed_roadmap"]["milestones"]
    print_roadmap(f"Roadmap to '{goal_skill}' ({len(new_milestones)} steps):", new_milestones)
 
    print("=== Result ===")
    print(f"Roadmap grew from {len(initial['milestones'])} to {len(new_milestones)} steps")
    print("after a single bad quiz score — the adaptive loop is working end-to-end.")
 