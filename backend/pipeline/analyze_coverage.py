import os
import json
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

from groq import AsyncGroq
from rich.console import Console
from rich.table import Table

console = Console()
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY", "dummy-key"))

PROFILES = [
    {
        "id": 1, "desc": "Female, 35, Bihar, SC, farmer, income ₹60k, BPL",
        "state": "bihar", "gender": "female", "age": 35, "category": "SC", 
        "occupation": "farmer", "income": 60000, "bpl": True, "disability": False
    },
    {
        "id": 2, "desc": "Male, 22, UP, OBC, student, income ₹1.2L",
        "state": "uttar pradesh", "gender": "male", "age": 22, "category": "OBC", 
        "occupation": "student", "income": 120000, "bpl": False, "disability": False
    },
    {
        "id": 3, "desc": "Widow, 55, Maharashtra, General, no occupation, income ₹40k",
        "state": "maharashtra", "gender": "female", "age": 55, "category": "General", 
        "occupation": "unemployed", "income": 40000, "bpl": False, "disability": False
    },
    {
        "id": 4, "desc": "Male, 45, Tamil Nadu, ST, agricultural labor, income ₹80k",
        "state": "tamil nadu", "gender": "male", "age": 45, "category": "ST", 
        "occupation": "laborer", "income": 80000, "bpl": False, "disability": False
    },
    {
        "id": 5, "desc": "Female, 19, Rajasthan, SC, student, income ₹90k",
        "state": "rajasthan", "gender": "female", "age": 19, "category": "SC", 
        "occupation": "student", "income": 90000, "bpl": False, "disability": False
    },
    {
        "id": 6, "desc": "Male, 60, Bihar, General, retired, income ₹30k, disabled",
        "state": "bihar", "gender": "male", "age": 60, "category": "General", 
        "occupation": "unemployed", "income": 30000, "bpl": False, "disability": True
    },
    {
        "id": 7, "desc": "Female, 28, UP, OBC, self-employed, income ₹1.5L",
        "state": "uttar pradesh", "gender": "female", "age": 28, "category": "OBC", 
        "occupation": "self_employed", "income": 150000, "bpl": False, "disability": False
    },
    {
        "id": 8, "desc": "Male, 14, Maharashtra, SC, student, income ₹75k (family)",
        "state": "maharashtra", "gender": "male", "age": 14, "category": "SC", 
        "occupation": "student", "income": 75000, "bpl": False, "disability": False
    },
    {
        "id": 9, "desc": "Street vendor, Male, 38, Delhi, OBC, income ₹1L",
        "state": "delhi", "gender": "male", "age": 38, "category": "OBC", 
        "occupation": "self_employed", "income": 100000, "bpl": False, "disability": False
    },
    {
        "id": 10, "desc": "Pregnant woman, 25, Bihar, ST, farmer, income ₹55k",
        "state": "bihar", "gender": "female", "age": 25, "category": "ST", 
        "occupation": "farmer", "income": 55000, "bpl": False, "disability": False
    }
]

def format_number(val):
    try:
        if val is None or val == "" or str(val).lower() == "null":
            return None
        return int(val)
    except:
        return None

def check_eligibility(profile: dict, scheme: dict) -> bool:
    """Rigorous mock-RAG metadata alignment test."""
    struct = scheme.get("structured_data", {})
    
    # State check
    sc_state = str(scheme.get("state", struct.get("state", "national"))).strip().lower()
    if sc_state not in ["national", "central", "all"] and sc_state != profile["state"]:
        return False
        
    # Gender check
    gen = str(struct.get("gender", "all")).lower()
    if gen in ["male", "female"] and gen != profile["gender"]:
        return False
        
    # Age check
    age_min = format_number(struct.get("age_min"))
    age_max = format_number(struct.get("age_max"))
    if age_min is not None and profile["age"] < age_min: return False
    if age_max is not None and profile["age"] > age_max: return False
        
    # Income check
    limit = format_number(struct.get("income_limit_annual"))
    if limit is not None and profile["income"] > limit:
        return False
        
    # BPL check
    req_bpl = struct.get("bpl_required")
    if str(req_bpl).lower() in ["true", "1"] and not profile["bpl"]:
        return False
        
    # Disability check
    req_dis = struct.get("disability_required")
    if str(req_dis).lower() in ["true", "1"] and not profile["disability"]:
        return False
        
    return True

async def run_gap_analysis(profile_results: dict, all_schemes: List[Dict]):
    """Uses Groq to analyze underserved demographics from the simulation."""
    console.print("\n[yellow]Requesting Gap Analysis from Groq API...[/yellow]")
    
    # Summarize results into string
    summary_str = ""
    for idx, res in profile_results.items():
        summary_str += f"Profile {idx} ({res['desc']}) matched {res['count']} schemes.\n"
        
    prompt = f"""
    We tested a Government Schemes Rag system database against 10 targeted Indian socio-economic profiles.
    Here are the match results:
    
    {summary_str}
    
    Given these 10 profiles and the available matching schemes, which types of citizens are underserved by our current database?
    Write a concise 2-3 paragraph gap analysis. No markdown, no json formatting. Just text.
    """
    
    try:
        response = await client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": "You are a senior data analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate gap analysis due to API error: {str(e)}"

