"""
Person 4 — LLM Layer (intake, narration, explainability)
==========================================================

FIX APPLIED: intake_extract() previously returned free-text `domain` and
`goal_skill` values (e.g. "software engineering", "backend development").
Person 1's skill graph only recognizes exact values ("backend" as a domain,
and real skill_ids like "deployment", "rest_apis" as goals) — the mismatch
would have silently broken get_allowed_skills_for_domain() and get_path()
for every real user. Fixed by pulling the real domain/skill_id list from
Person 1's API at import time and constraining Gemini's structured output
to those exact values via enum, so an invalid value is no longer possible.

Uses the Google Gemini API (free tier — no credit card needed).
Get a key at: https://aistudio.google.com/apikey
"""

import os
import requests
from typing import Optional

from google import genai
from google.genai import types

MODEL = "gemini-3.6-flash"
PATHREC_API_BASE = os.getenv("PATHREC_API_BASE", "http://127.0.0.1:8000")

_client: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    """Lazy singleton so importing this module doesn't require an API key to be set."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


# ---------------------------------------------------------------------------
# Fetch Person 1's real domain/skill taxonomy — this is what makes the fix work.
# Falls back to a small hardcoded list if their API isn't reachable yet, so
# this module still imports and runs standalone during early development.
# ---------------------------------------------------------------------------

_FALLBACK_DOMAINS = ["backend"]
_FALLBACK_SKILL_IDS = [
    "py_basics", "sql_basics", "rest_apis", "auth",
    "deployment", "system_design_basics",
]


def _fetch_real_domains_and_skills():
    try:
        resp = requests.get(f"{PATHREC_API_BASE}/", timeout=3)
        resp.raise_for_status()
        # "/" doesn't expose the full list directly, so hit a known domain
        # to pull skill_ids, and keep a small known-domains list in sync
        # with skills_template.csv. If Person 1 adds a /domains endpoint
        # later, swap this for that — simpler and always in sync.
        domain_resp = requests.get(f"{PATHREC_API_BASE}/skills/domain/backend", timeout=3)
        domain_resp.raise_for_status()
        data = domain_resp.json()
        return ["backend"], data["skill_ids"]
    except requests.exceptions.RequestException:
        print(f"Could not reach {PATHREC_API_BASE} — using fallback domain/skill list. "
              f"Start Person 1's server (`uvicorn api:app --port 8000`) for the real list.")
        return _FALLBACK_DOMAINS, _FALLBACK_SKILL_IDS


REAL_DOMAINS, REAL_SKILL_IDS = _fetch_real_domains_and_skills()


# ---------------------------------------------------------------------------
# Prompt 1 — Intake extraction (Day 1, priority) — FIXED
# ---------------------------------------------------------------------------

INTAKE_SYSTEM_PROMPT = f"""You extract structured data from a learner's free-text goal statement.

Given the learner's message, extract:
- goal_skill: the closest matching skill_id from this exact list (pick the one
  that best represents their ultimate goal, even if they described it loosely):
  {", ".join(REAL_SKILL_IDS)}
- domain: the domain their goal falls under, from this exact list: {", ".join(REAL_DOMAINS)}
- timeframe: how long they said they have, in their own words (e.g. "3 months"), or null if not mentioned
- claimed_skills: any skills they explicitly say they already know, mapped to the
  closest matching skill_id from the list above. Do not invent skill_ids not on this list.
  Empty list if none mentioned.

Rules:
- You MUST only use values from the lists given above for goal_skill, domain, and claimed_skills.
- If the message doesn't clearly state a goal, make your best reasonable inference rather than leaving goal_skill empty.
- If nothing in the message maps to a real skill_id for claimed_skills, return an empty list — do not guess.
"""

INTAKE_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "goal_skill": types.Schema(type=types.Type.STRING, enum=REAL_SKILL_IDS),
        "domain": types.Schema(type=types.Type.STRING, enum=REAL_DOMAINS),
        "timeframe": types.Schema(type=types.Type.STRING, nullable=True),
        "claimed_skills": types.Schema(
            type=types.Type.ARRAY,
            items=types.Schema(type=types.Type.STRING, enum=REAL_SKILL_IDS),
        ),
    },
    required=["goal_skill", "domain", "timeframe", "claimed_skills"],
)


def intake_extract(user_text: str) -> dict:
    """
    Take the learner's free-text goal statement and return structured JSON:
    {goal_skill, domain, timeframe, claimed_skills} — where goal_skill,
    domain, and every entry in claimed_skills are GUARANTEED to be real
    values from Person 1's skill graph (enforced by the enum schema, not
    just prompt wording), so this output can be passed directly to
    Person 1's get_path() / Person 2's get_allowed_skills_for_domain()
    with no translation step needed.

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
    """
    raise NotImplementedError("Day 2 — wire this up once Person 3's retrieval function is ready")


# ---------------------------------------------------------------------------
# Prompt 3 — "Why not X?" explainer (Day 3) — STUB
# ---------------------------------------------------------------------------

def explain_why_not(path_a: list, path_b: list, goal_a: str, goal_b: str) -> str:
    """
    TODO (Day 3): Given two computed paths, explain in plain language why
    they differ.
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

    print(f"Testing against real domains: {REAL_DOMAINS}")
    print(f"Testing against {len(REAL_SKILL_IDS)} real skill_ids\n")

    for i, phrasing in enumerate(TEST_PHRASINGS, 1):
        print(f"\n--- Test {i} ---")
        print(f"Input: {phrasing}")
        try:
            result = intake_extract(phrasing)
            print(f"Output: {result}")
            # sanity check: confirm the guarantee actually holds
            assert result["goal_skill"] in REAL_SKILL_IDS
            assert result["domain"] in REAL_DOMAINS
            assert all(s in REAL_SKILL_IDS for s in result["claimed_skills"])
            print("  (verified: all values are real skill_ids/domains)")
        except ValueError as e:
            print(f"FAILED: {e}")


if __name__ == "__main__":
    run_manual_tests()
