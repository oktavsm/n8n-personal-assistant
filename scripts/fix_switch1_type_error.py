#!/usr/bin/env python3
import json
from pathlib import Path

files_to_fix = [
    "workflow/wa-to-gcal-assistant.json",
    "n8n/workflow/wa-to-gcal-assistant.json",
    "workflow/manda-gcal-assistant.json",
    "n8n/workflow/manda-gcal-assistant.json"
]

for file_path in files_to_fix:
    path = Path(file_path)
    if not path.exists():
        print(f"Skipping {file_path} (not found)")
        continue

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_obj = data[0] if isinstance(data, list) else data

    fixed_count = 0
    for node in target_obj.get("nodes", []):
        if node.get("name") == "Switch1" and node.get("type") == "n8n-nodes-base.switch":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            for r in rules:
                conds = r.get("conditions", {}).get("conditions", [])
                for c in conds:
                    if c.get("id") == "ef35be2c-1706-473d-a6de-852a0bbf94eb":
                        # Fix operator from string contains to boolean true
                        c["rightValue"] = ""
                        c["operator"] = {
                            "type": "boolean",
                            "operation": "true",
                            "singleValue": True
                        }
                        fixed_count += 1
                        print(f"Fixed Switch1 condition in {file_path}")

    if fixed_count > 0:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully wrote updates to {file_path}")
    else:
        print(f"⚠️ No condition found to fix in {file_path}")
