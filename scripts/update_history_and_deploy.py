import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

wac_path = REPO_ROOT / "workflow" / "wa-conversation.json"
dest_n8n_path = REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json"

with open(wac_path) as f:
    raw = json.load(f)

wf = raw[0] if isinstance(raw, list) else raw

new_query = """SELECT role, sender_name, content, message_type, created_at 
FROM wa_chat_memory 
WHERE room_jid = '{{ $('Normalize WA Context').item.json.wa.remoteJid }}'
  AND created_at >= NOW() - INTERVAL '14 days'
ORDER BY created_at DESC 
LIMIT 40;"""

new_format_code = """const items = $input.all();
let historyLines = [];

for (const item of items) {
  const row = item.json;
  if (!row || !row.role || !row.content) continue;
  
  const roleLabel = row.role === 'assistant' ? 'Asisten (Bot)' : (row.sender_name || 'User');
  
  const msgDate = new Date(row.created_at);
  const nowDate = new Date();
  const isToday = msgDate.toLocaleDateString('id-ID', { timeZone: 'Asia/Jakarta' }) === nowDate.toLocaleDateString('id-ID', { timeZone: 'Asia/Jakarta' });
  
  const timeStr = isToday
    ? msgDate.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta' })
    : msgDate.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta' });
    
  const timeTag = timeStr ? ` [${timeStr}]` : '';
  historyLines.push(`- ${roleLabel}${timeTag}: ${row.content}`);
}

// URUTAN KRONOLOGIS: Dari pesan lama ke pesan terbaru
historyLines.reverse();

const memoryContext = historyLines.length > 0 
  ? historyLines.join('\\n')
  : '(Tidak ada percakapan sebelumnya dalam 14 hari terakhir)';

const prevItem = $('Normalize WA Context').item.json;

return [{
  json: {
    ...prevItem,
    memoryContext: memoryContext
  }
}];"""

updated_fetch = False
updated_format = False

for n in wf["nodes"]:
    if n["name"] == "[PG] Fetch History":
        n["parameters"]["query"] = new_query
        updated_fetch = True
        print("✅ Updated [PG] Fetch History: INTERVAL '14 days', LIMIT 40")
    elif n["name"] == "Format Memory Context":
        n["parameters"]["jsCode"] = new_format_code
        updated_format = True
        print("✅ Updated Format Memory Context: Chronological reverse() & Smart Date Formatting")

if not (updated_fetch and updated_format):
    print("❌ Failed to find both nodes in workflow JSON!")
    sys.exit(1)

# Save workflow locally
with open(wac_path, "w") as f:
    json.dump([wf], f, indent=2)

with open(dest_n8n_path, "w") as f:
    json.dump([wf], f, indent=2)

print("💾 Saved wa-conversation.json locally.")

# Deploy to remote n8n
host = "pg-bcc"
container = "notifier_n8n"
remote_tmp = "/tmp/wa-conversation.json"
container_tmp = "/tmp/wa-conversation.json"

print(f"🚀 Deploying wa-conversation.json to {host}...")
res = subprocess.run(["scp", str(wac_path), f"{host}:{remote_tmp}"], capture_output=True, text=True)
if res.returncode != 0:
    print(f"❌ SCP failed: {res.stderr}")
    sys.exit(1)

cp_cmd = f"docker cp {remote_tmp} {container}:{container_tmp}"
res = subprocess.run(["ssh", host, cp_cmd], capture_output=True, text=True)
if res.returncode != 0:
    print(f"❌ Docker cp failed: {res.stderr}")
    sys.exit(1)

import_cmd = f"docker exec {container} n8n import:workflow --input={container_tmp}"
res = subprocess.run(["ssh", host, import_cmd], capture_output=True, text=True)
if res.returncode != 0:
    print(f"❌ n8n import failed: {res.stderr}")
    sys.exit(1)
print(f"  {res.stdout.strip()}")

wf_id = wf.get("id")
if wf_id:
    act_cmd = f"docker exec {container} n8n publish:workflow --id={wf_id} || docker exec {container} n8n update:workflow --id={wf_id} --active=true"
    res = subprocess.run(["ssh", host, act_cmd], capture_output=True, text=True)
    print(f"  Published/Activated: {wf_id}")

print("🎉 wa-conversation deployed successfully!")