async def main():
    clean_file = Path("backend/data/clean/schemes_clean.json")
    if not clean_file.exists():
        # Look for fallback rejected schema just for mock simulation
        clean_file = Path("backend/data/clean/schemes_rejected.json")
        if not clean_file.exists():
            console.print("[red]Could not find any parsed schemas in clean directory. Run phase 2 first.[/red]")
            return
            
    with open(clean_file, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    if not schemes:
        console.print("[red]Schema registry is empty![/red]")
        return

    # 1. PROFILE COVERAGE CHECK
    console.print("\n[bold cyan]1. PROFILE COVERAGE CHECK[/bold cyan]")
    profile_results = {}
    
    profiles_with_matches = 0
    for p in PROFILES:
        match_count = 0
        for s in schemes:
            if check_eligibility(p, s):
                match_count += 1
                
        if match_count > 0:
            profiles_with_matches += 1
            
        color = "green" if match_count > 0 else "red"
        console.print(f"Profile {p['id']} matches [{color}]{match_count}[/{color}] schemes.")

    # 2. GAP ANALYSIS
    # Skips execution blindly if key isn't provided
    gap_analysis_text = "Gap analysis skipped (missing API Key)."
    if os.environ.get("GROQ_API_KEY", "dummy-key") != "dummy-key":
        gap_analysis_text = await run_gap_analysis(profile_results, schemes)
        
    console.print("\n[bold cyan]2. GAP ANALYSIS[/bold cyan]")
    console.print(f"[dim]{gap_analysis_text}[/dim]")

    # 3. SCHEME DISTRIBUTION REPORT
    console.print("\n[bold cyan]3. SCHEME DISTRIBUTION REPORT[/bold cyan]")
    
    states = defaultdict(int)
    categories = defaultdict(int)
    ministries = defaultdict(int)
    docs_complete = 0
    docs_incomplete = 0
    
    quality_sum = 0
    
    for s in schemes:
        struct = s.get("structured_data", {})
        
        # State
        st = str(s.get("state", struct.get("state", "national"))).title()
        states[st] += 1
        
        # Category (Beneficiary Target)
        cats = struct.get("category", [])
        if isinstance(cats, list) and cats:
            for c in cats: categories[str(c).title()] += 1
        else:
            categories["General/All"] += 1
            
        # Ministry
        min_name = str(struct.get("ministry", s.get("ministry", "Unknown"))).title()
        ministries[min_name] += 1
        
        # Docs check
        docs = struct.get("documents_needed", [])
        if isinstance(docs, list) and len(docs) > 0 and str(docs[0]).strip() not in ["", "null", "None"]:
            docs_complete += 1
        else:
            docs_incomplete += 1
            
        # Quality Average tracking
        q_score = struct.get("data_quality_score")
        if isinstance(q_score, (int, float)):
            quality_sum += q_score
            
    avg_quality = quality_sum / len(schemes)

    dist_table = Table(show_header=True)
    dist_table.add_column("Metric", style="bold")
    dist_table.add_column("Distribution")
    
    st_str = ", ".join([f"{k}: {v}" for k, v in sorted(states.items(), key=lambda x: x[1], reverse=True)[:5]])
    min_str = ", ".join([f"{k}: {v}" for k, v in sorted(ministries.items(), key=lambda x: x[1], reverse=True)[:3]])
    
    dist_table.add_row("Top States", st_str)
    dist_table.add_row("Top Ministries", min_str)
    dist_table.add_row("Document Data Completeness", f"{docs_complete} Complete / {docs_incomplete} Incomplete")
    console.print(dist_table)

    # 4. DEMO READINESS SCORE
    # Evaluate 3 pillars: Tier 1 coverage, Profile success rate, Data completeness
    
    tier_1_count = len([s for s in schemes if s.get("tier", 0) == 1])
    tier_1_score = min(100, (tier_1_count / 15) * 100) * 0.35  # Worth 35%
    
    profile_score = (profiles_with_matches / len(PROFILES)) * 100 * 0.40  # Worth 40%
    
    data_quality_score = min(100, max(0, avg_quality)) * 0.25  # Worth 25%
    
    final_score = int(tier_1_score + profile_score + data_quality_score)
    
    console.print("\n[bold cyan]4. DEMO READINESS SCORE[/bold cyan]")
    score_color = "green" if final_score >= 80 else "yellow" if final_score >= 50 else "red"
    console.print(f"Overall Hackathon Readiness: [bold {score_color}]{final_score} / 100[/]")
    if final_score >= 80:
        console.print("[green]Conclusion: Yes! This database is profoundly ready for a convincing hackathon demo.[/green]")
    else:
        console.print("[yellow]Conclusion: Needs supplementary seed data or refinement before full demonstration.[/yellow]")
        
    # Save output Report
    report_data = {
        "profile_results": profile_results,
        "gap_analysis": gap_analysis_text,
        "distribution": {
            "states": dict(states),
            "ministries": dict(ministries),
            "categories": dict(categories)
        },
        "demo_readiness_score": final_score
    }
    
    report_file = Path("backend/data/clean/coverage_analysis.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=4)
        
    console.print(f"\n[dim]Analysis saved to: {report_file}[/dim]")

if __name__ == "__main__":
    asyncio.run(main())
