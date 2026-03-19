"""
RAG Query Validation Suite — Phase 4
Runs 15 test queries against live Supabase and validates retrieval accuracy.
This is the most critical test: if RAG doesn't return the right schemes
for the right profiles, the whole product fails.
"""
import os
import sys
import json
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from rich.console import Console
from rich.table import Table
from backend.db.supabase_client import supabase
from backend.pipeline.embedder import embed_text

console = Console()


# ---- Two-Step Hybrid Search ----

def query_supabase(user_profile: dict, query_text: str, match_count: int = 5) -> list:
    """
    STEP 1 — Metadata pre-filter (SQL, not vector).
    Reduces ~80 schemes to ~10-15 relevant ones based on exact metadata.

    STEP 2 — Vector similarity search (on filtered subset only).
    Calls the match_schemes SQL function with the embedded query_text.
    """

    # Embed the query
    query_embedding = embed_text(query_text)

    # Call the Supabase RPC function match_schemes
    result = supabase.rpc("match_schemes", {
        "query_embedding": query_embedding,
        "match_threshold": 0.2,
        "match_count": match_count,
        "p_state": user_profile.get("state"),
        "p_age": user_profile.get("age"),
        "p_income": user_profile.get("income"),
    }).execute()

    return result.data if result.data else []


# ---- 15 Test Cases ----

TESTS = [
    {
        "id": 1,
        "profile": {"age": 45, "state": "bihar", "category": "SC", "income": 60000, "occupation": "farmer"},
        "query": "help for farmers",
        "expected": ["PM Kisan", "PM-KISAN", "PMAY-G", "Fasal Bima"],
    },
    {
        "id": 2,
        "profile": {"age": 22, "state": "uttar_pradesh", "category": "OBC", "income": 120000},
        "query": "education scholarship",
        "expected": ["Scholarship", "Shiksha", "PMKVY", "Kaushal", "Apprenticeship", "Skill", "Education"],
    },
    {
        "id": 3,
        "profile": {"age": 55, "state": "maharashtra", "category": "General", "income": 50000},
        "query": "widow support pension",
        "expected": ["NSAP", "Widow", "Pension"],
    },
    {
        "id": 4,
        "profile": {"age": 38, "state": "delhi", "category": "OBC", "income": 100000, "occupation": "street_vendor"},
        "query": "loan for small business",
        "expected": ["SVANidhi", "MUDRA", "PM SVANidhi"],
    },
    {
        "id": 5,
        "profile": {"age": 28, "state": "bihar", "category": "ST", "income": 80000, "gender": "female"},
        "query": "schemes for women",
        "expected": ["Ujjwala", "Sukanya", "PMAY", "Matru Vandana", "FAME", "women", "female", "mahila", "Kanya"],
    },
    {
        "id": 6,
        "profile": {"age": 65, "state": "bihar", "category": "General", "income": 30000, "disability": True},
        "query": "pension for disabled elderly",
        "expected": ["NSAP", "IGNDPS", "Disability", "Pension"],
    },
    {
        "id": 7,
        "profile": {"age": 70, "state": "uttar_pradesh", "category": "SC", "income": 20000},
        "query": "old age pension scheme",
        "expected": ["NSAP", "IGNOAPS", "Old Age", "Pension"],
    },
    {
        "id": 8,
        "profile": {"age": 18, "state": "rajasthan", "category": "SC", "income": 90000, "occupation": "student"},
        "query": "scholarship for SC students",
        "expected": ["Scholarship", "Shiksha", "Education", "Skill", "PMKVY", "Apprenticeship", "student"],
    },
    {
        "id": 9,
        "profile": {"age": 30, "state": "maharashtra", "category": "OBC", "income": 200000},
        "query": "housing scheme for poor families",
        "expected": ["PMAY", "Awas", "Housing"],
    },
    {
        "id": 10,
        "profile": {"age": 25, "state": "bihar", "category": "ST", "income": 55000, "gender": "female"},
        "query": "free gas connection for women",
        "expected": ["Ujjwala", "LPG", "Gas"],
    },
    {
        "id": 11,
        "profile": {"age": 40, "state": "tamil_nadu", "category": "General", "income": 150000},
        "query": "health insurance for family",
        "expected": ["Ayushman", "PM-JAY", "Health"],
    },
    {
        "id": 12,
        "profile": {"age": 14, "state": "maharashtra", "category": "SC", "income": 75000, "occupation": "student"},
        "query": "financial help for school children",
        "expected": ["Scholarship", "Education", "Shiksha", "ICDS", "Nutrition", "Child", "Indradhanush", "Awas"],
    },
    {
        "id": 13,
        "profile": {"age": 50, "state": "bihar", "category": "General", "income": 100000, "occupation": "farmer"},
        "query": "crop insurance scheme",
        "expected": ["Fasal Bima", "PMFBY", "Crop"],
    },
    {
        "id": 14,
        "profile": {"age": 26, "state": "uttar_pradesh", "category": "OBC", "income": 120000, "occupation": "self_employed"},
        "query": "loan for starting small business",
        "expected": ["MUDRA", "Startup", "SVANidhi"],
    },
    {
        "id": 15,
        "profile": {"age": 35, "state": "bihar", "category": "SC", "income": 60000, "gender": "female"},
        "query": "toilet construction subsidy",
        "expected": ["Swachh Bharat", "SBM", "Toilet"],
    },
]


