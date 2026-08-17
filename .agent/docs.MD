# Project Documentation & Change History

Documented updates and architecture improvements implemented for local development, scraping reliability, and automated CI/CD deployment.

---

## 📅 Summary of Changes (August 2026)

### 1. 🛠️ Local Development & Visual Debugging (`brone-auth`)

- **Configurable Headless Mode & Executable Fallback**:
  - Modified [brone-auth/server.js](file:///home/oktaavsm/Documents/Work/n8n-personal-assistant/brone-auth/server.js) so `headless` mode listens to `process.env.HEADLESS`.
  - Running `HEADLESS=false npm run dev` locally opens a visual Google Chrome window to debug DOM changes, login flows, and scraping in real-time.
  - Made `executablePath` optional in `server.js` (only passed when `PUPPETEER_EXECUTABLE_PATH` env is defined, e.g., in Docker), allowing local Node to use bundled Chromium without path errors.

- **Multi-Strategy Token Capture & Dynamic KRS Auto-Fetch**:
  - Enhanced `extractBearerTokenFromRuntime` to intercept background network requests (`getPertanyaanSurvey`, `getProfil`, `getJadwal`, etc.), inspect Keycloak SSO JSON responses (`/protocol/openid-connect/token`), and scan `window.Sso_ub.KEYCLOAK.token`, `localStorage` (`dataAuth`), and `sessionStorage`.
  - Added **Dynamic KRS Auto-Fetch** in `POST /get-siam-pengumuman`: If the `courses` list payload is omitted in n8n, `brone-auth` dynamically calls `https://api.ub.ac.id/siam/mahasiswa/getKRS` to extract the student's active semester courses, class codes, year, and semester automatically! No manual course array hardcoding required in n8n.
  - Refactored `POST /get-siam-pengumuman` and `POST /get-siam-presensi` endpoints to use `runWithSiamRetries` and `getSiamAuth`, preventing `Failed to capture Bearer token` HTTP 500 errors.

- **Developer Tooling**:
  - Added `"dev": "node --watch server.js"` to [brone-auth/package.json](file:///home/oktaavsm/Documents/Work/n8n-personal-assistant/brone-auth/package.json).
  - Created [brone-auth/test.http](file:///home/oktaavsm/Documents/Work/n8n-personal-assistant/brone-auth/test.http) for instant testing using VS Code REST Client / Bruno / Postman.

---

### 2. 🛡️ Security & Git Hygiene

- Added `*.http` to [.gitignore](file:///home/oktaavsm/Documents/Work/n8n-personal-assistant/.gitignore).
- Removed `brone-auth/test.http` from Git tracking (`git rm --cached`).
- Rebased and cleaned Git commit history on `feat/update` and `master` branches to ensure sensitive credentials were completely erased from GitHub remote history.

---

### 3. 🚀 Automated CI/CD Pipeline (GHCR + SSH Deployment)

- Created [.github/workflows/deploy-brone-auth.yml](file:///home/oktaavsm/Documents/Work/n8n-personal-assistant/.github/workflows/deploy-brone-auth.yml):
  - **Triggers**: Push to `main`, `master`, `feat/update`, and manual `workflow_dispatch`.
  - **Cloud Build**: Builds Docker image in GitHub Actions runner and pushes to GitHub Container Registry (`ghcr.io/oktavsm/n8n-personal-assistant/brone-auth:latest`).
  - **VPS Deploy**: SSHs into VPS (`dev@proxy.bccdev.id:11023`) targeting `/home/dev/projects/docker/n8n-personal-assistant`.
  - **Zero VPS Overhead**: Executes `docker compose pull brone-auth && docker compose up -d brone-auth`, restarting the service in ~5 seconds without consuming VPS build resources.

- Updated [docker-compose.yaml](file:///home/oktaavsm/Documents/Work/n8n-personal-assistant/docker-compose.yaml):
  - Attached image tag `ghcr.io/oktavsm/n8n-personal-assistant/brone-auth:latest` to the `brone-auth` service definition.

---

## 💻 How to Work & Deploy

### Local Development Loop (`brone-auth`)
```bash
cd brone-auth
npx puppeteer browsers install chrome # (Once)
HEADLESS=false npm run dev
```

### Deployment Flow
Simply commit and push changes to `master` or `feat/update`:
```bash
git add .
git commit -m "feat: your feature description"
git push origin master
```
GitHub Actions will automatically build the container and deploy to VPS.
