"""
Person 2 — Day 4 edge-case tests
Run this separately from quiz_engine.py's own demo block:
    python test_edge_cases.py
 
Checks the two scenarios explicitly called out in the team plan:
"make sure the quiz can't get stuck or produce a nonsensical confidence
score on edge cases (e.g. all-wrong or all-right answers)."
"""
 
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Quiz_Engine"))

from quiz_engine import StaircaseQuiz, QUESTION_BANK
def run_all_wrong():
    print("=== Edge case 1: learner answers every question WRONG ===")
    quiz = StaircaseQuiz(max_questions=6)
    while True:
        q = quiz.next_question()
        if q is None:
            break
        quiz.submit_answer(q["id"], "THIS_IS_NEVER_A_REAL_OPTION")
        print(f"  {q['id']} [{q['skill_id']}/{q['difficulty']}] -> forced wrong")
 
    confidence = quiz.compute_confidence()
    print("Resulting confidence dict:", confidence)
 
    # sanity checks
    assert all(0.0 <= v <= 1.0 for v in confidence.values()), "confidence out of [0,1] range!"
    assert all(v == 0.0 for v in confidence.values()), "expected all-zero confidence when every answer is wrong"
    print("PASS: all values are 0.0, nothing out of range, no crash.\n")
 
 
def run_all_right():
    print("=== Edge case 2: learner answers every question CORRECTLY ===")
    quiz = StaircaseQuiz(max_questions=6)
    while True:
        q = quiz.next_question()
        if q is None:
            break
        real_q = next(item for item in QUESTION_BANK if item["id"] == q["id"])
        quiz.submit_answer(q["id"], real_q["correct"])
        print(f"  {q['id']} [{q['skill_id']}/{q['difficulty']}] -> forced correct")
 
    confidence = quiz.compute_confidence()
    print("Resulting confidence dict:", confidence)
 
    assert all(0.0 <= v <= 1.0 for v in confidence.values()), "confidence out of [0,1] range!"
    assert all(v > 0.0 for v in confidence.values()), "expected all-positive confidence when every answer is correct"
    print("PASS: all values are positive and within range, no crash.\n")
 
 
def run_no_questions_available():
    print("=== Edge case 3: allowed_skill_ids doesn't match any question ===")
    quiz = StaircaseQuiz(allowed_skill_ids=["this_skill_does_not_exist"], max_questions=6)
    count = 0
    while True:
        q = quiz.next_question()
        if q is None:
            break
        count += 1
        # fallback logic in _pick_next_question should still find *some*
        # question from the full bank rather than looping forever
        quiz.submit_answer(q["id"], "irrelevant")
        if count > 20:
            raise AssertionError("quiz appears to be stuck in an infinite loop!")
    print(f"PASS: quiz terminated cleanly after {count} questions (fallback logic worked, no infinite loop).\n")
 
 
def run_empty_confidence_merge():
    print("=== Edge case 4: merging an empty text-extraction result ===")
    from quiz_engine import merge_confidence
    quiz_conf = {"py_basics": 0.6, "auth": 0.3}
    empty_text_conf = {}  # simulates extract_skill_mentions() failing safely and returning {}
    merged = merge_confidence(quiz_conf, empty_text_conf)
    assert merged == quiz_conf, "merging an empty dict should not change anything"
    print("PASS: merging with an empty result leaves the original confidence untouched.\n")
 
 
if __name__ == "__main__":
    run_all_wrong()
    run_all_right()
    run_no_questions_available()
    run_empty_confidence_merge()
    print("=== All edge-case tests passed ===")
 