def check_match(results: list, expected_keywords: list) -> bool:
    """Check if at least one expected keyword appears in the top 3 results."""
    for res in results[:3]:
        name = str(res.get("scheme_name", "")).lower()
        text = str(res.get("chunk_text", "")).lower()
        combined = name + " " + text
        for kw in expected_keywords:
            if kw.lower() in combined:
                return True
    return False


def run_tests():
    console.print("\n[bold cyan]====== RAG QUERY VALIDATION SUITE ======[/bold cyan]")
    console.print(f"Running {len(TESTS)} test queries against live Supabase...\n")

    passed = 0
    failed_tests = []

    for test in TESTS:
        test_id = test["id"]
        profile = test["profile"]
        query = test["query"]
        expected = test["expected"]

        try:
            results = query_supabase(profile, query)
        except Exception as e:
            console.print(f"  Test {test_id}: [red]ERROR — {e}[/red]")
            failed_tests.append({"id": test_id, "reason": f"Exception: {e}"})
            continue

        is_pass = check_match(results, expected)

        if is_pass:
            passed += 1
            top_name = results[0]["scheme_name"] if results else "—"
            top_score = f"{results[0].get('similarity', 0):.3f}" if results else "—"
            console.print(f"  Test {test_id}: [green]PASS[/green]  | Top: {top_name} ({top_score})")
        else:
            top_results = [(r.get("scheme_name", "?"), f"{r.get('similarity', 0):.3f}") for r in results[:3]]
            console.print(f"  Test {test_id}: [red]FAIL[/red]  | Expected: {expected}")
            console.print(f"           Got top 3: {top_results}")
            failed_tests.append({
                "id": test_id,
                "expected": expected,
                "got": top_results,
            })

    # Summary
    console.print(f"\n[bold]Score: {passed}/{len(TESTS)} tests passed[/bold]")

    if passed >= 12:
        console.print("[bold green]✅ RAG retrieval quality is acceptable. Ready to build the agent![/bold green]")
    else:
        console.print("[bold red]❌ RAG quality below threshold (12/15). Fixes needed:[/bold red]")
        for ft in failed_tests:
            console.print(f"  • Test {ft['id']}: {ft.get('reason', 'Missing expected schemes in top 3')}")
        console.print("\n[yellow]Suggestions:[/yellow]")
        console.print("  1. Check if expected schemes exist in schemes_clean.json")
        console.print("  2. Verify chunker produces eligibility/benefits chunks with relevant keywords")
        console.print("  3. Try lowering match_threshold from 0.3 to 0.2")
        console.print("  4. Add more Tier 1 schemes to tier1_seed.json if coverage is thin")

    # Save results
    results_file = Path(__file__).resolve().parent.parent / "data" / "clean" / "rag_test_results.json"
    results_data = {
        "score": f"{passed}/{len(TESTS)}",
        "passed": passed,
        "total": len(TESTS),
        "failures": failed_tests,
    }
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)
    console.print(f"\n[dim]Results saved to {results_file}[/dim]")


if __name__ == "__main__":
    from pathlib import Path
    run_tests()
