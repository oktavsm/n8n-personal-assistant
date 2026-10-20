# 📖 Panduan Lengkap & Playbook Pengujian Fitur Asisten WhatsApp (Okta & Kak Manda)

Dokumen ini memuat panduan lengkap serta **cheat-sheet copy-paste** untuk seluruh fitur asisten WhatsApp n8n yang aktif di sistem produksi VPS (`pg-bcc`), baik fitur baru maupun fitur inti kalender dan akademik.

---

## 🎯 Master Interactive Testing Checklist (Siap Copy-Paste)

Gunakan tabel ini untuk mencoba seluruh fitur satu per satu di WhatsApp:

| # | Kategori Fitur | Di Private Chat (PC) | Di Group Chat (Grup) | Output yang Diharapkan | Status |
|---|---|---|---|---|---|
| 1 | **Catatan Pribadi** | `/catat bayar kas kontrakan 50rb` | `@n8n catat bayar kas kontrakan 50rb` | Bot konfirmasi catatan disimpan ke PostgreSQL `user_notes` | [ ] |
| 2 | **Cek Catatan** | `/notes` atau `/catatan` | `@n8n catatanku sekarang apa aja?` | Bot menampilkan list catatan aktif milik Okta | [ ] |
| 3 | **Cross-Check Catatan** | `/catatan manda` | `@n8n catatan Kak Manda apa aja?` | Bot menampilkan list catatan aktif milik Kak Manda | [ ] |
| 4 | **Selesaikan Catatan** | `/catat done 1` | `@n8n tandai catatan 1 selesai` | Bot mengubah status catatan ID 1 menjadi tuntas (`is_done=true`) | [ ] |
| 5 | **Catat Pengeluaran** | `/expense 45000 Nasi Padang` | `@n8n catat pengeluaran makan 25rb` | Bot menyimpan data ke PostgreSQL `user_expenses` | [ ] |
| 6 | **Struk Foto OCR** | Kirim foto struk + *"catat pengeluaran dari struk ini"* | Kirim foto struk + quote `@n8n catat struk ini` | Gemini Vision mengekstrak nominal, toko, dan item struk | [ ] |
| 7 | **Rekap Pengeluaran** | `/expense` atau `/pengeluaran` | `@n8n rekap pengeluaranku bulan ini` | Bot merangkum transaksi & total pengeluaran 30 hari terakhir | [ ] |
| 8 | **Tugas Kalender Santai**| `"@n8n buatin tugas PPT deadlinenya lusa jam 23.59"` | `@n8n buatin tugas PPT comvis deadlinenya lusa 23.59` | Event dibuat di Google Calendar + kartu konfirmasi hijau | [ ] |
| 9 | **Cek Jadwal Hari Ini** | `/cek` | `@n8n jadwalku hari ini apa aja?` | Rangkuman jadwal kuliah dan kegiatan hari ini | [ ] |
| 10 | **Cek Jadwal Besok** | `/besok` | `@n8n besok ada jadwal apa aja?` | Rangkuman agenda esok hari | [ ] |
| 11 | **Cek Agenda 7 Hari** | `/agenda` | `@n8n agendaku minggu ini ada apa aja?`| Ringkasan kalender 7 hari ke depan | [ ] |
| 12 | **Cek Deadline Tugas** | `/tugas` | `@n8n tugasku yang belum apa aja?` | Daftar seluruh tugas aktif dan tanggal deadline | [ ] |
| 13 | **Tandai Tugas Selesai**| `/done PPT Pengabdian` | `@n8n tugas PPT pengabdian udah kelar nih` | Event di GCal diubah jadi `[SELESAI]` & warna hijau | [ ] |
| 14 | **Hapus Agenda Batal** | `/hapus-jadwal Meeting Tim` | `@n8n rapat tadi dicancel tolong hapus`| Event dihapus dari Google Calendar | [ ] |
| 15 | **Tanya Foto / Slide** | Kirim slide + *"maksud diagram ini apa?"* | Kirim slide + quote `@n8n jelasin alur ini` | Gemini Vision membaca diagram dan menjelaskan konteksnya | [ ] |
| 16 | **Voice Note Masuk** | Kirim VN audio apa saja | Kirim VN di Dev Group | Gemini audio mentranskripsi dan menjawab pesan suara | [ ] |
| 17 | **Morning Audio Brief**| Terjadwal tiap 07.00 WIB | Terjadwal tiap 07.00 WIB | Voice note radio TTS (`id-ID-ArdiNeural`) masuk otomatis | [ ] |
| 18 | **Akses Server Agent** | `/vps df -h` | `@n8n /agent periksa kondisi storage vps` | Terminal / Codex agent mengeksekusi di host VPS | [ ] |
| 19 | **Titip Pesan ke Manda**| `"Titip pesan ke Kak Manda: semangat ya"` | `"Titip pesan ke Kak Manda: nanti malam kabarin"` | Bot meneruskan kartu pesan langsung ke nomor Kak Manda | [ ] |
| 20 | **Presensi Instan UB** | Balas notif kuliah dengan: `hadir` | Balas notif kuliah dengan: `absen` | Panggilan otomatis ke API SIAM UB dalam 1 detik | [ ] |
| 21 | **Cek LMS Brone UB** | `/brone` | `@n8n cek tugas di brone dong` | Scraping tugas & kuis terbaru dari portal Brone UB | [ ] |
| 22 | **Cek Pengumuman SIAM**| `/pengumuman` | `@n8n cek pengumuman siam terbaru` | Mengambil pengumuman resmi kampus dari SIAM UB | [ ] |
| 23 | **Bikin Stiker WA** | Kirim foto + caption `/stiker` | Kirim foto + caption `/stiker` | Mengubah gambar menjadi stiker WhatsApp otomatis | [ ] |

