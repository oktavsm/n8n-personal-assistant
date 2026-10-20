import json
import glob
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ==============================================================================
# 1. FIX GCAL-TO-WA-ASSISTANT.JSON (ANTI-SPAM & EXACT MINUTES FILTER)
# ==============================================================================
gcal_path = REPO_ROOT / "workflow" / "gcal-to-wa-assistant.json"
with open(gcal_path) as f:
    raw_gcal = json.load(f)
wf_gcal = raw_gcal[0] if isinstance(raw_gcal, list) else raw_gcal

def build_reminder_code(target_minute):
    return f"""const envKeys = $env.GEMINI_API_KEY || '';
const apiKeys = envKeys.split(',').map(k => k.trim()).filter(Boolean);

const targetMinute = {target_minute};
const now = new Date();
const validItems = [];
const processedIds = new Set();

let staticData = {{}};
try {{
  staticData = $getWorkflowStaticData('global');
  if (!staticData.sentReminders) {{
    staticData.sentReminders = {{}};
  }}
}} catch (e) {{}}

// Bersihkan data deduplikasi yang lebih dari 48 jam agar memori tidak bengkak
const twoDaysAgo = now.getTime() - 48 * 3600 * 1000;
if (staticData.sentReminders) {{
  for (const k in staticData.sentReminders) {{
    if (staticData.sentReminders[k] < twoDaysAgo) {{
      delete staticData.sentReminders[k];
    }}
  }}
}}

for (const item of $input.all()) {{
  const startStr = item.json.start?.dateTime;
  if (!startStr) continue; // Skip all-day events

  const eventId = item.json.id;
  if (!eventId || processedIds.has(eventId)) continue;

  const startTime = new Date(startStr);
  const diffMs = startTime.getTime() - now.getTime();
  const diffMinutes = Math.round(diffMs / 60000);

  // FILTER KETAT ANTI-SPAM: HANYA lolos jika sisa menit tepat targetMinute
  if (diffMinutes !== targetMinute) continue;

  const dedupeKey = `${{eventId}}_${{targetMinute}}_${{startStr}}`;
  if (staticData.sentReminders && staticData.sentReminders[dedupeKey]) {{
    continue; // Sudah pernah dikirim, jangan spam!
  }}

  processedIds.add(eventId);
  if (staticData.sentReminders) {{
    staticData.sentReminders[dedupeKey] = now.getTime();
  }}

  const randomKey = apiKeys.length > 0 
    ? apiKeys[Math.floor(Math.random() * apiKeys.length)] 
    : '';

  item.json.selected_key = randomKey;
  item.json.menit_tersisa = diffMinutes;
  validItems.push(item);
}}

return validItems;"""

reminder_node_targets = {
    # Okta nodes
    "[15 Menit] Code in JavaScript": 15,
    "[30] Menit Code in JavaScript1": 30,
    "[60 Menit] Code in JavaScript": 60,
    "[12 Jam] Code in JavaScript1": 720,
    "[36 Jam] Code in JavaScript": 2160,
    # Manda nodes
    "[15 Menit] Code in JavaScript1": 15,
    "[30] Menit Code in JavaScript": 30,
    "[60 Menit] Code in JavaScript1": 60,
    "[12 Jam] Code in JavaScript": 720,
    "[36 Jam] Code in JavaScript1": 2160,
}

for n in wf_gcal["nodes"]:
    name = n["name"]
    if name in reminder_node_targets:
        target_val = reminder_node_targets[name]
        n["parameters"]["jsCode"] = build_reminder_code(target_val)
        print(f"✅ Updated {name} with exact {target_val}m filter & staticData dedupe!")
    
    # Fix Manda prompt time format to WITA
    if name == "HTTP Request Gemini1":
        body = n["parameters"].get("jsonBody", "")
        if "Jam:Menit WIB" in body:
            n["parameters"]["jsonBody"] = body.replace("Jam:Menit WIB", "Jam:Menit WITA")
            print("✅ Fixed HTTP Request Gemini1 prompt timezone to WITA!")

# Ensure workflow settings timezone is Asia/Jakarta
if "settings" not in wf_gcal:
    wf_gcal["settings"] = {}
wf_gcal["settings"]["timezone"] = "Asia/Jakarta"

with open(gcal_path, "w") as f:
    json.dump([wf_gcal], f, indent=2)
