# issue-audit-status-2026-04-22.md

## Ringkasan Audit

Status saat audit: **belum 100% tersolve**, tapi mayoritas sudah membaik dan berjalan.

## Status per Isu

### 1) n8n gagal init DB (`EAI_AGAIN db`)

**Status:** **Partially solved**

**Temuan runtime saat ini:**
- `notifier_db` sekarang **Up (healthy)**
- `notifier_n8n` sekarang **Up**
- `notifier_wa_gateway` sekarang **Up**

**Gap yang masih ada:**
- Container `notifier_db` yang sedang berjalan masih punya restart policy:
  - `restart=no`
- Padahal di `docker-compose.yaml` sudah ditulis `restart: always`.

**Artinya:**
- Perbaikan di file compose sudah ada, tapi **belum ter-apply ke container aktif** (container DB belum direcreate sejak config diubah).

**Aksi yang perlu dilakukan agar benar-benar permanen:**
```bash
docker compose up -d --force-recreate db
docker inspect notifier_db --format '{{.HostConfig.RestartPolicy.Name}}'
```
Target akhir harus keluar: `always`.

---

### 2) Storage penuh + prevention

**Status:** **Solved (configured and running)**

**Temuan yang tervalidasi:**
- Log rotation aktif di level Docker daemon:
  - `/etc/docker/daemon.json` berisi `json-file`, `max-size=10m`, `max-file=3`.
- Log rotation aktif pada container utama:
  - `notifier_db`, `notifier_n8n`, `notifier_wa_gateway`, `notifier_brone_auth`
  - semua terbaca `logDriver=json-file max-size=10m max-file=3`.
- Guard script tersedia dan terjadwal:
  - `/usr/local/sbin/docker-storage-guard.sh` **ada** dan executable.
  - `/etc/cron.d/docker-storage-guard` **ada** (jadwal harian 03:20).
- Bukti jalan:
  - `/var/log/docker-storage-guard.log` berisi histori eksekusi cleanup.
- Kondisi disk saat audit:
  - `/` di **71%** (masih aman, di bawah threshold 85%).

## Kesimpulan

1. **Prevention storage sudah ada dan berjalan.**
2. **Issue n8n init DB sudah pulih secara operasional saat ini**, tetapi belum fully hardened karena restart policy container DB aktif masih `no`.
3. Setelah DB container direcreate agar restart policy menjadi `always`, status isu bisa dianggap **fully resolved**.