---

## 👥 1. Akses VPS Agent dari WhatsApp (`/agent`, `/vps`)

Eksekusi perintah terminal dan instruksi agen AI Codex langsung dari chat WhatsApp pribadi maupun grup yang di-whitelist (`[General] Okta & Manda` atau Grup Dev).

### Cara Penggunaan:
* **Perintah Terminal Langsung:**
  ```text
  /vps df -h
  /vps docker ps --format "table {{.Names}}\t{{.Status}}"
  /vps uptime -p
  ```
* **Perintah Agen AI (Natural Language):**
  ```text
  /agent cek penggunaan CPU, RAM, dan disk server sekarang
  @n8n /agent periksa apakah container notifier_n8n berjalan sehat
  ```
* **🔒 Keamanan Zero-Trust:** Hanya nomor Okta terverifikasi (`$env.MY_WA_NUMBER`, `fromMe: true`, atau LID) yang dapat mengeksekusi perintah shell. Perintah berbahaya (`rm -rf /`, `mkfs`, `shutdown`) otomatis diblokir.

---

## ⚡ 2. One-Click & Conversational Presensi UB

Presensi perkuliahan di SIAM Universitas Brawijaya tanpa perlu buka browser atau mengetik panjang.

### Cara Penggunaan:
1. **One-Word Reply Instan:**  
   Saat notifikasi presensi kuliah masuk ke WhatsApp:
   > 🚨 *DAFTAR PRESENSI AKTIF: Pengembangan Aplikasi Perangkat Bergerak*  
   Cukup balas pesan tersebut dengan **satu kata**:
   ```text
   hadir
   ```
   *(atau `absen`, `hadir daring`, `hadir online`)*  
   Router langsung mengeksekusi presensi ke server SIAM UB dalam 1 detik!

2. **Percakapan Santai:**
   ```text
   @n8n tolong absenkan kelas sekarang dong bro
   bro tolong absen hadir ya
   ```

---

## 📝 3. Sistem Catatan Pribadi & Dua Arah (`/catat`, `/notes`)

Catatan harian, pengingat utang/piutang, ide proyek, dan to-do umum yang tidak terikat jam tertentu sekarang disimpan secara persisten di database PostgreSQL (`user_notes`).

### A. Menyimpan Catatan Baru
* **Slash Command:**
  ```text
  /catat belum bayar kas kosan 50rb
  /catat beli skincare sunscreen (untuk Kak Manda)
  ```
* **Bahasa Santai:**
  ```text
  @n8n catat kalau aku belum ngerjain resume jurnal
  bro catat tolong beliin telur 1 kg
  ```

### B. Melihat Catatan Sendiri
* **Slash Command:**
  ```text
  /notes
  /catatan
  ```
* **Bahasa Santai:**
  ```text
  @n8n catatanku apa aja sekarang?
  bro list to-do ku ada apa aja
  ```

### C. Saling Cek Catatan (Cross-Check Okta & Kak Manda)
* **Okta melihat catatan Kak Manda:**
  ```text
  /catatan manda
  /notes manda
  @n8n catatan Kak Manda ada apa aja?
  ```
* **Kak Manda melihat catatan Okta:**
  ```text
  /catatan okta
  /notes okta
  @n8n catatan Okta sekarang apa aja?
  ```

### D. Menandai Catatan Selesai
* **Slash Command:**
  ```text
  /catat done 1
  /catat selesai 2
  ```
* **Bahasa Santai:**
  ```text
  @n8n tandai catatan 1 selesai
  bro catatan nomor 2 udah beres
  ```

