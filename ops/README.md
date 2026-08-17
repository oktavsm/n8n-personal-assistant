# Storage guard operations

`brone-temp-guard.service` runs every five minutes through
`brone-temp-guard.timer`. It removes only stale profiles created under
`/tmp/brone-puppeteer/profile-*` and stale Chrome runtime sockets under
`/tmp/brone-runtime`; it never scans or removes generic `/tmp` content. A
profile is eligible after 30 minutes and is skipped while Chrome is still
running with that profile as `--user-data-dir`.

The service writes its state to the system journal. Disk usage at 75% is logged
as a warning and at 85% as critical; connect the host journal to the preferred
alerting service if remote notifications are required.

Install or update the host files after changing them in this directory:

```bash
sudo install -m 0755 ops/brone-temp-guard.sh /usr/local/sbin/brone-temp-guard.sh
sudo install -m 0644 ops/brone-temp-guard.service /etc/systemd/system/brone-temp-guard.service
sudo install -m 0644 ops/brone-temp-guard.timer /etc/systemd/system/brone-temp-guard.timer
sudo systemctl daemon-reload
sudo systemctl enable --now brone-temp-guard.timer
```
