import json
import difflib
from pathlib import Path
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def get_field(item, primary_key, *fallbacks):
    """Retrieve a field falling back to variations created by different scrapers."""
    if primary_key in item and item[primary_key]:
        return item[primary_key]
    for key in fallbacks:
        if key in item and item[key]:
            return item[key]
    return None

def check_encoding(text):
    """Check for common garbled characters and replacement chars."""
    if not isinstance(text, str):
        return False
    # Look for unicode replacement char or typical utf-8 double encoding artifacts
    mojibake = ['\ufffd', 'â€', 'Ã', 'Â']
    for bad_chars in mojibake:
        if bad_chars in text:
            return True
    return False

def main():
    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    input_file = data_dir / "all_schemes_raw.json"
    report_file = data_dir / "validation_report.json"

    if not input_file.exists():
        console.log(f"[bold red]Cannot find input file:[/bold red] {input_file}")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        console.log("[bold red]Expected a JSON array in all_schemes_raw.json[/bold red]")
        return

    total_schemes = len(data)
    if total_schemes == 0:
        console.log("[bold red]No schemes found in all_schemes_raw.json[/bold red]")
        return

    # Trackers
    failures = defaultdict(list)
    warnings = defaultdict(list)
    
    # 1. Duplicates check
    names = []
    for item in data:
        name = get_field(item, "scheme_name", "title", "id")
        if name:
            names.append(str(name).strip())

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if len(names[i]) > 0 and len(names[j]) > 0:
                ratio = difflib.SequenceMatcher(None, names[i].lower(), names[j].lower()).ratio()
                if ratio > 0.95:
                    failures["DUPLICATES"].append(f"{names[i]} <-> {names[j]}")

    # Item-level checks
    for idx, item in enumerate(data):
        name = get_field(item, "scheme_name", "title") or f"Unknown_Scheme_Index_{idx}"

        # 1. COMPLETENESS
        req_desc = get_field(item, "description", "brief_description")
        req_elig = get_field(item, "eligibility_text", "eligibility_criteria", "eligibility")
        
        if not req_desc:
            failures["COMPLETENESS_MISSING_DESCRIPTION"].append(name)
        if not req_elig:
            failures["COMPLETENESS_MISSING_ELIGIBILITY"].append(name)

        opt_income = get_field(item, "income_limit")
        opt_cat = get_field(item, "category", "category_tags")
        opt_docs = get_field(item, "documents_needed", "documents_required", "documents")

        if not opt_income:
            warnings["COMPLETENESS_MISSING_OPTIONAL_INCOME"].append(name)
        if not opt_cat:
            warnings["COMPLETENESS_MISSING_OPTIONAL_CATEGORY"].append(name)
        if not opt_docs:
            warnings["COMPLETENESS_MISSING_OPTIONAL_DOCS"].append(name)

        # 2. LENGTH CHECKS
        if req_desc and len(str(req_desc)) < 50:
            warnings["LENGTH_SHORT_DESCRIPTION"].append(name)
        if req_elig and len(str(req_elig)) < 30:
            warnings["LENGTH_SHORT_ELIGIBILITY"].append(name)
        
        if opt_docs is not None:
            if isinstance(opt_docs, list) and len(opt_docs) == 0:
                warnings["LENGTH_EMPTY_DOCS_LIST"].append(name)
            elif isinstance(opt_docs, str) and len(str(opt_docs).strip()) < 5:
                warnings["LENGTH_EMPTY_DOCS_LIST"].append(name)
        else:
            warnings["LENGTH_EMPTY_DOCS_LIST"].append(name)

        # 3. ENCODING ISSUES
        text_to_check = f"{name} {req_desc or ''} {req_elig or ''}"
        if check_encoding(text_to_check):
            failures["ENCODING_ISSUES"].append(name)

        # 4. URL VALIDITY
        app_url = get_field(item, "application_url", "apply_url", "official_application_url")
        src_url = get_field(item, "official_source_url", "detail_page_url")

        if not app_url or (isinstance(app_url, str) and not app_url.startswith("http")):
            warnings["URL_INVALID_APPLICATION"].append(name)
        if not src_url or (isinstance(src_url, str) and not src_url.startswith("http")):
            warnings["URL_INVALID_OFFICIAL_SOURCE"].append(name)

    # Calculate Data Quality Score
    # We penalize based on ratios
    max_deduction = 100
    
    # 2 pts per hard failure, 0.5 per warning. Max deducted per scheme capped mentally.
    total_failures = sum(len(lst) for lst in failures.values())
    total_warnings = sum(len(lst) for lst in warnings.values())
    
    deduction = (total_failures * 3.0) + (total_warnings * 0.5)
    
    # Normalize by total schemes so larger datasets don't auto-fail
    # If a scheme has 1 failure and 2 warnings, that's 4 points deducted.
    # Out of max roughly 10 points per scheme.
    average_deduction_per_scheme = deduction / total_schemes if total_schemes else 0
    # Let's say if avg deduction per scheme is > 5, score is 0.
    quality_score = max(0, min(100, 100 - (average_deduction_per_scheme * 20)))

    # Produce JSON Report Document
    report = {
        "total_schemes": total_schemes,
        "quality_score": round(quality_score, 2),
        "failures": dict(failures),
        "warnings": dict(warnings)
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    # Print Terminal Report
    console.print("\n[bold cyan]====== RAW DATA VALIDATION REPORT ======[/bold cyan]")
    console.print(f"[bold]Total Schemes Analyzed:[/bold] {total_schemes}")
    
    score_color = "green" if quality_score >= 80 else "yellow" if quality_score >= 50 else "red"
    console.print(f"[bold]Data Quality Score:[/bold] [{score_color}]{quality_score:.2f} / 100[/{score_color}]")

    recommendation = "Ready for AI pipeline" if quality_score >= 80 else "Fix issues first"
    console.print(f"[bold]Recommendation:[/bold] [{score_color}]{recommendation}[/{score_color}]\n")

    table = Table(title="Validation Checks Summary", show_header=True, header_style="bold magenta")
    table.add_column("Check Category", style="dim", width=40)
    table.add_column("Status", justify="center")
    table.add_column("Count", justify="right")
    
    # Add fail rows
    for k, v in failures.items():
        if len(v) > 0:
            table.add_row(k, "[red]FAIL[/red]", str(len(v)))
        else:
            table.add_row(k, "[green]PASS[/green]", "0")
            
    # Add warning rows
    for k, v in warnings.items():
        if len(v) > 0:
            table.add_row(k, "[yellow]WARN[/yellow]", str(len(v)))
        else:
            table.add_row(k, "[green]PASS[/green]", "0")
            
    console.print(table)

    # Details
    if failures:
        console.print("\n[bold red]Critical Failures Need Attention:[/bold red]")
        for k, v in failures.items():
            if v:
                console.print(f"  [red]* {k}[/red] ({len(v)} schemes)")
                # Print up to 3 examples
                for ex in v[:3]:
                    console.print(f"      - {ex}")
                if len(v) > 3:
                    console.print(f"      - ... and {len(v) - 3} more")

    console.print(f"\n[bold green]Report successfully saved to {report_file}[/bold green]\n")

if __name__ == "__main__":
    main()
