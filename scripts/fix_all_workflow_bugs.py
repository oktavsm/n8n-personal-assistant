import json
import uuid

# 1. FIX master-router-webhook.json
with open("workflow/master-router-webhook.json") as f:
    raw = json.load(f)
    wf_router = raw[0] if isinstance(raw, list) else raw

# Find the main Switch node
switch_node = None
for n in wf_router["nodes"]:
    if n["type"] == "n8n-nodes-base.switch" and len(n.get("parameters", {}).get("rules", {}).get("values", [])) >= 20:
        switch_node = n
        break

if not switch_node:
    raise Exception("Switch node not found in master-router-webhook.json")

rules = switch_node["parameters"]["rules"]["values"]
print(f"Total rules in Switch: {len(rules)}")

# Fix each rule
for i, r in enumerate(rules):
    # Ensure options have typeValidation = "loose"
    if "options" not in r["conditions"]:
        r["conditions"]["options"] = {}
    r["conditions"]["options"]["typeValidation"] = "loose"
    r["conditions"]["options"]["caseSensitive"] = False
    
    conds = r["conditions"]["conditions"]
    out_key = r.get("outputKey", "")
    
    # Fix rule 13: diaturun
    if out_key == "diaturun" or i == 13:
        conds[0]["leftValue"] = "={{ ($json.body?.data?.message?.conversation || $json.body?.data?.message?.extendedTextMessage?.text || '').toLowerCase().trim() }}"
        conds[0]["rightValue"] = "diaturun"
        conds[0]["operator"] = {"type": "string", "operation": "contains"}
        r["renameOutput"] = True
        r["outputKey"] = "diaturun"
        print(f"Fixed rule {i}: diaturun -> string contains diaturun")

    # Fix rule 14: eze
    elif out_key == "eze" or i == 14:
        conds[0]["leftValue"] = "={{ ($json.body?.data?.message?.conversation || $json.body?.data?.message?.extendedTextMessage?.text || '').toLowerCase().trim() }}"
        conds[0]["rightValue"] = "eze"
        conds[0]["operator"] = {"type": "string", "operation": "contains"}
        r["renameOutput"] = True
        r["outputKey"] = "eze"
        print(f"Fixed rule {i}: eze -> string contains eze")

    # Fix rule 15: kicau
    elif out_key == "kicau" or i == 15:
        conds[0]["leftValue"] = "={{ ($json.body?.data?.message?.conversation || $json.body?.data?.message?.extendedTextMessage?.text || '').toLowerCase().trim() }}"
        conds[0]["rightValue"] = "kicau"
        conds[0]["operator"] = {"type": "string", "operation": "contains"}
        r["renameOutput"] = True
        r["outputKey"] = "kicau"
        print(f"Fixed rule {i}: kicau -> string contains kicau")

    # Fix rule 16: jokowi
    elif out_key == "jokowi" or i == 16:
        conds[0]["leftValue"] = "={{ ($json.body?.data?.message?.conversation || $json.body?.data?.message?.extendedTextMessage?.text || '').toLowerCase().trim() }}"
        conds[0]["rightValue"] = "jokowi"
        conds[0]["operator"] = {"type": "string", "operation": "contains"}
        r["renameOutput"] = True
        r["outputKey"] = "jokowi"
        print(f"Fixed rule {i}: jokowi -> string contains jokowi")

    # Fix rule 19: stiker
    elif out_key == "stiker" or i == 19:
        conds[0]["leftValue"] = "={{ (() => { const text = ($json.body?.data?.message?.conversation || $json.body?.data?.message?.extendedTextMessage?.text || $json.body?.data?.message?.imageMessage?.caption || $json.body?.data?.message?.videoMessage?.caption || '').toLowerCase().trim(); return Boolean(text.startsWith('/stiker') || text.startsWith('/sticker')); })() }}"
        conds[0]["operator"] = {"type": "boolean", "operation": "true", "singleValue": True}
        conds[0]["rightValue"] = ""
        r["renameOutput"] = True
        r["outputKey"] = "stiker"
        print(f"Fixed rule {i}: stiker -> boolean true")

    # Fix rule 20: manda_pc
    elif out_key == "manda_pc" or i == 20:
        conds[0]["leftValue"] = "={{ (() => { const jid = $json.body?.data?.key?.remoteJid || ''; const part = $json.body?.data?.key?.participantAlt || ''; const isGroup = jid.endsWith('@g.us'); const isManda = jid.includes($env.MANDA_WA_NUMBER) || part.includes($env.MANDA_WA_NUMBER); return Boolean(!isGroup && isManda); })() }}"
        conds[0]["operator"] = {"type": "boolean", "operation": "true", "singleValue": True}
        conds[0]["rightValue"] = ""
        r["renameOutput"] = True
        r["outputKey"] = "manda_pc"
        print(f"Fixed rule {i}: manda_pc -> boolean true")

    # Fix rule 21: vps_agent
    elif out_key == "vps_agent" or i == 21:
        conds[0]["leftValue"] = "={{ (() => { const text = ($json.body?.data?.message?.conversation || $json.body?.data?.message?.extendedTextMessage?.text || '').trim(); const lower = text.toLowerCase(); const jid = $json.body?.data?.key?.remoteJid || ''; const part = $json.body?.data?.key?.participant || $json.body?.data?.key?.participantAlt || ''; const isOkta = jid.includes($env.MY_WA_NUMBER) || part.includes($env.MY_WA_NUMBER); return Boolean(isOkta && (lower.startsWith('/vps') || lower.startsWith('/agent'))); })() }}"
        conds[0]["operator"] = {"type": "boolean", "operation": "true", "singleValue": True}
        conds[0]["rightValue"] = ""
        r["renameOutput"] = True
        r["outputKey"] = "vps_agent"
        print(f"Fixed rule {i}: vps_agent -> boolean true")

