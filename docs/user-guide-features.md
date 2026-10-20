# 📖 Panduan Penggunaan Fitur Baru Asisten WhatsApp (Okta & Kak Manda)

Dokumen ini menjelaskan cara menggunakan seluruh fitur baru yang telah diimplementasikan dan aktif di sistem asisten WhatsApp n8n:
1. **Akses VPS Agent dari Grup WhatsApp**
2. **One-Click & Conversational Presensi UB**
3. **Sistem Catatan Pribadi & Dua Arah (`/catat`, `/notes`)**
4. **Multimodal Image OCR & Vision Q&A (Tanya Foto / Soal / Struk)**
5. **Lifecycle Tugas/Agenda di Google Calendar (`[SELESAI]` / Hapus)**
6. **Smart Expense Tracker Database & Struk OCR (`/expense`, `/pengeluaran`)**
7. **Proactive Morning Audio Briefing (Voice Note TTS 07:00 WIB)**
8. **Intelligent Calendar Conflict Resolver (Deteksi & Resolusi Bentrok)**

---

## 👥 1. Akses VPS Agent dari Grup WhatsApp

Sekarang kamu bisa mengeksekusi instruksi server dan Codex agent langsung dari grup WhatsApp yang di-whitelist (misal Grup Dev atau Grup Shared).

### Cara Penggunaan:
* **Perintah Langsung:**
  ```text
  /agent cek status docker dan disk server
  /vps uptime -p
  ```
* **Dengan Tag / Mention Bot di Grup:**
  ```text
  @bot /agent cek container apa saja yang lagi jalan
  @171619058196619 /agent periksa penggunaan memori
  ```

### 🔒 Keamanan:
* **Hanya Okta** yang diizinkan mengeksekusi perintah server (`participant` diverifikasi berdasarkan `$env.MY_WA_NUMBER`).
* Perintah diabaikan jika dikirim oleh anggota lain di grup.
* Hasil eksekusi dikirim balik secara transparan ke dalam grup tempat perintah dipanggil.

---

## ⚡ 2. One-Click & Conversational Presensi UB

Presensi kuliah SIAM Universitas Brawijaya kini bisa dieksekusi instan tanpa harus mengetik perintah panjang.

### Cara Penggunaan:
1. **Direct One-Word Reply:**
   Saat notifikasi presensi kuliah aktif masuk ke WhatsApp:
   > 🚨 *DAFTAR PRESENSI AKTIF: Pengembangan Aplikasi Perangkat Bergerak*
   
   Cukup balas pesan tersebut dengan **satu kata**:
   ```text
   hadir
   ```
   *(atau `absen`, `hadir daring`, `hadir online`)*
   
   Router langsung mengeksekusi absensi ke SIAM dalam 1 detik!

2. **Percakapan Santai (Natural Language):**
   Kamu juga bisa minta lewat percakapan AI biasa:
   ```text
   @n8n tolong absenkan kelas sekarang dong bro
   bro tolong absen hadir ya
   ```
   Asisten akan otomatis mengenali permintaan dan memicu aksi presensi ke SIAM UB.

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

### C. Saling Cek Catatan (Cross-Check Okta & Manda)
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

## 📸 4. Multimodal Image OCR & Vision Q&A

Asisten kini dapat "melihat", membaca, dan memahami foto atau gambar yang dikirimkan ke WhatsApp secara multimodal via **Gemini Vision (Gemini 2.5 Flash)**.

### Cara Penggunaan:
1. **Kirim foto langsung dengan caption**, ATAU
2. **Balas (quote reply) sebuah foto yang ada di chat** lalu ajukan pertanyaan:

### Contoh Skenario:
* **Tanya Maksud Slide / Materi Kuliah:**
  > *(Kirim foto slide materi diagram arsitektur)*  
  > 💬 *"Bro ini maksud diagram alurnya gimana ya?"*  
  > 🤖 Asisten akan membaca teks diagram dan menjelaskannya dengan bahasa santai.
* **Bantu Pahami Soal Tugas:**
  > *(Kirim foto lembar soal tugas matematika/coding)*  
  > 💬 *"Ini cara ngerjainnya langkah-langkahnya gimana bro?"*  
  > 🤖 Asisten melakukan OCR teks soal dan memberikan panduan solutif.
* **Ekstraksi Pengeluaran dari Struk Belanja:**
  > *(Kirim foto struk Indomaret / nota makan)*  
  > 💬 *"Catat pengeluaran dari struk ini dong bro"*  
  > 🤖 Asisten mengekstrak total harga dan item pembelian ke dalam ringkasan.

---

## 🗓️ 5. Lifecycle Tugas & Agenda Google Calendar (`[SELESAI]` / Hapus)

Sekarang kamu bisa menyelesaikan atau menghapus agenda langsung dari WhatsApp tanpa perlu membuka aplikasi Google Calendar.

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

## 💰 6. Smart Expense Tracker & Struk OCR (`/expense`, `/pengeluaran`)

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

## 🎙️ 7. Proactive Morning Audio Briefing (Voice Note TTS 07:00 WIB)

Setiap pagi pukul **07:00 WIB**, asisten secara proaktif mengirimkan **Voice Note Audio (PTT / Voice Note WhatsApp)** yang membacakan agenda hari ini dengan gaya penyiar radio profesional yang bersahabat.

### Karakteristik & Fitur:
* **Audio Voice Note (PTT):** Menggunakan model Neural TTS Bahasa Indonesia (`id-ID-ArdiNeural` via `edge-tts`). Pesan dikirim sebagai *voice note* asli WhatsApp (bisa diputar langsung dengan waveform).
* **Konten Siaran Pagi:**
  1. Ucapan salam pagi semangat.
  2. Ringkasan seluruh agenda Google Calendar hari ini (jadwal kuliah, rapat, janji temu).
  3. Tugas & deadline akademik terdekat (LMS Brone & SIAM UB).
  4. Perkiraan cuaca Malang / kota terkait.
  5. Pesan motivasi singkat untuk memulai hari.
* **Teks Pendamping:** Selain voice note audio, bot juga menyertakan pesan teks berformat rapi sebagai rangkuman visual cepat.

---

## 🛡️ 8. Intelligent Calendar Conflict Resolver (Deteksi & Resolusi Bentrok)

Mencegah tumpang tindih waktu saat menambahkan agenda baru ke Google Calendar.

### Cara Kerja:
1. Saat membuat agenda baru (misal *"Rapat Organisasi besok jam 10.00 - 12.00"*), asisten secara otomatis memindai seluruh acara pada rentang jam tersebut.
2. Jika terdeteksi adanya bentrok (misal bertabrakan dengan *"Kuliah Pemrograman Bergerak jam 09.30 - 11.30"*):
   * Asisten memberi peringatan jelas:
     > ⚠️ *Peringatan Bentrok Waktu! Agenda 'Rapat Organisasi' bertabrakan dengan 'Kuliah Pemrograman Bergerak' (09.30 - 11.30 WIB).*
   * Asisten menyarankan slot waktu kosong terdekat yang aman.
   * Pengguna diberikan pilihan untuk tetap menjadwalkan atau memindahkan ke slot rekomendasi.
