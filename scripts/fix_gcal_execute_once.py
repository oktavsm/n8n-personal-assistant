#!/usr/bin/env python3
"""
Add executeOnce: true to all chained Google Calendar and data processing nodes
to eliminate item multiplication (Cartesian product loop) in:
- wa-to-gcal-assistant.json
- manda-gcal-assistant.json
- wa-conversation.json
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 1. Update wa-to-gcal-assistant.json & manda-gcal-assistant.json
def update_assistant(fp: Path, is_manda: bool):
    if not fp.exists(): return
    with open(fp, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    user_prefix = "Manda " if is_manda else ""
    target_nodes = {
        f"{user_prefix}Fetch GCal Agenda For Match",
        f"{user_prefix}Fetch GCal Tugas For Match",
        f"{user_prefix}Fetch GCal Kuliah For Match",
        f"{user_prefix}Process Safe Calendar Action",
        f"[PG] {user_prefix}Execute Pending Action Query"
    }

    for n in data.get("nodes", []):
        if n.get("name") in target_nodes:
            n["executeOnce"] = True
            # Adjust time window to -14d to +60d for optimal speed
            if "GCal" in n.get("name", "") and "parameters" in n:
                tz = "Asia/Makassar" if is_manda else "Asia/Jakarta"
                n["parameters"]["timeMin"] = f"={{{{ $now.setZone('{tz}').minus({{days: 14}}).startOf('day').toISO() }}}}"
                n["parameters"]["timeMax"] = f"={{{{ $now.setZone('{tz}').plus({{days: 60}}).endOf('day').toISO() }}}}"
            print(f"[{fp.name}] Set executeOnce: true on {n['name']}")

    with open(fp, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Saved {fp.name}")

# 2. Update wa-conversation.json
def update_conversation(fp: Path):
    if not fp.exists(): return
    with open(fp, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    target_nodes = {
        "Get GCal Okta Agenda",
        "Get GCal Okta Tugas",
        "Get GCal Okta Kuliah",
        "Get GCal Manda Agenda",
        "Get GCal Manda Tugas",
        "Get GCal Manda Kuliah",
        "Format Calendar Vision"
    }

    for n in data.get("nodes", []):
        if n.get("name") in target_nodes:
            n["executeOnce"] = True
            print(f"[{fp.name}] Set executeOnce: true on {n['name']}")

    with open(fp, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Saved {fp.name}")

# Apply to all files
update_assistant(REPO_ROOT / "workflow" / "wa-to-gcal-assistant.json", is_manda=False)
update_assistant(REPO_ROOT / "n8n" / "workflow" / "wa-to-gcal-assistant.json", is_manda=False)

update_assistant(REPO_ROOT / "workflow" / "manda-gcal-assistant.json", is_manda=True)
update_assistant(REPO_ROOT / "n8n" / "workflow" / "manda-gcal-assistant.json", is_manda=True)

update_conversation(REPO_ROOT / "workflow" / "wa-conversation.json")
update_conversation(REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json")

print("\n🚀 All workflows updated with executeOnce: true!")
