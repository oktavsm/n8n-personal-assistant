import json
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
wac_path = REPO_ROOT / "workflow" / "wa-conversation.json"
dest_n8n_path = REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json"

with open(wac_path) as f:
    raw = json.load(f)

wf = raw[0] if isinstance(raw, list) else raw

# ==============================================================================
# 1. UPDATE GEMINI PROMPTS (INSTRUCT MODEL TO EMIT <<<ACTION:...>>> TAGS)
# ==============================================================================

ACTION_INSTRUCTION_OKTA = """
==================================================
FITUR AKSI OTOMATIS: PEMBUATAN TUGAS & AGENDA (ACTION TRIGGER)
==================================================
Perhatikan baik-baik: Jika pengguna (Okta atau Kak Manda) meminta kamu untuk MEMBUAT, MENCATAT, MENAMBAH, atau MENJADWALKAN tugas, deadline, agenda, jadwal, rapat, atau kegiatan:
- Termasuk jika permintaan merujuk ke obrolan sebelumnya! (Contoh: "buatin tugas yang aku sebut tadi deadlinenya lusa jam 23.59", "jadiin task lusa jam 23.59 dua duanya", "catat agenda yang tadi dibahas besok jam 10 pagi").
- Analisis riwayat percakapan sebelumnya untuk menemukan judul kegiatan/tugas yang dimaksud secara spesifik!

ATURAN OUTPUT ACTION:
1. Berikan respon ramah dan konfirmasi singkat bahwa tugas/agenda tersebut langsung diproses ke kalender.
2. DI BARIS PALING AKHIR responmu, WAJIB sertakan SATU ATAU LEBIH baris perintah aksi dengan format persis:
<<<ACTION:TUGAS|TARGET|DETAIL>>>
atau
<<<ACTION:JADWAL|TARGET|DETAIL>>>

Penjelasan Parameter:
- TUGAS: untuk deadline tugas kuliah, PR, project, laporan, submit paper, dsb.
- JADWAL: untuk agenda kegiatan, meeting, rapat, acara, janji temu, dsb.
- TARGET:
  * "okta" -> jika kalender tujuan adalah kalender Okta (default jika pengirim adalah Okta, atau jika diminta buat Okta).
  * "manda" -> jika kalender tujuan adalah kalender Kak Manda (jika pengirim adalah Kak Manda, atau jika diminta buat Manda).
- DETAIL: Tuliskan nama/judul kegiatan secara lengkap beserta waktu dan tanggal spesifik yang sudah kamu hitung berdasarkan waktu sekarang (misal: "PPT Pengabdian deadline Kamis 22 Oktober 2026 jam 23.59" atau "Meeting Project Kerjago besok jam 14.00"). Jika pengguna tidak menyebut kata jam, selalu cantumkan kata "jam HH.MM" (default tugas adalah jam 23.59, default jadwal agenda adalah jam 09.00).

CONTOH MULTI-ACTION (PENTING):
Jika pengguna bilang: "jadiin task aja deadlinenya lusa 23.59 dua duanya" dan di riwayat obrolan ada "PPT Pengabdian" dan "PPT Scope":
Maka responmu harus menyertakan DUA baris aksi di paling akhir:
<<<ACTION:TUGAS|okta|PPT Pengabdian deadline Kamis 22 Oktober 2026 jam 23.59>>>
<<<ACTION:TUGAS|okta|PPT Scope deadline Kamis 22 Oktober 2026 jam 23.59>>>

CATATAN:
- JANGAN sertakan tag ACTION jika pengguna HANYA MENANYAKAN atau MENGECEK jadwal/tugas (misal: "ada tugas apa?", "cek jadwal besok"). Tag ACTION HANYA untuk permintaan PEMBUATAN/PENCATATAN baru.
"""

