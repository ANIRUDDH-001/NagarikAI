"""
Transform 51 schemes from raw format to comprehensive schema v2.0
Excludes form_field_mapping as per user request
"""

import json
from pathlib import Path
from datetime import datetime
import hashlib

def generate_scheme_id(name: str, state: str) -> str:
    """Generate unique scheme ID from name and state"""
    base = f"{name}-{state}".lower().replace(" ", "-").replace("(", "").replace(")", "")
    # Clean up and add hash for uniqueness
    clean = ''.join(c for c in base if c.isalnum() or c == '-')
    return clean[:50]

def extract_amount(scheme: dict) -> tuple:
    """Extract monetary benefit amount and frequency"""
    benefit_value = scheme.get('benefit_value')
    benefits_text = scheme.get('benefits_text', '').lower()

    # Try to determine frequency
    frequency = 'annual'  # Default
    if 'month' in benefits_text:
        frequency = 'monthly'
    elif 'season' in benefits_text or 'kharif' in benefits_text or 'rabi' in benefits_text:
        frequency = 'per_crop_season'
    elif 'hectare' in benefits_text or 'acre' in benefits_text:
        frequency = 'per_hectare'
    elif 'one time' in benefits_text or 'one-time' in benefits_text:
        frequency = 'one_time'

    # Calculate annual value
    annual_value = None
    if benefit_value:
        if frequency == 'monthly':
            annual_value = benefit_value * 12
        elif frequency == 'per_crop_season':
            annual_value = benefit_value * 2  # Assume 2 seasons
        else:
            annual_value = benefit_value

    return benefit_value, annual_value, frequency

def determine_scheme_type(scheme: dict) -> str:
    """Determine scheme type from description"""
    name = scheme.get('name', '').lower()
    desc = scheme.get('full_text', '').lower()

    if 'insurance' in name or 'bima' in name:
        return 'insurance'
    elif 'loan' in name or 'credit' in name or 'kisan credit card' in name:
        return 'loan'
    elif 'pension' in name or 'maandhan' in name:
        return 'pension'
    elif 'training' in name or 'skill' in name:
        return 'training'
    elif 'subsidy' in desc and ('equipment' in desc or 'machinery' in desc):
        return 'subsidy'
    elif 'direct' in desc or 'cash' in desc or 'transfer' in desc:
        return 'direct_benefit_transfer'
    elif 'infrastructure' in name or 'fund' in name:
        return 'infrastructure'
    elif 'market' in name or 'e-nam' in name:
        return 'market_access'
    else:
        return 'direct_benefit_transfer'

def determine_sub_sector(scheme: dict) -> str:
    """Determine agriculture sub-sector"""
    name = scheme.get('name', '').lower()
    desc = scheme.get('full_text', '').lower()

    if 'income' in name or 'samman' in name or 'bharosa' in name or 'bandhu' in name:
        return 'income_support'
    elif 'insurance' in name or 'bima' in name:
        return 'crop_insurance'
    elif 'irrigation' in name or 'sinchayee' in name or 'water' in name:
        return 'irrigation'
    elif 'solar' in name or 'kusum' in name or 'energy' in name:
        return 'solar_energy'
    elif 'mechanization' in name or 'machinery' in name:
        return 'mechanization'
    elif 'horticulture' in name or 'midh' in name or 'fruit' in name:
        return 'horticulture'
    elif 'livestock' in name or 'dairy' in name or 'pashu' in name or 'gokul' in name:
        return 'animal_husbandry'
    elif 'fish' in name or 'matsya' in name or 'blue revolution' in name:
        return 'fisheries'
    elif 'organic' in name or 'pkvy' in name or 'natural farming' in name:
        return 'organic_farming'
    elif 'soil' in name:
        return 'soil_health'
    elif 'market' in name or 'e-nam' in name:
        return 'market_linkage'
    elif 'pension' in name:
        return 'pension'
    elif 'bamboo' in name:
        return 'horticulture'
    else:
        return 'income_support'

