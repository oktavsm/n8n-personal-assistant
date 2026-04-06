# n8n Personal Assistant

This is my personal n8n automation workspace.

It started as an email notifier project, then grew into a broader personal assistant setup with multiple workflows.

Main use cases:
- Email to AI summary to WhatsApp or Discord
- WhatsApp command to AI parser to Google Calendar event
- Google Calendar reminder to WhatsApp

This repo is public-safe: sensitive values inside exported workflows have been replaced with placeholders.

## Tech Stack
- n8n
- Evolution API
- PostgreSQL
- Gemini 2.5 Flash

## Project Structure

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

## Workflow Placeholders

These placeholders are intentionally left in workflow JSON files and must be replaced after import:
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

## Quick Start

1. Clone the repository.
```bash
git clone https://github.com/<your-username>/n8n-personal-assistant.git
cd n8n-personal-assistant
```

2. Create `.env` from template.
```bash
cp .env.example .env
```

3. Fill real values in `.env` (minimum):
- `DB_USER`
- `DB_PASSWORD`
- `N8N_ENCRYPTION_KEY`
- `N8N_PORT`
- `EVO_PORT`
- `WA_API_TOKEN`
- `GEMINI_API_KEY`

4. Start containers.
```bash
docker compose up -d
docker compose ps
```

## Evolution API Setup (Create Instance + Connect)

After containers are up, create a WhatsApp instance first.

1. Create instance (POST)
```bash
curl --location --request POST 'http://localhost:<EVO_PORT>/instance/create' \
  --header 'apikey: <WA_API_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data-raw '{
    "instanceName": "<WA_INSTANCE_NAME>",
    "qrcode": true,
    "integration": "WHATSAPP-BAILEYS"
  }'
```

2. Get QR data (GET connect)
```bash
curl --location --request GET 'http://localhost:<EVO_PORT>/instance/connect/<WA_INSTANCE_NAME>' \
  --header 'apikey: <WA_API_TOKEN>'
```

3. Scan the QR code with your WhatsApp account.

4. Verify instance status (optional but recommended)
```bash
curl --location --request GET 'http://localhost:<EVO_PORT>/instance/connectionState/<WA_INSTANCE_NAME>' \
  --header 'apikey: <WA_API_TOKEN>'
```

If status is connected/open, your instance is ready.

## Import Workflows to n8n

1. Open n8n at `http://localhost:<N8N_PORT>`.
2. Import workflows from:
- `n8n/workflow/email/`
- `n8n/workflow/calendar/`
3. Re-bind credentials in each workflow node (IMAP, Google Calendar, HTTP Header Auth, Discord, and others you use).
4. Replace all placeholders with your own values.
5. Run manual test execution first.
6. Activate workflows.

## Security Notes

- Never commit `.env`.
- Never keep real keys/tokens in exported workflow JSON.
- Rotate credentials immediately if they were ever exposed.
- Restrict inbound ports and use HTTPS reverse proxy for internet-facing deployment.

## Common Commands

```bash
docker compose up -d
docker compose down
docker compose logs -f
docker compose ps
```