ACTION_INSTRUCTION_MANDA = """
==================================================
FITUR AKSI OTOMATIS: PEMBUATAN TUGAS & AGENDA (ACTION TRIGGER)
==================================================
Jika Kak Manda meminta kamu untuk MEMBUAT, MENCATAT, MENAMBAH, atau MENJADWALKAN tugas, deadline, agenda, jadwal, rapat, atau kegiatan:
- Termasuk jika merujuk ke obrolan sebelumnya! (Contoh: "buatin tugas yang tadi disebut deadlinenya lusa jam 23.59", "jadiin task ya").
- Analisis riwayat percakapan sebelumnya untuk menemukan judul kegiatan/tugas secara spesifik!

ATURAN OUTPUT ACTION:
1. Berikan respon ramah dan manis bahwa tugas/agenda tersebut langsung diproses ke kalender.
2. DI BARIS PALING AKHIR responmu, WAJIB sertakan SATU ATAU LEBIH baris perintah aksi dengan format persis:
<<<ACTION:TUGAS|TARGET|DETAIL>>>
atau
<<<ACTION:JADWAL|TARGET|DETAIL>>>

Penjelasan Parameter:
- TUGAS: untuk deadline tugas kuliah farmasi, PR, laporan praktikum, dsb.
- JADWAL: untuk agenda kegiatan, meeting, acara, janji temu, dsb.
- TARGET:
  * "manda" -> default kalender Kak Manda.
  * "okta" -> jika Kak Manda minta membuatkan jadwal/tugas untuk Okta.
- DETAIL: Tuliskan nama/judul kegiatan secara lengkap beserta waktu dan tanggal spesifik yang sudah kamu hitung (misal: "Laporan Farmasi deadline Kamis 22 Oktober 2026 jam 23.59 WITA"). Jika tidak menyebut jam, gunakan jam default "jam 23.59" untuk tugas dan "jam 09.00" untuk jadwal.

CATATAN:
- JANGAN sertakan tag ACTION jika hanya mengecek jadwal/tugas. Tag ACTION HANYA untuk PEMBUATAN baru.
"""

for n in wf["nodes"]:
    if n["name"] == "[HTTP] Gemini Build Message":
        body = n["parameters"]["jsonBody"]
        if "FITUR AKSI OTOMATIS: PEMBUATAN TUGAS" not in body:
            # Insert before "Jawablah dengan ringkas dan solutif:"
            marker = "Jawablah dengan ringkas dan solutif:"
            if marker in body:
                n["parameters"]["jsonBody"] = body.replace(marker, f"{ACTION_INSTRUCTION_OKTA}\n\n{marker}")
                print("✅ Added ACTION instructions to [HTTP] Gemini Build Message!")
            else:
                n["parameters"]["jsonBody"] = body + f"\n\n{ACTION_INSTRUCTION_OKTA}"
                print("✅ Appended ACTION instructions to [HTTP] Gemini Build Message!")

    elif n["name"] == "[HTTP] Gemini Build Message1":
        body = n["parameters"]["jsonBody"]
        if "FITUR AKSI OTOMATIS: PEMBUATAN TUGAS" not in body:
            marker = "Jawablah pesan Kak Manda dengan ramah"
            if marker in body:
                n["parameters"]["jsonBody"] = body.replace(marker, f"{ACTION_INSTRUCTION_MANDA}\n\n{marker}")
                print("✅ Added ACTION instructions to [HTTP] Gemini Build Message1!")
            else:
                n["parameters"]["jsonBody"] = body + f"\n\n{ACTION_INSTRUCTION_MANDA}"
                print("✅ Appended ACTION instructions to [HTTP] Gemini Build Message1!")

    elif n["name"] == "[HTTP Whatsapp] Send Message1":
        # Ensure text uses cleanText
        n["parameters"]["bodyParameters"]["parameters"][1]["value"] = "={{ $json.cleanText || $json.candidates?.[0]?.content?.parts?.[0]?.text || 'Siap, pesan sudah diterima.' }}"
        print("✅ Updated Send Message1 to use cleanText!")

    elif n["name"] == "[HTTP Whatsapp] Send Message2":
        # Ensure text uses cleanText
        n["parameters"]["bodyParameters"]["parameters"][1]["value"] = "={{ $json.cleanText || $json.candidates?.[0]?.content?.parts?.[0]?.text || 'Halo kak Manda, pesan sudah aku terima yaa!' }}"
        print("✅ Updated Send Message2 to use cleanText!")

    elif n["name"] == "[PG] Save Bot Reply":
        # Ensure cleanText is recorded in memory
        new_save_query = """INSERT INTO wa_chat_memory (room_jid, sender_jid, sender_name, role, message_type, content)
VALUES (
  '{{ $('Normalize WA Context').item.json.wa.remoteJid }}',
  'bot',
  'Asisten Okta',
  'assistant',
  'text',
  '{{ (() => {
    let text = "";
    try { text = $('Process AI Output & Actions1').item.json.cleanText; } catch(e){}
    if (!text) {
      try { text = $('Process AI Output & Actions').item.json.cleanText; } catch(e){}
    }
    if (!text) {
      try { text = $('[HTTP] Gemini Build Message1').item.json.candidates[0].content.parts[0].text; } catch(e){}
    }
    if (!text) {
      try { text = $('[HTTP] Gemini Build Message').item.json.candidates[0].content.parts[0].text; } catch(e){}
    }
    if (!text && $json.message) {
      const m = $json.message;
      text = typeof m === "string" ? m : (m.conversation || m.extendedTextMessage?.text || "");
    }
    return (text || "Pesan terkirim").replace(/'/g, "''");
  })() }}'
);"""
        n["parameters"]["query"] = new_save_query
        print("✅ Updated [PG] Save Bot Reply to save cleanText!")

