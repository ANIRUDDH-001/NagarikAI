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

# Additional agriculture scheme portals from various states and sources
STATE_SCHEMES = [
    # Rajasthan
    {
        "slug": "raj-kisan-sathi",
        "name": "Rajasthan Kisan Sathi Portal",
        "url": "http://www.agriculture.rajasthan.gov.in/",
        "state": "rajasthan",
    },
    {
        "slug": "raj-mukhyamantri-kisan-kalyan",
        "name": "Rajasthan Mukhyamantri Kisan Kalyan Yojana",
        "url": "https://jansoochna.rajasthan.gov.in/",
        "state": "rajasthan",
    },
    # Uttar Pradesh
    {
        "slug": "up-kisan-registration",
        "name": "UP Kisan Registration & Various Schemes",
        "url": "http://upagriculture.com/",
        "state": "uttar_pradesh",
    },
    {
        "slug": "up-pardarshi-kisan",
        "name": "UP Pardarshi Kisan Seva Yojana",
        "url": "http://upagripardarshi.gov.in/Index-1.aspx",
        "state": "uttar_pradesh",
    },
    # Maharashtra
    {
        "slug": "maha-krishi",
        "name": "Maharashtra Agriculture Department",
        "url": "https://krishi.maharashtra.gov.in/",
        "state": "maharashtra",
    },
    {
        "slug": "maha-pkvy",
        "name": "Maharashtra Paramparagat Krishi Vikas Yojana",
        "url": "https://mahadbt.maharashtra.gov.in/",
        "state": "maharashtra",
    },
    # Madhya Pradesh
    {
        "slug": "mp-kisan-kalyan",
        "name": "MP Mukhyamantri Kisan Kalyan Yojana",
        "url": "https://mpkrishi.mp.gov.in/",
        "state": "madhya_pradesh",
    },
    {
        "slug": "mp-eparivahan",
        "name": "MP e-Krishi Yantra Anudan",
        "url": "https://dbt.mpdage.org/",
        "state": "madhya_pradesh",
    },
    # Karnataka
    {
        "slug": "karnataka-raita-samparka",
        "name": "Karnataka Raita Samparka Kendra",
        "url": "https://raitamitra.karnataka.gov.in/",
        "state": "karnataka",
    },
    {
        "slug": "karnataka-seva-sindhu",
        "name": "Karnataka Seva Sindhu Agriculture Schemes",
        "url": "https://sevasindhu.karnataka.gov.in/",
        "state": "karnataka",
    },
    # Tamil Nadu
    {
        "slug": "tn-agri-welfare",
        "name": "Tamil Nadu Agriculture Farmer Welfare",
        "url": "https://www.tnagrisnet.tn.gov.in/",
        "state": "tamil_nadu",
    },
    {
        "slug": "tn-cm-solar-pump",
        "name": "Tamil Nadu CM Solar Powered Pump",
        "url": "https://www.tnsolarfarmerscheme.tn.gov.in/",
        "state": "tamil_nadu",
    },
    # Telangana
    {
        "slug": "ts-rythu-bandhu",
        "name": "Telangana Rythu Bandhu Scheme",
        "url": "https://www.rythubandhu.telangana.gov.in/",
        "state": "telangana",
    },
    {
        "slug": "ts-rythu-bima",
        "name": "Telangana Rythu Bima Scheme",
        "url": "https://chief.telangana.gov.in/",
        "state": "telangana",
    },
    # West Bengal
    {
        "slug": "wb-krishak-bandhu",
        "name": "West Bengal Krishak Bandhu Scheme",
        "url": "https://krishakbandhu.net/",
        "state": "west_bengal",
    },
    {
        "slug": "wb-bangla-shasya-bima",
        "name": "West Bengal Bangla Shasya Bima",
        "url": "https://www.wbagrimarketingboard.gov.in/",
        "state": "west_bengal",
    },
    # Odisha
    {
        "slug": "odisha-kalia",
        "name": "Odisha KALIA Scheme",
        "url": "https://kalia.co.in/",
        "state": "odisha",
    },
    {
        "slug": "odisha-balaram",
        "name": "Odisha BALARAM Yojana",
        "url": "https://agri.odisha.gov.in/",
        "state": "odisha",
    },
    # Punjab
    {
        "slug": "punjab-samridhi",
        "name": "Punjab Anaaj Kharid Portal",
        "url": "https://anaajkharid.in/",
        "state": "punjab",
    },
    {
        "slug": "punjab-pusa",
        "name": "Punjab Agriculture Department Schemes",
        "url": "http://www.agripb.gov.in/",
        "state": "punjab",
    },
    # Haryana
    {
        "slug": "haryana-meri-fasal",
        "name": "Haryana Meri Fasal Mera Byora",
        "url": "https://fasal.haryana.gov.in/",
        "state": "haryana",
    },
    # Gujarat
    {
        "slug": "gujarat-ikhedut",
        "name": "Gujarat i-Khedut Portal",
        "url": "https://ikhedut.gujarat.gov.in/",
        "state": "gujarat",
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
            "source": "state_agriculture_portal",
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
        return {**scheme, "source": "state_agriculture_portal", "full_text": "", "error": str(e)}

Path("data").mkdir(exist_ok=True)
results = []

for i, scheme in enumerate(STATE_SCHEMES):
    print(f"[{i+1}/{len(STATE_SCHEMES)}] {scheme['name'][:60]}")
    result = scrape_portal(scheme)
    results.append(result)
    text_len = len(result.get("full_text", ""))
    if text_len > 100:
        print(f"  OK — {text_len} chars")
    else:
        print(f"  FAILED — no content")
    time.sleep(2)

with open("data/state_raw.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\nState: {len(results)} schemes scraped")
print(f"Successfully scraped: {sum(1 for r in results if len(r.get('full_text', '')) > 100)}")
print("Saved to data/state_raw.json")
