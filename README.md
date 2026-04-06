# n8n Personal Assistant

This repository is my personal automation hub built on n8n.

It started as a single email notifier, then evolved into a multi-workflow personal assistant for daily reminders, campus tasks, and WhatsApp-driven automation.

All exported workflows in this repo are sanitized for public sharing.

## Tech Stack

- n8n
- Evolution API (WhatsApp gateway)
- PostgreSQL
- Gemini 2.5 Flash
- Custom `brone-auth` helper service

## Services Overview

- `db` (PostgreSQL)
  - Stores data for both n8n (`n8n_db`) and Evolution API (`evo_db`).
- `n8n`
  - Workflow orchestrator and webhook entrypoint.
- `evolution-api`
  - WhatsApp gateway used by notification and command workflows.
- `brone-auth`
  - Internal helper API (Puppeteer-based) that logs in to Brone/SIAM and fetches academic data for n8n workflows.

## Current Workflows

Located in `n8n/workflow/`:

- `automatic-email-notifier-workflow.json`
  - Reads incoming email, summarizes with Gemini, and sends notification to WhatsApp/Discord.
- `wa-to-gcal-assistant.json`
  - Reads WhatsApp command and creates Google Calendar events.
- `gcal-to-wa-assistant.json`
  - Periodically checks calendar windows and sends smart reminders to WhatsApp.
- `automatic-brone-task-notifier.json`
  - Monitors Brone task updates and sends notifications.
- `siam-announcement-notifier.json`
  - Sends SIAM announcement reminders to WhatsApp.
- `siam-presensi-notifier.json`
  - Sends SIAM attendance/presence reminders to WhatsApp.
- `router-webhook.json`
  - Central webhook router for WhatsApp command routing and response handling.

## Repository Structure

```text
.
├── docker-compose.yaml
├── .env.example
├── init-dbs.sh
├── brone-auth/
│   ├── Dockerfile
│   ├── package.json
│   └── server.js
└── n8n/
    └── workflow/
        ├── automatic-brone-task-notifier.json
        ├── automatic-email-notifier-workflow.json
        ├── gcal-to-wa-assistant.json
        ├── router-webhook.json
        ├── siam-announcement-notifier.json
        ├── siam-presensi-notifier.json
        └── wa-to-gcal-assistant.json
```

## Sanitized Placeholders

Sensitive values were replaced with placeholders in workflow exports:

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
- `{{N8N_CREDENTIAL_ID}}`

Replace these values after importing workflows into your own n8n instance.

## Setup

1. Clone repository.

```bash
git clone https://github.com/<your-username>/n8n-personal-assistant.git
cd n8n-personal-assistant
```

2. Create environment file.

```bash
cp .env.example .env
```

3. Fill required variables in `.env`.

Minimum required:
- `DB_USER`
- `DB_PASSWORD`
- `BRONE_USERNAME`
- `BRONE_PASSWORD`
- `N8N_ENCRYPTION_KEY`
- `N8N_PORT`
- `EVO_PORT`
- `WA_API_TOKEN`
- `GEMINI_API_KEY`

Important compose notes:
- `docker-compose.yaml` currently sets `N8N_HOST` and `WEBHOOK_URL` to a fixed domain (`oktaavsm.bccdev.id`).
- If you run locally or on another server, update those values in `docker-compose.yaml` first.
- Named volumes are configured as external:
  - `email-notifier_postgres_data`
  - `email-notifier_evolution_instances`
  Create them before first run if they do not exist.

4. Start services.

```bash
docker volume create email-notifier_postgres_data
docker volume create email-notifier_evolution_instances
docker compose up -d --build
docker compose ps
```

## brone-auth API Endpoints

`brone-auth` is consumed internally by n8n workflows and exposes these endpoints:

- `POST /get-cookies`
  - Logs in to Brone and returns `cookieString` plus `sesskey`.
- `POST /get-siam-pengumuman`
  - Logs in to SIAM and returns filtered class announcements.
- `POST /get-siam-presensi`
  - Logs in to SIAM and returns active attendance/presence data.

These endpoints run on the internal Docker network (`http://brone-auth:3000`) and are not meant to be exposed publicly.

## Evolution API Instance Setup

After containers are running, create and connect your WhatsApp instance.

1. Create instance.

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

2. Request connect data / QR.

```bash
curl --location --request GET 'http://localhost:<EVO_PORT>/instance/connect/<WA_INSTANCE_NAME>' \
  --header 'apikey: <WA_API_TOKEN>'
```

3. Scan the QR from your WhatsApp app.

4. Verify connection status.

```bash
curl --location --request GET 'http://localhost:<EVO_PORT>/instance/connectionState/<WA_INSTANCE_NAME>' \
  --header 'apikey: <WA_API_TOKEN>'
```

If the state is `open` or `connected`, the instance is ready.

## Import and Configure Workflows

1. Open n8n at `http://localhost:<N8N_PORT>`.
2. Import all files from `n8n/workflow/`.
3. Recreate or rebind credentials in n8n:
   - IMAP
   - Google Calendar OAuth2
   - HTTP Header Auth (Evolution API)
   - Discord Webhook (if used)
4. For Brone/SIAM workflows, make sure request bodies include valid credentials (`BRONE_USERNAME`, `BRONE_PASSWORD`) and required course metadata where applicable.
5. Replace placeholder values in each workflow.
6. Run manual test execution for each workflow.
7. Activate workflows.

## Security Notes

- Keep `.env` private.
- Do not commit real secrets into workflow exports.
- Rotate credentials immediately if previously exposed.
- Put n8n and Evolution API behind HTTPS reverse proxy for public deployments.

## Useful Commands

```bash
docker compose up -d --build
docker compose down
docker compose logs -f
docker compose ps
```