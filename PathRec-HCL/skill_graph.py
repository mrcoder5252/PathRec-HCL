"""
Skill Graph module — Person 1
Loads skills + prerequisites from a CSV, builds a directed graph,
and exposes get_path() to find the missing skills between what a
learner knows and their goal skill.

Run this file directly to test it: python skill_graph.py
"""

import networkx as nx
import pandas as pd


def build_graph(csv_path: str) -> nx.DiGraph:
    """Builds a directed graph from a CSV with columns:
    skill_id, name, domain, prerequisites (semicolon-separated skill_ids, can be empty)
    Edge direction: prerequisite -> skill (you must learn the prerequisite first)
    """
    df = pd.read_csv(csv_path, keep_default_na=False)
    graph = nx.DiGraph()

    # add all nodes first, with their metadata
    for _, row in df.iterrows():
        graph.add_node(row["skill_id"], name=row["name"], domain=row["domain"])

    # add edges (prerequisite -> skill)
    for _, row in df.iterrows():
        prereqs = row["prerequisites"]
        if prereqs:
            for prereq_id in prereqs.split(";"):
                prereq_id = prereq_id.strip()
                if prereq_id:
                    graph.add_edge(prereq_id, row["skill_id"])

    return graph


def get_path(graph: nx.DiGraph, known_skills: list[str], goal_skill: str) -> list[str]:
    """
    Given the skills a learner already knows and their goal skill,
    returns the ORDERED list of missing skill_ids they need to learn,
    in the correct sequence (prerequisites before what depends on them).

    Approach:
    1. Find every ancestor of the goal skill (everything required, directly or
       indirectly) using the graph structure itself.
    2. Remove anything the learner already knows.
    3. Topologically sort what's left, so prerequisites always come first.
    4. Add the goal skill itself at the end.
    """
    if goal_skill not in graph:
        raise ValueError(f"Unknown goal skill: {goal_skill}")

    # everything the goal skill (directly or indirectly) requires
    required = nx.ancestors(graph, goal_skill)
    required.add(goal_skill)

    # drop what they already know
    missing = required - set(known_skills)

    if not missing:
        return []  # they already know everything needed

    # build the subgraph of just the missing skills and topologically sort it
    subgraph = graph.subgraph(missing)
    ordered = list(nx.topological_sort(subgraph))

    return ordered


def get_skills_for_domain(graph: nx.DiGraph, domain: str) -> list[str]:
    """Returns all skill_ids belonging to a domain — Person 2 uses this to
    filter the quiz bank once the learner has selected/stated their domain."""
    return [n for n, data in graph.nodes(data=True) if data["domain"] == domain]


def explain_path(graph: nx.DiGraph, path: list[str]) -> None:
    """Simple helper to print a human-readable path for debugging/demo purposes."""
    for i, skill_id in enumerate(path, 1):
        name = graph.nodes[skill_id]["name"]
        print(f"  {i}. {name} ({skill_id})")


if __name__ == "__main__":
    g = build_graph("skills_template.csv")

    print(f"Graph loaded: {g.number_of_nodes()} skills, {g.number_of_edges()} prerequisite links\n")

    # Test 1: a learner who knows nothing, aiming for REST API design
    print("Test 1 — knows nothing, goal = rest_apis")
    path = get_path(g, known_skills=[], goal_skill="rest_apis")
    explain_path(g, path)

    print()

    # Test 2: a learner who already knows some basics, aiming for deployment
    print("Test 2 — knows py_basics, variables, loops, functions, http_basics — goal = deployment")
    path = get_path(g, known_skills=["py_basics", "variables", "loops", "functions", "http_basics"],
                     goal_skill="deployment")
    explain_path(g, path)

    print()

    # Test 3 — the "why not X" scenario: compare two different goals
    print("Test 3 — same known skills, goal = system_design_basics (for 'why not X' comparison)")
    path_alt = get_path(g, known_skills=["py_basics", "variables", "loops", "functions", "http_basics"],
                         goal_skill="system_design_basics")
    explain_path(g, path_alt)