# Update [Script] Message Builder (/help message)
for n in wf_router["nodes"]:
    if n["name"] == "[Script] Message Builder":
        n["parameters"]["jsCode"] = """const textMsg = `📋 *MENU PERSONAL ASSISTANT*

Halo! Berikut panduan lengkap perintah dan fitur yang tersedia:

📅 *GOOGLE CALENDAR (OKTA & MANDA)*
• */jadwal [keterangan]*
  Buat jadwal atau agenda baru ke Google Calendar.
• */cek*
  Cek agenda jadwal hari ini.
• */besok*
  Cek jadwal untuk besok.
• */agenda*
  Rekap seluruh agenda 7 hari ke depan.

📚 *TUGAS & DEADLINE*
• */tugas*
  Cek daftar deadline tugas kuliah.
• */tugas [keterangan]*
  Catat deadline tugas baru ke kalender.

🎓 *AKADEMIK FILKOM UB*
• */brone*
  Cek tugas dan kuis terbaru dari LMS Brone.
• */uas*
  Cek jadwal UAS perkuliahan.
• */pengumuman*
  Cek rilis pengumuman akademik terbaru dari SIAM UB.
• */presensi*
  Cek status presensi perkuliahan hari ini.
• */presensi hadir | sakit | izin*
  Presensi otomatis status tertentu.

🎨 *STIKER WHATSAPP*
• */stiker* atau */sticker*
  Kirim foto/video pendek/GIF dengan caption ini, atau reply pesan media apa saja untuk membuat stiker WA langsung.

⚡ *VPS AI AGENT (Khusus Dev)*
• */agent [instruksi]* atau */vps [instruksi]*
  Jalankan tugas atau cek server via OpenAI Codex Agent langsung di host VPS.
  _Contoh:_ \`/agent cek uptime VPS dan sisa RAM\`

🤖 *AI CONVERSATION & MEMORI*
• */ask [pertanyaan]*
  Tanya apa saja kepada asisten (dilengkapi memori chat PostgreSQL).
• *@PA [pertanyaan]*
  Tag bot di grup untuk berdiskusi tanpa /ask.
• *Asisten Kak Manda:*
  Di ruang chat Kak Manda, bot bertindak ramah sebagai perwakilan Okta dan bisa meneruskan pesan titipan langsung ke WA Okta.

❓ *BANTUAN*
• */help*
  Menampilkan menu panduan ini.
`;

return { json: { text: textMsg } };
"""
        print("Updated [Script] Message Builder with all new features!")

with open("workflow/master-router-webhook.json", "w") as f:
    json.dump(wf_router, f, indent=2)

with open("n8n/workflow/master-router-webhook.json", "w") as f:
    json.dump(wf_router, f, indent=2)

print("Saved master-router-webhook.json successfully!")

# 2. FIX wa-conversation.json trigger inputSource: "passthrough"
with open("workflow/wa-conversation.json") as f:
    raw = json.load(f)
    wf_wac = raw[0] if isinstance(raw, list) else raw

for n in wf_wac["nodes"]:
    if n["name"] == "wa-msg" or n["type"] == "n8n-nodes-base.executeWorkflowTrigger":
        n["parameters"] = {"inputSource": "passthrough"}
        print("Fixed wa-conversation trigger: inputSource = passthrough")

with open("workflow/wa-conversation.json", "w") as f:
    json.dump(wf_wac, f, indent=2)

with open("n8n/workflow/wa-conversation.json", "w") as f:
    json.dump(wf_wac, f, indent=2)

print("Saved wa-conversation.json successfully!")

# 3. FIX vps-cli-runner.json trigger inputSource: "passthrough"
with open("workflow/vps-cli-runner.json") as f:
    raw = json.load(f)
    wf_vps = raw[0] if isinstance(raw, list) else raw

for n in wf_vps["nodes"]:
    if n["name"] == "vps-trigger" or n["type"] == "n8n-nodes-base.executeWorkflowTrigger":
        n["parameters"] = {"inputSource": "passthrough"}
        print("Fixed vps-cli-runner trigger: inputSource = passthrough")

with open("workflow/vps-cli-runner.json", "w") as f:
    json.dump(wf_vps, f, indent=2)

with open("n8n/workflow/vps-cli-runner.json", "w") as f:
    json.dump(wf_vps, f, indent=2)

print("Saved vps-cli-runner.json successfully!")
