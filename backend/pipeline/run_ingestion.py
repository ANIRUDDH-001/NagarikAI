"""
Ingestion Orchestrator — Phase 4
Reads schemes_clean.json → chunks → embeds → pushes to Supabase.
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn

console = Console()

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CLEAN_DIR = DATA_DIR / "clean"


def main():
    parser = argparse.ArgumentParser(description="Ingest clean schemes into Supabase")
    parser.add_argument("--fresh", action="store_true", help="Clear all existing data first")
    parser.add_argument("--tier1-only", action="store_true", help="Only ingest Tier 1 schemes")
    parser.add_argument("--dry-run", action="store_true", help="Run everything except Supabase writes")
    args = parser.parse_args()

    # ---- STEP 1: Pre-flight checks ----
    console.print("\n[bold cyan]STEP 1 — Pre-flight checks[/bold cyan]")

    # 1a. Supabase connection
    if not args.dry_run:
        try:
            from backend.db.supabase_client import supabase
            supabase.table("schemes").select("id").limit(1).execute()
            console.print("  ✅ Supabase connection OK")
        except Exception as e:
            console.print(f"  [red]❌ Supabase connection failed: {e}[/red]")
            sys.exit(1)
    else:
        console.print("  ⏩ Supabase check skipped (dry-run)")

    # 1b. Embedding model
    console.print("  Loading embedding model ...")
    from backend.pipeline.embedder import embed_text, embed_batch, EMBEDDING_DIM
    test_vec = embed_text("test")
    assert len(test_vec) == EMBEDDING_DIM
    console.print(f"  ✅ Embedding model OK ({EMBEDDING_DIM}-d vectors)")

    # 1c. Load data
    clean_file = CLEAN_DIR / "schemes_clean.json"
    if not clean_file.exists():
        console.print(f"  [red]❌ {clean_file} not found. Run the cleaning pipeline first.[/red]")
        sys.exit(1)

    with open(clean_file, "r", encoding="utf-8") as f:
        schemes = json.load(f)

    if args.tier1_only:
        schemes = [s for s in schemes if s.get("tier", 0) == 1]
        console.print(f"  [yellow]--tier1-only: filtered to {len(schemes)} Tier 1 schemes[/yellow]")

    # Sort by tier (Tier 1 first — so if something fails, best data is in)
    schemes.sort(key=lambda s: s.get("tier", 99))

    est_minutes = round(len(schemes) * 0.5 / 60, 1)  # ~0.5s per scheme
    console.print(f"  📦 {len(schemes)} schemes ready for ingestion (~{est_minutes} min)")

    if not args.dry_run:
        confirm = input(f"\n  Ingest {len(schemes)} schemes? This will take ~{est_minutes} minutes. Continue? (y/n): ")
        if confirm.strip().lower() != "y":
            console.print("[yellow]Aborted.[/yellow]")
            return

    # ---- STEP 1.5: Fresh wipe (if requested) ----
    if args.fresh and not args.dry_run:
        from backend.db.ingest_to_supabase import clear_schemes_data
        clear_schemes_data()

    # ---- STEP 2: Load chunker ----
    from backend.pipeline.chunker import chunk_scheme

    if not args.dry_run:
        from backend.db.ingest_to_supabase import insert_scheme, insert_chunks, verify_ingestion

    # ---- STEP 3: Process each scheme ----
    console.print("\n[bold cyan]STEP 3 — Ingesting schemes[/bold cyan]")
    start_time = time.perf_counter()

    success_count = 0
    fail_count = 0
    total_chunks = 0
    failed_schemes = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[green]Ingesting...", total=len(schemes))

        for scheme in schemes:
            name = scheme.get("scheme_name", "Unknown")
            try:
                # 3a. Insert scheme metadata
                if args.dry_run:
                    scheme_uuid = "dry-run-uuid"
                else:
                    scheme_uuid = insert_scheme(scheme)
                    if not scheme_uuid:
                        raise ValueError("insert_scheme returned None")

                # 3b. Generate chunks
                chunks = chunk_scheme(scheme)

                # 3c. Embed all chunks
                chunk_texts = [c["chunk_text"] for c in chunks]
                embeddings = embed_batch(chunk_texts)

                # 3d. Insert chunks with embeddings
                if not args.dry_run:
                    insert_chunks(chunks, scheme_uuid, embeddings)

                # 3e. Verify insertion
                if not args.dry_run:
                    verification = verify_ingestion(scheme_uuid)
                    if not verification["scheme_found"]:
                        raise ValueError("Verification failed: scheme not found after insert")

                success_count += 1
                total_chunks += len(chunks)
                progress.console.print(
                    f"  ✅ {name} — {len(chunks)} chunks ingested"
                )

            except Exception as e:
                fail_count += 1
                failed_schemes.append({"scheme_name": name, "error": str(e)})
                progress.console.print(f"  [red]❌ {name} — {e}[/red]")

            progress.advance(task)

    elapsed = time.perf_counter() - start_time

    # ---- STEP 4: Save errors ----
    if failed_schemes:
        err_file = CLEAN_DIR / "ingestion_errors.json"
        with open(err_file, "w", encoding="utf-8") as f:
            json.dump(failed_schemes, f, indent=2)
        console.print(f"\n[yellow]Error log saved to {err_file}[/yellow]")

    # ---- STEP 5: Final report ----
    console.print("\n[bold green]====== INGESTION REPORT ======[/bold green]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Schemes Ingested", f"[green]{success_count}[/green]")
    table.add_row("Total Chunks", str(total_chunks))
    table.add_row("Total Vector Records", str(total_chunks))
    table.add_row("Failed Schemes", f"[red]{fail_count}[/red]" if fail_count else "0")
    table.add_row("Time Taken", f"{elapsed:.1f}s")
    table.add_row("Mode", "DRY RUN" if args.dry_run else "LIVE")
    console.print(table)

    if fail_count == 0:
        console.print("[bold green]Database is ready for RAG queries ✅[/bold green]")
    else:
        console.print(f"[yellow]{fail_count} schemes failed — check ingestion_errors.json[/yellow]")


if __name__ == "__main__":
    main()