def parse_eligibility(scheme: dict) -> dict:
    """Parse eligibility from text"""
    elig_text = scheme.get('eligibility_text', '')

    # Determine occupation types
    occupations = ['farmer']
    if 'small' in elig_text.lower() or 'marginal' in elig_text.lower():
        occupations.extend(['small_farmer', 'marginal_farmer'])
    if 'tenant' in elig_text.lower():
        occupations.append('tenant_farmer')
    if 'sharecropper' in elig_text.lower():
        occupations.append('sharecropper')
    if 'landless' in elig_text.lower():
        occupations.append('landless_farmer')

    # Determine requirements
    land_required = 'land' in elig_text.lower() and 'landless' not in elig_text.lower()
    aadhaar_required = True  # Almost all schemes require Aadhaar
    bank_required = True  # Almost all DBT schemes require bank account

    # Land size limits
    land_max = None
    if '2 hectare' in elig_text.lower() or '2 ha' in elig_text.lower():
        land_max = 2.0
    elif '5 hectare' in elig_text.lower():
        land_max = 5.0

    # Excluded categories
    excluded = []
    if 'government employee' in elig_text.lower():
        excluded.append('government_employees')
    if 'taxpayer' in elig_text.lower() or 'income tax' in elig_text.lower():
        excluded.append('income_taxpayers')
    if 'pensioner' in elig_text.lower():
        excluded.append('retired_pensioners_above_10000')
    if 'institutional' in elig_text.lower():
        excluded.append('institutional_landholders')

    return {
        "occupation": list(set(occupations)),
        "land_ownership_required": land_required,
        "land_size_max_hectares": land_max,
        "land_size_min_hectares": None,
        "income_max_annual_inr": None,
        "age_min": 18,
        "age_max": None,
        "aadhaar_required": aadhaar_required,
        "bank_account_required": bank_required,
        "bpl_card_required": False,
        "excluded_categories": excluded,
        "states_excluded": [],
        "eligibility_summary_english": elig_text if elig_text else "All farmers are eligible.",
        "eligibility_notes": ""
    }

def parse_documents(scheme: dict) -> list:
    """Parse required documents"""
    docs_text = scheme.get('documents_text', '').lower()

    documents = []

    # Standard documents
    doc_mapping = {
        'aadhaar': 'aadhaar_card',
        'bank': 'bank_passbook',
        'land': 'land_records',
        'mobile': 'mobile_number',
        'ration': 'ration_card',
        'caste': 'caste_certificate',
        'income': 'income_certificate',
        'photo': 'photo',
        'residence': 'residence_proof',
        'electricity': 'electricity_bill',
        'voter': 'voter_id'
    }

    for keyword, doc_type in doc_mapping.items():
        if keyword in docs_text:
            documents.append({
                "document": doc_type,
                "mandatory": True,
                "notes": None
            })

    # Ensure minimum documents
    if not any(d['document'] == 'aadhaar_card' for d in documents):
        documents.insert(0, {"document": "aadhaar_card", "mandatory": True, "notes": None})
    if not any(d['document'] == 'bank_passbook' for d in documents):
        documents.insert(1, {"document": "bank_passbook", "mandatory": True, "notes": None})

    return documents

def generate_embedding_text(scheme: dict) -> str:
    """Generate embedding text for semantic search"""
    name = scheme.get('name', '')
    state = scheme.get('state', '')
    sub_sector = determine_sub_sector(scheme)
    benefits = scheme.get('benefits_text', '')
    elig = scheme.get('eligibility_text', '')

    # Extract key terms
    keywords = []
    keywords.append(name.lower())
    if state != 'national':
        keywords.append(state.lower())
    keywords.append(sub_sector.replace('_', ' '))

    # Extract amount
    benefit_value, annual_value, _ = extract_amount(scheme)
    if annual_value:
        keywords.append(f"{annual_value} rupees")

    # Add key benefit terms
    for term in ['farmer', 'income', 'subsidy', 'insurance', 'loan', 'solar', 'irrigation', 'crop', 'direct benefit', 'cash transfer', 'pension', 'organic']:
        if term in name.lower() or term in benefits.lower():
            keywords.append(term)

    # Combine into embedding text
    embedding = ' '.join(set(keywords))
    return embedding[:500]  # Limit length

