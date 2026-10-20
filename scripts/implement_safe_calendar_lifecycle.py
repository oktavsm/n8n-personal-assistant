#!/usr/bin/env python3
"""
Complete Implementation of Safe Calendar Lifecycle:
1. master-router-webhook: Rule 6 (lifecycle), help message update, okta sender check update.
2. wa-to-gcal-assistant: Interactive selection, candidate storage, Kuliah protection, dynamic calendarId.
3. manda-gcal-assistant: Mirrored safe lifecycle for Manda.
4. wa-conversation: Add Okta Tugas & Manda Tugas to vision, update Gemini system prompt.
5. README.md: Document /edit-kuliah, safe confirmation lifecycle, and all commands.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ==============================================================================
# 1. UPGRADE master-router-webhook.json
# ==============================================================================
print("🚀 [1/4] Upgrading master-router-webhook.json...")

HELP_MESSAGE_TEXT = """📋 *MENU & PANDUAN ASISTEN PRIBADI*

Halo! Berikut panduan lengkap perintah dan fitur yang tersedia di sistem asisten:

📅 *GOOGLE CALENDAR (AGENDA & TUGAS)*
• */jadwal [detail]*
  Buat agenda kegiatan baru (contoh: `/jadwal Meeting Tim besok jam 14.00`).
• */tugas [detail]*
  Catat deadline tugas akademik (contoh: `/tugas Laporan PAPB Jumat jam 23.59`).
• */cek* atau */besok*
  Cek agenda dan jadwal hari ini atau besok.
• */agenda*
  Rekap agenda kegiatan 7 hari ke depan.
• */tugas*
  Lihat seluruh daftar tugas dan deadline aktif.
• */done [judul]* atau */selesai [judul]*
  Tandai tugas/agenda selesai di kalender (status `[SELESAI]` & warna hijau).
• */hapus [judul]* atau */hapus-jadwal [judul]*
  Hapus agenda/tugas dari kalender (dilengkapi konfirmasi cerdas jika ada judul mirip/ganda).

🎓 *JADWAL KULIAH & AKADEMIK*
• */edit-kuliah [matkul] [ruang / LIBUR]*
  Perbarui ruang kelas atau tandai kelas libur tanpa menghapus jadwal semesteran.
  _Contoh:_ `/edit-kuliah comvis F3.11` atau `/edit-kuliah comvis [LIBUR]`
  ⚠️ _Catatan: Jadwal kuliah dilindungi dan tidak bisa dihapus._
• */brone*
  Cek tugas dan kuis terbaru dari portal LMS Brone UB.
• */uas*
  Cek jadwal Ujian Akhir Semester.
• */pengumuman*
  Cek rilis pengumuman akademik terbaru dari SIAM UB.
• *Presensi Instan:*
  Balas notifikasi presensi perkuliahan dengan satu kata: `hadir` atau `absen`.

📝 *CATATAN PRIBADI & DUA ARAH (`user_notes`)*
• */catat [isi]*
  Simpan catatan to-do, utang/piutang, atau memo pribadi ke database.
• */notes* atau */catatan*
  Lihat daftar catatan aktif milikmu.
• */catatan manda* (oleh Okta) / */catatan okta* (oleh Kak Manda)
  Saling intip catatan aktif antar pengguna.
• */catat done [id]*
  Tandai catatan selesai (contoh: `/catat done 1`).

💰 *SMART EXPENSE TRACKER (`user_expenses`)*
• */expense [jumlah] [nama]* atau */pengeluaran [jumlah] [nama]*
  Catat pengeluaran harian (contoh: `/expense 45000 Nasi Padang`).
• *Foto Struk Belanjaan:*
  Kirim/quote foto struk belanja dengan teks _"catat pengeluaran ini"_, bot otomatis melakukan OCR nama toko & total belanja.
• */expense* atau */pengeluaran*
  Rekap transaksi pengeluaran dan total akumulasi 30 hari terakhir.

🎙️ *AUDIO & VISION MULTIMODAL*
• *Voice Note Masuk:*
  Kirim VN audio WhatsApp apa saja, bot otomatis mentranskripsi dan merespons.
• *Morning Audio Brief (07.00 WIB):*
  Setiap pagi bot otomatis mengirim Voice Note siaran radio agenda hari ini.
• *Tanya Foto / Soal:*
  Kirim foto materi, soal coding, atau diagram + caption pertanyaan.

⚡ *VPS AGENT & DEVELOPER (Khusus Okta)*
• */vps [perintah]* (contoh: `/vps df -h` atau `/vps docker ps`).
• */agent [instruksi]* untuk menjalankan AI agent langsung di server host.

💌 *TITIP PESAN DUA ARAH*
• Ketik _"Titip pesan ke Kak Manda: semangat ya"_ di chat bot, bot otomatis meneruskan kartu pesan langsung ke WhatsApp Kak Manda (dan sebaliknya).

