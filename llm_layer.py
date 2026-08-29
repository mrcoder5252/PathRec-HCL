"""
Person 4 — LLM Layer (intake, narration, explainability)
==========================================================

Uses the Google Gemini API (free tier — no credit card needed).
Get a key at: https://aistudio.google.com/apikey

Owns the three AI prompts that hold the conversational experience together:
  1. intake_extract()   -> Day 1 (priority, blocks everyone else's testing)
  2. narrate_path()      -> Day 2 (needs Person 1's get_path() + Person 3's retrieval)
  3. explain_why_not()   -> Day 3 (needs two get_path() calls, diffed)

Contract with the rest of the team:
  - Person 2 (quiz/filtering) needs the JSON shape from intake_extract().
    CONFIRM the exact key names below match what Person 2's filter reads.
  - Person 5 (frontend) displays narrate_path() and explain_why_not() output.
  - Person 1's get_path(known_skills, goal_skill) -> [skill_ids] is called
    directly from explain_why_not() (imported once that module exists).
  - Person 3's retrieval function is called directly from narrate_path()
    (imported once that module exists).

Only Prompt 1 (intake) is implemented for now — that's the Day 1 blocker.
Prompts 2 and 3 are stubbed with clear TODOs so they slot in on Day 2/3.
"""

import os
from typing import Optional

from google import genai
from google.genai import types

# Free tier: generous daily quota, no card required.
# Check https://ai.google.dev/gemini-api/docs/models for the current
# fastest/cheapest flash model name if this one is deprecated later.
MODEL = "gemini-3.6-flash"

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Lazy singleton so importing this module doesn't require an API key to be set."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


# ---------------------------------------------------------------------------
# Prompt 1 — Intake extraction (Day 1, priority)
# ---------------------------------------------------------------------------

INTAKE_SYSTEM_PROMPT = """You extract structured data from a learner's free-text goal statement.

Given the learner's message, extract:
- goal_skill: the single skill/topic they ultimately want to learn (e.g. "backend development", "machine learning")
- domain: the broader domain the goal falls under (e.g. "software engineering", "data science")
- timeframe: how long they said they have, in their own words (e.g. "3 months"), or null if not mentioned
- claimed_skills: any skills/technologies they explicitly say they already know or have used; empty list if none mentioned

Rules:
- If the message doesn't clearly state a goal, make your best reasonable inference from context rather than leaving goal_skill empty.
- Keep goal_skill and domain short (a few words), not full sentences.
- claimed_skills should be individual skill names, not sentences.
"""

# Gemini's structured-output mode: the API guarantees the response matches
# this schema, so no manual JSON-parsing/fence-stripping is needed (unlike
# providers without native structured output).
INTAKE_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "goal_skill": types.Schema(type=types.Type.STRING),
        "domain": types.Schema(type=types.Type.STRING),
        "timeframe": types.Schema(type=types.Type.STRING, nullable=True),
        "claimed_skills": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING),
        ),
    },
    required=["goal_skill", "domain", "timeframe", "claimed_skills"],
)


def intake_extract(user_text: str) -> dict:
    """
    Take the learner's free-text goal statement and return structured JSON:
    {goal_skill, domain, timeframe, claimed_skills}.

    Raises ValueError if the model output doesn't parse — callers should
    catch this and retry or fall back to a clarifying question rather than
    crash the intake flow.
    """
    client = _get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=user_text,
        config=types.GenerateContentConfig(
            system_instruction=INTAKE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=INTAKE_RESPONSE_SCHEMA,
        ),
    )

    if response.parsed is None:
        raise ValueError(f"Gemini did not return parseable JSON. Raw text: {response.text!r}")

    data = response.parsed
    # response.parsed can be a dict or a pydantic-like object depending on SDK version — normalize to dict.
    if not isinstance(data, dict):
        data = dict(data)

    if not isinstance(data.get("claimed_skills"), list):
        raise ValueError(f"claimed_skills must be a list. Got: {data.get('claimed_skills')!r}")

    return data


# ---------------------------------------------------------------------------
# Prompt 2 — Path narration (Day 2) — STUB
# ---------------------------------------------------------------------------

def narrate_path(skill_gap_path: list, retrieved_courses: dict) -> str:
    """
    TODO (Day 2): Given the ordered list of skill gaps (from Person 1's
    get_path()) and the real candidate courses per skill (from Person 3's
    retrieval function), produce a short roadmap: one sentence of "why" per
    step, using ONLY the course titles actually provided.

    skill_gap_path: e.g. ["skill_id_3", "skill_id_7", "skill_id_9"]
    retrieved_courses: e.g. {"skill_id_3": [{"title": ..., "url": ...}, ...], ...}

    Hard constraint: never invent a course title. Test hard against Person 3's
    real data before the evening integration checkpoint.
    """
    raise NotImplementedError("Day 2 — wire this up once Person 3's retrieval function is ready")


# ---------------------------------------------------------------------------
# Prompt 3 — "Why not X?" explainer (Day 3) — STUB
# ---------------------------------------------------------------------------

def explain_why_not(path_a: list, path_b: list, goal_a: str, goal_b: str) -> str:
    """
    TODO (Day 3): Given two computed paths (two calls to Person 1's
    get_path() with different goal skills), explain in plain language why
    they differ. Diff the two lists and describe the divergence.
    """
    raise NotImplementedError("Day 3 — wire this up once the diffing logic is drafted")


# ---------------------------------------------------------------------------
# Manual test harness for Prompt 1
# ---------------------------------------------------------------------------

TEST_PHRASINGS = [
    "I want to become a backend developer in the next 3 months, I already know Python basics and a bit of SQL.",
    "trying to get into machine learning, no real timeline, know some numpy",
    "I'm a complete beginner and want to learn data science by the end of the year.",
    "web dev pls, i know html css",
    "I'd like to switch into cloud engineering. I currently work with Linux servers and basic networking.",
]


def run_manual_tests():
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY not set — skipping live tests.")
        print("Get a free key at https://aistudio.google.com/apikey")
        print("Then run: export GEMINI_API_KEY=your-key-here")
        return

    for i, phrasing in enumerate(TEST_PHRASINGS, 1):
        print(f"\n--- Test {i} ---")
        print(f"Input: {phrasing}")
        try:
            result = intake_extract(phrasing)
            print(f"Output: {result}")
        except ValueError as e:
            print(f"FAILED: {e}")


if __name__ == "__main__":
    run_manual_tests()
