import requests
import pdfplumber
import json
import time
from pathlib import Path
from io import BytesIO

BASE = "https://dbtagriculture.bihar.gov.in/krishimis/Download"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://dbtagriculture.bihar.gov.in/"
}

BIHAR_SCHEME_NAMES = {
    1: "Krishi Yantranikaran (Farm Mechanization)",
    2: "Rashtriya Bagwani Mission (National Horticulture Mission)",
    3: "Mukhyamantri Bagwani Mission",
    4: "Rashtriya Sukshma Sinchai Mission (National Micro Irrigation)",
    5: "Rashtriya Aushadhi Padap Mission (Medicinal Plants)",
    6: "Bagwani Vishesh Karyakram (Special Horticulture Program)",
    7: "Rashtriya Khadya Suraksha Mission (NFSM)",
    8: "Tailhan Evam Makka Samekit Yojana (Oilseed & Maize)",
    9: "Rajkiya Beej Utpadan Karyakram (State Seed Production)",
    10: "Bagicha Bachao Abhiyan (Save Orchard Campaign)",
    11: "Diara Vikas Rajya Yojana (Diara Development)",
    12: "ATMA Yojana (Extension Reforms)",
    13: "Jaivik Khad Protsahan Yojana (Organic Fertilizer Scheme)",
    14: "Tal Vikas Rajya Yojana (Tal Development)",
    15: "Rashtriya Baans Mission (National Bamboo Mission)",
    16: "Antavarti Fasal Yojana (Intercrop Scheme RKVY)",
    17: "Shushk Kshetra Bagwani Karyakram (Dry Area Horticulture)",
    18: "Rashtriya Sabji Vikas Karyakram (National Vegetable Program)",
    19: "Rashtriya Krishi Vikas Yojana (RKVY)",
    20: "Mukhyamantri Teevra Vistar Karyakram",
    21: "Beej Gram Yojana (Seed Village Scheme)",
    22: "Pramanit Beej Vitaran (Certified Seed Distribution)",
    23: "Bihar Rajya Beej Nigam Utpadan (Bihar Seed Corporation)",
}

def extract_section(text, keywords, max_chars=2000):
    lower = text.lower()
    for kw in keywords:
        idx = lower.find(kw.lower())
        if idx != -1:
            return text[idx:idx + max_chars].strip()
    return ""

Path("data/bihar_pdfs").mkdir(parents=True, exist_ok=True)
results = []

for n in range(1, 24):
    url = f"{BASE}/{n}.pdf"
    print(f"[{n}/23] Fetching: {url}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"  HTTP {r.status_code} — skipping")
            continue
        if "application/pdf" not in r.headers.get("Content-Type", ""):
            print(f"  Not a PDF — skipping")
            continue

        # Save PDF locally
        pdf_path = f"data/bihar_pdfs/{n}.pdf"
        with open(pdf_path, "wb") as f:
            f.write(r.content)

        # Extract text
        with pdfplumber.open(BytesIO(r.content)) as pdf:
            full_text = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )

        results.append({
            "slug": f"bihar-scheme-{n}",
            "name": BIHAR_SCHEME_NAMES.get(n, f"Bihar Agriculture Scheme {n}"),
            "state": "bihar",
            "source": "bihar_agriculture_department",
            "pdf_url": url,
            "full_text": full_text[:6000],
            "eligibility_text": extract_section(full_text, ["पात्रता", "eligibility", "eligible"]),
            "benefits_text": extract_section(full_text, ["लाभ", "benefits", "सहायता"]),
            "application_process_text": extract_section(full_text, ["आवेदन", "apply", "registration"]),
            "documents_text": extract_section(full_text, ["दस्तावेज़", "documents"]),
        })
        print(f"  OK — {len(full_text)} chars extracted")

    except Exception as e:
        print(f"  Error: {e}")

    time.sleep(1.5)

Path("data/bihar_raw.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2)
)
print(f"\nBihar: {len(results)}/23 schemes scraped")
print("Saved to data/bihar_raw.json")
