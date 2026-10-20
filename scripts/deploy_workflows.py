#!/usr/bin/env python3
import subprocess
import sys
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

workflows_to_deploy = [
    "workflow/master-router-webhook.json",
    "workflow/vps-cli-runner.json",
    "workflow/wa-conversation.json",
    "workflow/morning-audio-briefing.json",
    "workflow/wa-to-gcal-assistant.json",
    "workflow/manda-gcal-assistant.json"
]

host = "pg-bcc"
container = "notifier_n8n"

for wf in workflows_to_deploy:
    local_path = REPO_ROOT / wf
    remote_tmp = f"/tmp/{local_path.name}"
    container_tmp = f"/tmp/{local_path.name}"
    
    print(f"🚀 Deploying {local_path.name} to {host}...")
    
    # 1. SCP to remote host
    res = subprocess.run(["scp", str(local_path), f"{host}:{remote_tmp}"], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ SCP failed: {res.stderr}")
        sys.exit(1)
        
    # 2. Docker cp to container
    cp_cmd = f"docker cp {remote_tmp} {container}:{container_tmp}"
    res = subprocess.run(["ssh", host, cp_cmd], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Docker cp failed: {res.stderr}")
        sys.exit(1)
        
    # 3. Import workflow in n8n
    import_cmd = f"docker exec {container} n8n import:workflow --input={container_tmp}"
    res = subprocess.run(["ssh", host, import_cmd], capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ n8n import failed: {res.stderr}")
        sys.exit(1)
    print(f"  {res.stdout.strip()}")
    
    # 4. Activate workflow
    with open(local_path) as f:
        data = json.load(f)
        wf_id = (data[0] if isinstance(data, list) else data).get("id")
    
    if wf_id:
        act_cmd = f"docker exec {container} n8n publish:workflow --id={wf_id} || docker exec {container} n8n update:workflow --id={wf_id} --active=true"
        res = subprocess.run(["ssh", host, act_cmd], capture_output=True, text=True)
        print(f"  Published/Activated: {wf_id}")

print("🔄 Restarting notifier_n8n to reload all active webhooks & crons...")
subprocess.run(["ssh", host, f"docker restart {container}"], check=True)

print("🎉 All workflows deployed, published, and n8n reloaded successfully!")