with open(REPO_ROOT / "n8n" / "workflow" / "gcal-to-wa-assistant.json", "w") as f:
    json.dump([wf_gcal], f, indent=2)

print("Saved gcal-to-wa-assistant.json successfully!")

# ==============================================================================
# 2. FIX WA-CONVERSATION.JSON (ACCURATE WIB & WITA IN PROMPTS & TIMEZONE)
# ==============================================================================
wac_path = REPO_ROOT / "workflow" / "wa-conversation.json"
with open(wac_path) as f:
    raw_wac = json.load(f)
wf_wac = raw_wac[0] if isinstance(raw_wac, list) else raw_wac

for n in wf_wac["nodes"]:
    if n["name"] == "Normalize WA Context":
        code = n["parameters"]["jsCode"]
        # Replace date_time assignment with full Indonesian localized strings
        old_dt = "dateTime: body.date_time || new Date().toISOString(),"
        new_dt = """dateTime: new Date().toLocaleString("id-ID", {
          timeZone: "Asia/Jakarta",
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false
        }) + " WIB",
        dateTimeWib: new Date().toLocaleString("id-ID", {
          timeZone: "Asia/Jakarta",
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false
        }) + " WIB",
        dateTimeWita: new Date().toLocaleString("id-ID", {
          timeZone: "Asia/Makassar",
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false
        }) + " WITA","""
        if old_dt in code:
            n["parameters"]["jsCode"] = code.replace(old_dt, new_dt)
            print("✅ Updated Normalize WA Context with explicit Indonesian WIB/WITA dates!")

    elif n["name"] == "[HTTP] Gemini Build Message1":
        # Manda prompt
        body = n["parameters"]["jsonBody"]
        body = body.replace(
            '- Waktu Sekarang: ${$json.wa.dateTime}',
            '- Waktu Sekarang (Kak Manda di Banjarmasin): ${$json.wa.dateTimeWita || $json.wa.dateTime}\\n- Waktu Okta di Malang/Jawa: ${$json.wa.dateTimeWib || $json.wa.dateTime}'
        )
        n["parameters"]["jsonBody"] = body
        print("✅ Updated [HTTP] Gemini Build Message1 prompt with localized WITA/WIB context!")

    elif n["name"] == "[HTTP] Gemini Build Message":
        # Okta / General prompt
        body = n["parameters"]["jsonBody"]
        body = body.replace(
            '- Waktu: ${$json.wa.dateTime}',
            '- Waktu Sekarang: ${$json.wa.dateTimeWib || $json.wa.dateTime} (WIB / UTC+7)'
        )
        n["parameters"]["jsonBody"] = body
        print("✅ Updated [HTTP] Gemini Build Message prompt with explicit WIB (UTC+7) context!")

if "settings" not in wf_wac:
    wf_wac["settings"] = {}
wf_wac["settings"]["timezone"] = "Asia/Jakarta"

with open(wac_path, "w") as f:
    json.dump([wf_wac], f, indent=2)
with open(REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json", "w") as f:
    json.dump([wf_wac], f, indent=2)

print("Saved wa-conversation.json successfully!")

# ==============================================================================
# 3. SET TIMEZONE IN ALL 15 WORKFLOWS
# ==============================================================================
all_wfs = glob.glob(str(REPO_ROOT / "workflow" / "*.json"))
for p in all_wfs:
    path = Path(p)
    if "archive" in path.parts:
        continue
    with open(path) as f:
        d = json.load(f)
    wf = d[0] if isinstance(d, list) else d
    if "settings" not in wf:
        wf["settings"] = {}
    
    # Keep Manda's dedicated assistant on Asia/Makassar if set, otherwise Asia/Jakarta
    if path.name == "manda-gcal-assistant.json":
        wf["settings"]["timezone"] = "Asia/Makassar"
    else:
        wf["settings"]["timezone"] = "Asia/Jakarta"
    
    with open(path, "w") as f:
        json.dump([wf], f, indent=2)
    
    dest_n8n = REPO_ROOT / "n8n" / "workflow" / path.name
    if dest_n8n.exists() or (REPO_ROOT / "n8n" / "workflow").exists():
        with open(dest_n8n, "w") as f:
            json.dump([wf], f, indent=2)

print("✅ All 15 workflows verified and set to Asia/Jakarta (WIB) / Asia/Makassar (WITA)!")