---

## 💰 4. Smart Expense Tracker & Struk OCR (`/expense`, `/pengeluaran`)

Catat pengeluaran keuangan pribadi secara otomatis ke database PostgreSQL (`user_expenses`) via teks percakapan santai, slash command, maupun foto struk belanjaan (Multimodal OCR).

### A. Catat Pengeluaran Manual
* **Slash Command:**
  ```text
  /expense 45000 Makan Nasi Padang
  /pengeluaran 25000 Kopi Kenangan
  /expense 150000 Belanja Bulanan di Superindo
  ```
* **Bahasa Santai:**
  ```text
  @n8n catat pengeluaran tadi beli bensin 30 ribu
  bro catat makan siang 20.000
  ```

### B. Catat Pengeluaran Otomatis via Foto Struk (Vision OCR)
1. Kirim foto struk belanja (Indomaret, Alfamart, restoran, nota kafe) ke WhatsApp.
2. Berikan caption atau quote foto dengan teks:
   ```text
   Catat pengeluaran dari struk ini ya bro
   ```
3. Gemini Vision akan melakukan OCR, membaca nama merchant, total nominal, kategori, dan daftar item belanja, lalu menyimpannya langsung ke database `user_expenses`.
4. Asisten mengonfirmasi data tersimpan dalam bentuk struk ringkas.

### C. Cek Rekap Pengeluaran
* **Perintah:**
  ```text
  /expense
  /pengeluaran
  @n8n rekap pengeluaranku bulan ini dong
  bro total pengeluaranku berapa ya?
  ```
* Asisten akan menampilkan riwayat transaksi terbaru beserta **Total Pengeluaran** dalam periode 30 hari terakhir.

---

## 🗓️ 5. Lifecycle Tugas & Agenda Google Calendar (`[SELESAI]` / Hapus)

Menyelesaikan atau menghapus agenda langsung dari WhatsApp tanpa perlu membuka aplikasi Google Calendar.

### A. Menandai Tugas `[SELESAI]`
Saat tugas sudah selesai dikerjakan, asisten akan mengubah judul kegiatan di Google Calendar menjadi diawali `[SELESAI]` dan memberi warna hijau penanda tuntas.

* **Slash Command:**
  ```text
  /done PPT Pengabdian
  /selesai Laporan PAPB
  ```
* **Bahasa Santai:**
  ```text
  @n8n tugas PPT pengabdian udah selesai nih
  bro tandai tugas laporan PAPB beres
  ```

### B. Menghapus Agenda dari Kalender
Jika suatu acara atau janji temu dibatalkan:
* **Slash Command:**
  ```text
  /hapus-jadwal Meeting Tim
  /hapus Rapat Divisi
  ```
* **Bahasa Santai:**
  ```text
  @n8n meeting tim tadi di-cancel, tolong hapus dari kalender
  bro hapus jadwal rapat sore ini
  ```

### C. Alur Konfirmasi Otomatis:
Jika pengguna hanya bilang *"tugas X udah kelar"*, asisten akan otomatis mengonfirmasi:
> *"Tugas **PPT Pengabdian** ditemukan di kalender! Mau ditandai **[SELESAI]** di kalender atau langsung **dihapus** aja bro?"*
* Cukup balas *"tandai selesai"* atau *"hapus aja"*, bot langsung memprosesnya!

---

## 🛡️ 6. Intelligent Calendar Conflict Resolver (Deteksi & Resolusi Bentrok)

Mencegah tumpang tindih waktu saat menambahkan agenda baru ke Google Calendar.

### Cara Kerja:
1. Saat membuat agenda baru (misal *"Rapat Organisasi besok jam 10.00 - 12.00"*), asisten secara otomatis memindai seluruh acara pada rentang jam tersebut.
2. Jika terdeteksi adanya bentrok (misal bertabrakan dengan *"Kuliah Pemrograman Bergerak jam 09.30 - 11.30"*):
   * Asisten memberi peringatan jelas:
     > ⚠️ *Peringatan Bentrok Waktu! Agenda 'Rapat Organisasi' bertabrakan dengan 'Kuliah Pemrograman Bergerak' (09.30 - 11.30 WIB).*
   * Asisten menyarankan slot waktu kosong terdekat yang aman.
   * Pengguna diberikan pilihan untuk tetap menjadwalkan atau memindahkan ke slot rekomendasi.

---

## 📸 7. Multimodal Image OCR & Vision Q&A

Asisten didukung oleh model multimodal Gemini Vision (`gemini-2.5-flash`), dapat membaca, memahami, dan mengekstrak teks dari foto:

