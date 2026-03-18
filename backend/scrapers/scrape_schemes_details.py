import asyncio
import json
import argparse
import random
from pathlib import Path
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn, TimeRemainingColumn
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

console = Console()

class SchemeDetails(BaseModel):
    scheme_id: str
    eligibility_criteria: str
    benefits_description: str
    application_process: str
    documents_required: List[str]
    official_application_url: Optional[str] = None
    tables_data: List[List[List[str]]] = []  # Extracted tables grid

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
INPUT_FILE = DATA_DIR / "schemes_listing.json"
OUTPUT_FILE = DATA_DIR / "schemes_detailed.json"

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

def extract_text_from_section(soup: BeautifulSoup, section_keywords: List[str]) -> str:
    for heading in soup.find_all(['h2', 'h3']):
        if any(keyword.lower() in heading.text.lower() for keyword in section_keywords):
            content = []
            sibling = heading.find_next_sibling()
            while sibling and sibling.name not in ['h2', 'h3']:
                if sibling.text.strip():
                    content.append(sibling.text.strip())
                sibling = sibling.find_next_sibling()
            return "\n\n".join(content)
    return ""

def extract_list_from_section(soup: BeautifulSoup, section_keywords: List[str]) -> List[str]:
    for heading in soup.find_all(['h2', 'h3']):
        if any(keyword.lower() in heading.text.lower() for keyword in section_keywords):
            sibling = heading.find_next_sibling()
            while sibling and sibling.name not in ['h2', 'h3']:
                if sibling.name == 'ul':
                    return [li.text.strip() for li in sibling.find_all('li') if li.text.strip()]
                sibling = sibling.find_next_sibling()
            break
    return []

def extract_tables(soup: BeautifulSoup) -> List[List[List[str]]]:
    extracted_tables = []
    for table_el in soup.find_all("table"):
        table_data = []
        for row in table_el.find_all("tr"):
            row_data = [cell.text.strip() for cell in row.find_all(["th", "td"])]
            if row_data:
                table_data.append(row_data)
        if table_data:
            extracted_tables.append(table_data)
    return extracted_tables

async def scrape_detail(client: httpx.AsyncClient, scheme_id: str, url: str) -> Optional[SchemeDetails]:
    try:
        response = await fetch_page(client, url)
        soup = BeautifulSoup(response.text, "html.parser")
        
        next_data_script = soup.find("script", id="__NEXT_DATA__")
        
        eligibility = ""
        benefits = ""
        application = ""
        documents = []
        official_url = None
        tables = extract_tables(soup)
        
        if next_data_script:
            try:
                data = json.loads(next_data_script.string)
                
                # Different access patterns based on app structure
                scheme_data = data.get("props", {}).get("pageProps", {}).get("scheme", {})
                if not scheme_data and "apolloState" in data.get("props", {}).get("pageProps", {}):
                    state = data["props"]["pageProps"]["apolloState"]
                    for k, v in state.items():
                        if "Scheme" in k and isinstance(v, dict) and str(v.get("slug", "")) == scheme_id:
                            scheme_data = v
                            break

                if scheme_data:
                    def parse_obj(obj):
                        if isinstance(obj, list):
                            return "\n".join([item.get("description", "") for item in obj if isinstance(item, dict)])
                        elif isinstance(obj, str):
                            return obj
                        return ""
                    
                    eligibility = parse_obj(scheme_data.get("eligibilityCriteria"))
                    benefits = parse_obj(scheme_data.get("benefits"))
                    application = parse_obj(scheme_data.get("applicationProcess"))
                    
                    docs_obj = scheme_data.get("documentsRequired", [])
                    if isinstance(docs_obj, list):
                        documents = [item.get("description", "") for item in docs_obj if isinstance(item, dict)]
                        
                    details_obj = scheme_data.get("schemeDetails", {}) or scheme_data.get("basicDetails", {})
                    official_url = details_obj.get("schemeUrl") or details_obj.get("officialUrl")
            except Exception as e:
                console.log(f"[yellow]Failed to parse __NEXT_DATA__ for {scheme_id}: {e}[/yellow]")

        if not eligibility:
            eligibility = extract_text_from_section(soup, ["eligibility", "eligible"])
        if not benefits:
            benefits = extract_text_from_section(soup, ["benefits", "advantage"])
        if not application:
            application = extract_text_from_section(soup, ["application", "how to apply"])
        if not documents:
            documents = extract_list_from_section(soup, ["documents", "required"])
        
        if not official_url:
            for a in soup.find_all('a', href=True):
                if 'apply' in a.text.lower() and 'myscheme' not in a['href']:
                    official_url = a['href']
                    break

        return SchemeDetails(
            scheme_id=scheme_id,
            eligibility_criteria=eligibility or "Not Provided",
            benefits_description=benefits or "Not Provided",
            application_process=application or "Not Provided",
            documents_required=documents or ["Not Provided"],
            official_application_url=official_url or "None",
            tables_data=tables
        )
    except Exception as e:
        console.log(f"[red]Error scraping {scheme_id}: {str(e)}[/red]")
        return None

async def main():
    parser = argparse.ArgumentParser(description="Scrape myScheme details")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of schemes for testing")
    parser.add_argument("--resume", action="store_true", help="Resume from last saved state")
    args = parser.parse_args()

    if not INPUT_FILE.exists():
        console.log(f"[bold red]Listing file {INPUT_FILE} not found. Run scrape_schemes_list.py first![/bold red]")
        return
        
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        schemes_list = json.load(f)
        
    if args.limit:
        schemes_list = schemes_list[:args.limit]
        
    existing_details = []
    processed_ids = set()
    
    if args.resume and OUTPUT_FILE.exists():
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_details = json.load(f)
            processed_ids = {item["scheme_id"] for item in existing_details}
            console.log(f"[blue]Resuming: found {len(processed_ids)} already processed schemes.[/blue]")
        except Exception as e:
            console.log(f"[yellow]Could not load existing file for resume: {e}[/yellow]")
            
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    results = list(existing_details)
    save_counter = 0

    async with httpx.AsyncClient(headers=headers, http2=True) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("[cyan]Scraping scheme details...", total=len(schemes_list))
            progress.update(task, completed=len(processed_ids))
            
            for index, scheme in enumerate(schemes_list):
                scheme_id = scheme["scheme_id"]
                url = scheme["detail_page_url"]
                
                if args.resume and scheme_id in processed_ids:
                    continue
                    
                console.log(f"Scraping {scheme_id}...")
                details = await scrape_detail(client, scheme_id, url)
                
                if details:
                    results.append(details.model_dump())
                    save_counter += 1
                    
                await asyncio.sleep(1.5)
                progress.update(task, advance=1)
                
                # Save progress after every 10 schemes
                if save_counter >= 10:
                    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                        json.dump(results, f, indent=4, ensure_ascii=False)
                    save_counter = 0
                    console.log(f"[green]Checkpoint saved: {len(results)} details.[/green]")
                    
    # Final save
    if save_counter > 0 or len(results) == 0:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
            
    console.log(f"[bold green]Finished scraping. Total detailed schemes saved: {len(results)}[/bold green]")

if __name__ == "__main__":
    asyncio.run(main())
