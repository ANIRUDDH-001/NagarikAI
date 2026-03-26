"""
Step 9: Scrape Additional Live Sources for 50+ Schemes
Targets: Bihar, AP, Telangana, MIDH (Horticulture), and other high-potential portals
Purpose: Expand from 30 to 50+ schemes using Tier 1 & 2 sources (no outdated datasets)
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Optional
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
}

# ============================================================================
# HIGH PRIORITY SOURCES (Tier 1 & 2) - These will give you 30-40 new schemes
# ============================================================================

TIER1_SOURCES = [
    # Bihar Agriculture Department - Should have 15-20 schemes
    {
        "slug": "bihar-agriculture",
        "name": "Bihar Agriculture Department",
        "url": "https://agriculture.bihar.gov.in/",
        "state": "bihar",
        "selector": "a[href*='scheme'], .scheme-item, .yojana",  # Common selectors
        "expected_count": 15,
    },
    # Andhra Pradesh - 12-15 schemes
    {
        "slug": "ap-agriculture",
        "name": "Andhra Pradesh Agriculture Department",
        "url": "https://agriculture.ap.gov.in/",
        "state": "andhra_pradesh",
        "selector": ".scheme, a[href*='scheme'], .yojana-list",
        "expected_count": 12,
    },
    # Telangana - 10-15 schemes
    {
        "slug": "telangana-agriculture",
        "name": "Telangana Agriculture Department",
        "url": "https://agriculture.telangana.gov.in/",
        "state": "telangana",
        "selector": ".scheme, .yojana, a[href*='scheme']",
        "expected_count": 12,
    },
    # Horticulture Mission - 8-12 schemes
    {
        "slug": "midh-horticulture",
        "name": "Mission Integrated Development Horticulture (MIDH)",
        "url": "https://midh.gov.in/",
        "state": "national",
        "selector": ".scheme, .program, .mission",
        "expected_count": 10,
    },
    # Fisheries Portal - 5-8 schemes (different category, adds variety)
    {
        "slug": "fisheries-dac",
        "name": "Fisheries Division - DAC",
        "url": "https://fisheries.dac.gov.in/",
        "state": "national",
        "selector": ".scheme, .yojana, a[href*='fisheries']",
        "expected_count": 6,
    },
]

TIER2_SOURCES = [
    # Additional missing states
    {
        "slug": "himachal-agriculture",
        "name": "Himachal Pradesh Agriculture",
        "url": "https://himachalagri.nic.in/",
        "state": "himachal_pradesh",
        "expected_count": 8,
    },
    {
        "slug": "jk-agriculture",
        "name": "Jammu & Kashmir Agriculture",
        "url": "https://www.jkagri.gov.in/",
        "state": "jammu_kashmir",
        "expected_count": 10,
    },
    {
        "slug": "gujarat-agriculture",
        "name": "Gujarat Agriculture Department",
        "url": "https://agriculture.gujarat.gov.in/",
        "state": "gujarat",
        "expected_count": 15,
    },
    {
        "slug": "chhattisgarh-agriculture",
        "name": "Chhattisgarh Agriculture",
        "url": "https://agri.cg.gov.in/",
        "state": "chhattisgarh",
        "expected_count": 12,
    },
    {
        "slug": "westbengal-agriculture",
        "name": "West Bengal Agriculture",
        "url": "https://www.agriwbgov.in/",
        "state": "west_bengal",
        "expected_count": 10,
    },
]

# ============================================================================
# MAIN SCRAPER LOGIC
# ============================================================================

class LiveSchemeScraper:
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.session = None
        self.schemes = []
        self.failed_sources = []

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification for government sites
        self.session = aiohttp.ClientSession(headers=HEADERS, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL with retries"""
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Status {response.status} for {url}")
                    return None
        except asyncio.TimeoutError:
            logger.error(f"Timeout fetching {url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise

    def extract_scheme_names(self, html: str, source_name: str) -> List[str]:
        """Extract scheme names from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        schemes = []

        # Generic extractors - will find most scheme mentions
        patterns = [
            ("h1", None),
            ("h2", None),
            ("h3", None),
            ("a", None),  # All links
            ("p", None),
        ]

        # Look for keywords
        keywords = [
            "yojana", "scheme", "pradhan", "kisan", "krishi", "grant", "subsidy",
            "loan", "benefit", "samman", "कृषि", "योजना", "सहायता"
        ]

        for tag, selector in patterns:
            elements = soup.find_all(tag)
            for elem in elements:
                text = elem.get_text(strip=True)
                if len(text) > 10 and any(kw.lower() in text.lower() for kw in keywords):
                    if text not in schemes and len(schemes) < 30:  # Prevent duplicates
                        schemes.append(text)

        return schemes[:15]  # Return top 15 unique schemes

    async def scrape_source(self, source: Dict) -> Dict:
        """Scrape a single source"""
        logger.info(f"Starting: {source['name']} ({source['url']})")

        try:
            html = await self.fetch_url(source['url'])

            if not html:
                logger.error(f"Failed to fetch {source['name']}")
                self.failed_sources.append(source['name'])
                return {
                    "source": source['name'],
                    "state": source['state'],
                    "schemes": [],
                    "status": "FAILED - Could not fetch",
                    "error": "Network or server error"
                }

            # Extract schemes
            scheme_names = self.extract_scheme_names(html, source['name'])

            if not scheme_names:
                logger.warning(f"No schemes extracted from {source['name']}")
                return {
                    "source": source['name'],
                    "state": source['state'],
                    "schemes": [],
                    "status": "PARTIAL - Extraction failed",
                    "error": "Could not parse HTML structure"
                }

            schemes = [
                {
                    "name": name,
                    "state": source['state'],
                    "source_name": source['name'],
                    "source_url": source['url'],
                    "scraped_at": datetime.now().isoformat(),
                    "scheme_type": "government",
                    "verified": False,
                }
                for name in scheme_names
            ]

            logger.info(f"✓ {source['name']}: Found {len(schemes)} schemes")

            return {
                "source": source['name'],
                "state": source['state'],
                "schemes": schemes,
                "status": "SUCCESS",
                "count": len(schemes),
                "error": None
            }

        except Exception as e:
            logger.error(f"Exception scraping {source['name']}: {str(e)}")
            self.failed_sources.append(source['name'])
            return {
                "source": source['name'],
                "state": source['state'],
                "schemes": [],
                "status": "FAILED",
                "error": str(e)
            }

    async def scrape_all(self, sources: List[Dict], tier: str = "tier1") -> List[Dict]:
        """Scrape multiple sources concurrently"""
        logger.info(f"Starting {tier} scraping with {len(sources)} sources")

        # Scrape with controlled concurrency (max 3 concurrent requests)
        semaphore = asyncio.Semaphore(3)

        async def scrape_with_semaphore(source):
            async with semaphore:
                await asyncio.sleep(1)  # Polite delay between requests
                return await self.scrape_source(source)

        results = await asyncio.gather(
            *[scrape_with_semaphore(source) for source in sources],
            return_exceptions=True
        )

        return results

    def save_results(self, results: List[Dict], filename: str):
        """Save scraping results to JSON"""
        output_file = self.output_dir / filename
        
        all_schemes = []
        summary = {
            "total_sources": len(results),
            "successful": 0,
            "failed": 0,
            "total_schemes": 0,
            "timestamp": datetime.now().isoformat(),
            "results": []
        }

        for result in results:
            if result["status"] == "SUCCESS":
                summary["successful"] += 1
                summary["total_schemes"] += result["count"]
                all_schemes.extend(result["schemes"])

            summary["results"].append({
                "source": result["source"],
                "state": result["state"],
                "status": result["status"],
                "count": len(result["schemes"]),
                "error": result.get("error")
            })

        output_data = {
            "summary": summary,
            "schemes": all_schemes
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to {output_file}")
        return summary

    def print_summary(self, results: List[Dict]):
        """Print human-readable summary"""
        print("\n" + "="*80)
        print("SCRAPING SUMMARY")
        print("="*80)

        total_schemes = 0
        successful = 0
        failed = 0

        for result in results:
            status_icon = "[OK]" if result["status"] == "SUCCESS" else "[FAIL]"
            print(f"{status_icon} {result['source']:<50} | Schemes: {len(result['schemes']):>3} | {result['state']}")
            if result.get("error"):
                print(f"  Error: {result['error']}")

            total_schemes += len(result['schemes'])
            if result["status"] == "SUCCESS":
                successful += 1
            else:
                failed += 1

        print("="*80)
        print(f"Total Sources: {successful + failed} | Successful: {successful} | Failed: {failed}")
        print(f"Total New Schemes Collected: {total_schemes}")
        print("="*80 + "\n")


async def main():
    """Main execution"""
    
    logger.info("Starting Jan Saathi Live Scheme Collection - Round 2")
    logger.info(f"Goal: Expand from 30 to 50+ schemes")
    logger.info(f"Sources: Tier 1 (High Priority) - {len(TIER1_SOURCES)} sources")
    logger.info(f"         Tier 2 (Additional States) - {len(TIER2_SOURCES)} sources")
    logger.info("")

    async with LiveSchemeScraper() as scraper:
        
        # Tier 1: High Priority Sources
        print("\n[TIER 1] HIGH PRIORITY SOURCES (Should yield 50-60 schemes)")
        print("-" * 80)
        tier1_results = await scraper.scrape_all(TIER1_SOURCES, tier="Tier1")
        tier1_summary = scraper.save_results(tier1_results, "tier1_additional_schemes.json")
        scraper.print_summary(tier1_results)

        # Tier 2: Additional State Schemes
        print("\n[TIER 2] ADDITIONAL STATE SCHEMES (Should yield 40-50 schemes)")
        print("-" * 80)
        tier2_results = await scraper.scrape_all(TIER2_SOURCES, tier="Tier2")
        tier2_summary = scraper.save_results(tier2_results, "tier2_additional_schemes.json")
        scraper.print_summary(tier2_results)

        # Combined summary
        print("\n[COMBINED RESULTS]")
        print("="*80)
        tier1_total = tier1_summary['total_schemes']
        tier2_total = tier2_summary['total_schemes']
        grand_total = tier1_total + tier2_total

        print(f"Tier 1 Schemes Collected: {tier1_total}")
        print(f"Tier 2 Schemes Collected: {tier2_total}")
        print(f"\nGrand Total New Schemes: {grand_total}")
        print(f"\nCurrent Database:  30 schemes")
        print(f"After this run:    {30 + grand_total} schemes")
        print(f"Goal Target:       50+ schemes [CHECK]" if (30 + grand_total) >= 50 else f"Goal Target: 50+ schemes (Need {50 - 30 - grand_total} more)")
        print("="*80)

        # Save combined output
        combined_output = scraper.output_dir / "additional_schemes_all.json"
        combined_data = {
            "metadata": {
                "collection_date": datetime.now().isoformat(),
                "phase": "Round 2 - Live Sources",
                "total_sources": len(TIER1_SOURCES) + len(TIER2_SOURCES),
                "total_schemes": grand_total,
                "previous_count": 30,
                "new_total": 30 + grand_total,
            },
            "tier1": tier1_summary,
            "tier2": tier2_summary,
            "next_step": "Run step7_merge_all.py to combine with existing 30 schemes"
        }

        with open(combined_output, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)

        logger.info(f"\n[SUCCESS] Combined results saved to {combined_output}")
        logger.info(f"[NEXT] Run step7_merge_all.py to combine all {30 + grand_total} schemes")


if __name__ == "__main__":
    asyncio.run(main())
