# 📖 Panduan Penggunaan Fitur Baru Asisten WhatsApp (Okta & Kak Manda)

Dokumen ini menjelaskan cara menggunakan seluruh fitur baru yang telah diimplementasikan dan aktif di sistem asisten WhatsApp n8n:
1. **Akses VPS Agent dari Grup WhatsApp**
2. **One-Click & Conversational Presensi UB**
3. **Sistem Catatan Pribadi & Dua Arah (`/catat`, `/notes`)**
4. **Multimodal Image OCR & Vision Q&A (Tanya Foto / Soal / Struk)**
5. **Lifecycle Tugas/Agenda di Google Calendar (`[SELESAI]` / Hapus)**

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