🎨 *STIKER WA*
• Kirim foto/video/GIF dengan caption */stiker* untuk membuat stiker WhatsApp instan.
"""

def upgrade_master_router(filepath: Path):
    if not filepath.exists(): return
    with open(filepath, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    # 1. Update [Script] Message Builder (/help)
    for node in data.get("nodes", []):
        if node.get("name") == "[Script] Message Builder":
            node["parameters"]["jsCode"] = f"const textMsg = {json.dumps(HELP_MESSAGE_TEXT)};\n\nreturn {{ json: {{ text: textMsg }} }};\n"
            print(f"[{filepath.name}] Updated [Script] Message Builder (/help)")

        # 2. Update 'pengirim okta?'
        if node.get("name") == "pengirim okta?":
            node["parameters"]["conditions"]["conditions"][0]["leftValue"] = """={{
  Boolean(
    ($json.body?.data?.key?.remoteJid || '').includes($env.MY_WA_NUMBER) ||
    ($json.body?.data?.key?.participantAlt || '').includes($env.MY_WA_NUMBER) ||
    ($json.body?.data?.key?.participant || '').includes($env.MY_WA_NUMBER) ||
    Boolean($json.body?.data?.key?.fromMe) ||
    ($json.body?.data?.key?.participant || '').includes('158613192614132')
  )
}}"""
            print(f"[{filepath.name}] Updated 'pengirim okta?' with fromMe and LID")

        # 3. Update 'Switch'
        if node.get("name") == "Switch":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            conns = data.get("connections", {}).get("Switch", {}).get("main", [])

            # Check if lifecycle rule already inserted
            has_lifecycle = any(r.get("outputKey") == "lifecycle" for r in rules)
            if not has_lifecycle:
                lifecycle_rule = {
                    "conditions": {
                        "options": {"caseSensitive": False, "leftValue": "", "typeValidation": "loose", "version": 3},
                        "conditions": [
                            {
                                "id": "lifecycle-cmd-cond",
                                "leftValue": """={{ (() => {
  const data = $json.body?.data || {};
  const msg = data.message || {};
  const raw = (msg.conversation || msg.extendedTextMessage?.text || "").trim();
  const cleaned = raw.replace(/@[a-zA-Z0-9_\\-\\.]+\\s*/g, "").trim().toLowerCase();

  const isLifecycleCmd = cleaned.startsWith('/done') ||
                         cleaned.startsWith('/selesai') ||
                         cleaned.startsWith('/hapus') ||
                         cleaned.startsWith('/edit-kuliah') ||
                         cleaned.startsWith('/edit kuliah');

  const isSelectionReply = /^(?:hapus\\s+|selesai\\s+|pilih\\s+|#)?\\d+$/i.test(cleaned) ||
                           ['batal', 'cancel', '/batal', '/cancel'].includes(cleaned);

  return Boolean(isLifecycleCmd || isSelectionReply);
})() }}""",
                                "rightValue": "",
                                "operator": {"type": "boolean", "operation": "true", "singleValue": True}
                            }
                        ],
                        "combinator": "and"
                    },
                    "renameOutput": True,
                    "outputKey": "lifecycle"
                }
                # Insert at index 6 (before cek_brone)
                rules.insert(6, lifecycle_rule)
                conns.insert(6, [{"node": "pengirim okta?", "type": "main", "index": 0}])
                print(f"[{filepath.name}] Inserted 'lifecycle' rule at index 6 -> 'pengirim okta?'")

            # Update 'ask' rule to ignore explicit lifecycle commands
            for r in rules:
                if r.get("outputKey") == "ask":
                    cond = r["conditions"]["conditions"][0]
                    cond["leftValue"] = """={{ (() => {
  const data = $json.body?.data || {};
  const msg = data.message || {};
  const raw = (msg.conversation || msg.extendedTextMessage?.text || msg.imageMessage?.caption || msg.videoMessage?.caption || msg.documentMessage?.caption || "").trim();
  const cleaned = raw.replace(/@[a-zA-Z0-9_\\-\\.]+\\s*/g, "").trim().toLowerCase();
  const jid = data.key?.remoteJid || "";
  const isGroup = jid.endsWith("@g.us");

  const ctx = data.contextInfo ||
    msg.extendedTextMessage?.contextInfo ||
    msg.imageMessage?.contextInfo ||
    msg.videoMessage?.contextInfo ||
    msg.documentMessage?.contextInfo ||
    msg.audioMessage?.contextInfo ||
    {};
  const mentionedJid = ctx.mentionedJid || [];
  const botNumbers = ["171619058196619", "195095164887244", "158613192614132", "6283130151476", $env.MY_WA_NUMBER];

  // 1. Explicit commands handled by other switch rules: DO NOT consume here!
  const explicitCommands = [
    "/agenda", "/besok", "/tugas", "/jadwal", "/cek", "/uas",
    "/done", "/selesai", "/hapus", "/edit-kuliah", "/edit kuliah",
    "/brone", "/pengumuman", "/presensi", "/help", "/stiker", "/sticker",
    "/agent", "/vps"
  ];
  if (explicitCommands.some(cmd => cleaned.startsWith(cmd))) {
    return false;
  }
  if (["hadir", "absen", "absen hadir", "hadir daring", "hadir online"].includes(cleaned)) {
    return false;
  }

  // 2. Selection replies when pending action exists: do not consume here
  if (/^(?:hapus\\s+|selesai\\s+|pilih\\s+|#)?\\d+$/i.test(cleaned) || ['batal', 'cancel', '/batal', '/cancel'].includes(cleaned)) {
    return false;
  }

  // 3. Ask command
  const isAsk = cleaned.startsWith("/ask");

  // 4. Mentions in group
  const isMention = botNumbers.some(b => b && raw.includes("@" + b)) ||
                    mentionedJid.some(j => botNumbers.some(b => b && j.includes(b))) ||
                    raw.toLowerCase().includes("@n8n") ||
                    raw.toLowerCase().includes("@bot");

  // 5. Swipe / Quoted reply to bot in group
  const quotedParticipant = ctx.participant || ctx.quotedMessageSender || "";
  const isReplyingToBot = isGroup && botNumbers.some(b => b && quotedParticipant.includes(b));

  // 6. Notes & Expense commands
  const isNoteCmd = cleaned.startsWith("/catat") || cleaned.startsWith("/notes") || cleaned.startsWith("/catatan");
  const isExpenseCmd = cleaned.startsWith("/expense") || cleaned.startsWith("/pengeluaran");

  // 7. Voice note in dev group
  const isDevGroup = jid === ($env.WA_GROUP_DEV || "120363336434287340@g.us");
  const hasAudio = Boolean(msg.audioMessage || ctx.quotedMessage?.audioMessage);
  const isDevAudio = Boolean(isDevGroup && hasAudio);

  return Boolean(isAsk || isMention || isReplyingToBot || isNoteCmd || isExpenseCmd || isDevAudio);
})() }}"""
                    print(f"[{filepath.name}] Updated 'ask' rule explicit commands filter")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Saved {filepath}")

upgrade_master_router(REPO_ROOT / "workflow" / "master-router-webhook.json")
upgrade_master_router(REPO_ROOT / "n8n" / "workflow" / "master-router-webhook.json")

# ==============================================================================
# 2. UPGRADE wa-to-gcal-assistant.json & manda-gcal-assistant.json
# ==============================================================================
print("\n🚀 [2/4] Upgrading wa-to-gcal-assistant.json & manda-gcal-assistant.json...")

SAFE_CODE_TEMPLATE = """const waData = $('[Code] Get WA Data').first().json || {};
const rawText = (waData.pesanWA || '').trim();
const textLower = (waData.pesanWALower || '').trim();
const targetNumber = waData.targetNumber || '';
const userName = '{USER_NAME}';
const envAgenda = $env.{ENV_AGENDA};
const envTugas = $env.{ENV_TUGAS};
const envKuliah = $env.{ENV_KULIAH};
const userTz = '{TZ}';

// Check if user is replying to a pending selection
let pendingItem = null;
try {
  const p = $('{PG_FETCH_NODE}').first().json;
  if (p && p.action_type && p.candidates) {
    pendingItem = p;
    if (typeof pendingItem.candidates === 'string') {
      pendingItem.candidates = JSON.parse(pendingItem.candidates);
    }
  }
} catch (e) {}

const isCancel = ['batal', 'cancel', '/batal', '/cancel'].includes(textLower);
const numMatch = textLower.match(/^(?:hapus\\s+|selesai\\s+|pilih\\s+|#)?(\\d+)$/i);

// -------------------------------------------------------------
// 1. HANDLE SELECTION REPLY (IF PENDING ACTION EXISTS)
// -------------------------------------------------------------
if (pendingItem && (isCancel || numMatch)) {
  const deletePg = `DELETE FROM user_pending_actions WHERE user_name = '${userName}' AND room_jid = '${targetNumber}';`;

  if (isCancel) {
    return [{
      json: {
        decision: 'REPLY_ONLY',
        message: '❌ Permintaan dibatalkan. Tidak ada agenda atau tugas yang diubah.',
        pgQuery: deletePg
      }
    }];
  }

  const selectedIdx = parseInt(numMatch[1], 10);
  const candidates = Array.isArray(pendingItem.candidates) ? pendingItem.candidates : [];
  
  if (selectedIdx < 1 || selectedIdx > candidates.length) {
    return [{
      json: {
        decision: 'REPLY_ONLY',
        message: `⚠️ Nomor pilihan tidak valid. Silakan balas dengan angka *1* s/d *${candidates.length}*, atau ketik *batal*.`,
        pgQuery: 'SELECT 1;'
      }
    }];
  }

  const selected = candidates[selectedIdx - 1];
  const act = selected.actionType || pendingItem.action_type;

  if (act === 'hapus') {
    return [{
      json: {
        decision: 'EXECUTE_DELETE',
        calendarId: selected.calendarId,
        eventId: selected.eventId,
        message: `🗑️ Agenda/Tugas *${selected.summary}* telah berhasil dihapus dari Google Calendar!`,
        pgQuery: deletePg
      }
    }];
  } else {
    // Selesai / Done
    const origSummary = selected.summary || 'Agenda';
    const newSummary = origSummary.startsWith('[SELESAI]') ? origSummary : `[SELESAI] ${origSummary}`;
    return [{
      json: {
        decision: 'EXECUTE_UPDATE',
        calendarId: selected.calendarId,
        eventId: selected.eventId,
        newSummary: newSummary,
        message: `✅ Agenda/Tugas *${origSummary}* telah ditandai *[SELESAI]* di Google Calendar! 🎉`,
        pgQuery: deletePg
      }
    }];
  }
}

// -------------------------------------------------------------
// 2. HANDLE /edit-kuliah
// -------------------------------------------------------------
const isEditKuliah = textLower.startsWith('/edit-kuliah') || textLower.startsWith('/edit kuliah');
if (isEditKuliah) {
  const cleanCmd = rawText.replace(/^\\/edit-?kuliah\\s*/i, '').trim();
  const parts = cleanCmd.split(/\\s+/);
  
  if (parts.length < 2) {
    return [{
      json: {
        decision: 'REPLY_ONLY',
        message: `⚠️ Format tidak lengkap!\\n\\n*Format:* \\`/edit-kuliah [matkul] [ruang / LIBUR]\\`\\n*Contoh:*\\n• \\`/edit-kuliah comvis F3.11\\`\\n• \\`/edit-kuliah comvis [LIBUR]\\``,
        pgQuery: 'SELECT 1;'
      }
    }];
  }

  const updateVal = parts[parts.length - 1].trim();
  const matkulQuery = parts.slice(0, -1).join(' ').toLowerCase().trim();

  // Search Kuliah events
  let kuliahEvents = [];
  try { kuliahEvents = $('{GCAL_KULIAH_NODE}').all(); } catch (e) {}

  let matchedKuliah = null;
  for (const item of kuliahEvents) {
    const d = item.json;
    if (!d || !d.id || !d.summary) continue;
    const sLower = d.summary.toLowerCase();
    if (sLower.includes(matkulQuery) || matkulQuery.includes(sLower)) {
      matchedKuliah = d;
      break;
    }
  }

  if (!matchedKuliah) {
    return [{
      json: {
        decision: 'REPLY_ONLY',
        message: `⚠️ Jadwal kuliah *"${matkulQuery}"* tidak ditemukan di kalender Kuliah.`,
        pgQuery: 'SELECT 1;'
      }
    }];
  }

  const oldSummary = matchedKuliah.summary;
  let newSummary = oldSummary;

  if (updateVal.toUpperCase().includes('LIBUR')) {
    newSummary = oldSummary.includes('[LIBUR]') ? oldSummary : `[LIBUR] ${oldSummary}`;
  } else {
    // Room code update
    const roomUpper = updateVal.toUpperCase();
    if (/\\b[A-Za-z]\\d+\\.\\d+\\b/.test(oldSummary)) {
      newSummary = oldSummary.replace(/\\b[A-Za-z]\\d+\\.\\d+\\b/g, roomUpper);
    } else {
      newSummary = `[${roomUpper}] ${oldSummary}`;
    }
  }

  return [{
    json: {
      decision: 'EXECUTE_UPDATE',
      calendarId: envKuliah,
      eventId: matchedKuliah.id,
      newSummary: newSummary,
      message: `✅ Jadwal kuliah berhasil diperbarui:\\n📚 *${oldSummary}* ➡️ *${newSummary}*`,
      pgQuery: 'SELECT 1;'
    }
  }];
}

// -------------------------------------------------------------
// 3. HANDLE /hapus and /done (/selesai)
// -------------------------------------------------------------
const isDelete = textLower.startsWith('/hapus');
let query = '';
if (isDelete) {
  query = rawText.replace(/^\\/hapus(-jadwal)?\\s*/i, '').trim();
} else {
  query = rawText.replace(/^(\\/done|\\/selesai)\\s*/i, '').trim();
}
query = query.replace(/^(manda|okta)\\s*/i, '').trim();

if (!query) {
  // If input is just a number or random text without active pending action, silently ignore
  if (/^\\d+$/.test(textLower)) {
    return [{
      json: {
        decision: 'IGNORE',
        message: '',
        pgQuery: 'SELECT 1;'
      }
    }];
  }
  return [{
    json: {
      decision: 'REPLY_ONLY',
      message: `⚠️ Mohon sertakan nama agenda atau tugas yang ingin ${isDelete ? 'dihapus' : 'ditandai selesai'}.\\n_Contoh:_ \\`${isDelete ? '/hapus' : '/done'} Laporan PAPB\\``,
      pgQuery: 'SELECT 1;'
    }
  }];
}

// Helper to format event date/time
function formatEventTime(d) {
  if (d.start?.date) return `${d.start.date} (Seharian)`;
  if (d.start?.dateTime) {
    const dt = new Date(d.start.dateTime);
    return dt.toLocaleDateString('id-ID', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: userTz });
  }
  return '-';
}

// Check if query matches Jadwal Kuliah
let kuliahEvents = [];
try { kuliahEvents = $('{GCAL_KULIAH_NODE}').all(); } catch (e) {}

const qLower = query.toLowerCase();
let matchedKuliahOnly = false;
for (const item of kuliahEvents) {
  const d = item.json;
  if (d && d.summary && d.summary.toLowerCase().includes(qLower)) {
    matchedKuliahOnly = true;
    break;
  }
}

// Collect matches from Agenda and Tugas
const candidates = [];

let agendaEvents = [];
try { agendaEvents = $('{GCAL_AGENDA_NODE}').all(); } catch (e) {}
for (const item of agendaEvents) {
  const d = item.json;
  if (!d || !d.id || !d.summary) continue;
  if (d.summary.toLowerCase().includes(qLower) || qLower.includes(d.summary.toLowerCase())) {
    candidates.push({
      calendarType: 'Agenda',
      calendarId: envAgenda,
      eventId: d.id,
      summary: d.summary,
      timeText: formatEventTime(d),
      actionType: isDelete ? 'hapus' : 'selesai'
    });
  }
}

let tugasEvents = [];
try { tugasEvents = $('{GCAL_TUGAS_NODE}').all(); } catch (e) {}
for (const item of tugasEvents) {
  const d = item.json;
  if (!d || !d.id || !d.summary) continue;
  if (d.summary.toLowerCase().includes(qLower) || qLower.includes(d.summary.toLowerCase())) {
    candidates.push({
      calendarType: 'Tugas',
      calendarId: envTugas,
      eventId: d.id,
      summary: d.summary,
      timeText: formatEventTime(d),
      actionType: isDelete ? 'hapus' : 'selesai'
    });
  }
}

// Case 1: Kuliah match but 0 in Agenda/Tugas -> Protected!
if (matchedKuliahOnly && candidates.length === 0) {
  return [{
    json: {
      decision: 'REPLY_ONLY',
      message: `⚠️ *Jadwal kuliah dilindungi dan tidak dapat dihapus atau ditandai selesai.*\\n\\nUntuk mengubah ruang kelas atau menandai libur, gunakan perintah:\\n👉 */edit-kuliah [matkul] [ruang / LIBUR]*\\n_Contoh:_ \\`/edit-kuliah ${query} F3.11\\` atau \\`/edit-kuliah ${query} [LIBUR]\\``,
      pgQuery: 'SELECT 1;'
    }
  }];
}

// Case 2: 0 matches found
if (candidates.length === 0) {
  return [{
    json: {
      decision: 'REPLY_ONLY',
      message: `⚠️ Agenda atau tugas *"${query}"* tidak ditemukan di kalender Agenda maupun Tugas.`,
      pgQuery: 'SELECT 1;'
    }
  }];
}

// Case 3: Exactly 1 match -> Execute immediately!
if (candidates.length === 1) {
  const single = candidates[0];
  const deletePg = `DELETE FROM user_pending_actions WHERE user_name = '${userName}' AND room_jid = '${targetNumber}';`;
  if (isDelete) {
    return [{
      json: {
        decision: 'EXECUTE_DELETE',
        calendarId: single.calendarId,
        eventId: single.eventId,
        message: `🗑️ Agenda/Tugas *${single.summary}* telah berhasil dihapus dari Google Calendar!`,
        pgQuery: deletePg
      }
    }];
  } else {
    const origSummary = single.summary || 'Agenda';
    const newSummary = origSummary.startsWith('[SELESAI]') ? origSummary : `[SELESAI] ${origSummary}`;
    return [{
      json: {
        decision: 'EXECUTE_UPDATE',
        calendarId: single.calendarId,
        eventId: single.eventId,
        newSummary: newSummary,
        message: `✅ Agenda/Tugas *${origSummary}* telah ditandai *[SELESAI]* di Google Calendar! 🎉`,
        pgQuery: deletePg
      }
    }];
  }
}

// Case 4: Multiple matches (> 1) -> Prompt selection and store in user_pending_actions!
const numberedList = candidates.map((c, i) => `${i + 1}️⃣ *[${c.calendarType}]* ${c.summary} _(${c.timeText})_`).join('\\n');
const actionLabel = isDelete ? 'hapus' : 'selesai';

const promptMsg = `🔍 Ditemukan *${candidates.length}* item yang cocok dengan *"${query}"*:\\n\\n${numberedList}\\n\\nKetik nomor untuk konfirmasi *${actionLabel}* (contoh: *1*, *2*, atau *batal* untuk membatalkan).`;

// Prepare candidates array for PG
const candJsonStr = JSON.stringify(candidates).replace(/'/g, "''");
const escapedQuery = query.replace(/'/g, "''");

const insertPendingPg = `INSERT INTO user_pending_actions (user_name, room_jid, action_type, query_text, candidates, created_at)
VALUES ('${userName}', '${targetNumber}', '${actionLabel}', '${escapedQuery}', '${candJsonStr}'::jsonb, NOW())
ON CONFLICT (user_name, room_jid) DO UPDATE SET
  action_type = EXCLUDED.action_type,
  query_text = EXCLUDED.query_text,
  candidates = EXCLUDED.candidates,
  created_at = NOW();`;

return [{
  json: {
    decision: 'REPLY_ONLY',
    message: promptMsg,
    pgQuery: insertPendingPg
  }
}];
"""

def upgrade_gcal_assistant(filepath: Path, is_manda: bool):
    if not filepath.exists(): return
    with open(filepath, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    user_prefix = "Manda " if is_manda else ""
    user_name = "manda" if is_manda else "okta"
    env_agenda = "GCAL_MANDA_AGENDA" if is_manda else "GCAL_OKTA_AGENDA"
    env_tugas = "GCAL_MANDA_TUGAS" if is_manda else "GCAL_OKTA_TUGAS"
    env_kuliah = "GCAL_MANDA_KULIAH" if is_manda else "GCAL_OKTA_KULIAH"
    user_tz = "Asia/Makassar" if is_manda else "Asia/Jakarta"

    node_fetch_pg = f"[PG] {user_prefix}Fetch Pending Selection"
    node_gcal_agenda = f"{user_prefix}Fetch GCal Agenda For Match"
    node_gcal_tugas = f"{user_prefix}Fetch GCal Tugas For Match"
    node_gcal_kuliah = f"{user_prefix}Fetch GCal Kuliah For Match"
    node_process = f"{user_prefix}Process Safe Calendar Action"
    node_exec_pg = f"[PG] {user_prefix}Execute Pending Action Query"
    node_switch_dec = f"{user_prefix}Switch Lifecycle Decision"
    node_update_gcal = f"{user_prefix}Update Safe GCal Event"
    node_delete_gcal = f"{user_prefix}Delete Safe GCal Event"

    # 1. Update Switch1 condition for rule 7
    for node in data.get("nodes", []):
        if node.get("name") == "Switch1":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            if len(rules) > 7:
                rules[7]["conditions"]["conditions"][0]["leftValue"] = """={{
  $json.pesanWALower.startsWith('/done') ||
  $json.pesanWALower.startsWith('/selesai') ||
  $json.pesanWALower.startsWith('/hapus') ||
  $json.pesanWALower.startsWith('/edit-kuliah') ||
  $json.pesanWALower.startsWith('/edit kuliah') ||
  /^(?:hapus\\s+|selesai\\s+|pilih\\s+|#)?\\d+$/i.test($json.pesanWALower) ||
  ['batal', 'cancel', '/batal', '/cancel'].includes($json.pesanWALower)
}}"""
                print(f"[{filepath.name}] Updated Switch1 Rule 7 condition")

        if node.get("name") == "[HTTP Whatsapp]8":
            node["parameters"]["bodyParameters"]["parameters"][1]["value"] = f"={{{{ $json.message || $('{node_process}').first().json.message }}}}"
            print(f"[{filepath.name}] Updated [HTTP Whatsapp]8 text expression")

    # 2. Names of old lifecycle nodes to remove
    old_names = {
        f"{user_prefix}Parse Done Action",
        f"{user_prefix}Search GCal Events",
        f"{user_prefix}Match Event",
        f"{user_prefix}If Event Found",
        f"{user_prefix}Switch Done vs Delete",
        f"{user_prefix}Mark Event Selesai",
        f"{user_prefix}Delete GCal Event",
        f"{user_prefix}Format Done Msg",
        f"{user_prefix}Format Delete Msg"
    }

    # Filter out old nodes
    data["nodes"] = [n for n in data["nodes"] if n.get("name") not in old_names]

    # Generate JS code for process node
    js_code = SAFE_CODE_TEMPLATE.replace("{USER_NAME}", user_name) \
                                .replace("{ENV_AGENDA}", env_agenda) \
                                .replace("{ENV_TUGAS}", env_tugas) \
                                .replace("{ENV_KULIAH}", env_kuliah) \
                                .replace("{TZ}", user_tz) \
                                .replace("{PG_FETCH_NODE}", node_fetch_pg) \
                                .replace("{GCAL_AGENDA_NODE}", node_gcal_agenda) \
                                .replace("{GCAL_TUGAS_NODE}", node_gcal_tugas) \
                                .replace("{GCAL_KULIAH_NODE}", node_gcal_kuliah)

    # 3. Create replacement nodes
    new_nodes = [
        {
            "parameters": {
                "operation": "executeQuery",
                "query": f"SELECT action_type, query_text, candidates, created_at FROM user_pending_actions WHERE user_name = '{user_name}' AND room_jid = '{{{{ $('[Code] Get WA Data').first().json.targetNumber }}}}' AND created_at > NOW() - INTERVAL '15 minutes' LIMIT 1;"
            },
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.5,
            "position": [1300, 1100],
            "id": f"{user_name}-pg-fetch-pending-01",
            "name": node_fetch_pg,
            "credentials": {
                "postgres": {
                    "id": "pgChatMemory0001",
                    "name": "Postgres Chat Memory"
                }
            },
            "alwaysOutputData": True
        },
        {
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": f"={{{{ $env.{env_agenda} }}}}",
                    "mode": "id"
                },
                "returnAll": True,
                "timeMin": f"={{{{ $now.setZone('{user_tz}').minus({{days: 30}}).toISO() }}}}",
                "timeMax": f"={{{{ $now.setZone('{user_tz}').plus({{days: 90}}).toISO() }}}}",
                "options": {}
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [1500, 1100],
            "id": f"{user_name}-gcal-fetch-agenda-01",
            "name": node_gcal_agenda,
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            },
            "alwaysOutputData": True
        },
        {
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": f"={{{{ $env.{env_tugas} }}}}",
                    "mode": "id"
                },
                "returnAll": True,
                "timeMin": f"={{{{ $now.setZone('{user_tz}').minus({{days: 30}}).toISO() }}}}",
                "timeMax": f"={{{{ $now.setZone('{user_tz}').plus({{days: 90}}).toISO() }}}}",
                "options": {}
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [1700, 1100],
            "id": f"{user_name}-gcal-fetch-tugas-01",
            "name": node_gcal_tugas,
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            },
            "alwaysOutputData": True
        },
        {
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": f"={{{{ $env.{env_kuliah} }}}}",
                    "mode": "id"
                },
                "returnAll": True,
                "timeMin": f"={{{{ $now.setZone('{user_tz}').minus({{days: 30}}).toISO() }}}}",
                "timeMax": f"={{{{ $now.setZone('{user_tz}').plus({{days: 90}}).toISO() }}}}",
                "options": {}
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [1900, 1100],
            "id": f"{user_name}-gcal-fetch-kuliah-01",
            "name": node_gcal_kuliah,
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            },
            "alwaysOutputData": True
        },
        {
            "parameters": {
                "jsCode": js_code
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [2100, 1100],
            "id": f"{user_name}-code-safe-action-01",
            "name": node_process
        },
        {
            "parameters": {
                "operation": "executeQuery",
                "query": "={{ $json.pgQuery || 'SELECT 1;' }}"
            },
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.5,
            "position": [2300, 1100],
            "id": f"{user_name}-pg-exec-pending-01",
            "name": node_exec_pg,
            "credentials": {
                "postgres": {
                    "id": "pgChatMemory0001",
                    "name": "Postgres Chat Memory"
                }
            }
        },
        {
            "parameters": {
                "rules": {
                    "values": [
                        {
                            "conditions": {
                                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 3},
                                "conditions": [
                                    {
                                        "id": f"{user_name}-cond-update",
                                        "leftValue": "={{ $json.decision }}",
                                        "rightValue": "EXECUTE_UPDATE",
                                        "operator": {"type": "string", "operation": "equals"}
                                    }
                                ],
                                "combinator": "and"
                            },
                            "renameOutput": True,
                            "outputKey": "update"
                        },
                        {
                            "conditions": {
                                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 3},
                                "conditions": [
                                    {
                                        "id": f"{user_name}-cond-delete",
                                        "leftValue": "={{ $json.decision }}",
                                        "rightValue": "EXECUTE_DELETE",
                                        "operator": {"type": "string", "operation": "equals"}
                                    }
                                ],
                                "combinator": "and"
                            },
                            "renameOutput": True,
                            "outputKey": "delete"
                        },
                        {
                            "conditions": {
                                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 3},
                                "conditions": [
                                    {
                                        "id": f"{user_name}-cond-reply",
                                        "leftValue": "={{ $json.decision }}",
                                        "rightValue": "REPLY_ONLY",
                                        "operator": {"type": "string", "operation": "equals"}
                                    }
                                ],
                                "combinator": "and"
                            },
                            "renameOutput": True,
                            "outputKey": "reply"
                        }
                    ]
                }
            },
            "type": "n8n-nodes-base.switch",
            "typeVersion": 3.2,
            "position": [2500, 1100],
            "id": f"{user_name}-switch-decision-01",
            "name": node_switch_dec
        },
        {
            "parameters": {
                "operation": "update",
                "calendar": {
                    "__rl": True,
                    "value": f"={{{{ $('{node_process}').first().json.calendarId }}}}",
                    "mode": "id"
                },
                "eventId": f"={{{{ $('{node_process}').first().json.eventId }}}}",
                "updateFields": {
                    "summary": f"={{{{ $('{node_process}').first().json.newSummary }}}}"
                }
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [2720, 1000],
            "id": f"{user_name}-gcal-update-safe-01",
            "name": node_update_gcal,
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            }
        },
        {
            "parameters": {
                "operation": "delete",
                "calendar": {
                    "__rl": True,
                    "value": f"={{{{ $('{node_process}').first().json.calendarId }}}}",
                    "mode": "id"
                },
                "eventId": f"={{{{ $('{node_process}').first().json.eventId }}}}",
                "options": {}
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [2720, 1200],
            "id": f"{user_name}-gcal-delete-safe-01",
            "name": node_delete_gcal,
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            }
        }
    ]

    data["nodes"].extend(new_nodes)

    # 4. Clean and rebuild connections
    conns = data.get("connections", {})

    # Remove all connections originating from or pointing to old nodes
    for name in list(conns.keys()):
        if name in old_names:
            del conns[name]
        else:
            for out_type, out_list in conns[name].items():
                for branch in out_list:
                    branch[:] = [t for t in branch if t.get("node") not in old_names]

    # Connect Switch1[7] -> node_fetch_pg
    if "Switch1" in conns and "main" in conns["Switch1"]:
        while len(conns["Switch1"]["main"]) <= 7:
            conns["Switch1"]["main"].append([])
        conns["Switch1"]["main"][7] = [{"node": node_fetch_pg, "type": "main", "index": 0}]

    conns[node_fetch_pg] = {"main": [[{"node": node_gcal_agenda, "type": "main", "index": 0}]]}
    conns[node_gcal_agenda] = {"main": [[{"node": node_gcal_tugas, "type": "main", "index": 0}]]}
    conns[node_gcal_tugas] = {"main": [[{"node": node_gcal_kuliah, "type": "main", "index": 0}]]}
    conns[node_gcal_kuliah] = {"main": [[{"node": node_process, "type": "main", "index": 0}]]}
    conns[node_process] = {"main": [[{"node": node_exec_pg, "type": "main", "index": 0}]]}
    conns[node_exec_pg] = {"main": [[{"node": node_switch_dec, "type": "main", "index": 0}]]}

    conns[node_switch_dec] = {
        "main": [
            [{"node": node_update_gcal, "type": "main", "index": 0}],
            [{"node": node_delete_gcal, "type": "main", "index": 0}],
            [{"node": "[HTTP Whatsapp]8", "type": "main", "index": 0}]
        ]
    }
    conns[node_update_gcal] = {"main": [[{"node": "[HTTP Whatsapp]8", "type": "main", "index": 0}]]}
    conns[node_delete_gcal] = {"main": [[{"node": "[HTTP Whatsapp]8", "type": "main", "index": 0}]]}

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Successfully upgraded {filepath.name}")

upgrade_gcal_assistant(REPO_ROOT / "workflow" / "wa-to-gcal-assistant.json", is_manda=False)
upgrade_gcal_assistant(REPO_ROOT / "n8n" / "workflow" / "wa-to-gcal-assistant.json", is_manda=False)
upgrade_gcal_assistant(REPO_ROOT / "workflow" / "manda-gcal-assistant.json", is_manda=True)
upgrade_gcal_assistant(REPO_ROOT / "n8n" / "workflow" / "manda-gcal-assistant.json", is_manda=True)

# ==============================================================================
# 3. UPGRADE wa-conversation.json
# ==============================================================================
print("\n🚀 [3/4] Upgrading wa-conversation.json...")

def upgrade_wa_conversation(filepath: Path):
    if not filepath.exists(): return
    with open(filepath, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    nodes = data.get("nodes", [])
    conns = data.get("connections", {})

    # 1. Add Get GCal Okta Tugas & Get GCal Manda Tugas if not present
    existing_node_names = {n.get("name") for n in nodes}
    
    if "Get GCal Okta Tugas" not in existing_node_names:
        nodes.append({
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": "={{ $env.GCAL_OKTA_TUGAS }}",
                    "mode": "id"
                },
                "returnAll": True,
                "timeMin": "={{ $now.setZone('Asia/Jakarta').minus({ days: 7 }).startOf('day').toISO() }}",
                "timeMax": "={{ $now.setZone('Asia/Jakarta').plus({ days: 30 }).endOf('day').toISO() }}",
                "options": {
                    "singleEvents": True
                }
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [350, -180],
            "id": "get-gcal-okta-tugas-vision",
            "name": "Get GCal Okta Tugas",
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            },
            "alwaysOutputData": True
        })
        print(f"[{filepath.name}] Added 'Get GCal Okta Tugas'")

    if "Get GCal Manda Tugas" not in existing_node_names:
        nodes.append({
            "parameters": {
                "operation": "getAll",
                "calendar": {
                    "__rl": True,
                    "value": "={{ $env.GCAL_MANDA_TUGAS }}",
                    "mode": "id"
                },
                "returnAll": True,
                "timeMin": "={{ $now.setZone('Asia/Makassar').minus({ days: 7 }).startOf('day').toISO() }}",
                "timeMax": "={{ $now.setZone('Asia/Makassar').plus({ days: 30 }).endOf('day').toISO() }}",
                "options": {
                    "singleEvents": True
                }
            },
            "type": "n8n-nodes-base.googleCalendar",
            "typeVersion": 1.3,
            "position": [790, -180],
            "id": "get-gcal-manda-tugas-vision",
            "name": "Get GCal Manda Tugas",
            "credentials": {
                "googleCalendarOAuth2Api": {
                    "id": "kXkpk4YfItv3zvuT",
                    "name": "Google Calendar account"
                }
            },
            "alwaysOutputData": True
        })
        print(f"[{filepath.name}] Added 'Get GCal Manda Tugas'")

    # Connect serial chain:
    # Switch Vision Query[0] -> Get GCal Okta Agenda -> Get GCal Okta Tugas -> Get GCal Okta Kuliah
    # -> Get GCal Manda Agenda -> Get GCal Manda Tugas -> Get GCal Manda Kuliah -> Format Calendar Vision
    conns["Get GCal Okta Agenda"] = {"main": [[{"node": "Get GCal Okta Tugas", "type": "main", "index": 0}]]}
    conns["Get GCal Okta Tugas"] = {"main": [[{"node": "Get GCal Okta Kuliah", "type": "main", "index": 0}]]}
    conns["Get GCal Okta Kuliah"] = {"main": [[{"node": "Get GCal Manda Agenda", "type": "main", "index": 0}]]}
    conns["Get GCal Manda Agenda"] = {"main": [[{"node": "Get GCal Manda Tugas", "type": "main", "index": 0}]]}
    conns["Get GCal Manda Tugas"] = {"main": [[{"node": "Get GCal Manda Kuliah", "type": "main", "index": 0}]]}
    conns["Get GCal Manda Kuliah"] = {"main": [[{"node": "Format Calendar Vision", "type": "main", "index": 0}]]}

    # 2. Update Format Calendar Vision
    for node in nodes:
        if node.get("name") == "Format Calendar Vision":
            node["parameters"]["jsCode"] = """function extractEvents(nodeName, label, tz = 'Asia/Jakarta') {
  let raw = [];
  try {
    raw = $(nodeName).all();
  } catch (e) {}
  
  const valid = raw.filter(e => e.json && (e.json.summary || e.json.id));
  if (valid.length === 0) return `${label}: Tidak ada.`;
  
  const lines = [];
  for (const item of valid) {
    const d = item.json;
    const summary = d.summary || '(Tanpa judul)';
    if (d.start?.date) {
      lines.push(`  • ${summary} [Seharian - ${d.start.date}]`);
    } else if (d.start?.dateTime) {
      const start = new Date(d.start.dateTime);
      const end = d.end?.dateTime ? new Date(d.end.dateTime) : null;
      const startStr = start.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: tz });
      const endStr = end ? end.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: tz }) : '';
      const dateStr = start.toLocaleDateString('id-ID', { weekday: 'short', day: 'numeric', month: 'short', timeZone: tz });
      const timeRange = endStr ? `${startStr} - ${endStr}` : startStr;
      lines.push(`  • ${summary} (${dateStr}, ${timeRange})`);
    }
  }
  return `${label}:\\n` + lines.join('\\n');
}

const oktaKuliah = extractEvents('Get GCal Okta Kuliah', 'Jadwal Kuliah Okta', 'Asia/Jakarta');
const oktaAgenda = extractEvents('Get GCal Okta Agenda', 'Agenda Pribadi Okta', 'Asia/Jakarta');
const oktaTugas = extractEvents('Get GCal Okta Tugas', 'Tugas & Deadline Okta', 'Asia/Jakarta');
const mandaKuliah = extractEvents('Get GCal Manda Kuliah', 'Jadwal Kuliah Kak Manda', 'Asia/Makassar');
const mandaAgenda = extractEvents('Get GCal Manda Agenda', 'Agenda Kak Manda', 'Asia/Makassar');
const mandaTugas = extractEvents('Get GCal Manda Tugas', 'Tugas & Deadline Kak Manda', 'Asia/Makassar');

const visionText = `📅 DATA GOOGLE CALENDAR TERKINI (KULIAH, AGENDA & TUGAS AKTIF):\\n\\n${oktaKuliah}\\n\\n${oktaAgenda}\\n\\n${oktaTugas}\\n\\n${mandaKuliah}\\n\\n${mandaAgenda}\\n\\n${mandaTugas}`;

const prev = $('Format Memory Context').item.json;
return [{
  json: {
    ...prev,
    visionContext: visionText
  }
}];"""
            print(f"[{filepath.name}] Updated Format Calendar Vision")

        # 3. Update Gemini System Prompt in Gemini Build Message & Gemini Build Message1
        if "Gemini Build Message" in node.get("name", ""):
            prompt_text = """Kamu adalah AI Asisten Cerdas untuk WhatsApp.

LOGIKA PERAN:
1. JIKA PENGIRIM ADALAH OKTA (${$env.MY_WA_NUMBER}):
   - Kamu adalah co-pilot developer & asisten pribadi Okta.
   - Bersikap sigap, efisien, to-the-point, santai (panggil "bro" atau "Okta").
   - Jika Okta mengirimkan pesan suara (voice note), dengarkan audio yang terlampir dengan seksama lalu responi.
   - TITIP PESAN KE KAK MANDA:
     - Jika Okta menitipkan pesan untuk Kak Manda (misal: "titip pesan ke manda", "bilang ke manda"):
       - Konfirmasi bahwa pesan untuk Kak Manda sudah dicatat dan langsung otomatis diteruskan ke WhatsApp Kak Manda!

2. JIKA DI GRUP ATAU PENGIRIM LAIN:
   - Bersikap ramah, santai, solutif, ringkas, dan menyesuaikan obrolan.

3. KEMAMPUAN MULTIMODAL & IMAGE OCR / VISION:
   - Jika pengguna melampirkan atau me-reply/quote gambar/foto:
     - Amati dan pahami gambar secara visual (bisa materi kuliah, slide presentasi, grafik, lembar soal tugas, struk belanja, dsb).
     - Lakukan OCR untuk membaca teks dalam gambar secara tepat jika ditanyakan.
     - Jelaskan maksud gambar, bantu kerjakan soal tugas, atau ekstrak data belanjaan dengan ringkas dan jelas.

RIWAYAT PERCAKAPAN SEBELUMNYA:
${$json.memoryContext || "(Belum ada riwayat sebelumnya)"}

${$json.visionContext ? `INFORMASI REAL-TIME SISTEM (VISION KAMU):
${$json.visionContext}

ATURAN PENTING PENGGUNAAN DATA VISION DI ATAS:
- Gunakan data real-time di atas LANGSUNG untuk menjawab pertanyaan jadwal, agenda, tugas, catatan/notes, pengumuman, atau presensi secara to-the-point dan akurat.
- DILARANG KERAS menjawab "bentar aku cek dulu", "tunggu ya aku cekin", atau sejenisnya, KARENA KAMU SUDAH MEMEGANG DATA NYATA DI ATAS!
- Jika di data tertulis tidak ada jadwal / catatan kosong, sampaikan dengan jelas bahwa tidak ada acara / catatan.` : ''}

INFORMASI SAAT INI:
- Pengirim: ${$json.wa.pushName || "User"} (${$json.wa.participant || $json.wa.remoteJid})
- Waktu Sekarang: ${$json.wa.dateTimeWib || $json.wa.dateTime} (WIB / UTC+7)
- Pesan: "${$json.wa.currentText || $json.wa.cleanText || ($json.wa.hasAudio ? '[Pesan Suara / Voice Note terlampir di atas]' : $json.wa.hasImage ? '[Foto / Gambar terlampir di atas]' : '[Media]')}"
- Quoted: "${$json.wa.quotedText || '-'}"

==================================================
FITUR AKSI OTOMATIS (ACTION TRIGGERS)
==================================================
Jika pengguna meminta kamu melakukan suatu aksi nyata, kamu WAJIB menyertakan tag aksi di BARIS PALING AKHIR responmu:

1. PEMBUATAN TUGAS & AGENDA KALENDER:
   <<<ACTION:TUGAS|TARGET|DETAIL>>>  -> untuk tugas kuliah, PR, deadline project.
   <<<ACTION:JADWAL|TARGET|DETAIL>>> -> untuk rapat, meeting, acara, kegiatan.
   TARGET: "okta" atau "manda"
   DETAIL: Judul lengkap + waktu & tanggal spesifik (contoh: "PPT Pengabdian deadline Kamis 22 Oktober 2026 jam 23.59")

2. LIFECYCLE TUGAS/AGENDA KALENDER (SELESAI / HAPUS) & PERLINDUNGAN KULIAH:
   <<<ACTION:DONE|TARGET|JUDUL>>>   -> tandai tugas/jadwal sebagai [SELESAI] di kalender.
   <<<ACTION:DELETE|TARGET|JUDUL>>> -> hapus tugas/jadwal dari kalender.
   TARGET: "okta" atau "manda"
   
   ⚠️ ATURAN KETAT LIFECYCLE KALENDER:
   a. JADWAL KULIAH TIDAK DAPAT DIHAPUS ATAU DITANDAI SELESAI!
      - Kalender kuliah dilindungi penuh. Jika user meminta hapus jadwal kuliah, TOLAK dengan sopan dan jelaskan bahwa jadwal kuliah dilindungi, namun ruang kelas bisa diubah atau ditandai libur via perintah `/edit-kuliah [matkul] [ruang / LIBUR]`. DILARANG MENGELUARKAN `<<<ACTION:DELETE>>>` untuk mata kuliah!
   b. JANGAN BERHALUSINASI MENYATAKAN SUDAH BERHASIL MENGHAPUS SEBELUM SISTEM MEMPROSES!
      - Katakan "Oke bro, aku bantu proses di kalender..." bukan "Udah aku hapus ya".
   c. TUGAS/AGENDA DUPLIKAT:
      - Jika user menyebut ada tugas ganda / duplikat dan ingin menghapus salah satunya (contoh: "hapus salah satu tugas comvis"), keluarkan tag `<<<ACTION:DELETE|okta|comvis>>>`. Sistem backend akan otomatis memeriksa dan mengirimkan menu nomor pilihan kepada user jika terdapat duplikat!

3. PENCATATAN & TO-DO (NOTES SYSTEM):
   <<<ACTION:NOTE_ADD|TARGET|DETAIL>>> -> catat hal penting/utang/to-do tanpa jam terikat.
   <<<ACTION:NOTE_DONE|ID>>>           -> tandai catatan selesai berdasarkan ID catatan.

4. PENCATATAN PENGELUARAN & EXPENSE TRACKER (DARI FOTO STRUK ATAU TEKS):
   - Jika pengguna mengirim foto struk/nota belanjaan ATAU mengetik pengeluaran:
     <<<ACTION:EXPENSE_ADD|TARGET|AMOUNT|CATEGORY|MERCHANT|ITEMS>>>
     TARGET: "okta" atau "manda"
     AMOUNT: Angka murni tanpa titik/koma (misal: 25000)
     CATEGORY: "makan", "transport", "belanja", "tagihan", atau "lainnya"
     MERCHANT: Nama toko / warung / merchant
     ITEMS: Ringkasan barang yang dibeli

5. PRESENSI KULIAH UB:
   <<<ACTION:PRESENSI|hadir>>> -> jika Okta meminta absen ("@n8n tolong absenkan kelas sekarang").

Jawablah dengan ringkas, cerdas, dan to-the-point:"""

            node["parameters"]["jsonBody"] = """={{
  {
    "contents": [
      {
        "parts": [
          ...( $json.base64Audio ? [{
            "inline_data": {
              "mime_type": "audio/ogg",
              "data": $json.base64Audio
            }
          }] : [] ),
          ...( $json.base64Image ? [{
            "inline_data": {
              "mime_type": $json.imageMimetype || "image/jpeg",
              "data": $json.base64Image
            }
          }] : [] ),
          {
            "text": `""" + prompt_text + """`
          }
        ]
      }
    ],
    "generationConfig": {
      ...( ($json.base64Audio || $json.base64Image) ? { "thinkingConfig": { "thinkingBudget": 0 } } : { "maxOutputTokens": 1024 } )
    }
  }
}}"""
            print(f"[{filepath.name}] Updated prompt in {node['name']}")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Successfully upgraded {filepath.name}")

upgrade_wa_conversation(REPO_ROOT / "workflow" / "wa-conversation.json")
upgrade_wa_conversation(REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json")

# ==============================================================================
# 4. UPDATE README.md
# ==============================================================================
print("\n🚀 [4/4] Updating README.md...")

readme_path = REPO_ROOT / "README.md"
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        readme_content = f.read()

    # Add /edit-kuliah and safe confirmation explanation if not in README
    if "/edit-kuliah" not in readme_content:
        # Update calendar commands section
        target_marker = "| `/hapus [judul]` | Menghapus agenda dari Google Calendar |"
        replacement = """| `/done [judul]` atau `/selesai [judul]` | Menandai tugas/agenda selesai di Google Calendar (`[SELESAI]`) |
| `/hapus [judul]` | Menghapus agenda/tugas (dilengkapi konfirmasi cerdas jika ada duplikat) |
| `/edit-kuliah [matkul] [ruang / LIBUR]` | Mengubah ruang kelas atau menandai `[LIBUR]` tanpa menghapus jadwal |"""
        if target_marker in readme_content:
            readme_content = readme_content.replace(target_marker, replacement)
        
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        print("✅ Updated README.md with safe calendar lifecycle and /edit-kuliah")

print("\n🎉 ALL WORKFLOWS SUCCESSFULLY UPGRADED!")
