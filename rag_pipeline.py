"""
RAG / Course Retrieval module — Person 3
Loads a real, hand-curated course dataset and retrieves the best-matching
courses for a given skill gap. Uses direct skill-tag matching first (most
reliable), and falls back to TF-IDF text similarity if a skill has no
directly tagged course.

Why TF-IDF and not an embeddings API right now: it needs zero API keys and
zero internet access, so you can build and test the whole retrieval logic
immediately. Swap in OpenAI/Anthropic/sentence-transformer embeddings later
if you have time — the retrieve_courses() interface won't need to change.

Run this file directly to test it: python rag_pipeline.py
"""

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_courses(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, keep_default_na=False)
    df["skills_taught_list"] = df["skills_taught"].apply(
        lambda s: [x.strip() for x in s.split(";") if x.strip()]
    )
    return df


def build_text_index(courses: pd.DataFrame):
    """Builds a TF-IDF index over course titles + domain, used as a fallback
    similarity search when a skill has no directly tagged course."""
    corpus = (courses["title"] + " " + courses["domain"]).tolist()
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(corpus)
    return vectorizer, matrix


def retrieve_courses(skill_id: str, skill_name: str, courses: pd.DataFrame,
                      vectorizer, matrix, top_k: int = 3) -> list[dict]:
    """
    Returns up to top_k real courses relevant to the given skill.
    1. Direct tag match: any course explicitly tagged with this skill_id.
    2. If fewer than top_k found, fill the rest using TF-IDF similarity
       between the skill's name and course titles.
    Never returns a course that isn't in the dataset — nothing is invented.
    """
    tagged = courses[courses["skills_taught_list"].apply(lambda lst: skill_id in lst)]
    results = tagged.head(top_k).to_dict("records")

    if len(results) < top_k:
        query_vec = vectorizer.transform([skill_name])
        scores = cosine_similarity(query_vec, matrix).flatten()
        courses_scored = courses.copy()
        courses_scored["score"] = scores
        already_have = {r["course_id"] for r in results}
        fallback = (
            courses_scored[~courses_scored["course_id"].isin(already_have)]
            .sort_values("score", ascending=False)
            .head(top_k - len(results))
        )
        results.extend(fallback.to_dict("records"))

    return results


if __name__ == "__main__":
    courses = load_courses("courses_template.csv")
    vectorizer, matrix = build_text_index(courses)

    print(f"Loaded {len(courses)} real courses.\n")

    # Test: retrieve courses for a single skill gap
    print("Test 1 — retrieving courses for skill: rest_apis (REST API Design)")
    results = retrieve_courses("rest_apis", "REST API Design", courses, vectorizer, matrix)
    for r in results:
        print(f"  - {r['title']} ({r['provider']}) -> {r['url']}")

    print()

    # Test 2 — chain it with Person 1's skill graph output to show the full pipeline
    print("Test 2 — full pipeline: gap-path from skill_graph.py -> retrieved courses per step")
    try:
        from skill_graph import build_graph, get_path

        g = build_graph("skills_template.csv")
        path = get_path(g, known_skills=["py_basics", "variables", "loops", "functions", "http_basics"],
                         goal_skill="deployment")

        for skill_id in path:
            skill_name = g.nodes[skill_id]["name"]
            recs = retrieve_courses(skill_id, skill_name, courses, vectorizer, matrix, top_k=1)
            course_title = recs[0]["title"] if recs else "No course found"
            print(f"  {skill_name} -> {course_title}")
    except ImportError:
        print("  (skill_graph.py not found in this run — that's fine, this test needs both files together)")
