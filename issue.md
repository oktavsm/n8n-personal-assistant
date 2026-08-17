# Issue: `notifier_brone_auth` Fills Root Disk via Puppeteer/Chrome Temporary Profiles

## Status

- **Severity:** High
- **Component:** `notifier_brone_auth`
- **Environment:** Docker host `okta-pg`
- **Observed:** Root filesystem `/` reached **100% usage**
- **Primary suspected root cause:** Puppeteer/Chrome temporary profiles accumulating under `/tmp` inside the `notifier_brone_auth` container
- **Current affected storage:** Approximately **5.2 GB** in the container writable layer, specifically `/tmp`

---

## 1. Problem Summary

The Docker host has a 23 GB root filesystem:

```text
/dev/sda1  23G  23G  0  100% /
```

Investigation showed that Docker is responsible for most of the disk usage:

```text
/var                  13G
/var/lib              13G
/var/lib/docker       12G
/var/lib/docker/overlay2  11G
```

Docker's `system df` identified `notifier_brone_auth` as the largest writable container:

```text
notifier_brone_auth    6.1GB
```

The container's writable layer was identified as:

```text
/var/lib/docker/overlay2/c16dff0f6cad861d54b3c0c03c77b382d74e2f8531c76ba1a3ca88c88a384e27/diff
```

Inspection showed:

```text
5.2G .../diff/tmp
```

The contents are dominated by temporary Puppeteer/Chrome profiles:

```text
puppeteer_dev_profile-*
com.google.Chrome.*
```

Examples observed included individual profiles ranging from tens to hundreds of MB, with many profiles accumulated over time.

This strongly indicates that Puppeteer/Chrome temporary browser profiles are not being cleaned up reliably.

---

## 2. Evidence

### Host disk

```text
/dev/sda1        23G   23G     0 100% /
```

### Docker usage

```text
Images          11        11        5.008GB
Containers      11        11        6.22GB
Local Volumes    8         3      676.6MB
Build Cache     11         0           0B
```

### Largest writable container

```text
notifier_brone_auth    6.1GB
```

### Overlay2

```text
5.2G /var/lib/docker/overlay2/c16dff0f6cad861d54b3c0c03c77b382d74e2f8531c76ba1a3ca88c88a384e27
```

The layer maps to `notifier_brone_auth`:

```bash
docker inspect --format '{{.GraphDriver.Data.UpperDir}}' notifier_brone_auth
```

Result:

```text
/var/lib/docker/overlay2/c16dff0f6cad861d54b3c0c03c77b382d74e2f8531c76ba1a3ca88c88a384e27/diff
```

### Directory breakdown

```text
5.2G .../diff/tmp
19M  .../diff/root
316K .../diff/app
184K .../diff/var
84K  .../diff/usr
```

Therefore the disk consumption is not primarily application source, database data, Docker images, Docker volumes, or system logs.

---

## 3. Root Cause Hypothesis

The application uses Puppeteer/Chrome and creates temporary browser profiles under `/tmp`.

The observed pattern is:

```text
/tmp/
├── puppeteer_dev_profile-*
├── com.google.Chrome.chrome_chrome_url_fetcher_*
├── com.google.Chrome.chrome_chrome_Unpacker_*
└── ...
```

These directories are accumulating instead of being reliably removed after browser jobs finish.

Likely causes to investigate:

1. `browser.close()` is not always executed.
2. Browser/page cleanup is missing from `finally` blocks.
3. Browser processes crash or are force-killed before Puppeteer can clean temporary profiles.
4. Multiple browser instances are launched repeatedly without deterministic cleanup.
5. Custom `userDataDir` / temporary profile handling may create persistent profiles without cleanup.
6. The application may be terminating individual browser/page objects but not the entire browser process.
7. Long-running workers may accumulate temporary files even when browser sessions appear successful.

Do **not** assume one specific cause until the source code is inspected.

---

## 4. Immediate Cleanup

Once the container is accessible, disposable Puppeteer/Chrome temporary files can be removed from inside the container:

```bash
docker exec notifier_brone_auth sh -c 'rm -rf /tmp/puppeteer_dev_profile-* /tmp/com.google.Chrome.*'
```

After cleanup:

```bash
df -h /
```

and:

```bash
docker system df
```

The expected disk recovery is approximately **5 GB**, depending on files created between inspection and cleanup.

### Important

Do **not** manually delete:

```text
/var/lib/docker/overlay2/*
```

The overlay2 directory is Docker-managed storage. Manual deletion can corrupt the container filesystem.

Do not delete PostgreSQL or MariaDB volumes as part of this issue.

---

## 5. Required Permanent Fix

The application must guarantee cleanup of Puppeteer/Chrome resources and temporary profiles.

### Browser lifecycle

All browser launches should follow a structure equivalent to:

```js
let browser;

try {
  browser = await puppeteer.launch(...);

  // perform work
} finally {
  if (browser) {
    try {
      await browser.close();
    } catch (error) {
      // log cleanup failure
    }
  }
}
```

The exact implementation should follow the existing project's architecture.

### Page lifecycle

Pages should also be closed deterministically:

```js
let page;

try {
  page = await browser.newPage();

  // perform work
} finally {
  if (page) {
    try {
      await page.close();
    } catch (error) {
      // log cleanup failure
    }
  }
}
```

