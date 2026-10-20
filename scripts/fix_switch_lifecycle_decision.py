#!/usr/bin/env python3
"""
Fix Switch Lifecycle Decision in wa-to-gcal-assistant and manda-gcal-assistant:
The node before Switch is [PG] Execute Pending Action Query which returns { success: true }.
Therefore, Switch must evaluate $('Process Safe Calendar Action').first().json.decision
instead of $json.decision!
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def fix_workflow(fp: Path, is_manda: bool):
    if not fp.exists(): return
    with open(fp, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    user_prefix = "Manda " if is_manda else ""
    switch_node_name = f"{user_prefix}Switch Lifecycle Decision"
    process_node_name = f"{user_prefix}Process Safe Calendar Action"

    for n in data.get("nodes", []):
        if n.get("name") == switch_node_name:
            rules = n.get("parameters", {}).get("rules", {}).get("values", [])
            for r in rules:
                for c in r.get("conditions", {}).get("conditions", []):
                    c["leftValue"] = f"={{{{ $('{process_node_name}').first().json.decision }}}}"
            print(f"[{fp.name}] Fixed leftValue in {switch_node_name} to reference {process_node_name}")

    with open(fp, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Saved {fp.name}")

fix_workflow(REPO_ROOT / "workflow" / "wa-to-gcal-assistant.json", is_manda=False)
fix_workflow(REPO_ROOT / "n8n" / "workflow" / "wa-to-gcal-assistant.json", is_manda=False)
fix_workflow(REPO_ROOT / "workflow" / "manda-gcal-assistant.json", is_manda=True)
fix_workflow(REPO_ROOT / "n8n" / "workflow" / "manda-gcal-assistant.json", is_manda=True)

print("\n🚀 Ready for deployment!")
