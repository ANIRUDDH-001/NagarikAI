import os
import sys
import json
import argparse
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

# Add the project root to sys.path so backend.pipeline.groq_extractor works
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.pipeline.groq_extractor import extract_structured_scheme

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn

console = Console()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
CLEAN_DIR = DATA_DIR / "clean"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    raw_file = RAW_DIR / "all_schemes_raw.json"
    tier1_file = RAW_DIR / "tier1_seed.json"
    
    with open(raw_file, "r", encoding="utf-8") as f:
        raw_schemes = json.load(f)
        
    tier1_schemes = []
    if tier1_file.exists():
        with open(tier1_file, "r", encoding="utf-8") as f:
            tier1_schemes = json.load(f)
            
    console.print(f"[bold cyan]Loaded {len(raw_schemes)} schemes for processing[/bold cyan]")
    return raw_schemes, tier1_schemes

def deduplicate_schemes(raw_schemes: List[Dict]) -> List[Dict]:
    initial_count = len(raw_schemes)
    unique_map = {}
    
    for scheme in raw_schemes:
        name = str(scheme.get("scheme_name", scheme.get("title", ""))).strip().lower()
        state = str(scheme.get("state", "national")).strip().lower()
        key = (name, state)
        
        # Count filled keys to determine 'best' record
        filled_count = sum(1 for v in scheme.values() if v)
        
        if key not in unique_map:
            unique_map[key] = (filled_count, scheme)
        else:
            if filled_count > unique_map[key][0]:
                unique_map[key] = (filled_count, scheme)
                
    deduped = [val[1] for val in unique_map.values()]
    console.print(f"[bold yellow]Removed {initial_count - len(deduped)} duplicates, {len(deduped)} unique schemes remain[/bold yellow]")
    return deduped

def prioritize_schemes(schemes: List[Dict], tier1_data: List[Dict]) -> List[Dict]:
    tier1_names = {str(t.get("scheme_name", "")).strip().lower() for t in tier1_data}
    
    tier1_list = []
    national_list = []
    state_list = []
    
    for s in schemes:
        name_clean = str(s.get("scheme_name", "")).strip().lower()
        state_clean = str(s.get("state", "")).strip().lower()
        
        if name_clean in tier1_names:
            tier1_list.append(s)
        elif state_clean == "national" or state_clean == "central":
            national_list.append(s)
        else:
            state_list.append(s)
            
    # Combine in priority order
    prioritized = tier1_list + national_list + state_list
    return prioritized

async def run_extraction(schemes: List[Dict], resume: bool = False, dry_run: bool = False, tier1_only: bool = False):
    checkpoint_file = CLEAN_DIR / "checkpoint.json"
    processed = []
    
    if resume and checkpoint_file.exists():
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            processed = json.load(f)
        console.print(f"[cyan]Resuming from checkpoint: {len(processed)} schemes already processed.[/cyan]")
        
    processed_names = {str(p.get("scheme_name", "")).strip().lower() for p in processed}
    
    # Filter schemes we haven't done
    remaining = [s for s in schemes if str(s.get("scheme_name", "")).strip().lower() not in processed_names]
    
    if tier1_only:
        # User requested 15 tier 1. We'll just take the top 15 of whatever remains from Tier 1.
        remaining = remaining[:15]
        console.print("[yellow]--tier1-only flag enabled. Processing top 15 schemes.[/yellow]")
    elif dry_run:
        remaining = remaining[:5]
        console.print("[yellow]--dry-run flag enabled. Processing only 5 schemes.[/yellow]")
        
    console.print(f"[magenta]Processing {len(remaining)} schemes through Groq API...[/magenta]")
    
    if not remaining:
        return processed

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Extracting data...", total=len(remaining))
        
        for idx, scheme in enumerate(remaining):
            name = scheme.get("scheme_name", "Unknown")
            
            # Update progress parsing text
            progress.update(task, description=f"[cyan]Extracting: {name[:30]}...[/cyan]")
            
            # API Call
            enriched = await extract_structured_scheme(scheme)
            
            # Get Quality Score dynamically for logs
            struct_data = enriched.get("structured_data", {})
            score = struct_data.get("data_quality_score", 0)
            
            progress.console.print(f"  ➜ [dim]{name}[/dim] | Quality: [bold {'green' if score and score >= 70 else 'yellow'}]{score}[/]")
            
            processed.append(enriched)
            progress.advance(task)
            
            # Checkpoint every 20 schemes
            if (idx + 1) % 20 == 0:
                with open(checkpoint_file, "w", encoding="utf-8") as f:
                    json.dump(processed, f, indent=4, ensure_ascii=False)
                    
            # API Rate Limit Delay (30 RPM = 2s delay)
            await asyncio.sleep(2.0)
            
    # Final checkpoint save
    with open(checkpoint_file, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=4, ensure_ascii=False)
        
    return processed

