import requests
import pdfplumber
import json
import time
from pathlib import Path
from io import BytesIO
import warnings
warnings.filterwarnings('ignore')

CDN_BASE = "https://cdn.myscheme.in/documents/schemes"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Known agriculture slugs — verified from myScheme URL patterns
AGRICULTURE_SLUGS = [
    # Central flagship
    "pmkisan", "pmfby", "pm-kusum", "smam", "pkvy", "nfsm",
    "pm-kmy", "rkvy-raftaar", "agri-infra-fund", "e-nam",
    "soil-health-card-scheme", "national-bamboo-mission",
    "national-beekeeping-honey-mission", "nmsa", "pmksy",
    # State — Bihar
    "bihar-rajya-fasal-sahayata-yojana", "brfsy",
    "dbt-agriculture-bihar", "mukhyamantri-horticulture-mission-bihar",
    # State — Rajasthan
    "rajasthan-cm-kisan-samman-nidhi", "rajasthan-fasal-bima",
    "rajasthan-solar-pump-scheme",
    # State — UP
    "up-kisan-karj-rahat", "up-agriculture-department-scheme",
    "mukhyamantri-krishak-sathi-yojana",
    # State — Maharashtra
    "dr-babasaheb-ambedkar-krishi-swavalamban-yojana",
    "nanaji-deshmukh-krishi-sanjivani-yojana",
    # State — MP
    "mp-kisan-anudan-yojana", "mukhyamantri-kisan-kalyan-yojana",
    # Animal husbandry / allied
    "national-livestock-mission", "rashtriya-gokul-mission",
    "blue-revolution", "pradhan-mantri-matsya-sampada",
]

def _section(text, keywords, max_chars=2500):
    lower = text.lower()
    for kw in keywords:
        idx = lower.find(kw.lower())
        if idx != -1:
            return text[idx:idx+max_chars].strip()
    return ""

Path("data/cdn_pdfs").mkdir(parents=True, exist_ok=True)
results = []
failed = []

for i, slug in enumerate(AGRICULTURE_SLUGS):
    url = f"{CDN_BASE}/{slug}.pdf"
    print(f"[{i+1}/{len(AGRICULTURE_SLUGS)}] {slug}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        if r.status_code == 200 and "pdf" in r.headers.get("Content-Type", "").lower():
            # Save PDF
            pdf_path = f"data/cdn_pdfs/{slug}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(r.content)

            # Extract text
            with pdfplumber.open(BytesIO(r.content)) as pdf:
                text = "\n".join(p.extract_text() or "" for p in pdf.pages)

            results.append({
                "slug": slug,
                "source": "myscheme_cdn_pdf",
                "pdf_url": url,
                "pdf_path": pdf_path,
                "full_text": text[:6000],
                "eligibility_text": _section(text, ["eligibility","पात्रता","eligible"]),
                "benefits_text": _section(text, ["benefits","लाभ","benefit"]),
                "application_process_text": _section(text, ["apply","आवेदन","how to"]),
                "documents_text": _section(text, ["documents","दस्तावेज़"]),
            })
            print(f"  OK — {len(text)} chars, {r.headers.get('Content-Length', '?')} bytes")
        else:
            failed.append(slug)
            print(f"  HTTP {r.status_code} — not found")
    except Exception as e:
        failed.append(slug)
        print(f"  Error: {str(e)[:50]}")

    time.sleep(0.8)

with open("data/cdn_raw.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

with open("data/cdn_failed_slugs.json", "w", encoding="utf-8") as f:
    json.dump(failed, f, ensure_ascii=False, indent=2)

print(f"\nCDN PDF: {len(results)} found, {len(failed)} not found")
print(f"Saved to data/cdn_raw.json")