# ==============================================================================
# 2. ADD ACTION PROCESSING NODES & CONNECTIONS
# ==============================================================================

NODE_PROCESS_ACTIONS_CODE = """const geminiRaw = $input.first().json;
let rawText = "";
try {
  rawText = geminiRaw.candidates[0].content.parts[0].text || "";
} catch (e) {}

// Regex for action tags: <<<ACTION:(TUGAS|JADWAL)\\|(okta|manda)\\|(.*?)>>>
const actionRegex = /<<<ACTION:(TUGAS|JADWAL)\\|(okta|manda)\\|(.*?)>>>/gi;
const actions = [];
let match;

while ((match = actionRegex.exec(rawText)) !== null) {
  const actionType = match[1].toLowerCase();
  const target = match[2].toLowerCase();
  const detail = match[3].trim();
  
  const cmd = actionType === 'tugas' ? '/tugas' : '/jadwal';
  const commandText = target === 'manda'
    ? `${cmd} manda ${detail}`
    : `${cmd} ${detail}`;

  actions.push({
    actionType,
    target,
    detail,
    commandText
  });
}

// Clean user response by removing action tags
const cleanText = rawText.replace(/<<<ACTION:(TUGAS|JADWAL)\\|(okta|manda)\\|(.*?)>>>/gi, '').trim();

let waData = {};
try {
  waData = $('Normalize WA Context').item.json.wa || {};
} catch (e) {}

return [{
  json: {
    cleanText,
    hasActions: actions.length > 0,
    actions,
    wa: waData,
    candidates: [
      {
        content: {
          parts: [
            { text: cleanText }
          ]
        }
      }
    ]
  }
}];"""

NODE_PREPARE_PAYLOADS_CODE = """const parent = $input.first().json;
const wa = parent.wa || {};
const actions = parent.actions || [];

if (!actions || actions.length === 0) {
  return [];
}

const items = [];
const defaultOktaNumber = $env.MY_WA_NUMBER || "628XXXXXXXXXX";
const defaultMandaNumber = $env.MANDA_WA_NUMBER || "628YYYYYYYYYY";

for (const act of actions) {
  const isMandaTarget = act.target === 'manda';
  const senderNumber = isMandaTarget ? defaultMandaNumber : defaultOktaNumber;
  const remoteJid = wa.remoteJid || `${senderNumber}@s.whatsapp.net`;

  items.push({
    json: {
      target: act.target,
      actionType: act.actionType,
      detail: act.detail,
      commandText: act.commandText,
      body: {
        data: {
          key: {
            remoteJid: remoteJid,
            participant: `${senderNumber}@s.whatsapp.net`,
            participantAlt: `${senderNumber}@s.whatsapp.net`
          },
          message: {
            conversation: act.commandText
          }
        }
      }
    }
  });
}

return items;"""

