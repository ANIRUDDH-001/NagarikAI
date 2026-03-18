import json
from pathlib import Path
from collections import defaultdict

def main():
    data_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    output_file = data_dir / "all_schemes_raw.json"
    
    if not data_dir.exists():
        print(f"Directory {data_dir} does not exist.")
        return

    # To track deduplication by (scheme_name, state)
    unique_schemes = {}
    
    # Stats
    total_files_processed = 0
    source_stats = defaultdict(int)
    state_stats = defaultdict(int)

    # Exclude the output file itself if it exists
    json_files = [f for f in data_dir.glob("*.json") if f.name != "all_schemes_raw.json"]

    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                print(f"Skipping {file_path.name}: not a JSON array.")
                continue

            total_files_processed += 1
            source_name = file_path.name
            
            for item in data:
                # Normalize keys to find name and state
                scheme_name = item.get("scheme_name", item.get("title", ""))
                if not scheme_name and item.get("scheme_id"):
                    scheme_name = item.get("scheme_id")
                    
                # Skip invalid or junk entries
                if not scheme_name or "Example" in str(scheme_name):
                    continue
                    
                # Normalize keys to match tier1_seed.json schema (Phase 2 expectation)
                if "eligibility_criteria" in item:
                    item["eligibility_text"] = item.pop("eligibility_criteria")
                if "benefits_description" in item:
                    item["benefits_text"] = item.pop("benefits_description")
                if "documents_required" in item:
                    item["documents_needed"] = item.pop("documents_required")
                    
                state = item.get("state", item.get("state_or_central", "Unknown State/Central"))
                
                # Combine keys
                dedup_key = (str(scheme_name).lower().strip(), str(state).lower().strip())
                
                if dedup_key not in unique_schemes:
                    # Keep track of source for statistics if useful
                    item["_source_file"] = source_name
                    unique_schemes[dedup_key] = item
                    
                    source_stats[source_name] += 1
                    state_stats[state] += 1
                else:
                    # If it exists, we could merge fields. For now, we just keep the existing or update with new non-empty fields
                    existing_item = unique_schemes[dedup_key]
                    for k, v in item.items():
                        if k not in existing_item or (not existing_item[k] and v):
                            existing_item[k] = v
                            
        except Exception as e:
            print(f"Error processing {file_path.name}: {e}")

    # Write merged data
    merged_data = list(unique_schemes.values())
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, indent=4, ensure_ascii=False)

    # Print Summary
    print("\n" + "="*50)
    print("           DATA COMBINATION SUMMARY")
    print("="*50)
    print(f"Total files processed: {total_files_processed}")
    print(f"Total unique schemes: {len(merged_data)}")
    
    print("\n--- By Source File ---")
    for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source}: {count} schemes")
        
    print("\n--- By State / Type ---")
    for state, count in sorted(state_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {state}: {count} schemes")
    print("="*50 + "\n")
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    main()