### Contoh Skenario:
* **Tanya Maksud Slide / Materi Kuliah:**  
  Kirim foto slide materi kuliah diagram arsitektur + caption:  
  💬 *"Bro ini maksud diagram alurnya gimana ya?"*
* **Bantu Pahami Soal Tugas:**  
  Kirim foto lembar soal tugas matematika/coding:  
  💬 *"Ini cara ngerjainnya langkah-langkahnya gimana bro?"*
* **Ekstraksi Teks Catatan Papan Tulis / Dokumen:**  
  Kirim foto tulisan tangan / dokumen PDF scan:  
  💬 *"Tolong rangkumkan poin-poin utama dari foto ini bro"*

---

## 🎙️ 8. Proactive Morning Audio Briefing (Voice Note TTS 07:00 WIB)

Setiap pagi pukul **07:00 WIB**, asisten secara proaktif mengirimkan **Voice Note Audio (PTT / Voice Note WhatsApp)** yang membacakan agenda hari ini dengan gaya penyiar radio profesional yang bersahabat.

### Karakteristik & Fitur:
* **Audio Voice Note (PTT):** Menggunakan model Neural TTS Bahasa Indonesia (`id-ID-ArdiNeural` via `edge-tts`). Pesan dikirim sebagai *voice note* asli WhatsApp (bisa diputar langsung dengan waveform hijau).
* **Konten Siaran Pagi:**
  1. Ucapan salam pagi semangat.
  2. Ringkasan seluruh agenda Google Calendar hari ini (jadwal kuliah, rapat, janji temu).
  3. Tugas & deadline akademik terdekat (LMS Brone & SIAM UB).
  4. Perkiraan cuaca Malang / kota terkait.
  5. Pesan motivasi singkat untuk memulai hari.
* **Teks Pendamping:** Selain voice note audio, bot juga menyertakan pesan teks berformat rapi sebagai rangkuman visual cepat.

---

## 📅 9. Google Calendar Queries & Natural Scheduling

Asisten mengenali bahasa percakapan sehari-hari untuk membuat dan mengecek jadwal:

### A. Membuat Tugas & Jadwal
* **Percakapan Santai:**
  ```text
  @n8n buatin tugas PPT Comvis deadlinenya lusa jam 23.59
  bro jadwalkan meeting tim besok jam 14.00 sampai 16.00
  ```
* **Slash Command:**
  ```text
  /jadwal Meeting Koordinasi besok jam 10.00
  /tugas Laporan Praktikum PAPB Jumat jam 23.59
  ```

### B. Mengecek Jadwal & Kegiatan
* `/cek` : Jadwal kuliah dan agenda hari ini.
* `/besok` : Jadwal dan kegiatan esok hari.
* `/agenda` : Ringkasan agenda 7 hari ke depan.
* `/tugas` : Daftar seluruh deadline tugas aktif.
* `/uas` : Jadwal Ujian Akhir Semester.

---

## 💌 10. Titip Pesan Otomatis (Relay Dua Arah Okta $\leftrightarrow$ Kak Manda)

Fitur relay otomatis jika Okta ingin menyampaikan pesan ke Kak Manda, atau Kak Manda ingin menyampaikan pesan ke Okta:

* **Okta menitipkan pesan:**
  > Di chat dengan bot: *"Titip pesan ke Kak Manda: semangat ya praktikumnya, jangan lupa istirahat"*  
  > 🤖 Bot otomatis memformat kartu pesan manis dan mengirimkannya langsung ke WhatsApp Kak Manda.
* **Kak Manda menitipkan pesan:**
  > Kak Manda bilang ke bot: *"Titip pesan ke Okta: nanti malam telepon ya"*  
  > 🤖 Bot langsung meneruskannya ke WhatsApp pribadi Okta.

---

## 🎨 11. WhatsApp Sticker Generator (`/stiker`, `/sticker`)

Mengubah foto, video singkat, atau animasi GIF menjadi stiker WhatsApp resmi secara instan:
1. Kirim foto / video pendek ke chat.
2. Berikan caption `/stiker` atau `/sticker`.
3. Bot langsung membalas dalam bentuk stiker WhatsApp!

---

## 🎓 12. Akademik & Kampus (SIAM UB & Brone LMS)

* `/brone` : Mengecek daftar tugas, kuis, dan submission terbaru di portal LMS Brone UB (menggunakan bypass autentikasi Keycloak Puppeteer).
* `/pengumuman` : Menampilkan pengumuman resmi terbaru dari portal akademik SIAM Universitas Brawijaya.
* Notifikasi Tugas & Presensi otomatis masuk ke WhatsApp tanpa perlu diminta setiap kali dosen membuka sesi baru.
