#!/usr/bin/env python3
"""
Fix Morning Audio Briefing:
1. Switch Gemini model from gemini-2.5-flash to gemini-3.5-flash-lite (fast, stable, no 503 limits).
2. Add retryOnFail: true, maxTries: 3, waitBetweenTries: 2000 to Gemini HTTP node.
3. Add onError: "continueRegularOutput" so temporary Gemini outages don't crash the workflow.
4. Add intelligent fallback speech generator in [Code] Prepare TTS Command if LLM response is empty/errored.
5. Add executeWorkflowTrigger (Manual / Call Trigger) to support on-demand triggers (/briefing).
6. Use unique timestamped temp audio files to prevent file conflicts.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

paths = [
    REPO_ROOT / "workflow" / "morning-audio-briefing.json",
    REPO_ROOT / "n8n" / "workflow" / "morning-audio-briefing.json"
]

def upgrade_briefing_workflow(wf):
    # 1. Add executeWorkflowTrigger if missing
    has_exec_trigger = any(n.get("type") == "n8n-nodes-base.executeWorkflowTrigger" for n in wf["nodes"])
    if not has_exec_trigger:
        exec_node = {
            "parameters": {
                "inputSource": "passthrough"
            },
            "type": "n8n-nodes-base.executeWorkflowTrigger",
            "typeVersion": 1.1,
            "position": [-600, 360],
            "id": "morningManualTrigger01",
            "name": "Manual / Call Trigger"
        }
        wf["nodes"].append(exec_node)
        wf["connections"]["Manual / Call Trigger"] = {
            "main": [
                [
                    {
                        "node": "[Code] Date Calculation",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        }

    for node in wf["nodes"]:
        # 2. Fix [HTTP] Gemini Audio Script
        if node["name"] == "[HTTP] Gemini Audio Script":
            # Change URL to gemini-3.5-flash-lite
            node["parameters"]["url"] = "=https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={{ $json.selected_key }}"
            # Add retries & continue on error
            node["onError"] = "continueRegularOutput"
            node["retryOnFail"] = True
            node["maxTries"] = 3
            node["waitBetweenTries"] = 2000

        # 3. Fix [Code] Prepare TTS Command with fallback script generator
        elif node["name"] == "[Code] Prepare TTS Command":
            node["parameters"]["jsCode"] = """const res = $input.first().json || {};
let scriptText = "";
try {
  scriptText = res.candidates[0].content.parts[0].text.trim();
} catch(e) {}

// Intelligent Fallback Script if Gemini is unavailable or returns 503/error
if (!scriptText) {
  const now = new Date();
  const dayName = now.toLocaleDateString("id-ID", { weekday: "long", timeZone: "Asia/Jakarta" });
  const dateStr = now.toLocaleDateString("id-ID", { day: "numeric", month: "long", timeZone: "Asia/Jakarta" });

  let kuliahList = [];
  try {
    kuliahList = $('Get GCal Okta Kuliah').all()
      .map(i => i.json?.summary)
      .filter(Boolean)
      .filter(s => !s.toUpperCase().includes('[LIBUR]'));
  } catch(e) {}

  let agendaList = [];
  try {
    agendaList = $('Get GCal Okta Agenda').all()
      .map(i => i.json?.summary)
      .filter(Boolean);
  } catch(e) {}

  let tugasList = [];
  try {
    tugasList = $('Get GCal Okta Tugas').all()
      .map(i => i.json?.summary)
      .filter(Boolean)
      .filter(s => !s.toUpperCase().includes('[SELESAI]'));
  } catch(e) {}

  let items = [];
  if (kuliahList.length > 0) {
    items.push(`ada ${kuliahList.length} kelas kuliah hari ini`);
  }
  if (agendaList.length > 0) {
    items.push(`ada agenda ${agendaList[0]}`);
  }

  const activityText = items.length > 0
    ? `Hari ini kamu ${items.join(' dan ')}.`
    : 'Hari ini jadwalmu terpantau santai dan tidak ada kelas kuliah.';

  const taskText = tugasList.length > 0
    ? `Jangan lupa ada deadline tugas ${tugasList[0]}.`
    : 'Tidak ada deadline tugas mendesak hari ini.';

  scriptText = `Selamat pagi bro Okta! Hari ini hari ${dayName}, tanggal ${dateStr}. ${activityText} ${taskText} Semangat dan sukses buat semua aktivitasmu hari ini ya!`;
}

// Clean text for speech (strip markdown characters and extra line breaks)
scriptText = scriptText.replace(/[*_#`~]/g, "").replace(/\\n+/g, " ").trim();

const ts = Date.now();
const tmpFile = `/tmp/morning_brief_${ts}.mp3`;
const escaped = JSON.stringify(scriptText);
const cmd = `/home/dev/.local/bin/edge-tts --voice id-ID-ArdiNeural --text ${escaped} --write-media ${tmpFile} && base64 -w 0 ${tmpFile} && rm -f ${tmpFile}`;

return [{
  json: {
    scriptText,
    cmd
  }
}];"""

for p in paths:
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    wf = data[0] if isinstance(data, list) else data
    upgrade_briefing_workflow(wf)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Upgraded {p.name}")

print("🎉 Morning Audio Briefing workflow successfully patched with high resilience!")
