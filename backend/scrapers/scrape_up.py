import asyncio
import json
import argparse
from pathlib import Path
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

console = Console()

class RawScheme(BaseModel):
    scheme_id: str
    scheme_name: str
    state: str
    eligibility_criteria: str = "TBD"
    benefits_description: str = "TBD"
    documents_required: str = "TBD"
    official_application_url: str = "TBD"

STATE_NAME = "uttar_pradesh"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUTPUT_FILE = DATA_DIR / f"state_{STATE_NAME}.json"
TEMPLATE_FILE = DATA_DIR / f"MANUAL_COLLECTION_TEMPLATE_{STATE_NAME}.json"

URLS = [
    "https://sspy-up.gov.in",
    "https://mksy.up.gov.in"
]

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=5),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True
)
async def fetch_page(client: httpx.AsyncClient, url: str) -> httpx.Response:
    response = await client.get(url, timeout=15.0)
    response.raise_for_status()
    return response

async def scrape_site(client: httpx.AsyncClient, url: str) -> List[RawScheme]:
    schemes = []
    try:
        response = await fetch_page(client, url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Simulated extraction for structural logic
        main_links = soup.find_all("a", href=True)
        for i, link in enumerate(main_links[:3]):  # Just extracting top few as examples
            text = link.text.strip()
            if len(text) > 5 and 'login' not in text.lower():
                schemes.append(RawScheme(
                    scheme_id=f"{STATE_NAME}_{i}",
                    scheme_name=text,
                    state=STATE_NAME,
                    official_application_url=url + link['href'] if link['href'].startswith('/') else link['href']
                ))
    except Exception as e:
        console.log(f"[yellow]Bot blocked or error on {url}: {e}[/yellow]")
        raise e
        
    return schemes

def generate_manual_template():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    template = [
        RawScheme(
            scheme_id=f"{STATE_NAME}_manual_1",
            scheme_name=f"Example {STATE_NAME.capitalize()} Welfare Scheme Base",
            state=STATE_NAME,
            eligibility_criteria="Enter eligibility here: Requires detailed text > 30 chars for validation.",
            benefits_description="Enter benefits here: Requires detailed text > 50 chars for validation.",
            documents_required="Provide document 1, Document 2.",
            official_application_url="http://example.in/apply"
        ).model_dump()
    ]
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(template, f, indent=4)
    console.log(f"[bold yellow]Generated manual collection template at {TEMPLATE_FILE}[/bold yellow]")

async def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    all_schemes = []
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    client_blocked = False
    async with httpx.AsyncClient(headers=headers, verify=False) as client:
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task(f"[cyan]Scraping {STATE_NAME} portals...", total=len(URLS))
            for url in URLS:
                try:
                    schemes = await scrape_site(client, url)
                    all_schemes.extend(schemes)
                except Exception:
                    client_blocked = True
                await asyncio.sleep(1.5)
                progress.update(task, advance=1)

    if client_blocked and not all_schemes:
        console.log("[red]All targets blocked. Generating manual template...[/red]")
        generate_manual_template()
    else:
        if client_blocked:
            console.log("[yellow]Some targets blocked. Generating manual template for remainder...[/yellow]")
            generate_manual_template()
            
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump([s.model_dump() for s in all_schemes], f, indent=4, ensure_ascii=False)
        console.log(f"[bold green]Successfully saved {len(all_schemes)} schemes to {OUTPUT_FILE}[/bold green]")

if __name__ == "__main__":
    asyncio.run(main())
