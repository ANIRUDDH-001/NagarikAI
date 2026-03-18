import os
import json
import asyncio
from typing import Dict, Any
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from groq import AsyncGroq
from tenacity import retry, wait_exponential, stop_after_attempt
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

console = Console()

# Configuration
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 2.0  # seconds

# Initialize async client safely
client = AsyncGroq(api_key=os.environ.get("GROQ_API_KEY", "dummy-key"))

SYSTEM_PROMPT = """You are a government data analyst specializing in Indian welfare schemes.
Your job is to extract structured eligibility data from raw scheme text.
Always respond with valid JSON only. No explanation. No markdown. No extra text.
If a value cannot be determined from the text, use null.
Income values must be annual amounts in Indian Rupees as integers.
Age values must be integers."""

USER_PROMPT_TEMPLATE = """Extract structured data from this government scheme:

SCHEME NAME: {scheme_name}
RAW DESCRIPTION: {description}
RAW ELIGIBILITY TEXT: {eligibility_text}
RAW BENEFITS TEXT: {benefits_text}
DOCUMENTS TEXT: {documents_text}

Return ONLY this JSON:
{{
  "scheme_name_clean": "cleaned official name",
  "ministry": "exact ministry name",
  "category": ["SC", "ST", "OBC", "General", "EWS", "All"],
  "gender": "all|male|female",
  "age_min": integer or null,
  "age_max": integer or null,
  "income_limit_annual": integer in rupees or null,
  "occupation": ["farmer", "student", "laborer", "self_employed", "unemployed", "any"],
  "bpl_required": true/false,
  "disability_required": true/false,
  "marital_status": "any|married|widow|single|divorced",
  "documents_needed": ["clean document name 1", "clean document name 2"],
  "benefits_summary": "one clear sentence describing what the citizen gets",
  "eligibility_summary": "one clear sentence describing who qualifies",
  "application_steps": ["step 1", "step 2", "step 3"],
  "data_quality_score": 0-100,
  "quality_notes": "any issues or uncertainties found"
}}"""

@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def call_groq_api(messages: list) -> str:
    """Executes the API call using tenacity for retries."""
    response = await client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

async def extract_structured_scheme(raw_scheme: dict) -> dict:
    """Core function: Packages scheme data, calls Groq, formats JSON, and merges fields."""
    user_prompt = USER_PROMPT_TEMPLATE.format(
        scheme_name=raw_scheme.get("scheme_name", ""),
        description=raw_scheme.get("description", ""),
        eligibility_text=raw_scheme.get("eligibility_text", ""),
        benefits_text=raw_scheme.get("benefits_text", ""),
        documents_text=raw_scheme.get("documents_needed", "")
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        raw_json_str = await call_groq_api(messages)
    except Exception as e:
        console.print(f"[red]Error calling Groq API for {raw_scheme.get('scheme_name')}: {e}[/red]")
        raw_json_str = "{}"
        
    extracted_data = {}
    try:
        clean_str = raw_json_str.strip()
        # Fallback strip for unwanted markdown ticks
        if clean_str.startswith("```json"):
            clean_str = clean_str[7:]
        elif clean_str.startswith("```"):
            clean_str = clean_str[3:]
        if clean_str.endswith("```"):
            clean_str = clean_str[:-3]
            
        extracted_data = json.loads(clean_str.strip())
    except json.JSONDecodeError:
        console.print(f"[yellow]Failed to parse JSON response for scheme '{raw_scheme.get('scheme_name')}'.[/yellow]")
        console.print(f"Raw Output: {raw_json_str}")
        extracted_data = {}
        
    # Merge extracted fields back with original raw data
    enriched_scheme = raw_scheme.copy()
    enriched_scheme["structured_data"] = extracted_data
    
    return enriched_scheme


def quality_score_explainer(score: int) -> str:
    """Returns a human-readable explanation of what a data_quality_score range means."""
    if score is None:
        return "Unscored: Data quality could not be determined."
    if score >= 90:
        return "Excellent (90-100): High confidence in all extracted fields. The source text was detailed, unambiguous, and structurally complete."
    elif score >= 75:
        return "Good (75-89): Reliable extraction, but minor details like exact income limits or certain document specifics might be implicit or generalized."
    elif score >= 50:
        return "Fair (50-74): Significant gaps in available information. Missing core details like age boundaries or exact eligibility definitions."
    else:
        return "Poor (0-49): Extremely sparse or malformed scheme data. Heavily lacking distinct requirements or comprehensible benefits text."


async def process_all_schemes():
    input_file = Path("backend/data/raw/all_schemes_raw.json")
    output_dir = Path("backend/data/clean")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "schemes_clean.json"
    
    if not input_file.exists():
        console.print(f"[bold red]Input file not found at {input_file}. Run Phase 1 first.[/bold red]")
        return
        
    with open(input_file, "r", encoding="utf-8") as f:
        raw_schemes = json.load(f)
        
    console.print(f"[bold cyan]Starting Groq extraction for {len(raw_schemes)} schemes...[/bold cyan]")
    enriched_schemes = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Extracting data API calls...", total=len(raw_schemes))
        
        for scheme in raw_schemes:
            enriched = await extract_structured_scheme(scheme)
            enriched_schemes.append(enriched)
            
            # Save progressively in case of mid-run interruption
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(enriched_schemes, f, indent=4, ensure_ascii=False)
                
            progress.advance(task)
            
            # Enforce Groq free tier rate limits (30 RPM = strictly 2 second delay)
            await asyncio.sleep(RATE_LIMIT_DELAY)
            
    console.print(f"[bold green]Successfully extracted and saved {len(enriched_schemes)} schemes to {output_file}[/bold green]")

if __name__ == "__main__":
    if not os.environ.get("GROQ_API_KEY"):
        console.print("[yellow]WARNING: GROQ_API_KEY environment variable is not set. The script will likely fail during API calls.[/yellow]")
    
    asyncio.run(process_all_schemes())
