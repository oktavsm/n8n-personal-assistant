# issue-storage.md

## Ringkasan Masalah

Host sempat mengalami kondisi **storage hampir penuh** (`/` mencapai ~99.9%) dan muncul warning **zombie process** dalam jumlah besar.  
Dampaknya: service berisiko tidak stabil (restart loop, gagal write log/temp file, performa turun).

## Temuan Utama

1. Pemakaian terbesar ada di `/var/lib/docker` (khususnya `overlay2` + image/cache lama).
2. Ada container yang sempat restart loop, sehingga berpotensi menambah tekanan log.
3. Belum ada pembatasan default ukuran log Docker di level host.

## Perbaikan yang Sudah Dilakukan

1. Cleanup aman tanpa mengganggu volume data aktif:
   - `docker container prune`
   - `docker image prune -a`
   - `docker builder prune -a`
   - `journalctl --vacuum-time=...`
2. Pembersihan cache user aman (`~/.cache`, npm cache).
3. Pencegahan zombie process pada `brone-auth`:
   - pakai init process (`dumb-init` + `init: true`)
   - graceful shutdown + cleanup browser process.
4. Pencegahan storage penuh level host:
   - `/etc/docker/daemon.json` diset:
     - `log-driver: json-file`
     - `max-size: 10m`
     - `max-file: 3`
   - cron guard harian:
     - `/etc/cron.d/docker-storage-guard`
     - script: `/usr/local/sbin/docker-storage-guard.sh`

## SOP Kalau Kejadian Terulang

### 1. Cek cepat kondisi host

```bash
df -h
free -h
docker ps
docker system df -v
sudo du -xhd1 /var | sort -h
sudo du -xhd1 /var/lib/docker | sort -h
```

### 2. Identifikasi container bermasalah

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}'
docker logs --tail 200 <container_name>
docker inspect --format 'RestartCount={{.RestartCount}} Status={{.State.Status}}' <container_name>
```

Jika ada restart loop, selesaikan root cause dulu (DB/ENV/network/config), jangan hanya restart berulang.

### 3. Cleanup aman (prioritas)

```bash
docker container prune -f
docker image prune -a -f
docker builder prune -a -f
sudo journalctl --vacuum-time=7d
```

> Hindari `docker volume prune` kecuali sudah yakin volume itu tidak dipakai dan datanya boleh hilang.

### 4. Verifikasi sesudah cleanup

```bash
df -h
docker system df -v
docker ps
```

Pastikan service utama tetap `Up` dan sisa storage kembali aman.

## Checklist Preventif

- [ ] Pastikan `/etc/docker/daemon.json` tetap berisi log rotation.
- [ ] Pastikan cron `/etc/cron.d/docker-storage-guard` ada dan aktif.
- [ ] Audit disk mingguan (`df -h`, `docker system df -v`).
- [ ] Hindari image dangling menumpuk setelah build/deploy.
- [ ] Tangani restart loop secepatnya agar log tidak membengkak.

## Catatan Operasional

- Threshold aman praktis: usahakan `/` di bawah **80–85%**.
- Jika beban service bertambah terus, pertimbangkan tambah kapasitas disk root.
- Simpan cleanup sebagai rutinitas, bukan tunggu sampai disk kritis.
