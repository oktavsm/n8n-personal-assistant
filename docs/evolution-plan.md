# 🚀 Dokumentasi Implementasi WhatsApp Bot & Agent Ecosystem

Dokumen ini mencatat seluruh implementasi, perubahan arsitektur, dan status optimasi resource pada ekosistem **n8n Personal Assistant** di VPS `pg-bcc`.

---

## 📊 1. Ringkasan Status & Hasil Optimasi VPS

| Parameter | Sebelum Optimasi | Sesudah Optimasi | Status |
| :--- | :--- | :--- | :--- |
| **Available RAM** | ~785 MiB | **~800-900 MiB** | ✅ Sangat Sehat |
| **Swap Used** | 1,056 MiB | **880 MiB** (-176 MiB) | ✅ Berkurang |
| **Free Disk** | 3.6 GB (84% used) | **7.3 GB** (68% used) | 🎉 **+3.7 GB Dibebaskan!** |
| **Container Non-aktif** | Running | **Stopped & Disabled Restart** | ✅ `okta-pma`, `notifier_wa_manager`, `okta-db-paw`, `okta-php` |
| **VS Code Server Cache**| 3.3 GB + Zombie Process | **Dihapus & Killed** | ✅ +3.2 GB Storage Pulih |
| **Container Prioritas** | Running | **Tetap Running Normal** | ✅ `okta-tiksave`, `okta-backend`, `okta-nginx`, `notifier_n8n`, `notifier_wa_gateway`, `notifier_db`, `notifier_brone_auth` |

### 🔍 Status Generator SVG di VPS:
- Folder `/home/dev/projects/docker/readme-server` & `/home/dev/projects/docker/github-svg`: **Tidak berjalan sama sekali** (tidak ada container atau daemon aktif).
- Script `/home/dev/projects/daily-digest/script/daily_digest.py`: Berjalan via `crontab` setiap jam 00:00, 08:00, dan 16:00 untuk menghasilkan `latest.svg`.

---

## 🧠 2. Chat Memory Database (PostgreSQL)

- **Database Host & Port**: Internal container `notifier_db:5432` (`db`).
- **Database Name**: `n8n_db`.
- **Tabel**: `public.wa_chat_memory`.
- **Index**: `idx_wa_chat_room_time (room_jid, created_at DESC)`.
- **Credential n8n**: `pgChatMemory0001` (Postgres Chat Memory).

### Skema Tabel:
```sql
CREATE TABLE IF NOT EXISTS public.wa_chat_memory (
    id SERIAL PRIMARY KEY,
    room_jid VARCHAR(100) NOT NULL,
    sender_jid VARCHAR(100) NOT NULL,
    sender_name VARCHAR(100),
    role VARCHAR(20) NOT NULL,            -- 'user' | 'assistant'
    message_type VARCHAR(20) DEFAULT 'text', -- 'text' | 'media'
    content TEXT NOT NULL,
    quoted_content TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
```

### Mekanisme Sliding Window:
Setiap pesan masuk diambil **15 riwayat chat terakhir** dalam rentang waktu **7 hari terakhir** (`WHERE room_jid = $1 AND created_at >= NOW() - INTERVAL '7 days' LIMIT 15`), kemudian diformat secara kronologis ke prompt Gemini.

---

## 🎭 3. Persona "Perwakilan Okta" & Titip Pesan Dua Arah

### Persona Khusus Kak Manda (`Gemini Build Message1`):
- Berperan sebagai **Perwakilan / Asisten Pribadi Okta**, bukan menggantikan Okta.
- Panggilan akrab: **Kak Manda**.
- Sikap: Hangat, sopan, responsif, santai namun tidak alay/cringe.
- **Titip Pesan ke Okta:** Jika Kak Manda menitipkan pesan (misal *"titip pesan ke okta"*, *"bilang ke okta"*), sistem otomatis mengekstrak pesan dan memicu node `[HTTP Whatsapp] Forward Note to Target` untuk meneruskannya langsung ke WhatsApp Okta (`$env.MY_WA_NUMBER`).

### Persona Okta & Group (`Gemini Build Message`):
- **Okta (Dev):** Co-pilot teknis, to the point, ringkas, dan solutif.
- **Titip Pesan ke Kak Manda:** Jika Okta menitipkan pesan untuk Kak Manda (misal *"titip pesan ke manda"*, *"bilang ke manda"*), sistem otomatis meneruskan pesan tersebut langsung ke WhatsApp Kak Manda (`$env.MANDA_WA_NUMBER`).
- **Group Chat:** Menyesuaikan vibe santai grup tanpa mendominasi percakapan.

---

## 🎙️ 4. Voice Note Listener (Gemini 2.5 Flash Multimodal)

