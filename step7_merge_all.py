import json
from pathlib import Path

all_raw = []
slugs_seen = set()

sources = [
    ("data/central_raw.json", "central_ministry"),
    ("data/state_raw.json", "state_agriculture"),
    ("data/additional_raw.json", "additional_schemes"),
]

print("Merging agriculture scheme data from all sources...\n")

for filepath, label in sources:
    if not Path(filepath).exists():
        print(f"SKIPPED: {filepath} — file not found")
        continue

    data = json.loads(Path(filepath).read_text(encoding="utf-8"))
    added = 0
    skipped_duplicate = 0
    skipped_short = 0

    for scheme in data:
        slug = scheme.get("slug", "")

        # Check for duplicates
        if slug and slug in slugs_seen:
            skipped_duplicate += 1
            continue

        # Only include if has meaningful text
        text = scheme.get("full_text", "")
        if len(text) < 200:
            skipped_short += 1
            continue

        if slug:
            slugs_seen.add(slug)

        all_raw.append(scheme)
        added += 1

    print(f"{label}:")
    print(f"  Added: {added}")
    print(f"  Skipped (duplicate): {skipped_duplicate}")
    print(f"  Skipped (too short): {skipped_short}")
    print()

print(f"="*60)
print(f"TOTAL AGRICULTURE SCHEMES COLLECTED: {len(all_raw)}")
print(f"="*60)

# Save merged data
output_path = "data/raw_agriculture_all.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_raw, f, ensure_ascii=False, indent=2)

print(f"\nSaved to {output_path}")

# Statistics
states_count = {}
for scheme in all_raw:
    state = scheme.get("state", "unknown")
    states_count[state] = states_count.get(state, 0) + 1

print("\nBreakdown by state/category:")
for state, count in sorted(states_count.items(), key=lambda x: -x[1]):
    print(f"  {state}: {count} schemes")

# Check content quality
with_eligibility = sum(1 for s in all_raw if len(s.get("eligibility_text", "")) > 50)
with_benefits = sum(1 for s in all_raw if len(s.get("benefits_text", "")) > 50)
with_application = sum(1 for s in all_raw if len(s.get("application_process_text", "")) > 50)

print("\nContent quality:")
print(f"  With eligibility text: {with_eligibility}/{len(all_raw)}")
print(f"  With benefits text: {with_benefits}/{len(all_raw)}")
print(f"  With application process: {with_application}/{len(all_raw)}")
print(f"\nReady for enrichment!")
