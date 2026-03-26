import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

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

# Additional specific well-known agriculture schemes
ADDITIONAL_SCHEMES = [
    # Animal Husbandry
    {
        "slug": "national-dairy-development",
        "name": "National Dairy Development Program",
        "url": "https://www.nddb.coop/",
        "state": "national",
    },
    {
        "slug": "rashtriya-gokul-mission",
        "name": "Rashtriya Gokul Mission",
        "url": "https://dahd.nic.in/related-links/rashtriya-gokul-mission",
        "state": "national",
    },
    {
        "slug": "national-livestock-mission",
        "name": "National Livestock Mission",
        "url": "https://dahd.nic.in/related-links/national-livestock-mission",
        "state": "national",
    },
    # Fisheries
    {
        "slug": "pradhan-mantri-matsya-sampada",
        "name": "Pradhan Mantri Matsya Sampada Yojana (PMMSY)",
        "url": "https://dof.gov.in/pmmsy",
        "state": "national",
    },
    {
        "slug": "blue-revolution",
        "name": "Blue Revolution (Integrated Development of Fisheries)",
        "url": "https://dof.gov.in/blue-revolution",
        "state": "national",
    },
    # Horticulture
    {
        "slug": "mission-for-integrated-development-horticulture",
        "name": "Mission for Integrated Development of Horticulture (MIDH)",
        "url": "https://midh.gov.in/",
        "state": "national",
    },
    # Bamboo & Forest
    {
        "slug": "national-bamboo-mission",
        "name": "National Bamboo Mission",
        "url": "https://nbm.nic.in/",
        "state": "national",
    },
    # Additional PM Schemes
    {
        "slug": "pm-fme",
        "name": "PM Formalisation of Micro food processing Enterprises (PM FME)",
        "url": "https://pmfme.mofpi.gov.in/",
        "state": "national",
    },
    {
        "slug": "pm-aasha",
        "name": "Pradhan Mantri Annadata Aay Sanrakshan Abhiyan (PM-AASHA)",
        "url": "https://agricoop.nic.in/en/divisiontype/pm-aasha",
        "state": "national",
    },
    # State Schemes - More URLs
    {
        "slug": "telangana-rythu-bandhu",
        "name": "Telangana Rythu Bandhu Investment Support Scheme",
        "url": "https://agricoop.nic.in/en/Minor1",
        "state": "telangana",
    },
    {
        "slug": "odisha-kalia",
        "name": "Odisha Krushak Assistance for Livelihood and Income Augmentation (KALIA)",
        "url": "https://kalia.odisha.gov.in/",
        "state": "odisha",
    },
    {
        "slug": "andhra-ysrfs",
        "name": "Andhra Pradesh YSR Free Crop Insurance Scheme",
        "url": "https://ysrfreecropyojana.ap.gov.in/",
        "state": "andhra_pradesh",
    },
    {
        "slug": "andhra-rytu-bharosa",
        "name": "Andhra Pradesh YSR Rytu Bharosa",
        "url": "https://www.apagrisnet.gov.in/",
        "state": "andhra_pradesh",
    },
    {
        "slug": "kerala-homestead-farming",
        "name": "Kerala Homestead Farming",
        "url": "https://keralaagriculture.gov.in/",
        "state": "kerala",
    },
    {
        "slug": "chhattisgarh-rajiv-gandhi",
        "name": "Chhattisgarh Rajiv Gandhi Kisan Nyay Yojana",
        "url": "https://rgkny.cg.nic.in/",
        "state": "chhattisgarh",
    },
    {
        "slug": "jharkhand-birsa-krishi",
        "name": "Jharkhand Birsa Harit Gram Yojana",
        "url": "https://jharkhand.gov.in/agriculture",
        "state": "jharkhand",
    },
    {
        "slug": "assam-mukhyamantri-krishi-sa-ayog",
        "name": "Assam Mukhyamantri Krishi Sa-Ayog Yojana",
        "url": "https://agri-horti.assam.gov.in/",
        "state": "assam",
    },
    {
        "slug": "himachal-prakritik-kheti",
        "name": "Himachal Pradesh Prakritik Kheti Khushal Kisan Yojana",
        "url": "https://www.hpagriculture.com/",
        "state": "himachal_pradesh",
    },
    {
        "slug": "uttarakhand-mukhyamantri-krishi-vikas",
        "name": "Uttarakhand Mukhyamantri Krishi Utthan Yojana",
        "url": "https://agriculture.uk.gov.in/",
        "state": "uttarakhand",
    },
    {
        "slug": "goa-sanjivani-agro",
        "name": "Goa Sanjivani Agro Products Production Scheme",
        "url": "https://www.goa.gov.in/department/agriculture/",
        "state": "goa",
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
            "source": "additional_scheme_portal",
            "full_text": full_text[:6000],
            "eligibility_text": extract_section(full_text,
                ["eligibility", "eligible", "who can", "criteria", "पात्रता", "योग्यता"]),
            "benefits_text": extract_section(full_text,
                ["benefit", "financial", "assistance", "support", "amount", "लाभ", "सहायता"]),
            "application_process_text": extract_section(full_text,
                ["how to apply", "apply online", "application", "register", "csc", "आवेदन"]),
            "documents_text": extract_section(full_text,
                ["documents", "aadhaar", "required", "documents required", "दस्तावेज़"]),
        }
    except Exception as e:
        print(f"  Error: {str(e)[:60]}")
        return {**scheme, "source": "additional_scheme_portal", "full_text": "", "error": str(e)}

Path("data").mkdir(exist_ok=True)
results = []

for i, scheme in enumerate(ADDITIONAL_SCHEMES):
    print(f"[{i+1}/{len(ADDITIONAL_SCHEMES)}] {scheme['name'][:60]}")
    result = scrape_portal(scheme)
    results.append(result)
    text_len = len(result.get("full_text", ""))
    if text_len > 100:
        print(f"  OK — {text_len} chars")
    else:
        print(f"  FAILED — no content")
    time.sleep(2)

with open("data/additional_raw.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nAdditional: {len(results)} schemes scraped")
print(f"Successfully scraped: {sum(1 for r in results if len(r.get('full_text', '')) > 100)}")
print("Saved to data/additional_raw.json")