def filter_and_save_quality(processed_schemes: List[Dict]):
    clean = []
    review = []
    rejected = []
    
    for s in processed_schemes:
        struct = s.get("structured_data", {})
        score = struct.get("data_quality_score")
        
        # Fallback if model didn't return an int
        if not isinstance(score, (int, float)):
            try:
                score = int(score)
            except:
                score = 0
                
        if score >= 70:
            clean.append(s)
        elif 40 <= score < 70:
            review.append(s)
        else:
            rejected.append(s)
            
    with open(CLEAN_DIR / "schemes_clean.json", "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=4, ensure_ascii=False)
    with open(CLEAN_DIR / "schemes_review.json", "w", encoding="utf-8") as f:
        json.dump(review, f, indent=4, ensure_ascii=False)
    with open(CLEAN_DIR / "schemes_rejected.json", "w", encoding="utf-8") as f:
        json.dump(rejected, f, indent=4, ensure_ascii=False)
        
    return clean, review, rejected

def generate_report(clean: List, review: List, rejected: List):
    all_processed = clean + review + rejected
    total = len(all_processed)
    
    if total == 0:
        return
        
    avg_score = sum(
        s.get("structured_data", {}).get("data_quality_score", 0) for s in all_processed
    ) / total
    
    # Track RAG coverage
    categories = set()
    occupations = set()
    genders = set()
    issues_list = []
    
    highest = None
    lowest = None
    
    for s in all_processed:
        struct = s.get("structured_data", {})
        
        # Coverage
        for cat in struct.get("category", []): categories.add(str(cat))
        for occ in struct.get("occupation", []): occupations.add(str(occ))
        if struct.get("gender"): genders.add(str(struct.get("gender")))
        
        # Issues
        if struct.get("quality_notes"):
            issues_list.append(struct.get("quality_notes"))
            
        # High Low
        score = struct.get("data_quality_score", 0)
        
        if not highest or score > highest.get("structured_data", {}).get("data_quality_score", 0):
            highest = s
        if not lowest or score < lowest.get("structured_data", {}).get("data_quality_score", 0):
            lowest = s
            
    report = {
        "metrics": {
            "total_processed": total,
            "passed_clean": len(clean),
            "needs_review": len(review),
            "rejected": len(rejected),
            "average_quality_score": round(avg_score, 2)
        },
        "coverage_rag_profiles": {
            "categories_supported": list(categories),
            "occupations_supported": list(occupations),
            "genders_supported": list(genders)
        },
        "extremes": {
            "highest_scorer": highest.get("scheme_name", "N/A") if highest else "N/A",
            "lowest_scorer": lowest.get("scheme_name", "N/A") if lowest else "N/A"
        },
        "common_issues": issues_list[:10] # Just top 10 unique notes for brevity
    }
    
    with open(CLEAN_DIR / "cleaning_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
        
    # Print Rich Summary Table
    console.print("\n[bold green] ====== GROQ PIPELINE SUMMARY ====== [/bold green]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Value")
    
    table.add_row("Total Processed", str(total))
    table.add_row("Cleaned (Score >= 70)", f"[green]{len(clean)}[/green]")
    table.add_row("Review (Score 40-69)", f"[yellow]{len(review)}[/yellow]")
    table.add_row("Rejected (Score < 40)", f"[red]{len(rejected)}[/red]")
    table.add_row("Average Score", f"{round(avg_score, 2)}")
    table.add_row("Highest Scoring Scheme", highest.get("scheme_name", "N/A") if highest else "N/A")
    table.add_row("Lowest Scoring Scheme", lowest.get("scheme_name", "N/A") if lowest else "N/A")
    
    console.print(table)
    console.print(f"[bold cyan]Report saved to: {CLEAN_DIR / 'cleaning_report.json'}[/bold cyan]")

async def main():
    parser = argparse.ArgumentParser(description="Groq Cleaning Orchestrator")
    parser.add_argument("--dry-run", action="store_true", help="Process only 5 schemes for testing")
    parser.add_argument("--tier1-only", action="store_true", help="Process only top 15 Tier 1 schemes")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint.json")
    args = parser.parse_args()

    # 1. LOAD
    raw_schemes, tier1_schemes = load_data()
    
    if not raw_schemes:
        console.print("[red]Aborting: No schemes available found.[/red]")
        sys.exit(1)
        
    # 2. DEDUPLICATE
    unique_schemes = deduplicate_schemes(raw_schemes)
    
    # 3. PRIORITIZE
    ordered_schemes = prioritize_schemes(unique_schemes, tier1_schemes)
    
    # 4. RUN GROQ EXTRACTION
    processed = await run_extraction(
        ordered_schemes, 
        resume=args.resume, 
        dry_run=args.dry_run, 
        tier1_only=args.tier1_only
    )
    
    if not processed:
        console.print("[red]No schemes were processed.[/red]")
        sys.exit(1)
        
    # 5. QUALITY FILTER
    clean, review, rejected = filter_and_save_quality(processed)
    
    # 6 & 7. GENERATE REPORT & SUMMARY
    generate_report(clean, review, rejected)

if __name__ == "__main__":
    asyncio.run(main())
