# n8n Personal Assistant

Koleksi workflow n8n untuk personal automation, terutama:
- Email -> ringkasan AI -> notifikasi WhatsApp/Discord
- WhatsApp command -> parsing AI -> create Google Calendar event
- Google Calendar -> reminder otomatis ke WhatsApp

Repository ini sudah disiapkan agar aman dipublish ke public: nilai sensitif di file workflow telah diganti placeholder.

## Stack
- n8n (workflow orchestration)
- Evolution API (WhatsApp gateway)
- PostgreSQL (DB untuk n8n + Evolution API)
- Gemini 2.5 Flash (text generation/summarization)

## Struktur Folder

```text
.
├── docker-compose.yaml
├── .env.example
├── init-dbs.sh
├── brone-auth/
└── n8n/
    └── workflow/
        ├── calendar/
        │   ├── wa-to-gcal-assistant.json
        │   └── gcal-to-wa-assistant.json
        └── email/
            └── automatic-email-notifier-workflow.json
```

## Placeholder Di Workflow (Wajib Diganti Setelah Import)

Workflow publik memakai placeholder berikut:
- `{{GEMINI_API_KEY_PLACEHOLDER}}`
- `{{WHATSAPP_TARGET_NUMBER}}`
- `{{WA_INSTANCE_NAME}}`
- `{{PRIMARY_CALENDAR_ID}}`
- `{{GOOGLE_CALENDAR_ID}}`
- `{{WEBHOOK_ID}}`
- `{{DISCORD_WEBHOOK_USERNAME}}`
- `{{CONTACT_PERSON_1}}`
- `{{CONTACT_PERSON_2}}`
- `{{N8N_INSTANCE_ID}}`

Catatan:
- Placeholder ini memang sengaja tidak valid untuk menjaga data private.
- Setelah import ke n8n, update node yang relevan sesuai environment kamu.

## Quick Start

1. Clone repository
```bash
git clone https://github.com/<your-username>/n8n-personal-assistant.git
cd n8n-personal-assistant
```

2. Buat file environment
```bash
cp .env.example .env
```

3. Isi `.env` dengan nilai real, minimal:
- `DB_USER`
- `DB_PASSWORD`
- `N8N_ENCRYPTION_KEY`
- `N8N_PORT`
- `EVO_PORT`
- `WA_API_TOKEN`
- `GEMINI_API_KEY`

4. Jalankan service
```bash
docker compose up -d
docker compose ps
```

## Import Workflow Ke n8n

1. Buka n8n di `http://localhost:<N8N_PORT>`.
2. Import workflow dari folder:
   - `n8n/workflow/email/`
   - `n8n/workflow/calendar/`
3. Re-bind credentials di setiap node (IMAP, Google Calendar, HTTP Header Auth, Discord, dll).
4. Ganti semua placeholder dengan nilai environment kamu.
5. Test manual (Execute Workflow) sebelum diaktifkan.
6. Activate workflow.

## Evolution API Setup (Contoh)

Gunakan nama instance sesuai konfigurasi kamu (jangan hardcode dari contoh lama):

```bash
curl --location --request GET 'http://localhost:<EVO_PORT>/instance/connect/<WA_INSTANCE_NAME>' \
  --header 'apikey: <WA_API_TOKEN>'
```

## Security Checklist

- Jangan commit `.env`.
- Jangan simpan API key/token real di export workflow.
- Rotasi credential jika pernah terlanjur ke-push.
- Batasi akses port n8n dan Evolution API.
- Gunakan reverse proxy HTTPS untuk deployment publik.

## Operasional

```bash
docker compose up -d
docker compose down
docker compose logs -f
docker compose ps
```

## Roadmap Singkat

- Standardisasi placeholder lint workflow
- Versioning workflow per use-case
- Template onboarding agar import workflow lebih cepat