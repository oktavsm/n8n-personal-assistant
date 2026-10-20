#!/usr/bin/env python3
"""
Sync n8n Workflows from Remote VPS to Local Repository
Author: Assistant & Okta
Usage:
    ./scripts/sync-workflows.sh
    or
    python3 scripts/sync-workflows.py [--host pg-bcc] [--container notifier_n8n]
"""

import os
import sys
import json
import re
import argparse
import subprocess
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DIR_WORKFLOW = REPO_ROOT / "workflow"
DIR_N8N_WORKFLOW = REPO_ROOT / "n8n" / "workflow"

# Patterns to alert if leaked
LEAK_PATTERNS = {
    "Gemini API Key": re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"),
    "Hardcoded Password": re.compile(r"Rahasiawoy\d*!"),
}

def sanitize_filename(name: str) -> str:
    # Remove characters invalid in filenames
    clean = re.sub(r'[\/\\:\*\?"<>\|]', '_', name.strip())
    # Replace whitespace sequences with hyphen
    clean = re.sub(r'\s+', '-', clean).lower()
    return f"{clean}.json"

def run_ssh(host: str, cmd: str) -> str:
    res = subprocess.run(["ssh", host, cmd], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"SSH command failed ({res.returncode}): {res.stderr.strip()}")
    return res.stdout

def main():
    parser = argparse.ArgumentParser(description="Sync n8n workflows from VPS to local repo")
    parser.add_argument("--host", default=os.getenv("SSH_HOST", "pg-bcc"), help="SSH Host alias or address (default: pg-bcc)")
    parser.add_argument("--container", default=os.getenv("N8N_CONTAINER", "notifier_n8n"), help="Docker container name (default: notifier_n8n)")
    args = parser.parse_args()

    print(f"🚀 Connecting to {args.host} (Container: {args.container})...")
    
    # 1. List workflows
    list_output = run_ssh(args.host, f"docker exec {args.container} n8n list:workflow")
    lines = [l.strip() for l in list_output.splitlines() if "|" in l]
    
    if not lines:
        print("⚠️ No workflows found or unexpected output format.")
        sys.exit(1)

    print(f"📦 Found {len(lines)} workflows on remote n8n.")

    DIR_WORKFLOW.mkdir(parents=True, exist_ok=True)
    DIR_N8N_WORKFLOW.mkdir(parents=True, exist_ok=True)

    synced_count = 0
    warnings = []

    for line in lines:
        w_id, w_name = line.split("|", 1)
        w_name = w_name.strip()
        print(f"  📥 Exporting: {w_name} ({w_id})...", end="", flush=True)

        try:
            exp_out = run_ssh(args.host, f"docker exec {args.container} n8n export:workflow --id={w_id} --stdout")
            idx = exp_out.find("[")
            if idx == -1:
                print(" ❌ Failed to find valid JSON")
                continue

            wf_data = json.loads(exp_out[idx:])
            # Pretty json formatting
            wf_json_str = json.dumps(wf_data, indent=2, ensure_ascii=False) + "\n"

            # Check for leaked secrets
            for leak_name, pattern in LEAK_PATTERNS.items():
                if pattern.search(wf_json_str):
                    warnings.append(f"⚠️ WARNING: Possible {leak_name} found in '{w_name}' ({w_id})")

            # Determine file names
            fname = sanitize_filename(w_name)
            
            # Save to both workflow/ and n8n/workflow/
            (DIR_WORKFLOW / fname).write_text(wf_json_str, encoding="utf-8")
            (DIR_N8N_WORKFLOW / fname).write_text(wf_json_str, encoding="utf-8")

            print(f" ✅ Saved -> {fname}")
            synced_count += 1
        except Exception as e:
            print(f" ❌ Error: {e}")

    print("\n" + "="*50)
    print(f"🎉 Successfully synced {synced_count}/{len(lines)} workflows to local repository!")
    print(f"📁 Destination 1: {DIR_WORKFLOW}")
    print(f"📁 Destination 2: {DIR_N8N_WORKFLOW}")
    
    if warnings:
        print("\n⚠️ SECURITY AUDIT WARNINGS:")
        for w in warnings:
            print(f"  {w}")
    else:
        print("🔒 Security check passed: No raw API keys or passwords detected in exported workflows!")
    print("="*50)

if __name__ == "__main__":
    main()
