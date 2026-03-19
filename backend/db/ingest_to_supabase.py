"""
Supabase Ingestion Module — Phase 4
Pushes chunked + embedded scheme data into the schemes / scheme_chunks tables.
"""
import sys
import os
import json
from typing import Dict, List, Any, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.db.supabase_client import supabase
from rich.console import Console

console = Console()


# ---- 1. clear_schemes_data ----

def clear_schemes_data():
    """
    Deletes ALL rows from scheme_chunks and schemes tables.
    ONLY use for a full re-ingestion. Asks for confirmation.
    """
    console.print("[bold red]⚠ WARNING: This will delete ALL scheme data from Supabase![/bold red]")
    confirm = input("Are you sure? Type YES to confirm: ").strip()
    if confirm != "YES":
        console.print("[yellow]Aborted.[/yellow]")
        return False

    # Delete chunks first (foreign key dependency)
    supabase.table("scheme_chunks").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    supabase.table("schemes").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    console.print("[green]All scheme data cleared from Supabase.[/green]")
    return True


# ---- 2. insert_scheme ----

def insert_scheme(scheme: Dict[str, Any]) -> Optional[str]:
    """
    Inserts one scheme into the schemes table.
    Returns the generated UUID.
    Handles duplicate scheme_name + state gracefully via upsert.
    """
    struct = scheme.get("structured_data", {})

    def safe_int(val):
        """Coerce a value to int or None. Handles dicts, strings, etc."""
        if val is None:
            return None
        if isinstance(val, int):
            return val
        if isinstance(val, float):
            return int(val)
        if isinstance(val, str):
            try:
                return int(val)
            except ValueError:
                return None
        # If it's a dict (e.g. tiered income limits), take the max value
        if isinstance(val, dict):
            nums = [v for v in val.values() if isinstance(v, (int, float))]
            return int(max(nums)) if nums else None
        return None

    def safe_bool(val):
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return False

    row = {
        "scheme_name": struct.get("scheme_name_clean", scheme.get("scheme_name", "")),
        "ministry": struct.get("ministry", scheme.get("ministry", "")),
        "state": scheme.get("state", "national"),
        "category": struct.get("category", []),
        "gender": struct.get("gender", "all"),
        "age_min": safe_int(struct.get("age_min")),
        "age_max": safe_int(struct.get("age_max")),
        "income_limit": safe_int(struct.get("income_limit_annual")),
        "occupation": struct.get("occupation", []),
        "marital_status": struct.get("marital_status", "any"),
        "bpl_required": safe_bool(struct.get("bpl_required", False)),
        "disability_required": safe_bool(struct.get("disability_required", False)),
        "documents_needed": struct.get("documents_needed", []),
        "application_url": scheme.get("application_url", ""),
        "official_source_url": scheme.get("official_source_url", ""),
        "tier": scheme.get("tier", 2),
        "data_quality_score": struct.get("data_quality_score"),
    }

    # Manual dedup: check if a scheme with same name + state already exists
    existing = (
        supabase.table("schemes")
        .select("id")
        .eq("scheme_name", row["scheme_name"])
        .eq("state", row["state"])
        .execute()
    )

    if existing.data and len(existing.data) > 0:
        # Update existing row
        scheme_id = existing.data[0]["id"]
        supabase.table("schemes").update(row).eq("id", scheme_id).execute()
        return scheme_id
    else:
        # Insert new row
        result = supabase.table("schemes").insert(row).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]["id"]
        return None


# ---- 3. insert_chunks ----

def insert_chunks(chunks: List[Dict[str, Any]], scheme_uuid: str, embeddings: List[List[float]]):
    """
    Takes the list of chunks from chunker.py, pairs them with pre-computed
    embeddings, and batch-inserts all rows into scheme_chunks.

    Supabase pgvector accepts Python lists of floats directly for the
    embedding column — no special formatting is needed.
    """
    rows = []
    for chunk, emb in zip(chunks, embeddings):
        rows.append({
            "scheme_id": scheme_uuid,
            "chunk_text": chunk["chunk_text"],
            "chunk_type": chunk["chunk_type"],
            "embedding": emb,  # list[float] — pgvector accepts this directly
        })

    # Batch insert (single round-trip, much faster than one-by-one)
    supabase.table("scheme_chunks").insert(rows).execute()


# ---- 4. verify_ingestion ----

def verify_ingestion(scheme_uuid: str) -> Dict[str, Any]:
    """
    Queries Supabase to confirm a scheme and its chunks exist.
    Returns {scheme_found, chunk_count, chunk_types}.
    """
    scheme_res = supabase.table("schemes").select("id").eq("id", scheme_uuid).execute()
    scheme_found = len(scheme_res.data) > 0

    chunks_res = (
        supabase.table("scheme_chunks")
        .select("chunk_type")
        .eq("scheme_id", scheme_uuid)
        .execute()
    )
    chunk_count = len(chunks_res.data)
    chunk_types = list({row["chunk_type"] for row in chunks_res.data})

    return {
        "scheme_found": scheme_found,
        "chunk_count": chunk_count,
        "chunk_types": chunk_types,
    }
