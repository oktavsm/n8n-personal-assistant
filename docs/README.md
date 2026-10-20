# 📚 Documentation & Technical Specifications

Selamat datang di direktori dokumentasi **n8n Personal Assistant & Academic Co-Pilot**.

Direktori ini memuat seluruh dokumen perancangan arsitektur, katalog fitur workflow, laporan perbaikan, dan roadmap inovasi masa depan:

---

## 📑 Daftar Dokumen

### 1. 📖 [User Guide & Panduan Fitur Baru](user-guide-features.md)
* **Deskripsi:** Panduan lengkap penggunaan seluruh fitur baru: Akses VPS Agent dari grup WhatsApp, One-Click Presensi UB, Sistem Catatan Pribadi & Dua Arah (`/catat`, `/notes`), Multimodal Image OCR & Vision Q&A, Lifecycle Google Calendar (`[SELESAI]` / Hapus), Smart Expense Tracker (`/expense`), dan Morning Audio Briefing (Voice Note TTS).
* **Status:** Implemented & Production Ready.

### 2. 🚀 [Strategic Roadmap & Expansion Ideas](roadmap.md)
* **Deskripsi:** Rencana pengembangan inovasi jangka panjang: *Long-term Semantic Memory (`pgvector`)*, *Morning Audio Briefing (TTS Voice Note)*, *Receipt & Expense Tracker via Vision OCR*, *One-Click Auto Presensi UB*, dan *Intelligent Calendar Conflict Resolver*.
* **Status:** Phase 1, 2, & 3 Completed & Active.

### 3. 🧠 [WhatsApp Chatbot Evolution Plan](evolution-plan.md)
* **Deskripsi:** Rencana arsitektur evolusi asisten WhatsApp: *Master Router*, integrasi model bahasa ganda (Gemini 3.5 Flash Lite untuk teks & 2.5 Flash untuk audio/image), pemisahan memori per room chat, dan penanganan multi-timezone WIB/WITA.
* **Status:** Implemented & Verified.

### 4. 📦 [Workflow Feature Catalog](workflow-catalog.md)
* **Deskripsi:** Katalog komprehensif 16 workflow n8n yang aktif: pemetaan ID workflow, node trigger, sub-workflow caller, dan matriks fungsionalitas kalender/akademik/ops.
* **Status:** Implemented & Synced.

### 5. 🛠️ [Workflow Improvement & Bugfix Report](improvement-report.md)
* **Deskripsi:** Laporan analisis teknis perbaikan bug kritis: eliminasi spam reminder Google Calendar 30 menit via `staticData` deduplication, sinkronisasi zona waktu server/container/database ke WIB & WITA, perbaikan timeout Codex runner, dan integrasi action triggers.
* **Status:** Resolved & Production Ready.

---

## 🔗 Referensi Tambahan
* **[README Utama](../README.md):** Gambaran umum proyek, diagram arsitektur Mermaid, dan panduan instalasi Docker.
* **[Issues & Postmortem](../issues/issue.md):** Analisis masalah log/temporary storage Puppeteer pada `notifier_brone_auth`.
