# Puppeteer/Chrome Storage Remediation — 2026-08-14

## Status

**Implemented and verified** on host `okta-pg`.

Issue awal: temporary Chrome/Puppeteer profiles pada container
`notifier_brone_auth` dapat tertinggal di `/tmp`, lalu membengkakkan writable
layer Docker hingga root filesystem penuh.

## Root Cause

`brone-auth` sudah memanggil `browser.close()` pada lifecycle utamanya, tetapi
masih mengandalkan temporary profile bawaan Puppeteer. Cleanup bawaan tidak
selalu selesai pada jalur timeout, crash, atau force-kill, sehingga direktori
`puppeteer_dev_profile-*` dan artifact `com.google.Chrome.*` dapat tertinggal.

Container juga menjalankan browser cukup sering melalui workflow SIAM, sehingga
leak kecil dapat terakumulasi dengan cepat.

## Perubahan Aplikasi

### 1. Profile directory milik aplikasi

Ditambahkan `brone-auth/browser-session.js` sebagai satu-satunya helper untuk
membuat dan menutup sesi browser.

- Setiap launch membuat profile unik pada `/tmp/brone-puppeteer/profile-*`.
- Profile tersebut diteruskan ke Puppeteer melalui `userDataDir`.
- Setelah sesi selesai, profile dihapus eksplisit dengan `fs.rm(..., force)`.
- Jika launch gagal, profile dan slot browser tetap dibersihkan.
- Direktori di luar prefix profile milik aplikasi ditolak; helper tidak dapat
  menghapus path arbitrary.

### 2. Chrome runtime directory

Compose menetapkan `TMPDIR=/tmp/brone-runtime`.

Chrome memerlukan runtime socket directory di `TMPDIR`; helper sekarang
membuatnya sebelum launch dan menghapus artifact `com.google.Chrome.*` setelah
browser ditutup. Ini memperbaiki error berikut yang sempat muncul saat runtime
directory belum ada:

```text
Failed to create a ProcessSingleton for your profile directory
```

### 3. Lifecycle dan concurrency

Semua lokasi `puppeteer.launch()` di `server.js` memakai helper sesi yang sama.

- Browser ditutup dengan timeout yang dapat dikonfigurasi.
- Bila close gagal, proses browser dicoba dihentikan sebelum cleanup profile.
- Maksimum satu browser aktif secara default untuk mencegah lonjakan profile
  paralel dari polling SIAM.
- Graceful shutdown menutup sesi aktif dan Compose memberi stop grace period
  45 detik.
- Endpoint internal `GET /health` menyediakan jumlah browser aktif/antrian.

Variabel konfigurasi Compose:

```text
BRONE_BROWSER_PROFILE_ROOT=/tmp/brone-puppeteer
TMPDIR=/tmp/brone-runtime
BRONE_BROWSER_CONCURRENCY=1
BRONE_BROWSER_QUEUE_TIMEOUT_MS=60000
BRONE_BROWSER_CLOSE_TIMEOUT_MS=10000
```

## Operational Safeguard

Ditambahkan systemd service dan timer:

```text
/usr/local/sbin/brone-temp-guard.sh
/etc/systemd/system/brone-temp-guard.service
/etc/systemd/system/brone-temp-guard.timer
```

Timer aktif setiap **5 menit** dan bersifat persistent setelah host reboot.

Guard melakukan hal berikut:

1. Memeriksa penggunaan root filesystem.
2. Menulis warning pada 75% dan critical pada 85% ke system journal.
3. Menghapus hanya `/tmp/brone-puppeteer/profile-*` yang stale lebih dari 30
   menit.
4. Tidak menghapus profile bila Chrome masih terlihat memakai
   `--user-data-dir` tersebut.
5. Menghapus artifact stale `com.google.Chrome.*` hanya di
   `/tmp/brone-runtime` dan hanya saat tidak ada proses Chrome aktif.
6. Menggunakan lock file agar dua eksekusi guard tidak berjalan bersamaan.

Guard sengaja **tidak** menghapus `/tmp/*` atau generic
`/tmp/puppeteer_dev_profile-*`, karena itu bisa mengganggu browser yang masih
aktif atau aplikasi lain.

Perintah status:

```bash
systemctl status brone-temp-guard.timer
journalctl -u brone-temp-guard.service -n 50 --no-pager
docker exec notifier_brone_auth node -e "fetch('http://127.0.0.1:3000/health').then(async r => console.log(await r.text()))"
```

## Docker Storage Guard

Script host `/usr/local/sbin/docker-storage-guard.sh` disamakan dengan versi
yang tersimpan pada `ops/storage-guard.sh`. Cron harian yang sudah ada tetap
digunakan untuk prune Docker dan journal ketika usage melewati threshold.

Guard ini bersifat pelengkap. Ia tidak dapat membersihkan writable layer dari
container aktif, sehingga `brone-temp-guard` dan cleanup level aplikasi adalah
proteksi utama untuk issue ini.

## Verifikasi yang Dilakukan

- `npm test`: **2/2 passed**.
  - profile dihapus setelah browser sukses;
  - profile dan slot concurrency dibersihkan ketika launch gagal.
- `node --check server.js`: passed.
- `docker compose config --quiet`: passed.
- Smoke test endpoint browser tanpa kredensial berhasil launch browser, gagal
  secara aman pada input kosong, dan menyisakan **0** owned profile serta **0**
  runtime artifact.
- Timer diuji memakai direktori dummy stale; profile dan runtime artifact dummy
  keduanya dihapus, sementara path di luar scope tidak ditargetkan.
- `notifier_brone_auth` telah direbuild dan berjalan dengan restart policy
  `always` dan stop grace period 45 detik.

## Kondisi Setelah Perbaikan

Saat verifikasi akhir:

```text
Root filesystem: 81% used, approximately 4.5 GB available
brone /tmp:     12 KB
Browser profiles active: 0
brone-temp-guard.timer: enabled and active
```

Penggunaan disk root yang tersisa bukan berasal dari temporary profile brone.
Salah satu pemakaian besar yang tidak diubah adalah `/home/dev/.vscode-server`
(sekitar 4.1 GB); jangan hapus otomatis karena dapat mengganggu VS Code Remote.

## Remaining Operational Note

Warning/critical dari guard saat ini dicatat ke system journal. Notifikasi
remote WhatsApp/email belum diaktifkan karena endpoint atau channel alert host
belum dikonfigurasi. Bila endpoint tersedia, guard dapat diperluas untuk
mengirim alert pada threshold tersebut.
