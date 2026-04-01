# Automatic Email Notifier (AI Assistant)

Automatic Email Notifier reads incoming email from IMAP, summarizes it with Gemini, then sends the result to WhatsApp through Evolution API.

This project runs with Docker Compose and uses:
- n8n for workflow orchestration
- Evolution API for WhatsApp gateway
- PostgreSQL for n8n and Evolution data
- Gemini 2.5 Flash for summarization

## Features
- Email-to-WhatsApp automation flow
- Indonesian summary style with urgency score
- Multiple Gemini keys (random selection) to reduce rate-limit issues
- Containerized setup for VPS or local deployment

## Project Files
- `docker-compose.yaml`: service definitions for PostgreSQL, n8n, and Evolution API
- `.env.example`: environment variable template
- `automatic-email-notifier-workflow.json`: n8n workflow export file
- `init-dbs.sh`: PostgreSQL initialization script for multiple databases

## Prerequisites
- Docker and Docker Compose installed
- 2 WhatsApp accounts (one bot sender, one recipient)
- IMAP account credentials (email + app password)
- At least 1 Gemini API key (recommended 3-5 keys)

## Quick Start

### 1. Clone and enter project
```bash
git clone https://github.com/oktavsm/automatic-email-notifier.git
cd automatic-email-notifier
```

### 2. Configure environment
```bash
cp .env.example .env
```

Edit `.env` and set your real values.

Minimal required variables:
- `DB_USER`
- `DB_PASSWORD`
- `N8N_ENCRYPTION_KEY`
- `N8N_PORT`
- `EVO_PORT`
- `WA_API_TOKEN`
- `GEMINI_API_KEY`

Notes:
- `GEMINI_API_KEY` supports comma-separated values if you want multiple keys.
- Keep `.env` private and never commit it.

### 3. Start services
```bash
docker compose up -d
```

### 4. Verify containers
```bash
docker compose ps
```

## Configure Evolution API (WhatsApp)

Generate connection data for instance `okta_wa`:
```bash
curl --location --request GET 'http://localhost:9001/instance/connect/okta_wa' \
   --header 'apikey: YOUR_EVOLUTION_API_KEY'
```

Scan QR from the response with the WhatsApp account used as bot sender.

## Configure n8n Workflow

1. Open n8n at `http://localhost:<N8N_PORT>`.
2. Import `automatic-email-notifier-workflow.json`.
3. Configure credentials used by nodes:
    - IMAP credential: monitored mailbox and app password.
    - HTTP Header Auth credential: Evolution API key header (`apikey`).
4. Update destination WhatsApp number in the send-text node.
5. Replace placeholder Gemini keys in the code node.
6. Activate the workflow.

## Security Checklist

- Do not store secrets in workflow JSON files.
- Keep `.env` in `.gitignore`.
- Rotate keys immediately if they were ever committed.
- Use long random values for `DB_PASSWORD` and `N8N_ENCRYPTION_KEY`.
- Put n8n and Evolution API behind HTTPS reverse proxy in production.
- Restrict inbound ports with firewall rules.

## Troubleshooting

- `db` keeps restarting:
   - Check database credentials in `.env`.
   - Review logs with `docker compose logs db`.
- n8n cannot connect to PostgreSQL:
   - Ensure `db` is healthy via `docker compose ps`.
   - Confirm `DB_USER` and `DB_PASSWORD` are correct.
- WhatsApp message not sent:
   - Re-check Evolution API instance connection status.
   - Verify `WA_API_TOKEN` and header auth credential.
- Gemini request fails:
   - Validate API key format and quota.
   - Confirm node URL and model name are still valid.

## Operational Commands

```bash
docker compose up -d
docker compose down
docker compose logs -f
docker compose ps
```

## Contributing

Pull requests are welcome. For major changes, open an issue first to discuss the proposal.