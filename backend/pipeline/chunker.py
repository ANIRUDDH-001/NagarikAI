import json
from typing import List, Dict, Any
from pathlib import Path

def chunk_scheme(scheme: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Splits a thoroughly cleaned scheme object into semantically categorized RAG chunks.
    This enables retrieving specialized components dynamically based on user queries,
    mitigating giant context windows and noisy cross-contamination.
    """
    chunks = []
    
    # Core identifiers
    scheme_id = str(scheme.get("scheme_id", ""))
    if not scheme_id:
        # Fallback pseudo-ID if actual is missing
        scheme_id = scheme.get("scheme_name", "Unknown").lower().replace(" ", "_")
        
    scheme_name = scheme.get("scheme_name", "Unknown Scheme")
    
    # Locate the AI-structured data payload
    struct = scheme.get("structured_data", {})
    
    # -------------------------------------------------------------------------
    # Supabase Pre-filtering Metadata
    # -------------------------------------------------------------------------
    # The metadata attached to every semantic chunk is designed precisely to enable 
    # exact pre-filtering in Supabase BEFORE executing the pgvector cosine similarity search.
    # This is an absolute critical step for RAG accuracy. It forcefully isolates the vector 
    # search space to ONLY the schemes a user is strictly eligible for (matching their state,
    # age, income limits, categorical status), drastically mitigating hallucinations from 
    # visually similar but procedurally inapplicable policies.
    metadata = {
        "state": scheme.get("state", struct.get("state", "national")),
        "category": struct.get("category", []),
        "age_min": struct.get("age_min"),
        "age_max": struct.get("age_max"),
        "income_limit": struct.get("income_limit_annual"),
        "occupation": struct.get("occupation", []),
        "bpl_required": struct.get("bpl_required"),
        "tier": scheme.get("tier", 1)
    }

    # Internal helper to softly truncate lengths retaining completeness bounds
    def truncate(text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."

    # 1. OVERVIEW CHUNK
    ministry = struct.get("ministry", scheme.get("ministry", ""))
    benefits_sum = struct.get("benefits_summary", "")
    eligibility_sum = struct.get("eligibility_summary", "")
    
    overview_text = f"Scheme: {scheme_name}. Ministry: {ministry}. Benefits: {benefits_sum}. Eligibility: {eligibility_sum}."
    chunks.append({
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "chunk_type": "overview",
        "chunk_text": truncate(overview_text.strip(), 400),
        "metadata": metadata
    })

    # 2. ELIGIBILITY CHUNK
    raw_elig = scheme.get("eligibility_text", "")
    
    # Translate structured conditionals into natural language bindings
    criteria_parts = []
    age_min = struct.get("age_min")
    age_max = struct.get("age_max")
    
    if age_min is not None and age_max is not None:
        criteria_parts.append(f"Applicants must be between {age_min} and {age_max} years old.")
    elif age_min is not None:
        criteria_parts.append(f"Applicants must be at least {age_min} years old.")
    elif age_max is not None:
        criteria_parts.append(f"Applicants must be at most {age_max} years old.")
        
    inc_limit = struct.get("income_limit_annual")
    if inc_limit is not None:
        criteria_parts.append(f"Annual household income must be below ₹{inc_limit}.")
        
    cats = struct.get("category", [])
    if cats and "All" not in cats:
        cat_str = ", ".join(cats)
        criteria_parts.append(f"This scheme is available for {cat_str} category citizens.")
        
    bpl = struct.get("bpl_required")
    if bpl is True:
        criteria_parts.append("Applicants strictly require a Below Poverty Line (BPL) status.")
        
    nl_criteria = " ".join(criteria_parts)
    eligibility_text = f"Official Guidelines: {raw_elig} Computed Criteria: {nl_criteria}"
    
    chunks.append({
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "chunk_type": "eligibility",
        "chunk_text": truncate(eligibility_text.strip(), 600),
        "metadata": metadata
    })

    # 3. BENEFITS CHUNK
    raw_ben = scheme.get("benefits_text", "")
    benefits_text = f"{raw_ben} Key takeaway: {benefits_sum}"
    
    chunks.append({
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "chunk_type": "benefits",
        "chunk_text": truncate(benefits_text.strip(), 400),
        "metadata": metadata
    })

    # 4. PROCESS CHUNK
    app_steps = struct.get("application_steps", [])
    if isinstance(app_steps, list):
        steps_str = " ".join(app_steps)
    else:
        steps_str = str(app_steps)
        
    docs = struct.get("documents_needed", [])
    if isinstance(docs, list):
        docs_str = ", ".join(docs)
    else:
        docs_str = str(docs)
        
    if not steps_str and not docs_str:
        process_text = "Standard application process applies. Refer to official portal or CSC."
    else:
        process_text = f"To apply: {steps_str}. Documents needed: {docs_str}."
        
    chunks.append({
        "scheme_id": scheme_id,
        "scheme_name": scheme_name,
        "chunk_type": "process",
        "chunk_text": truncate(process_text.strip(), 600),
        "metadata": metadata
    })

    return chunks

def test_chunker():
    """Validates the Chunking algorithms over local sample records."""
    data = []
    
    # Try fetching actively cleaned structures
    clean_file = Path("backend/data/clean/schemes_clean.json")
    if clean_file.exists():
        with open(clean_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
    # Fallback to rejected records if they haven't explicitly seeded success yet
    if not data:
        fallback_file = Path("backend/data/clean/schemes_rejected.json")
        if fallback_file.exists():
            with open(fallback_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
    if not data:
        # Deep fallback to raw Tier 1 schema just to prove the module runs without crashing
        raw_fallback_file = Path("backend/data/raw/tier1_seed.json")
        if raw_fallback_file.exists():
            with open(raw_fallback_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
    if not data:
        print("[!] Cannot find any JSON arrays inside backend/data/... run the earlier pipelines first.")
        return
        
    test_schemes = data[:3]
    print(f"Testing Semantic Chunker on {len(test_schemes)} sampled schemes...\n")
    print("=" * 100)
    
    for i, scheme in enumerate(test_schemes):
        print(f"--- RESOURCE #{i+1}: {scheme.get('scheme_name')} ---")
        chunks = chunk_scheme(scheme)
        
        for chunk in chunks:
            print(f"\n❖ [TYPE: {chunk['chunk_type'].upper()}] | Cap: {len(chunk['chunk_text'])} chars")
            print(f"TEXT: {chunk['chunk_text']}")
            print(f"METADATA: {json.dumps(chunk['metadata'], indent=2)}")
        print("\n" + "=" * 100)

if __name__ == "__main__":
    test_chunker()
