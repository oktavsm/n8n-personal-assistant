#!/usr/bin/env python3
"""
Beautify and Segment all Core n8n Workflows:
1. wa-conversation.json
2. wa-to-gcal-assistant.json
3. manda-gcal-assistant.json
4. master-router-webhook.json

Adds color-coded Sticky Notes (segmentation & guide) and rearranges all nodes
into clean, strictly left-to-right, non-overlapping grid layouts.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ==============================================================================
# 1. BEAUTIFY wa-conversation.json
# ==============================================================================
print("🚀 [1/4] Beautifying wa-conversation.json...")

WA_CONV_POSITIONS = {
    # 1. Ingestion
    "wa-msg": [-1200, 40],
    "Normalize WA Context": [-920, 40],

    # 2. Memory
    "[PG] Save Incoming Chat": [-500, 40],
    "[PG] Fetch History": [-240, 40],
    "Format Memory Context": [20, 40],

    # 3. Vision & Live Context
    "Switch Vision Query": [360, 40],
    # 3A. GCal Chain
    "Get GCal Okta Agenda": [640, -480],
    "Get GCal Okta Tugas": [880, -480],
    "Get GCal Okta Kuliah": [1120, -480],
    "Get GCal Manda Agenda": [1360, -480],
    "Get GCal Manda Tugas": [1600, -480],
    "Get GCal Manda Kuliah": [1840, -480],
    "Format Calendar Vision": [2080, -480],
    # 3B. Announcements
    "[HTTP] Get SIAM Pengumuman": [640, -220],
    "Format Pengumuman Vision": [940, -220],
    # 3C. Presensi
    "[HTTP] Get SIAM Presensi": [640, -60],
    "Format Presensi Vision": [940, -60],
    # 3D. Notes
    "[PG] Fetch Active Notes": [640, 100],
    "Format Notes Vision": [940, 100],
    # 3E. Expenses
    "[PG] Fetch Recent Expenses": [640, 260],
    "Format Expense Vision": [940, 260],
    # 3F. Default Vision
    "Format Default Vision": [640, 420],

    # 4. Multimodal Audio & Image
    "If Has Audio": [2380, 40],
    "Prepare Audio Payload": [2580, -60],
    "[HTTP] Evolution Get Base64 Audio": [2820, -60],
    "Attach Audio Base64": [3060, -60],
    "If Has Image": [2580, 160],
    "Prepare Image Payload": [2820, 160],
    "[HTTP] Evolution Get Base64 Image": [3060, 160],
    "Attach Image Base64": [3300, 160],

    # 5. Persona Routing & Gemini Engine
    "Switch": [3540, 40],
    "Switch1": [3780, -100],
    # Manda Persona Branch
    "Javascript Randomize API Key 1": [4000, -200],
    "[HTTP] Gemini Build Message1": [4240, -200],
    "Process AI Output & Actions1": [4480, -200],
    # Okta Persona Branch
    "Javascript Randomize API Key ": [4000, 60],
    "[HTTP] Gemini Build Message": [4240, 60],
    "Process AI Output & Actions": [4480, 60],

    # 6. Response Delivery
    "[HTTP Whatsapp] Send Message2": [4740, -200],
    "[HTTP Whatsapp] Send Message1": [4740, 60],
    "[PG] Save Bot Reply": [4980, 60],
    "If Titip Pesan": [4980, -200],
    "[HTTP Whatsapp] Forward Note to Target": [5220, -200],

    # 7. Automated Action Dispatcher
    "If Has Calendar Actions": [4740, 360],
    "Prepare Calendar Payloads": [4980, 360],
    "Switch Target Calendar": [5220, 360],
    "Call 'wa-to-gcal-assistant'": [5460, 300],
    "Call 'manda-to-gcal-assistant'": [5460, 420],
    "If Has Note Actions": [4740, 540],
    "[PG] Execute Note Action": [4980, 540],
    "If Has Presensi Actions": [4740, 700],
    "Call 'siam-presensi-from-action'": [4980, 700],
    "If Has Expense Actions": [4740, 860],
    "[PG] Execute Expense Action": [4980, 860],

    # 8. Quick Utilities (Sticker & Empty Tags)
    "If1": [3780, 440],
    "Prepare Media Payload": [4000, 440],
    "[HTTP] Evolution Get Base64": [4240, 440],
    "[HTTP] Evolution Send Sticker": [4480, 440],
    "[HTTP Whatsapp] Send Message3": [4000, 580],
    "If": [3780, 680],
    "Code in JavaScript": [4000, 680],
    "[HTTP Whatsapp] Send Message": [4240, 680]
}

WA_CONV_NOTES = [
    {
        "parameters": {
            "content": "### 📥 1. Ingestion & Normalisasi Context\n- **wa-msg**: Trigger webhook dari Evolution API.\n- **Normalize WA Context**: Membedakan chat pribadi (PC) vs grup, mengekstrak sender, caption, audio, gambar, dan filter query.",
            "height": 340,
            "width": 640,
            "color": 2
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [-1260, -80],
        "name": "Note: Ingestion"
    },
    {
        "parameters": {
            "content": "### 🧠 2. PostgreSQL Memory Pipeline (40 Turns / 14 Hari)\n- **[PG] Save Incoming Chat**: Menyimpan chat user ke tabel `wa_chat_memory`.\n- **[PG] Fetch History**: Mengambil 40 riwayat chat terakhir terisolasi per `room_jid`.\n- **Format Memory Context**: Menyusun transkrip percakapan kronologis dengan timestamp cerdas.",
            "height": 340,
            "width": 840,
            "color": 3
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [-560, -80],
        "name": "Note: Memory"
    },
    {
        "parameters": {
            "content": "### 👁️ 3. Dynamic Real-Time Vision & Live Context Injection\n- **Switch Vision Query**: Menghubungkan secara dinamis data terkini ke prompt Gemini:\n  • **Kalender**: 6 kalender real-time (Agenda, Tugas, Kuliah Okta & Manda).\n  • **Pengumuman**: Rilis pengumuman akademik terbaru dari SIAM UB.\n  • **Presensi**: Status presensi kuliah hari ini dari SIAM UB.\n  • **Notes**: Catatan aktif milik user di PostgreSQL `user_notes`.\n  • **Expenses**: Riwayat pengeluaran 30 hari di PostgreSQL `user_expenses`.\n  • **Default**: Obrolan santai umum & pertanyaan foto/diagram.",
            "height": 1100,
            "width": 1960,
            "color": 4
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [320, -580],
        "name": "Note: Vision Context"
    },
    {
        "parameters": {
            "content": "### 🎙️📸 4. Multimodal Audio VN & Image OCR Ingestion\n- Mengunduh Voice Note audio atau Foto/Diagram dari Evolution API menjadi Base64.\n- Mengirimkan media ke Gemini 2.5 Flash untuk analisis native multimodal.",
            "height": 400,
            "width": 1100,
            "color": 7
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [2320, -120],
        "name": "Note: Multimodal Ingestion"
    },
    {
        "parameters": {
            "content": "### 🤖 5. Dual-Persona Gemini AI Engine\n- **Switch & Switch1**: Memilah persona Okta (WIB) vs Kak Manda (WITA) dan memilih API key acak (5 keys load-balancing).\n- **Gemini Engine**: `gemini-2.5-flash` untuk media / `gemini-3.5-flash-lite` untuk teks cepat.\n- **Process AI Output & Actions**: Memisahkan teks jawaban bersih untuk user dan mengekstrak tag aksi `<<<ACTION:...>>>`.",
            "height": 580,
            "width": 1120,
            "color": 6
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [3480, -280],
        "name": "Note: Gemini AI Engine"
    },
    {
        "parameters": {
            "content": "### 📤 6. Response Delivery & Relay Titip Pesan\n- **Send Message**: Mengirim pesan balasan resmi ke WhatsApp via Evolution API.\n- **Save Bot Reply**: Menyimpan jawaban AI ke riwayat memori PostgreSQL.\n- **Titip Pesan**: Otomatis meneruskan pesan titipan ke pasangan (Okta ⇄ Manda).",
            "height": 580,
            "width": 960,
            "color": 2
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [4660, -280],
        "name": "Note: Response Delivery"
    },
    {
        "parameters": {
            "content": "### ⚡ 7. Automated Action Execution Dispatcher\nMengeksekusi aksi nyata di latar belakang berdasarkan tag aksi yang dikeluarkan Gemini:\n- **Kalender**: Dispatch ke sub-workflow `wa-to-gcal-assistant` atau `manda-gcal-assistant`.\n- **Catatan**: Menyimpan catatan to-do baru atau menandai tuntas di `user_notes`.\n- **Presensi**: Memanggil presensi otomatis SIAM UB.\n- **Expense**: Menyimpan transaksi pengeluaran ke `user_expenses`.",
            "height": 720,
            "width": 1140,
            "color": 5
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [4660, 320],
        "name": "Note: Action Dispatcher"
    },
    {
        "parameters": {
            "content": "### 🎨 8. Quick Utilities (Sticker Generator & Empty Mentions)\n- **Sticker**: Mengubah foto/video/GIF yang masuk menjadi stiker WhatsApp instan.\n- **Empty Mentions**: Membalas sapaan ramah saat pengguna hanya men-tag bot tanpa pesan.",
            "height": 420,
            "width": 1120,
            "color": 1
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [3480, 380],
        "name": "Note: Utilities"
    }
]

def apply_wa_conv_layout(filepath: Path):
    if not filepath.exists(): return
    with open(filepath, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    # Remove existing sticky notes
    data["nodes"] = [n for n in data["nodes"] if n.get("type") != "n8n-nodes-base.stickyNote"]

    # Reposition functional nodes
    for n in data["nodes"]:
        name = n.get("name")
        if name in WA_CONV_POSITIONS:
            n["position"] = WA_CONV_POSITIONS[name]

    # Add new styled sticky notes
    data["nodes"].extend(WA_CONV_NOTES)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Successfully beautified {filepath.name}")

apply_wa_conv_layout(REPO_ROOT / "workflow" / "wa-conversation.json")
apply_wa_conv_layout(REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json")

# ==============================================================================
# 2. BEAUTIFY wa-to-gcal-assistant.json & manda-gcal-assistant.json
# ==============================================================================
print("\n🚀 [2/4] Beautifying wa-to-gcal-assistant.json & manda-gcal-assistant.json...")

def get_gcal_positions(is_manda: bool):
    p = "Manda " if is_manda else ""
    return {
        # 1. Ingestion
        "WA Command": [-760, 260],
        "[Code] Get WA Data": [-460, 260],
        "Switch1": [-160, 260],

        # 2. Natural Language Scheduling
        # Agenda Lane (Y: -380)
        "Code in JavaScript": [280, -380],
        "[HTTP] Gemini Brone": [520, -380],
        "[Code] Status Check Jadwal": [760, -380],
        "Switch": [1000, -380],
        "Create an event": [1240, -440],
        "[HTTP Whatsapp]10": [1480, -440],
        # Tugas Lane (Y: -160)
        "Code in JavaScript3": [280, -160],
        "[HTTP] Gemini Brone2": [520, -160],
        "[Code] Status Check Tugas": [760, -160],
        "Switch2": [1000, -160],
        "Create an event1": [1240, -160],

        # 3. Schedule & Deadlines Queries
        # Cek Hari Ini
        "Get many events": [280, 80],
        "Get many jadwal kuliah": [520, 80],
        "Code: Recap Jadwal": [760, 80],
        "If2": [1000, 80],
        # Cek Besok
        "Get many events3": [280, 240],
        "Get many jadwal kuliah2": [520, 240],
        "Code: Recap Jadwal4": [760, 240],
        "If5": [1000, 240],
        # Agenda 7 Hari
        "Get many events2": [280, 400],
        "Code: Recap Jadwal3": [520, 400],
        "If4": [760, 400],
        # Tugas Aktif
        "Get many events1": [280, 560],
        "Code: Recap Jadwal2": [520, 560],
        "If3": [760, 560],
        # UAS Sem 4
        "Get many jadwal kuliah1": [280, 720],
        "Code: Recap Jadwal1": [520, 720],
        "If": [760, 720],

        # 4. Safe Lifecycle Engine (/done, /hapus, /edit-kuliah)
        f"[PG] {p}Fetch Pending Selection": [280, 1020],
        f"{p}Fetch GCal Agenda For Match": [520, 1020],
        f"{p}Fetch GCal Tugas For Match": [760, 1020],
        f"{p}Fetch GCal Kuliah For Match": [1000, 1020],
        f"{p}Process Safe Calendar Action": [1240, 1020],
        f"[PG] {p}Execute Pending Action Query": [1480, 1020],
        f"{p}Switch Lifecycle Decision": [1720, 1020],
        f"{p}Update Safe GCal Event": [1960, 940],
        f"{p}Delete Safe GCal Event": [1960, 1100],

        # 5. Outbound WhatsApp Dispatcher
        "[HTTP Whatsapp]8": [2320, 360],
        "[HTTP Whatsapp]9": [2320, 220]
    }

def get_gcal_notes(is_manda: bool):
    user_label = "Kak Manda (WITA)" if is_manda else "Okta (WIB)"
    return [
        {
            "parameters": {
                "content": f"### 📥 1. Ingestion & Command Router ({user_label})\n- **WA Command**: Menerima request dari webhook atau `wa-conversation`.\n- **[Code] Get WA Data**: Menentukan pengirim, chat target, dan membersihkan teks.\n- **Switch1**: Membagi ke 8 rute perintah (/jadwal, /cek, /uas, /tugas, /agenda, /besok, /lifecycle).",
                "height": 340,
                "width": 840,
                "color": 2
            },
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [-820, 140],
            "name": "Note: Ingestion"
        },
        {
            "parameters": {
                "content": "### ✍️ 2. Natural Language Scheduling (Gemini Time Parsing)\n- Menggunakan Gemini untuk mengekstrak judul, tanggal, dan jam secara otomatis.\n- Menangani pembuatan agenda pribadi (`/jadwal`) dan deadline tugas akademik (`/tugas <detail>`).",
                "height": 520,
                "width": 1420,
                "color": 6
            },
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [220, -500],
            "name": "Note: Scheduling"
        },
        {
            "parameters": {
                "content": "### 📅 3. Schedule, Deadline & Exam Queries\n- **/cek**: Menampilkan jadwal kuliah dan agenda hari ini.\n- **/besok**: Menampilkan jadwal kuliah dan agenda esok hari.\n- **/agenda**: Rekap seluruh kegiatan 7 hari ke depan.\n- **/tugas**: Menampilkan seluruh deadline tugas aktif.\n- **/uas**: Menampilkan jadwal Ujian Akhir Semester.",
                "height": 840,
                "width": 1040,
                "color": 4
            },
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [220, 40],
            "name": "Note: Queries"
        },
        {
            "parameters": {
                "content": "### 🛡️ 4. Safe Calendar Lifecycle Engine (/done, /hapus, /edit-kuliah)\n- **Konfirmasi Cerdas**: Jika ditemukan > 1 item yang mirip/duplikat, bot meminta user memilih nomor (1, 2, batal).\n- **Perlindungan Jadwal Kuliah**: Kuliah dilindungi dari hapus/done; hanya bisa diubah ruang atau libur via `/edit-kuliah`.\n- **Scope Aman**: Hanya menghapus / menandai [SELESAI] pada kalender Agenda dan Tugas.",
                "height": 400,
                "width": 1960,
                "color": 3
            },
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [220, 900],
            "name": "Note: Lifecycle"
        },
        {
            "parameters": {
                "content": "### 📤 5. WhatsApp Response Dispatcher\nMengirim pesan konfirmasi resmi ke WhatsApp via Evolution API.",
                "height": 380,
                "width": 380,
                "color": 2
            },
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "position": [2260, 140],
            "name": "Note: Dispatcher"
        }
    ]

def apply_gcal_layout(filepath: Path, is_manda: bool):
    if not filepath.exists(): return
    with open(filepath, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    pos_map = get_gcal_positions(is_manda)

    # Remove existing sticky notes
    data["nodes"] = [n for n in data["nodes"] if n.get("type") != "n8n-nodes-base.stickyNote"]

    # Reposition functional nodes
    for n in data["nodes"]:
        name = n.get("name")
        if name in pos_map:
            n["position"] = pos_map[name]

    # Add sticky notes
    data["nodes"].extend(get_gcal_notes(is_manda))

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Successfully beautified {filepath.name}")

apply_gcal_layout(REPO_ROOT / "workflow" / "wa-to-gcal-assistant.json", is_manda=False)
apply_gcal_layout(REPO_ROOT / "n8n" / "workflow" / "wa-to-gcal-assistant.json", is_manda=False)
apply_gcal_layout(REPO_ROOT / "workflow" / "manda-gcal-assistant.json", is_manda=True)
apply_gcal_layout(REPO_ROOT / "n8n" / "workflow" / "manda-gcal-assistant.json", is_manda=True)

# ==============================================================================
# 3. BEAUTIFY master-router-webhook.json
# ==============================================================================
print("\n🚀 [3/4] Beautifying master-router-webhook.json...")

MASTER_ROUTER_POSITIONS = {
    # 1. Main Ingestion
    "Webhook": [-180, 80],
    "Switch": [180, 80],

    # 2. Core Sub-Workflow Routers
    "pengirim okta?": [640, -120],
    "jadwal manda?": [880, -180],
    "Call 'manda-to-gcal-assistant'": [1140, -180],
    "Call 'wa-to-gcal-assistant'": [1140, -60],
    "pengirim manda?": [880, 0],
    "jadwal okta?": [1140, 60],
    "Call 'wa-conversation'": [640, 140],
    "Call 'automatic-brone-task-notifier'": [640, 240],
    "Call 'siam-pengumuman'": [880, 240],
    "Call 'siam-presensi-notifier'": [1140, 240],
    "Call 'vps-cli-runner'": [640, 340],

    # 3. Information & Help Manual
    "[Script] Message Builder": [640, 480],
    "[HTTP Whatsapp] Send Message": [880, 480],
    "[Script] Message Builder1": [640, 600],
    "[HTTP Whatsapp] Send Message10": [880, 600],

    # 4. Fun & Keyword Sidecars (brought from far negative X to clean bottom grid!)
    "sender check6": [-180, 860],
    "HTTP Request": [60, 860],
    "Code in JavaScript": [300, 860],
    "Switch1": [540, 860],
    "[HTTP Whatsapp] Send Message2": [780, 820],
    "[HTTP Whatsapp] Send Message1": [780, 900],

    "sender check7": [-180, 1000],
    "HTTP Request1": [60, 1000],
    "Code in JavaScript1": [300, 1000],
    "Switch2": [540, 1000],
    "[HTTP Whatsapp] Send Message4": [780, 960],
    "If": [780, 1040],
    "[HTTP Whatsapp] Send Message3": [1020, 1040],

    "sender check8": [-180, 1140],
    "HTTP Request2": [60, 1140],
    "Code in JavaScript4": [300, 1140],
    "Switch3": [540, 1140],
    "[HTTP Whatsapp] Send Message7": [780, 1100],
    "Code in JavaScript3": [780, 1180],
    "[HTTP Whatsapp] Send Message6": [1020, 1180],

    "sender check9": [-180, 1280],
    "HTTP Request3": [60, 1280],
    "Switch4": [300, 1280],
    "[HTTP Whatsapp] Send Message9": [540, 1240],
    "[HTTP Whatsapp] Send Message8": [540, 1320],
    "Code in JavaScript2": [300, 1380],
    "[HTTP Whatsapp] Send Message5": [540, 1380],

    "HTTP Request5": [-180, 1500],
    "Code in JavaScript7": [60, 1500],
    "[HTTP Whatsapp] Send Message14": [300, 1460],
    "[HTTP Whatsapp] Send Message15": [300, 1540],

    "HTTP Request6": [-180, 1640],
    "Code in JavaScript8": [60, 1640],
    "[HTTP Whatsapp] Send Message16": [300, 1600],
    "[HTTP Whatsapp] Send Message17": [300, 1680]
}

MASTER_ROUTER_NOTES = [
    {
        "parameters": {
            "content": "### 🌐 1. Central Webhook & Master Switch\n- **Webhook**: Menangkap seluruh event pesan WhatsApp dari Evolution API.\n- **Switch**: Memilah pesan berdasarkan slash commands, mentions bot, pesan pribadi, atau media.",
            "height": 340,
            "width": 640,
            "color": 2
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [-240, -40],
        "name": "Note: Webhook Router"
    },
    {
        "parameters": {
            "content": "### 🎯 2. Core Sub-Workflow Routers\n- **Kalender Okta & Manda**: Menentukan target kalender dan memanggil assistant terkait.\n- **AI Conversation**: Memanggil `wa-conversation` untuk pemrosesan teks, audio VN, gambar, notes, dan expenses.\n- **Academic Monitors**: Memanggil Brone, Presensi, dan Pengumuman SIAM.\n- **VPS Agent**: Memanggil `vps-cli-runner` untuk perintah terminal.",
            "height": 560,
            "width": 860,
            "color": 6
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [580, -220],
        "name": "Note: Core Routers"
    },
    {
        "parameters": {
            "content": "### 📋 3. Information & Help Manual\n- **/help**: Menampilkan menu panduan lengkap seluruh fitur asisten.\n- **/kewajiban okta**: Personal reminder.",
            "height": 300,
            "width": 860,
            "color": 3
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [580, 420],
        "name": "Note: Help & Info"
    },
    {
        "parameters": {
            "content": "### 🎭 4. Fun & Community Keywords Sidecars\nKumpulan trigger kata kunci grup interaktif (fasta, abil, diaturun, kicau, jokowi, dll).",
            "height": 940,
            "width": 1540,
            "color": 1
        },
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [-240, 800],
        "name": "Note: Fun Keywords"
    }
]

def apply_master_router_layout(filepath: Path):
    if not filepath.exists(): return
    with open(filepath, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    # Remove existing sticky notes
    data["nodes"] = [n for n in data["nodes"] if n.get("type") != "n8n-nodes-base.stickyNote"]

    # Reposition functional nodes
    for n in data["nodes"]:
        name = n.get("name")
        if name in MASTER_ROUTER_POSITIONS:
            n["position"] = MASTER_ROUTER_POSITIONS[name]

    # Add sticky notes
    data["nodes"].extend(MASTER_ROUTER_NOTES)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Successfully beautified {filepath.name}")

apply_master_router_layout(REPO_ROOT / "workflow" / "master-router-webhook.json")
apply_master_router_layout(REPO_ROOT / "n8n" / "workflow" / "master-router-webhook.json")

print("\n🎉 ALL 4 WORKFLOWS BEAUTIFIED AND SEGMENTED WITH STICKY NOTES!")