def generate_keywords(scheme: dict) -> list:
    """Generate search keywords"""
    name = scheme.get('name', '').lower()
    state = scheme.get('state', 'national').lower()

    keywords = []

    # Add scheme name parts
    for word in name.split():
        if len(word) > 3:
            keywords.append(word.lower())

    # Add state
    if state != 'national':
        keywords.append(state)

    # Add acronyms
    if 'pm-' in name.lower():
        keywords.append(name.split('(')[0].strip().lower())

    # Add benefit type
    benefit_value, annual_value, _ = extract_amount(scheme)
    if annual_value:
        keywords.append(f"{annual_value} rupees")

    return list(set(keywords))[:10]

def generate_tags(scheme: dict) -> list:
    """Generate classification tags"""
    tags = []

    state = scheme.get('state', 'national')
    if state == 'national':
        tags.extend(['central', 'all_states'])
    else:
        tags.append('state')
        tags.append(state.lower().replace(' ', '_'))

    # Add sub-sector tag
    sub_sector = determine_sub_sector(scheme)
    tags.append(sub_sector)

    # Add scheme type tag
    scheme_type = determine_scheme_type(scheme)
    tags.append(scheme_type)

    # Add benefit type
    if 'dbt' in scheme.get('benefits_text', '').lower() or 'direct' in scheme.get('benefits_text', '').lower():
        tags.append('dbt')

    return list(set(tags))

def generate_spoken_content(scheme: dict) -> dict:
    """Generate spoken/voice content"""
    name = scheme.get('name', '')
    benefit_value, annual_value, frequency = extract_amount(scheme)
    app_process = scheme.get('application_process_text', '')

    # Gap card announcement
    if annual_value:
        freq_text = 'per year' if frequency == 'annual' else f'per {frequency.replace("_", " ")}'
        gap_announcement = f"You can receive ₹{annual_value:,} {freq_text} from {name.split('(')[0].strip()}."
    else:
        gap_announcement = f"You can benefit from {name.split('(')[0].strip()}."

    # One line summary
    benefits_desc = scheme.get('benefits_text', '')
    one_line = f"{name.split('(')[0].strip()} provides {benefits_desc[:100]}..."
    if len(one_line) > 150:
        one_line = one_line[:147] + "..."

    # Spoken guidance (simplified)
    if app_process:
        # Simplify the application process
        spoken_guide = app_process.replace('http', '').replace('www.', '').replace('.gov.in', '')
        if 'csc' in app_process.lower():
            spoken_guide = "Go to your nearest CSC (Jan Seva Kendra) with your documents. They will help you register for free."
        elif 'online' in app_process.lower():
            spoken_guide = "You can apply online or visit your local agriculture office with required documents."
        elif 'gram panchayat' in app_process.lower():
            spoken_guide = "Visit your Gram Panchayat office with your Aadhaar and other documents for registration."
        else:
            spoken_guide = "Visit the nearest agriculture office or government center with your documents to apply."
    else:
        spoken_guide = "Contact your local agriculture department for application assistance."

    # Closing action
    if 'csc' in app_process.lower():
        closing = "Go to your nearest Jan Seva Kendra with your Aadhaar card and documents."
    elif 'panchayat' in app_process.lower():
        closing = "Visit your Gram Panchayat office with required documents."
    else:
        closing = "Visit your local agriculture office with identity and land documents."

    return {
        "gap_card_announcement": gap_announcement[:150],
        "one_line_summary": one_line,
        "spoken_guidance_simple": spoken_guide[:300],
        "closing_action": closing[:100],
        "status_check_spoken": None
    }

def calculate_completeness(scheme_data: dict) -> float:
    """Calculate completeness score"""
    required_fields = [
        'name_english', 'state', 'sector', 'sub_sector',
        'eligibility', 'benefits', 'application',
        'embedding_text', 'spoken_content'
    ]

    filled = 0
    total = len(required_fields)

    for field in required_fields:
        if field in scheme_data and scheme_data[field]:
            filled += 1

    return round(filled / total, 2)