- **Normalisasi Audio:** Mendeteksi `audioMessage` dari WhatsApp.
- **Base64 Audio Pipeline:**
  1. `If Has Audio` memeriksa apakah pesan berisi voice note.
  2. Mengambil base64 audio via `/chat/getBase64FromMediaMessage/okta_wa` di Evolution API.
  3. Mengirimkan `inline_data` audio (`audio/ogg`) ke Google **Gemini 2.5 Flash**.
- **Hasil:** Gemini mendengarkan langsung rekaman suara, memahami isi perkataan Kak Manda atau Okta, dan meresponsnya secara kontekstual!

---

## 🧹 5. Housekeeping Cron (`memory-housekeeping-cron`)

- **Workflow ID:** `memHousekeep01`.
- **Jadwal:** Setiap hari Minggu jam 03:00 WIB (`0 3 * * 0`).
- **Query:** `DELETE FROM wa_chat_memory WHERE created_at < NOW() - INTERVAL '30 days';`.
- **Hasil:** Menjaga database PostgreSQL tetap ringan tanpa maintenance manual.

---

## 🎨 4. WhatsApp Sticker Generator

- **Perintah**: `/stiker` atau `/sticker` (bisa dengan caption gambar/video/gif atau membalas/reply media).
- **Alur Kerja**:
  1. `master-router-webhook` mencocokkan prefix `/stiker` / `/sticker` (Rule 19) dan merutekannya ke `wa-conversation`.
  2. Node `Prepare Media Payload` menyiapkan objek media message.
  3. Node `[HTTP] Evolution Get Base64` mengambil base64 dari `/chat/getBase64FromMediaMessage/okta_wa`.
  4. Node `[HTTP] Evolution Send Sticker` mengirim stiker webp animasi/statis ke nomor/grup via `/message/sendSticker/okta_wa`.

---

## ⚡ 5. VPS CLI Agent Runner (`/vps` / `/agent`)

Menghubungkan WhatsApp Okta langsung ke **OpenAI Codex CLI** (`codex-cli v0.147.0` dengan model `gpt-5.6-luna`) yang berjalan di host VPS.

### Keamanan Berlapis (Zero-Trust):
1. **Sender Authentication**: Hanya pesan dari nomor WhatsApp Okta (`$env.MY_WA_NUMBER`) yang diizinkan memicu runner (Rule 21 di `master-router-webhook`). Pengirim lain otomatis diabaikan.
2. **Command Blacklist**: Script runner `/home/dev/.local/bin/run-agent.sh` memblokir instruksi destruktif seperti `rm -rf /`, `mkfs`, `shutdown`, `reboot`, fork bombs, dsb.
3. **Execution Safeguard**: Dilengkapi `timeout 120s` dan eksekusi non-interaktif terisolasi tanpa background daemon berat (RAM tambahan 0 MB saat idle).
4. **Immediate Acknowledgment**: Saat perintah diterima, WhatsApp otomatis mengirim balasan awal bahwa tugas sedang diproses sebelum hasil dikirimkan.

### Cara Penggunaan via WhatsApp:
Kirim pesan dari nomor Okta ke bot WhatsApp:
```text
/agent cek sisa storage disk dan sisa ram vps
```
atau
```text
/vps restart container okta-backend lalu cek apakah sudah healthy
```
Bot akan membalas dengan status proses dan menyajikan laporan hasil eksekusi langsung ke chat WhatsApp.

---

## 📂 6. Status Seluruh Workflow n8n (14 Workflows Aktif)

Semua 14 workflow saat ini aktif dan tersinkronisasi 100% antara VPS dan repository lokal (`workflow/` dan `n8n/workflow/`):

1. `master-router-webhook` (`yViHMhfkTHv6uNFC`) — Active & Webhook live (`/webhook/wa-assistant`)
2. `wa-conversation` (`WmvJdI22Wr5O1k9y`) — Active (Memory, Persona, Titip Pesan, Stiker)
3. `vps-cli-runner` (`vpsCLIRunner0001`) — Active (Codex CLI via SSH)
4. `wa-to-gcal-assistant` (`U43zT3sJktIA9LaL`) — Active
5. `manda-gcal-assistant` (`TcoP1qZ8e4dvKU9F`) — Active
6. `gcal-to-wa-assistant` (`eCtWrmeyciUgg8f2`) — Active
7. `automatic-email-notifier-workflow` (`GNtnCWmLXbMF5iON`) — Active
8. `siam-announcement-notifier` (`OOvaMsCEOkqLuIL8`) — Active
9. `siam-presensi-notifier` (`H5lVT2ani2aaNkyV`) — Active
10. `automatic-brone-task-notifier` (`hpEygIQDgIYN7IVy`) — Active
11. `global-error-notifier` (`ERRnotif01UB2026`) — Active
12. `personal-porto-chatbot` (`vunnMOdxPHnUhABI`) — Active
13. `personal-porto-generate-article` (`wmv1KZ32E8OnHmYc`) — Active
14. `My workflow 4` (`M8b8EyT5nJkzsGPQ`) — Active
