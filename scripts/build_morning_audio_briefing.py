import json

wf = {
  "name": "morning-audio-briefing",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "cronExpression",
              "expression": "0 7 * * *"
            }
          ]
        }
      },
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1.2,
      "position": [
        -600,
        200
      ],
      "id": "morningSchedule01",
      "name": "Cron (07:00 WIB Daily)"
    },
    {
      "parameters": {
        "jsCode": '''const now = new Date();
const dateStr = now.toLocaleDateString("id-ID", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "Asia/Jakarta"
});

return [{
  json: {
    todayDateWib: dateStr,
    isoStart: new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0).toISOString(),
    isoEnd: new Date(now.getFullYear(), now.getMonth(), now.getDate(), 23, 59, 59).toISOString()
  }
}];'''
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [
        -380,
        200
      ],
      "id": "morningDateCalc01",
      "name": "[Code] Date Calculation"
    },
    {
      "parameters": {
        "operation": "getAll",
        "calendar": {
          "__rl": True,
          "value": "={{ $env.GCAL_OKTA_KULIAH }}",
          "mode": "id"
        },
        "returnAll": True,
        "timeMin": "={{ $now.setZone('Asia/Jakarta').startOf('day').toISO() }}",
        "timeMax": "={{ $now.setZone('Asia/Jakarta').endOf('day').toISO() }}",
        "options": {}
      },
      "type": "n8n-nodes-base.googleCalendar",
      "typeVersion": 1.3,
      "position": [
        -160,
        100
      ],
      "id": "morningGetKuliah01",
      "name": "Get GCal Okta Kuliah",
      "credentials": {
        "googleCalendarOAuth2Api": {
          "id": "kXkpk4YfItv3zvuT",
          "name": "Google Calendar account"
        }
      },
      "alwaysOutputData": True
    },
    {
      "parameters": {
        "operation": "getAll",
        "calendar": {
          "__rl": True,
          "value": "={{ $env.GCAL_OKTA_AGENDA }}",
          "mode": "id"
        },
        "returnAll": True,
        "timeMin": "={{ $now.setZone('Asia/Jakarta').startOf('day').toISO() }}",
        "timeMax": "={{ $now.setZone('Asia/Jakarta').endOf('day').toISO() }}",
        "options": {}
      },
      "type": "n8n-nodes-base.googleCalendar",
      "typeVersion": 1.3,
      "position": [
        -160,
        260
      ],
      "id": "morningGetAgenda01",
      "name": "Get GCal Okta Agenda",
      "credentials": {
        "googleCalendarOAuth2Api": {
          "id": "kXkpk4YfItv3zvuT",
          "name": "Google Calendar account"
        }
      },
      "alwaysOutputData": True
    },
    {
      "parameters": {
        "operation": "getAll",
        "calendar": {
          "__rl": True,
          "value": "={{ $env.GCAL_OKTA_TUGAS }}",
          "mode": "id"
        },
        "returnAll": True,
        "timeMin": "={{ $now.setZone('Asia/Jakarta').startOf('day').toISO() }}",
        "timeMax": "={{ $now.setZone('Asia/Jakarta').plus({days: 2}).endOf('day').toISO() }}",
        "options": {}
      },
      "type": "n8n-nodes-base.googleCalendar",
      "typeVersion": 1.3,
      "position": [
        -160,
        420
      ],
      "id": "morningGetTugas01",
      "name": "Get GCal Okta Tugas",
      "credentials": {
        "googleCalendarOAuth2Api": {
          "id": "kXkpk4YfItv3zvuT",
          "name": "Google Calendar account"
        }
      },
      "alwaysOutputData": True
    },
    {
      "parameters": {
        "jsCode": '''function parseEvents(nodeName, label) {
  let list = [];
  try { list = $(nodeName).all(); } catch(e){}
  const valid = list.filter(i => i.json && i.json.summary);
  if (valid.length === 0) return `${label}: Tidak ada jadwal.`;
  return `${label}:\\n` + valid.map(i => {
    const s = i.json.summary;
    let time = "";
    if (i.json.start?.dateTime) {
      const d = new Date(i.json.start.dateTime);
      time = " (jam " + d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Jakarta" }) + ")";
    }
    return `  • ${s}${time}`;
  }).join("\\n");
}

const kuliah = parseEvents("Get GCal Okta Kuliah", "Jadwal Kuliah Hari Ini");
const agenda = parseEvents("Get GCal Okta Agenda", "Agenda Kegiatan Hari Ini");
const tugas = parseEvents("Get GCal Okta Tugas", "Deadline Tugas Mendatang (1-2 hari)");

const dateInfo = $('[Code] Date Calculation').first().json.todayDateWib;

return [{
  json: {
    dateInfo,
    briefingContext: `Hari ini: ${dateInfo}\\n\\n${kuliah}\\n\\n${agenda}\\n\\n${tugas}`
  }
}];'''
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [
        100,
        260
      ],
      "id": "morningFormatContext01",
      "name": "[Code] Format Context"
    },
    {
      "parameters": {
        "jsCode": '''const keys = ($env.GEMINI_API_KEY || "").split(",").map(k => k.trim()).filter(Boolean);
const selected_key = keys[Math.floor(Math.random() * keys.length)];
return [{
  json: {
    ...$input.first().json,
    selected_key
  }
}];'''
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [
        300,
        260
      ],
      "id": "morningApiKeyRand01",
      "name": "[Code] Randomize Key"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={{ $json.selected_key }}",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": '''={{\n  {\n    "contents": [\n      {\n        "parts": [\n          {\n            "text": `Kamu adalah AI Co-Pilot & Asisten Pribadi Okta. Tugasmu adalah membuat naskah Voice Note \"Morning Audio Briefing\" untuk Okta yang akan dibacakan dengan suara ramah, bersemangat, to-the-point, dan santai (gaya obrolan radio / asisten cerdas panggil \"bro\" atau \"Okta\").\\n\\nDATA REAL-TIME HARI INI:\\n${$json.briefingContext}\\n\\nATURAN PENULISAN NASKAH:\\n1. Panjang naskah: MAKSIMAL 3-4 kalimat pendek (agar voice note berdurasi sekitar 20-30 detik).\\n2. Sapa Okta dan sebutkan harinya secara ringkas.\\n3. Bacakan kelas kuliah penting atau agenda utama hari ini.\\n4. Jika ada tugas/deadline mendesak, ingatkan singkat.\\n5. Tutup dengan kalimat penyemangat hari ini.\\n6. JANGAN gunakan tanda format markdown tebal (* atau **) atau bullet points di dalam teks naskah audio, karena teks ini akan langsung dibaca oleh Text-To-Speech engine.\\n\\nTuliskan NASKAH AUDIO murni saja sekarang:`\n          }\n        ]\n      }\n    ],\n    "generationConfig": {\n      "maxOutputTokens": 300\n    }\n  }\n}}''',
        "options": {
          "timeout": 20000
        }
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [
        500,
        260
      ],
      "id": "morningGeminiScript01",
      "name": "[HTTP] Gemini Audio Script"
    },
    {
      "parameters": {
        "jsCode": '''const res = $input.first().json;
let scriptText = "";
try {
  scriptText = res.candidates[0].content.parts[0].text.trim();
} catch(e) {}

// Clean text for speech
scriptText = scriptText.replace(/[*_#`~]/g, "").replace(/\\n+/g, " ");

const escaped = JSON.stringify(scriptText);
const cmd = `/home/dev/.local/bin/edge-tts --voice id-ID-ArdiNeural --text ${escaped} --write-media /tmp/morning_brief.mp3 && base64 -w 0 /tmp/morning_brief.mp3`;

return [{
  json: {
    scriptText,
    cmd
  }
}];'''
      },
      "type": "n8n-nodes-base.code",
      "typeVersion": 2,
      "position": [
        700,
        260
      ],
      "id": "morningPrepareTtsCmd01",
      "name": "[Code] Prepare TTS Command"
    },
    {
      "parameters": {
        "resource": "command",
        "operation": "execute",
        "authentication": "privateKey",
        "command": "={{ $json.cmd }}"
      },
      "type": "n8n-nodes-base.ssh",
      "typeVersion": 1.1,
      "position": [
        900,
        260
      ],
      "id": "morningSshSynthesize01",
      "name": "[SSH] Synthesize Audio",
      "credentials": {
        "sshPrivateKey": {
          "id": "sshHostDev0001",
          "name": "SSH Host Dev"
        }
      }
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://evolution-api:8080/message/sendWhatsAppAudio/okta_wa",
        "authentication": "genericCredentialType",
        "genericAuthType": "=httpHeaderAuth",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": '''={{ {
  number: $env.MY_WA_NUMBER,
  audio: $json.stdout.trim()
} }}''',
        "options": {
          "timeout": 20000
        }
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [
        1120,
        200
      ],
      "id": "morningSendWaAudio01",
      "name": "[HTTP] Send Audio to Okta",
      "credentials": {
        "httpHeaderAuth": {
          "id": "GEmHpHffIDZKhtvn",
          "name": "Header Auth account"
        }
      }
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://evolution-api:8080/message/sendText/okta_wa",
        "authentication": "genericCredentialType",
        "genericAuthType": "=httpHeaderAuth",
        "sendBody": True,
        "bodyParameters": {
          "parameters": [
            {
              "name": "number",
              "value": "={{ $env.MY_WA_NUMBER }}"
            },
            {
              "name": "text",
              "value": '''={{ `🎙️ *Morning Audio Briefing (07:00 WIB)* ☀️\\n\\n${$('Get GCal Okta Kuliah').all().length > 0 ? "📚 *Jadwal Kuliah Hari Ini:* Ada kelas.\\n" : "📚 *Jadwal Kuliah:* Kosong hari ini!\\n"}\\n📻 *Transkrip Audio:*\\n\"${$('[Code] Prepare TTS Command').first().json.scriptText}\"\\n\\nSelamat beraktivitas bro Okta! 🚀` }}'''
            }
          ]
        },
        "options": {}
      },
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [
        1120,
        340
      ],
      "id": "morningSendWaText01",
      "name": "[HTTP] Send Text Summary",
      "credentials": {
        "httpHeaderAuth": {
          "id": "GEmHpHffIDZKhtvn",
          "name": "Header Auth account"
        }
      }
    }
  ],
  "connections": {
    "Cron (07:00 WIB Daily)": {
      "main": [
        [
          {
            "node": "[Code] Date Calculation",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "[Code] Date Calculation": {
      "main": [
        [
          {
            "node": "Get GCal Okta Kuliah",
            "type": "main",
            "index": 0
          },
          {
            "node": "Get GCal Okta Agenda",
            "type": "main",
            "index": 0
          },
          {
            "node": "Get GCal Okta Tugas",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get GCal Okta Kuliah": {
      "main": [
        [
          {
            "node": "[Code] Format Context",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get GCal Okta Agenda": {
      "main": [
        [
          {
            "node": "[Code] Format Context",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "Get GCal Okta Tugas": {
      "main": [
        [
          {
            "node": "[Code] Format Context",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "[Code] Format Context": {
      "main": [
        [
          {
            "node": "[Code] Randomize Key",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "[Code] Randomize Key": {
      "main": [
        [
          {
            "node": "[HTTP] Gemini Audio Script",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "[HTTP] Gemini Audio Script": {
      "main": [
        [
          {
            "node": "[Code] Prepare TTS Command",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "[Code] Prepare TTS Command": {
      "main": [
        [
          {
            "node": "[SSH] Synthesize Audio",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "[SSH] Synthesize Audio": {
      "main": [
        [
          {
            "node": "[HTTP] Send Audio to Okta",
            "type": "main",
            "index": 0
          },
          {
            "node": "[HTTP] Send Text Summary",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "id": "morningBrief0001",
  "active": True
}

with open('workflow/morning-audio-briefing.json', 'w') as f:
    json.dump([wf], f, indent=2)

print('Built workflow/morning-audio-briefing.json successfully!')
