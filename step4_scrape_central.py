import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def extract_section(text, keywords, max_chars=2500):
    lower = text.lower()
    for kw in keywords:
        idx = lower.find(kw)
        if idx != -1:
            return text[max(0, idx-100):idx + max_chars].strip()
    return ""

CENTRAL_SCHEMES = [
    {
        "slug": "pm-kisan",
        "name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "url": "https://pmkisan.gov.in/",
        "eligibility_url": "https://pmkisan.gov.in/",
        "benefit_value": 6000,
        "state": "national",
    },
    {
        "slug": "pmfby",
        "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "url": "https://pmfby.gov.in/",
        "benefit_value": None,  # varies by crop
        "state": "national",
    },
    {
        "slug": "pmksy",
        "name": "Pradhan Mantri Krishi Sinchayee Yojana (PMKSY)",
        "url": "https://pmksy.gov.in/",
        "benefit_value": None,
        "state": "national",
    },
    {
        "slug": "pm-kusum",
        "name": "Pradhan Mantri Kisan Urja Suraksha evam Utthan Mahabhiyan (PM-KUSUM)",
        "url": "https://mnre.gov.in/solar/schemes",
        "benefit_value": 150000,
        "state": "national",
    },
    {
        "slug": "soil-health-card",
        "name": "Soil Health Card Scheme",
        "url": "https://soilhealth.dac.gov.in/",
        "benefit_value": 0,  # free service
        "state": "national",
    },
    {
        "slug": "e-nam",
        "name": "National Agriculture Market (e-NAM)",
        "url": "https://www.enam.gov.in/web/",
        "benefit_value": None,
        "state": "national",
    },
    {
        "slug": "rkvy",
        "name": "Rashtriya Krishi Vikas Yojana (RKVY)",
        "url": "https://rkvy.da.gov.in/",
        "benefit_value": None,
        "state": "national",
    },
    {
        "slug": "pkvy",
        "name": "Paramparagat Krishi Vikas Yojana (PKVY)",
        "url": "https://pgsindia-ncof.gov.in/PKVY/Index.aspx",
        "benefit_value": 50000,  # per hectare over 3 years
        "state": "national",
    },
    {
        "slug": "smam",
        "name": "Sub-Mission on Agricultural Mechanization (SMAM)",
        "url": "https://agrimachinery.nic.in/",
        "benefit_value": None,
        "state": "national",
    },
    {
        "slug": "kcc",
        "name": "Kisan Credit Card (KCC)",
        "url": "https://fasalrin.gov.in/",
        "benefit_value": 300000,
        "state": "national",
    },
    {
        "slug": "pm-kisan-maan-dhan",
        "name": "PM Kisan Maandhan Yojana (PM-KMY)",
        "url": "https://pmkmy.gov.in/",
        "benefit_value": 36000,  # Rs 3000/month pension
        "state": "national",
    },
    {
        "slug": "agri-infra-fund",
        "name": "Agriculture Infrastructure Fund (AIF)",
        "url": "https://agriinfra.dac.gov.in/",
        "benefit_value": None,
        "state": "national",
    },
    {
        "slug": "nfsm",
        "name": "National Food Security Mission (NFSM)",
        "url": "https://nfsm.gov.in/",
        "benefit_value": None,
        "state": "national",
    },
    {
        "slug": "national-beekeeping-honey-mission",
        "name": "National Beekeeping and Honey Mission (NBHM)",
        "url": "https://dahd.gov.in/",
        "benefit_value": None,
        "state": "national",
    },
    {
        "slug": "mgnrega",
        "name": "Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGA)",
        "url": "https://nrega.nic.in/",
        "benefit_value": 26400,  # 100 days × ₹264/day avg
        "state": "national",
    },
]

def scrape_portal(scheme: dict) -> dict:
    try:
        print(f"  Fetching {scheme['url']}")
        r = requests.get(scheme["url"], headers=HEADERS, timeout=20, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")

        # Extract all visible text
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        full_text = soup.get_text(separator="\n", strip=True)
        full_text = "\n".join(line for line in full_text.split("\n") if line.strip())

        return {
            **scheme,
            "source": "ministry_portal",
            "full_text": full_text[:6000],
            "eligibility_text": extract_section(full_text,
                ["eligibility", "eligible", "who can", "criteria"]),
            "benefits_text": extract_section(full_text,
                ["benefit", "financial", "assistance", "support", "amount"]),
            "application_process_text": extract_section(full_text,
                ["how to apply", "apply online", "application", "register", "csc"]),
            "documents_text": extract_section(full_text,
                ["documents", "aadhaar", "required", "documents required"]),
        }
    except Exception as e:
        print(f"  Error: {e}")
        return {**scheme, "source": "ministry_portal", "full_text": "", "error": str(e)}

Path("data").mkdir(exist_ok=True)
results = []

for i, scheme in enumerate(CENTRAL_SCHEMES):
    print(f"[{i+1}/{len(CENTRAL_SCHEMES)}] {scheme['name'][:60]}")
    result = scrape_portal(scheme)
    results.append(result)
    text_len = len(result.get("full_text", ""))
    if text_len > 0:
        print(f"  OK — {text_len} chars")
    else:
        print(f"  FAILED — no content")
    time.sleep(2)

with open("data/central_raw.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nCentral: {len(results)} schemes scraped")
print(f"Successfully scraped: {sum(1 for r in results if len(r.get('full_text', '')) > 100)}")
print("Saved to data/central_raw.json")
