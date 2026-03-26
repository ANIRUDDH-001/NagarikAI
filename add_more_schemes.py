"""
Add 5 more schemes to reach 50+ total
"""

import json
from pathlib import Path

# Additional 5 schemes to reach 50+
ADDITIONAL_SCHEMES = [
    {
        "slug": "national-livestock-mission",
        "name": "National Livestock Mission",
        "url": "https://dahd.nic.in/",
        "state": "national",
        "source": "ministry_portal",
        "benefit_value": None,
        "full_text": "National Livestock Mission aims at sustainable development of livestock sector focusing on improving availability of quality feed and fodder, risk coverage, effective extension, and improved flow of credit. Provides assistance for breed improvement, feed and fodder development, innovation and extension. Eligibility: Farmers, cooperatives, private entrepreneurs involved in livestock rearing. Benefits: Financial assistance for infrastructure, breed improvement, insurance. Application through state animal husbandry departments.",
        "eligibility_text": "Individual farmers, dairy cooperatives, private entrepreneurs engaged in livestock rearing and dairy farming.",
        "benefits_text": "Financial assistance for ration balancing, silage making, fodder development, insurance schemes for livestock.",
        "application_process_text": "Apply through district animal husbandry office or state livestock development board.",
        "documents_text": "Identity proof, cattle ownership documents (if applicable), Bank details"
    },
    {
        "slug": "blue-revolution",
        "name": "Blue Revolution (Integrated Development of Fisheries)",
        "url": "https://dof.gov.in/",
        "state": "national",
        "source": "ministry_portal",
        "benefit_value": None,
        "full_text": "Blue Revolution aims to achieve economic prosperity of fishers and fish farmers as well as contribute towards food and nutritional security through sustainable utilization of fisheries resources. Focus on increasing production and productivity. Eligibility: Fishers, fish farmers, aquaculture entrepreneurs. Benefits: Infrastructure development, technology adoption, market support. Application through state fisheries departments.",
        "eligibility_text": "Individual fishers, fish farmers, self-help groups, cooperatives engaged in fisheries and aquaculture.",
        "benefits_text": "Assistance for pond construction, cage culture, feed mills, ice plants, cold storage, marketing infrastructure.",
        "application_process_text": "Submit application to district fisheries development officer or state fisheries department.",
        "documents_text": "Identity proof, Land/water body ownership documents, Project proposal, Bank account"
    },
    {
        "slug": "national-dairy-development",
        "name": "National Dairy Plan (NDP)",
        "url": "https://www.nddb.coop/",
        "state": "national",
        "source": "ministry_portal",
        "benefit_value": None,
        "full_text": "National Dairy Plan aims to increase milk production through breed improvement, strengthening and creation of infrastructure for procurement, processing and marketing of milk. Focus on increasing productivity of milch animals. Eligibility: Dairy cooperatives, milk producer companies, dairy farmers. Benefits: Support for breed improvement, cattle feed plants, chilling centers, milk processing infrastructure. Through National Dairy Development Board and state dairy federations.",
        "eligibility_text": "Dairy cooperative societies, milk unions, milk producer companies, individual dairy farmers.",
        "benefits_text": "Financial assistance for AI services, breed improvement, cattle nutrition, milk procurement and processing infrastructure.",
        "application_process_text": "Apply through state milk federation or district dairy development board.",
        "documents_text": "Registration certificate, Project details, Financial statements, Bank account"
    },
    {
        "slug": "nmsa",
        "name": "National Mission for Sustainable Agriculture (NMSA)",
        "url": "https://nmsa.dac.gov.in/",
        "state": "national",
        "source": "ministry_portal",
        "benefit_value": None,
        "full_text": "NMSA aims to enhance agricultural productivity through climate resilient practices. Focus on soil health management, water-use efficiency, rainfed area development, climate change adaptation. Eligibility: All farmers, emphasis on rainfed areas. Benefits: Support for sustainable farming practices, soil testing, integrated nutrient management, water conservation. Through state agriculture departments.",
        "eligibility_text": "All farmers, especially in rainfed and climate vulnerable areas, through state implementation.",
        "benefits_text": "Financial assistance for dryland farming, watershed development, soil conservation, climate resilient technologies.",
        "application_process_text": "Implemented through state agriculture departments under various sub-missions and components.",
        "documents_text": "Varies by component, generally land records and identity proof"
    },
    {
        "slug": "nrlm",
        "name": "National Rural Livelihoods Mission (NRLM) - Aajeevika",
        "url": "https://nrlm.gov.in/",
        "state": "national",
        "source": "ministry_portal",
        "benefit_value": None,
        "full_text": "NRLM aims to reduce poverty by enabling rural poor households to access gainful self-employment and skilled wage employment. Promotes self-help groups, microfinance, and livelihood opportunities including agriculture and allied activities. Eligibility: Rural poor households, women SHGs. Benefits: Credit linkage, capacity building, market access, livelihood support. Through state rural livelihood missions.",
        "eligibility_text": "Rural poor households, particularly women, organized into self-help groups and federations.",
        "benefits_text": "Revolving fund, community investment fund, credit linkage up to Rs 10 lakh, training, livelihood support.",
        "application_process_text": "Form or join self-help groups through gram panchayat or block office, register with state rural livelihood mission.",
        "documents_text": "Identity proof, SHG membership records, Bank account (group account)"
    }
]

# Load existing additional_raw.json and add new schemes
additional_file = Path("data/additional_raw.json")
existing_data = []
if additional_file.exists():
    with open(additional_file, "r", encoding="utf-8") as f:
        existing_data = json.load(f)

# Add new schemes
existing_data.extend(ADDITIONAL_SCHEMES)

# Save updated file
with open(additional_file, "w", encoding="utf-8") as f:
    json.dump(existing_data, f, ensure_ascii=False, indent=2)

print("="*70)
print("ADDED 5 MORE SCHEMES")
print("="*70)
print(f"New schemes added: {len(ADDITIONAL_SCHEMES)}")
print(f"Updated data/additional_raw.json")
print("\nNext: Re-run step7_merge_all.py to reach 51 total schemes!")
print("="*70)