Avoid relying exclusively on garbage collection or process shutdown for cleanup.

---

## 6. Temporary Profile Strategy

Investigate whether the application explicitly sets:

```js
userDataDir
```

or creates temporary Chrome profiles manually.

If a custom temporary profile is required:

1. Generate a unique temporary directory.
2. Use it for exactly one browser lifecycle.
3. Close the browser.
4. Remove the temporary directory in `finally`.
5. Ensure cleanup also happens when the job fails.

Example pattern:

```js
const fs = require('fs/promises');
const os = require('os');
const path = require('path');

const profileDir = await fs.mkdtemp(
  path.join(os.tmpdir(), 'brone-puppeteer-')
);

let browser;

try {
  browser = await puppeteer.launch({
    userDataDir: profileDir,
  });

  // work
} finally {
  if (browser) {
    try {
      await browser.close();
    } catch {}

  try {
    await fs.rm(profileDir, {
      recursive: true,
      force: true,
    });
  } catch (error) {
    // log cleanup failure
  }
}
```

Adapt this to the project's actual Puppeteer version and codebase.

---

## 7. Important: Do Not Just Add a Blind `/tmp` Cron Cleanup

A periodic cleanup can be used as a **defense-in-depth measure**, but it should not replace application-level cleanup.

Avoid blindly deleting all `/tmp` content while Chrome/Puppeteer is running.

If a scheduled cleanup is introduced, it must:

- target only application-owned directories;
- avoid deleting active browser profiles;
- use a safe age threshold;
- run outside active job lifecycles where possible.

Prefer application-owned prefixes such as:

```text
/tmp/brone-puppeteer-*
```

instead of generic:

```text
/tmp/*
```

---

## 8. Docker-Level Improvements

Add operational protections so a future cleanup failure does not silently consume the entire server.

### Docker log rotation

Ensure Docker's `json-file` logging driver has rotation configured.

Example daemon configuration:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Only apply this if it matches the host's Docker configuration strategy.

Existing logs were not the primary issue here, but rotation is still recommended.

### Monitoring

Add monitoring/alerting for:

```text
/root filesystem usage > 80%
/root filesystem usage > 90%
```

Also monitor container writable-layer growth if practical.

---

## 9. Verification / Acceptance Criteria

The fix is considered successful when all of the following are true:

### Functional

- Puppeteer/Chrome jobs continue to work normally.
- Browser sessions are closed on success.
- Browser sessions are closed on errors.
- Temporary browser profiles are removed after completed jobs.

### Storage

After repeated browser jobs:

```bash
du -sh /tmp
```

must not continuously grow.

Inside the container:

```bash
du -sh /tmp
```

should remain bounded and should not accumulate hundreds/thousands of `puppeteer_dev_profile-*` directories.

### Regression test

Run a representative browser workload repeatedly, for example:

```text
10 jobs
50 jobs
100 jobs
```

After each batch, measure:

```bash
du -sh /tmp
docker system df
df -h /
```

The writable layer should remain approximately stable rather than increasing by hundreds of MB/GB per batch.

### Error-path test

Force a browser job to fail and verify that:

- the browser closes;
- the page closes;
- the temporary profile is removed;
- no orphan Chrome/Puppeteer profile remains.

### Long-running test

Leave the service running for at least several hours / representative production workload and confirm that `/tmp` does not grow continuously.

---

## 10. Useful Diagnostic Commands

Identify container writable layer:

```bash
docker inspect --format '{{.GraphDriver.Data.UpperDir}}' notifier_brone_auth
```

Inspect temporary storage:

```bash
docker exec notifier_brone_auth sh -c 'du -xhd1 /tmp 2>/dev/null | sort -h'
```

Find Puppeteer profiles:

```bash
docker exec notifier_brone_auth sh -c 'find /tmp -maxdepth 1 -type d -name "puppeteer_dev_profile-*" -print'
```

Find Chrome temporary directories:

```bash
docker exec notifier_brone_auth sh -c 'find /tmp -maxdepth 1 -type d -name "com.google.Chrome.*" -print'
```

Monitor container size:

```bash
docker system df -v
```

Monitor host:

```bash
df -h
```

---

## 11. Non-Goals

This issue is **not** currently attributed to:

- PostgreSQL volume growth
- MariaDB volume growth
- Docker image accumulation
- Docker build cache
- systemd journal growth
- Docker JSON logs

Those were investigated and found to be relatively small compared with the 5.2 GB `/tmp` accumulation.

---

## 12. Codex Task

Inspect the `notifier_brone_auth` source code and identify every Puppeteer/Chrome lifecycle.

For each browser lifecycle:

1. Find where browser instances are created.
2. Find where pages/contexts are created.
3. Verify cleanup on success.
4. Verify cleanup on exceptions.
5. Verify cleanup on timeout/cancellation.
6. Identify whether custom `userDataDir` or temporary profiles are used.
7. Ensure temporary profile directories are explicitly cleaned up.
8. Avoid leaking browser processes.
9. Add tests for cleanup on both success and failure paths.
10. Add a lightweight operational safeguard if appropriate.

Do not change unrelated application behavior.

Do not delete persistent application data.

Do not modify PostgreSQL/MariaDB storage.

Do not manually manipulate Docker's `overlay2` directory.

The final implementation should make temporary browser storage bounded and prevent `/tmp` from growing indefinitely during long-running service operation.