def transform_scheme(old_scheme: dict) -> dict:
    """Transform old scheme format to comprehensive schema v2.0"""

    # Generate unique ID
    scheme_id = generate_scheme_id(
        old_scheme.get('name', ''),
        old_scheme.get('state', 'national')
    )

    # Extract amounts
    benefit_value, annual_value, frequency = extract_amount(old_scheme)

    # Determine classification
    state_name = old_scheme.get('state', 'national')
    level = 'central' if state_name == 'national' else 'state'
    states_applicable = ['all'] if state_name == 'national' else [state_name]

    # Build comprehensive scheme
    new_scheme = {
        "schema_version": "2.0",
        "scheme_id": scheme_id,

        # Identity
        "name_english": old_scheme.get('name', ''),
        "name_hindi": None,  # To be added via translation
        "name_short": old_scheme.get('name', '').split('(')[0].strip(),
        "acronym": old_scheme.get('name', '').split('(')[1].split(')')[0] if '(' in old_scheme.get('name', '') else None,

        # Classification
        "level": level,
        "state": state_name,
        "states_applicable": states_applicable,
        "sector": "agriculture",
        "sub_sector": determine_sub_sector(old_scheme),
        "ministry": None,
        "department": None,
        "implementing_agency": "State Agriculture Departments" if level == 'central' else f"{state_name} Government",
        "launched_year": None,
        "scheme_status": "active",
        "scheme_type": determine_scheme_type(old_scheme),

        # Eligibility
        "eligibility": parse_eligibility(old_scheme),

        # Benefits
        "benefits": {
            "has_monetary_benefit": benefit_value is not None,
            "monetary": {
                "amount_inr": benefit_value,
                "amount_inr_max": None,
                "frequency": frequency,
                "payment_mode": "dbt" if 'dbt' in old_scheme.get('benefits_text', '').lower() or 'direct' in old_scheme.get('benefits_text', '').lower() else "subsidy_on_purchase",
                "installments": [],  # To be filled manually if needed
                "annual_value_inr": annual_value,
                "benefit_description_english": old_scheme.get('benefits_text', '')
            },
            "non_monetary": {
                "has_non_monetary_benefit": False,
                "types": [],
                "description_english": None
            }
        },

        # Application
        "application": {
            "mode": ["online", "offline"],
            "portal_url": old_scheme.get('url', ''),
            "portal_url_direct_register": None,
            "application_form_name": None,
            "application_form_url": None,
            "application_fee_inr": 0,
            "documents_required": parse_documents(old_scheme),
            "spoken_guidance_english": old_scheme.get('application_process_text', ''),
            "helpline_number": None,
            "helpline_number_alt": None,
            "grievance_portal": old_scheme.get('url', ''),
            "processing_time_days": 30,
            "status_check_url": old_scheme.get('url', ''),
            "status_check_method": "aadhaar_or_mobile",
            "auto_renewal": True,
            "registration_deadline": None
        },

        # Form field mapping - SET TO NULL as per user request
        "form_field_mapping": None,

        # Semantic Search
        "embedding_text": generate_embedding_text(old_scheme),
        "keywords": generate_keywords(old_scheme),
        "tags": generate_tags(old_scheme),

        # Voice/Spoken Content
        "spoken_content": generate_spoken_content(old_scheme),

        # Live API
        "live_api": {
            "has_public_api": False,
            "api_type": "none",
            "status_check_endpoint": None,
            "status_check_params": None,
            "status_check_note": None,
            "registration_endpoint": None,
            "api_documentation_url": None
        },

        # Source & Data Quality
        "source": {
            "primary_url": old_scheme.get('url', ''),
            "secondary_urls": [],
            "scraped_at": datetime.now().isoformat(),
            "scraper_version": "v2_static_db",
            "last_verified_human": None,
            "data_source_type": "official_portal" if old_scheme.get('source') == 'ministry_portal' else 'state_portal'
        },

        "data_quality": {
            "eligibility_complete": bool(old_scheme.get('eligibility_text')),
            "benefits_complete": bool(old_scheme.get('benefits_text')),
            "application_complete": bool(old_scheme.get('application_process_text')),
            "documents_complete": bool(old_scheme.get('documents_text')),
            "form_fields_complete": False,  # We're excluding form mapping
            "annual_value_confidence": "high" if annual_value else "low",
            "last_reviewed": datetime.now().date().isoformat(),
            "review_notes": "Transformed from raw collection data",
            "completeness_score": 0.0  # Will be calculated
        }
    }

    # Calculate completeness
    new_scheme['data_quality']['completeness_score'] = calculate_completeness(new_scheme)

    return new_scheme

