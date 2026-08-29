# PathRec API — Person 1 + Person 3 combined

Wraps the skill graph (Person 1) and course retrieval (Person 3) as HTTP
endpoints so the frontend (Person 5) and LLM layer (Person 4) can call
them directly instead of importing Python functions locally.

## Setup
```
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

Then open http://localhost:8000/docs — interactive Swagger UI, lets anyone
on the team try every endpoint by hand with no code.

## Endpoints

- `GET /` — health check, shows how many skills/courses loaded
- `GET /skills/domain/{domain}` — list of skill_ids for a domain (Person 2 uses this to filter the quiz)
- `POST /path` — `{known_skills: [...], goal_skill: "..."}` → ordered list of missing skills
- `POST /roadmap` — same input, but returns full milestones with a real course attached to each step (this is the main endpoint the frontend should call)
- `POST /compare` — `{known_skills, goal_a, goal_b}` → both paths + shared/unique skills, powers the "why not X?" feature
- `POST /courses` — `{skill_id, top_k}` → real courses for a single skill

## Example: full roadmap
```
curl -X POST http://localhost:8000/roadmap \
  -H "Content-Type: application/json" \
  -d '{"known_skills": ["py_basics","variables","loops","functions","http_basics"], "goal_skill": "deployment"}'
```

## Notes
- CORS is wide open (`allow_origins=["*"]`) for easy local dev — tighten this to the real frontend URL before the actual demo.
- All data is loaded once at startup from the CSVs, not re-read per request.
