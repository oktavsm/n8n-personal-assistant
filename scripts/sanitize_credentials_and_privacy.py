import re
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

OKTA_NUM = "6285750583867"
MANDA_NUM = "62895605917452"

# 1. Sanitize wa-to-gcal-assistant.json
for folder in ["workflow", "n8n/workflow"]:
    gcal_path = REPO_ROOT / folder / "wa-to-gcal-assistant.json"
    if gcal_path.exists():
        text = gcal_path.read_text(encoding="utf-8")
        text = text.replace(OKTA_NUM, "${$env.MY_WA_NUMBER}")
        gcal_path.write_text(text, encoding="utf-8")
        print(f"✅ Sanitized {folder}/wa-to-gcal-assistant.json")

# 2. Sanitize master-router-webhook.json
for folder in ["workflow", "n8n/workflow"]:
    mr_path = REPO_ROOT / folder / "master-router-webhook.json"
    if mr_path.exists():
        text = mr_path.read_text(encoding="utf-8")
        text = text.replace(f'\\"number\\": \\"{OKTA_NUM}\\"', '\\"number\\": \\"={{ $env.MY_WA_NUMBER }}\\"')
        text = text.replace(f'"number": "{OKTA_NUM}"', '"number": "={{ $env.MY_WA_NUMBER }}"')
        text = text.replace(f"'{OKTA_NUM}'", "$env.MY_WA_NUMBER")
        text = text.replace(f'"{OKTA_NUM}"', "$env.MY_WA_NUMBER")
        mr_path.write_text(text, encoding="utf-8")
        print(f"✅ Sanitized {folder}/master-router-webhook.json")

# 3. Sanitize wa-conversation.json
for folder in ["workflow", "n8n/workflow"]:
    wac_path = REPO_ROOT / folder / "wa-conversation.json"
    if wac_path.exists():
        text = wac_path.read_text(encoding="utf-8")
        text = text.replace(f', "{OKTA_NUM}"', "")
        text = text.replace(f'"{OKTA_NUM}"', "$env.MY_WA_NUMBER")
        text = text.replace(f'"{MANDA_NUM}"', "$env.MANDA_WA_NUMBER")
        text = text.replace(OKTA_NUM, "${$env.MY_WA_NUMBER}")
        text = text.replace(MANDA_NUM, "${$env.MANDA_WA_NUMBER}")
        wac_path.write_text(text, encoding="utf-8")
        print(f"✅ Sanitized {folder}/wa-conversation.json")

print("🔒 Privacy and credential sanitization complete!")