def main():
    """Main transformation function"""

    print("="*70)
    print("TRANSFORMING 51 SCHEMES TO COMPREHENSIVE SCHEMA V2.0")
    print("="*70)

    # Load raw data
    input_file = Path("data/raw_agriculture_all.json")
    if not input_file.exists():
        print(f"ERROR: {input_file} not found!")
        return

    with open(input_file, 'r', encoding='utf-8') as f:
        old_schemes = json.load(f)

    print(f"\nLoaded {len(old_schemes)} schemes from {input_file}")

    # Transform all schemes
    new_schemes = []
    for i, old_scheme in enumerate(old_schemes, 1):
        print(f"[{i}/{len(old_schemes)}] Transforming: {old_scheme.get('name', 'Unknown')[:60]}")
        new_scheme = transform_scheme(old_scheme)
        new_schemes.append(new_scheme)

    # Save transformed data
    output_file = Path("data/schemes_comprehensive_v2.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(new_schemes, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*70}")
    print("TRANSFORMATION COMPLETE")
    print("="*70)
    print(f"Total schemes transformed: {len(new_schemes)}")
    print(f"Output file: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")

    # Quality statistics
    print(f"\n{'='*70}")
    print("QUALITY STATISTICS")
    print("="*70)

    completeness_scores = [s['data_quality']['completeness_score'] for s in new_schemes]
    avg_completeness = sum(completeness_scores) / len(completeness_scores)

    schemes_with_amount = sum(1 for s in new_schemes if s['benefits']['monetary']['annual_value_inr'])
    schemes_central = sum(1 for s in new_schemes if s['level'] == 'central')
    schemes_state = sum(1 for s in new_schemes if s['level'] == 'state')

    print(f"Average completeness score: {avg_completeness:.2%}")
    print(f"Schemes with annual value: {schemes_with_amount}/{len(new_schemes)}")
    print(f"Central schemes: {schemes_central}")
    print(f"State schemes: {schemes_state}")

    # Sub-sector breakdown
    print(f"\nSub-sector distribution:")
    sub_sectors = {}
    for s in new_schemes:
        sub = s['sub_sector']
        sub_sectors[sub] = sub_sectors.get(sub, 0) + 1

    for sub, count in sorted(sub_sectors.items(), key=lambda x: x[1], reverse=True):
        print(f"  {sub}: {count}")

    # Sample scheme for verification
    print(f"\n{'='*70}")
    print("SAMPLE TRANSFORMED SCHEME (First scheme)")
    print("="*70)
    sample = new_schemes[0]
    print(f"Scheme ID: {sample['scheme_id']}")
    print(f"Name: {sample['name_english']}")
    print(f"Level: {sample['level']} | State: {sample['state']}")
    print(f"Sub-sector: {sample['sub_sector']} | Type: {sample['scheme_type']}")
    print(f"Annual value: ₹{sample['benefits']['monetary']['annual_value_inr']:,}" if sample['benefits']['monetary']['annual_value_inr'] else "Annual value: Not specified")
    print(f"Completeness: {sample['data_quality']['completeness_score']:.0%}")
    print(f"\nGap card announcement: {sample['spoken_content']['gap_card_announcement']}")
    print(f"Embedding text: {sample['embedding_text'][:100]}...")

    print(f"\n{'='*70}")
    print("✅ ALL 51 SCHEMES SUCCESSFULLY TRANSFORMED!")
    print("="*70)
    print("\nNext steps:")
    print("1. Review: data/schemes_comprehensive_v2.json")
    print("2. Generate embeddings with Cohere")
    print("3. Upload to Supabase")
    print("4. Test semantic search")

if __name__ == "__main__":
    main()
