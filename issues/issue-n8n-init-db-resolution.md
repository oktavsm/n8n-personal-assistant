# issue-n8n-init-db-resolution.md

## Ringkasan Masalah

`n8n` gagal inisialisasi karena tidak bisa mengakses service database `db`, sehingga container `notifier_n8n` masuk restart loop.

Error berulang:

```text
There was an error initializing DB
getaddrinfo EAI_AGAIN db
```

## Temuan Utama

1. `docker compose ps --all` menunjukkan:
   - `notifier_db` **Exited (0)** sejak ~45 jam lalu.
   - `notifier_n8n` **Up beberapa detik** lalu restart lagi.
   - `notifier_wa_gateway` juga restart loop (ikut bergantung ke DB yang sama).
2. `docker compose logs db` di akhir log menunjukkan:
   - `received fast shutdown request`
   - DB shutdown normal (bukan crash), exit code `0`.
3. Di `docker-compose.yaml`, service `db` **belum memiliki restart policy**.
4. Service `n8n` dan `evolution-api` punya `restart: always`, jadi keduanya hidup lagi, tapi gagal karena DB tidak ikut naik.

## Akar Masalah (Root Cause)

PostgreSQL container (`db`) pernah dihentikan normal (manual stop / host restart), lalu tidak auto-start kembali karena tidak ada `restart` policy. Akibatnya hostname `db` tidak tersedia stabil untuk service lain, dan n8n gagal init DB.

## Planning Solusi

### 1. Recovery cepat (operasional sekarang)

1. Start DB dulu:
   ```bash
   docker compose up -d db
   ```
2. Setelah DB sehat, restart service yang tergantung DB:
   ```bash
   docker compose restart n8n evolution-api
   ```
3. Verifikasi:
   ```bash
   docker compose ps
   docker compose logs --tail=100 n8n
   ```

### 2. Perbaikan permanen (konfigurasi)

Tambahkan restart policy pada service `db` di `docker-compose.yaml`:

```yaml
services:
  db:
    restart: always
```

Tujuannya supaya setelah reboot host / Docker daemon restart, DB otomatis naik sebelum/bersamaan service lain.

### 3. Hardening tambahan

1. Jalankan stack lewat satu perintah:
   ```bash
   docker compose up -d
   ```
   (hindari start service parsial tanpa dependency).
2. Tambahkan SOP quick-check pasca reboot:
   - `docker compose ps --all`
   - pastikan `db`, `n8n`, `evolution-api` status `Up`.
3. (Opsional) Tambah alert sederhana jika `db` state `Exited` > N menit.

## Dampak ke Fitur

Selama DB down:
- n8n webhook/router tidak bisa inisialisasi.
- Workflow otomatis berhenti.
- Evolution API ikut gagal migrasi/boot karena tidak bisa akses `db:5432`.
