import asyncio
import json
import argparse
import random
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
    ministry: Optional[str] = None
    state_or_central: Optional[str] = None
    category_tags: List[str] = Field(default_factory=list)
    brief_description: Optional[str] = None
    detail_page_url: str

BASE_URL = "https://www.myscheme.gov.in"
API_URL = "https://www.myscheme.gov.in/api/v1/schemes"
HTML_SEARCH_URL = "https://www.myscheme.gov.in/search"

# Output directory relative to this script or current working directory
# We assume the user runs this from d:/HACK05 or similar
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUTPUT_FILE = DATA_DIR / "schemes_listing.json"

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    reraise=True
)
async def fetch_page(client: httpx.AsyncClient, url: str) -> httpx.Response:
    response = await client.get(url, timeout=15.0)
    response.raise_for_status()
    return response

async def try_fetch_api_schemes(client: httpx.AsyncClient, limit: Optional[int]) -> List[RawScheme]:
    try:
        console.log(f"[blue]Attempting to fetch via API: {API_URL}[/blue]")
        response = await fetch_page(client, API_URL)
        data = response.json()
        
        schemes = []
        items = data.get("data", []) if isinstance(data, dict) else []
        for index, item in enumerate(items):
            if limit and index >= limit:
                break
                
            scheme_id = str(item.get("id") or item.get("slug", f"api_scheme_{index}"))
            scheme = RawScheme(
                scheme_id=scheme_id,
                scheme_name=item.get("title", "Unnamed Scheme"),
                ministry=item.get("ministryName"),
                state_or_central=item.get("nodalDepartmentName", "Central"),
                category_tags=[t.get("name") for t in item.get("tags", [])] if isinstance(item.get("tags"), list) else [],
                brief_description=item.get("description", ""),
                detail_page_url=f"{BASE_URL}/schemes/{scheme_id}"
            )
            schemes.append(scheme)
            
        if schemes:
            return schemes
        else:
            console.log("[yellow]API returned successfully but no schemes found. Falling back to HTML.[/yellow]")
            return []
    except Exception as e:
        console.log(f"[yellow]API fetch failed ({str(e)}). Falling back to HTML scraping.[/yellow]")
        return []

async def fetch_html_schemes(client: httpx.AsyncClient, limit: Optional[int]) -> List[RawScheme]:
    console.log(f"[blue]Fetching via HTML fallback: {HTML_SEARCH_URL}[/blue]")
    schemes = []
    
    try:
        response = await fetch_page(client, HTML_SEARCH_URL)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Try finding Next.js state
        next_data_script = soup.find("script", id="__NEXT_DATA__")
        if next_data_script:
            try:
                data = json.loads(next_data_script.string)
                page_props = data.get("props", {}).get("pageProps", {})
                
                found_schemes = page_props.get("initialSchemes", []) or page_props.get("schemes", [])
                
                if not found_schemes and "apolloState" in page_props:
                    state = page_props["apolloState"]
                    found_schemes = [v for k,v in state.items() if "Scheme" in k]
                
                for index, item in enumerate(found_schemes):
                    if limit and index >= limit:
                        break
                    
                    slug = str(item.get("slug", f"html_scheme_{index}"))
                    scheme = RawScheme(
                        scheme_id=slug,
                        scheme_name=item.get("basicDetails", {}).get("schemeName", item.get("title", "Unnamed Scheme")),
                        ministry=item.get("schemeDetails", {}).get("ministryName", item.get("ministry", "Unknown")),
                        state_or_central=item.get("schemeDetails", {}).get("level", "Central"),
                        category_tags=[tag.get("name", "") for tag in item.get("tags", [])] if isinstance(item.get("tags"), list) else [],
                        brief_description=item.get("basicDetails", {}).get("briefDescription", item.get("description", "")),
                        detail_page_url=f"{BASE_URL}/schemes/{slug}"
                    )
                    schemes.append(scheme)
                    
                if schemes:
                    console.log(f"[green]Successfully parsed {len(schemes)} schemes from static Next.js state.[/green]")
                    return schemes
            except Exception as e:
                console.log(f"[red]Error parsing __NEXT_DATA__: {e}[/red]")
                
        # Structural HTML parsing
        scheme_cards = soup.find_all("div", class_=lambda c: c and "scheme-card" in c.lower())
        
        for index, card in enumerate(scheme_cards):
            if limit and index >= limit:
                break
            title_el = card.find("h2") or card.find("h3") or card.find("a")
            title = title_el.text.strip() if title_el else f"Scheme {index}"
            link_el = card.find("a", href=True)
            href = link_el["href"] if link_el else ""
            slug = href.split("/")[-1] if href else f"scheme_{index}"
            
            desc_el = card.find("p")
            desc = desc_el.text.strip() if desc_el else ""
            
            scheme = RawScheme(
                scheme_id=slug,
                scheme_name=title,
                ministry="Unknown",
                state_or_central="Unknown",
                category_tags=[],
                brief_description=desc,
                detail_page_url=f"{BASE_URL}{href}" if href.startswith("/") else href
            )
            schemes.append(scheme)
            
        if not schemes:
            console.log("[yellow]No schemes found via standard HTML structural parsing. Returning empty list.[/yellow]")
                
        return schemes
        
    except Exception as e:
        console.log(f"[red]HTML scraping fallback also failed: {e}[/red]")
        return []

async def main():
    parser = argparse.ArgumentParser(description="Scrape myScheme list")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of schemes for testing")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9"
    }

    async with httpx.AsyncClient(headers=headers, http2=True) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Fetching schemes listing...", total=1)
            
            schemes = await try_fetch_api_schemes(client, args.limit)
            
            if not schemes:
                await asyncio.sleep(random.uniform(1.0, 2.0))
                schemes = await fetch_html_schemes(client, args.limit)
                
            progress.update(task, completed=1)
            
    if schemes:
        console.log(f"[green]Total {len(schemes)} schemes scraped.[/green]")
        output_data = [scheme.model_dump() for scheme in schemes]
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        console.log(f"[bold green]Successfully saved listing to {OUTPUT_FILE}[/bold green]")
    else:
        console.log("[bold red]Failed to fetch any schemes![/bold red]")

if __name__ == "__main__":
    asyncio.run(main())
