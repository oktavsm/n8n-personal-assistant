#!/usr/bin/env python3
"""
Fix Prepare Calendar Payloads and Manda branch in wa-conversation:
1. Prepare Calendar Payloads: Add 'reschedule' to calActions filter so reschedule commands aren't dropped.
2. Process AI Output & Actions1 (Manda branch): Add RESCHEDULE regex, parsing, and hasCalendarActions check.
3. [HTTP] Gemini Build Message1 (Manda branch): Add ACTION:RESCHEDULE system prompt instructions.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

paths = [
    REPO_ROOT / "workflow" / "wa-conversation.json",
    REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json"
]

RESCHEDULE_PROMPT_DOC = """   <<<ACTION:RESCHEDULE|TARGET|JUDUL|START_ISO|END_ISO|WAKTU_TEXT>>> -> ganti tanggal/jam atau jadwalkan ulang agenda/tugas.
   TARGET: "okta" atau "manda"
   START_ISO: ISO string waktu mulai UTC+7 (contoh: 2026-10-22T20:00:00+07:00)
   END_ISO: ISO string waktu selesai UTC+7 (contoh: 2026-10-22T21:00:00+07:00)
   WAKTU_TEXT: Deskripsi waktu baru (contoh: "Kamis, 22 Okt 2026 jam 20.00 WIB")
   
   ⚠️ ATURAN KETAT RESCHEDULE & GANTI TANGGAL/JAM:
   - JIKA PENGGUNA INGIN MENGUNDUR, MEMAJUKAN, ATAU MENGGANTI TANGGAL/JAM AGENDA ATAU TUGAS:
     - DILARANG KERAS MENGELUARKAN <<<ACTION:JADWAL>>> ATAU <<<ACTION:TUGAS>>> karena itu akan MEMBUAT JADWAL BARU (DUPLIKAT)!
     - WAJIB mengeluarkan tag <<<ACTION:RESCHEDULE|TARGET|JUDUL|START_ISO|END_ISO|WAKTU_TEXT>>>.
     - Contoh:
       User: "rapat TSA diundur besok jam 8 malam"
       Baris terakhir: <<<ACTION:RESCHEDULE|okta|TSA|2026-10-22T20:00:00+07:00|2026-10-22T21:00:00+07:00|Kamis, 22 Okt 2026 jam 20.00 WIB>>>
       User: "deadline tugas metopen ganti jadi jumat 23.59"
       Baris terakhir: <<<ACTION:RESCHEDULE|okta|metopen|2026-10-23T23:59:00+07:00|2026-10-23T23:59:00+07:00|Jumat, 23 Okt 2026 jam 23.59 WIB>>>
"""

def update_workflow(wf):
    for node in wf["nodes"]:
        # 1. Prepare Calendar Payloads
        if node["name"] == "Prepare Calendar Payloads":
            js = node["parameters"].get("jsCode", "")
            old_filter = "['tugas', 'jadwal', 'done', 'delete', 'edit'].includes(a.actionType)"
            new_filter = "['tugas', 'jadwal', 'done', 'delete', 'edit', 'reschedule'].includes(a.actionType)"
            if old_filter in js:
                node["parameters"]["jsCode"] = js.replace(old_filter, new_filter)
                print("  Updated 'Prepare Calendar Payloads' filter")

        # 2. Process AI Output & Actions1 (Manda branch)
        elif node["name"] == "Process AI Output & Actions1":
            js = node["parameters"].get("jsCode", "")
            # Update actionRegex
            if "ACTION:(TUGAS|JADWAL|DONE|DELETE|EDIT|" in js:
                js = js.replace(
                    "ACTION:(TUGAS|JADWAL|DONE|DELETE|EDIT|",
                    "ACTION:(TUGAS|JADWAL|DONE|DELETE|EDIT|RESCHEDULE|"
                )
            
            # Add reschedule handler
            if "actionType === 'reschedule'" not in js:
                resched_branch = (
                    "  } else if (actionType === 'reschedule') {\n"
                    "    const target = (parts[0] || 'okta').toLowerCase();\n"
                    "    const query = parts[1] || '';\n"
                    "    const startIso = parts[2] || '';\n"
                    "    const endIso = parts[3] || '';\n"
                    "    const timeText = parts[4] || '';\n"
                    "    const newTitle = parts[5] || '';\n"
                    "    const commandText = target === 'manda'\n"
                    "      ? `/reschedule manda ${query} | ${startIso} | ${endIso} | ${timeText} | ${newTitle}`.trim()\n"
                    "      : `/reschedule ${query} | ${startIso} | ${endIso} | ${timeText} | ${newTitle}`.trim();\n"
                    "    actions.push({\n"
                    "      actionType: 'reschedule',\n"
                    "      target,\n"
                    "      query,\n"
                    "      startIso,\n"
                    "      endIso,\n"
                    "      timeText,\n"
                    "      newTitle,\n"
                    "      detail: `${query} -> ${timeText || startIso}`,\n"
                    "      commandText\n"
                    "    });\n"
                )
                js = js.replace("  } else if (actionType === 'edit') {", resched_branch + "  } else if (actionType === 'edit') {")

            # Update hasCalendarActions
            old_has = "['tugas', 'jadwal', 'done', 'delete', 'edit'].includes(a.actionType)"
            new_has = "['tugas', 'jadwal', 'done', 'delete', 'edit', 'reschedule'].includes(a.actionType)"
            if old_has in js:
                js = js.replace(old_has, new_has)

            node["parameters"]["jsCode"] = js
            print("  Updated 'Process AI Output & Actions1'")

        # 3. [HTTP] Gemini Build Message1 (Manda branch)
        elif node["name"] == "[HTTP] Gemini Build Message1":
            body = node["parameters"].get("jsonBody", "")
            if "ACTION:RESCHEDULE" not in body:
                target_str = "   <<<ACTION:EDIT|TARGET|JUDUL_LAMA|JUDUL_BARU>>>      -> ralat/ubah nama agenda atau tugas yang sudah ada.\n"
                if target_str in body:
                    body = body.replace(target_str, target_str + RESCHEDULE_PROMPT_DOC)
                    node["parameters"]["jsonBody"] = body
                    print("  Updated '[HTTP] Gemini Build Message1' prompt")

for p in paths:
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    wf = data[0] if isinstance(data, list) else data
    print(f"Fixing {p.name}...")
    update_workflow(wf)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {p.name}")

print("🎉 wa-conversation successfully updated!")