node_process_okta = {
    "parameters": {
        "jsCode": NODE_PROCESS_ACTIONS_CODE
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [1080, -20],
    "id": "code-proc-actions-okta",
    "name": "Process AI Output & Actions"
}

node_process_manda = {
    "parameters": {
        "jsCode": NODE_PROCESS_ACTIONS_CODE
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [1080, -220],
    "id": "code-proc-actions-manda",
    "name": "Process AI Output & Actions1"
}

node_if_actions = {
    "parameters": {
        "conditions": {
            "options": {
                "caseSensitive": True,
                "leftValue": "",
                "typeValidation": "strict",
                "version": 3
            },
            "conditions": [
                {
                    "id": "action-cond-01",
                    "leftValue": "={{ $json.hasActions }}",
                    "rightValue": "",
                    "operator": {
                        "type": "boolean",
                        "operation": "true",
                        "singleValue": True
                    }
                }
            ],
            "combinator": "and"
        }
    },
    "type": "n8n-nodes-base.if",
    "typeVersion": 2.2,
    "position": [1340, -100],
    "id": "if-has-cal-actions",
    "name": "If Has Calendar Actions"
}

node_prepare_payloads = {
    "parameters": {
        "jsCode": NODE_PREPARE_PAYLOADS_CODE
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [1540, -100],
    "id": "code-prep-cal-payloads",
    "name": "Prepare Calendar Payloads"
}

node_switch_target = {
    "parameters": {
        "rules": {
            "values": [
                {
                    "conditions": {
                        "options": {
                            "caseSensitive": False,
                            "leftValue": "",
                            "typeValidation": "loose",
                            "version": 3
                        },
                        "conditions": [
                            {
                                "id": "target-okta-cond",
                                "leftValue": "={{ $json.target }}",
                                "rightValue": "okta",
                                "operator": {
                                    "type": "string",
                                    "operation": "equals"
                                }
                            }
                        ],
                        "combinator": "and"
                    },
                    "renameOutput": True,
                    "outputKey": "okta"
                },
                {
                    "conditions": {
                        "options": {
                            "caseSensitive": False,
                            "leftValue": "",
                            "typeValidation": "loose",
                            "version": 3
                        },
                        "conditions": [
                            {
                                "id": "target-manda-cond",
                                "leftValue": "={{ $json.target }}",
                                "rightValue": "manda",
                                "operator": {
                                    "type": "string",
                                    "operation": "equals"
                                }
                            }
                        ],
                        "combinator": "and"
                    },
                    "renameOutput": True,
                    "outputKey": "manda"
                }
            ]
        },
        "options": {}
    },
    "type": "n8n-nodes-base.switch",
    "typeVersion": 3.4,
    "position": [1740, -100],
    "id": "switch-cal-target",
    "name": "Switch Target Calendar"
}

node_call_okta_gcal = {
    "parameters": {
        "workflowId": {
            "__rl": True,
            "value": "U43zT3sJktIA9LaL",
            "mode": "list",
            "cachedResultUrl": "/n8n/workflow/U43zT3sJktIA9LaL",
            "cachedResultName": "wa-to-gcal-assistant"
        },
        "mode": "each",
        "workflowInputs": {
            "mappingMode": "defineBelow",
            "value": {},
            "matchingColumns": [],
            "schema": [],
            "attemptToConvertTypes": False,
            "convertFieldsToString": True
        },
        "options": {
            "waitForSubWorkflow": True
        }
    },
    "type": "n8n-nodes-base.executeWorkflow",
    "typeVersion": 1.3,
    "position": [1980, -180],
    "id": "call-okta-gcal-subwf",
    "name": "Call 'wa-to-gcal-assistant'"
}

node_call_manda_gcal = {
    "parameters": {
        "workflowId": {
            "__rl": True,
            "value": "TcoP1qZ8e4dvKU9F",
            "mode": "list",
            "cachedResultUrl": "/n8n/workflow/TcoP1qZ8e4dvKU9F",
            "cachedResultName": "manda-gcal-assistant"
        },
        "mode": "each",
        "workflowInputs": {
            "mappingMode": "defineBelow",
            "value": {},
            "matchingColumns": [],
            "schema": [],
            "attemptToConvertTypes": False,
            "convertFieldsToString": True
        },
        "options": {
            "waitForSubWorkflow": True
        }
    },
    "type": "n8n-nodes-base.executeWorkflow",
    "typeVersion": 1.3,
    "position": [1980, -20],
    "id": "call-manda-gcal-subwf",
    "name": "Call 'manda-to-gcal-assistant'"
}

# Remove if already exists (for idempotent re-run)
new_nodes = [
    node_process_okta,
    node_process_manda,
    node_if_actions,
    node_prepare_payloads,
    node_switch_target,
    node_call_okta_gcal,
    node_call_manda_gcal
]
new_names = {n["name"] for n in new_nodes}
wf["nodes"] = [n for n in wf["nodes"] if n["name"] not in new_names]
wf["nodes"].extend(new_nodes)

# Shift Send Message nodes slightly to the right to look nice
for n in wf["nodes"]:
    if n["name"] == "[HTTP Whatsapp] Send Message1":
        n["position"] = [1300, 80]
    elif n["name"] == "[HTTP Whatsapp] Send Message2":
        n["position"] = [1300, -320]

# Update connections:
conns = wf.get("connections", {})

# 1. [HTTP] Gemini Build Message -> Process AI Output & Actions
conns["[HTTP] Gemini Build Message"] = {
    "main": [
        [
            {
                "node": "Process AI Output & Actions",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

# 2. [HTTP] Gemini Build Message1 -> Process AI Output & Actions1
conns["[HTTP] Gemini Build Message1"] = {
    "main": [
        [
            {
                "node": "Process AI Output & Actions1",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

# 3. Process AI Output & Actions -> [HTTP Whatsapp] Send Message1 & If Has Calendar Actions
conns["Process AI Output & Actions"] = {
    "main": [
        [
            {
                "node": "[HTTP Whatsapp] Send Message1",
                "type": "main",
                "index": 0
            },
            {
                "node": "If Has Calendar Actions",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

# 4. Process AI Output & Actions1 -> [HTTP Whatsapp] Send Message2 & If Has Calendar Actions
conns["Process AI Output & Actions1"] = {
    "main": [
        [
            {
                "node": "[HTTP Whatsapp] Send Message2",
                "type": "main",
                "index": 0
            },
            {
                "node": "If Has Calendar Actions",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

# 5. If Has Calendar Actions -> Prepare Calendar Payloads (Output 0 / true)
conns["If Has Calendar Actions"] = {
    "main": [
        [
            {
                "node": "Prepare Calendar Payloads",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

# 6. Prepare Calendar Payloads -> Switch Target Calendar
conns["Prepare Calendar Payloads"] = {
    "main": [
        [
            {
                "node": "Switch Target Calendar",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

# 7. Switch Target Calendar -> Output 0 (okta), Output 1 (manda)
conns["Switch Target Calendar"] = {
    "main": [
        [
            {
                "node": "Call 'wa-to-gcal-assistant'",
                "type": "main",
                "index": 0
            }
        ],
        [
            {
                "node": "Call 'manda-to-gcal-assistant'",
                "type": "main",
                "index": 0
            }
        ]
    ]
}

# 8. Call 'wa-to-gcal-assistant' and Call 'manda-to-gcal-assistant' have no downstream
conns["Call 'wa-to-gcal-assistant'"] = {"main": [[]]}
conns["Call 'manda-to-gcal-assistant'"] = {"main": [[]]}

wf["connections"] = conns

# Save locally
with open(wac_path, "w") as f:
    json.dump([wf], f, indent=2)

with open(dest_n8n_path, "w") as f:
    json.dump([wf], f, indent=2)

print(f"🎉 Successfully updated {wac_path.name} with Action Calling & Subworkflow Triggering!")
print(f"Total nodes now: {len(wf['nodes'])}")
