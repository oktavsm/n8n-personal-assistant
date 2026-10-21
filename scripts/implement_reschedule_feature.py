#!/usr/bin/env python3
"""
Complete Implementation of Reschedule (Change Date/Time) Feature:
1. wa-to-gcal-assistant & manda-gcal-assistant:
   - Switch1: Fix routing so /edit-* and /reschedule never trigger new event creation
   - Update Safe GCal Event: Add start & end to updateFields
   - Process Safe Calendar Action: Add /reschedule logic with candidate matching, multi-choice, and fallback
2. master-router-webhook:
   - Switch: Add /reschedule, prevent /jadwal & /tugas from intercepting /edit & /reschedule
   - [Script] Message Builder: Add /edit-jadwal and /reschedule to /help
3. wa-conversation:
   - Gemini prompt: Add <<<ACTION:RESCHEDULE|TARGET|JUDUL|START_ISO|END_ISO|WAKTU_TEXT>>>
   - Process AI Output & Actions: Parse ACTION:RESCHEDULE and route to /reschedule
4. README.md: Update documentation and command reference
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

OKTA_GCAL_PATH = REPO_ROOT / "workflow" / "wa-to-gcal-assistant.json"
MANDA_GCAL_PATH = REPO_ROOT / "workflow" / "manda-gcal-assistant.json"
WA_CONV_PATH = REPO_ROOT / "workflow" / "wa-conversation.json"
ROUTER_PATH = REPO_ROOT / "workflow" / "master-router-webhook.json"

OKTA_GCAL_N8N = REPO_ROOT / "n8n" / "workflow" / "wa-to-gcal-assistant.json"
MANDA_GCAL_N8N = REPO_ROOT / "n8n" / "workflow" / "manda-gcal-assistant.json"
WA_CONV_N8N = REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json"
ROUTER_N8N = REPO_ROOT / "n8n" / "workflow" / "master-router-webhook.json"

README_PATH = REPO_ROOT / "README.md"


def update_json_file(path_src, path_dst, updater_fn):
    with open(path_src, "r", encoding="utf-8") as f:
        data = json.load(f)
    is_list = isinstance(data, list)
    wf = data[0] if is_list else data
    updater_fn(wf)
    with open(path_dst, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Updated {path_dst.name}")


# ==============================================================================
# 1. SAFE CALENDAR ACTION CODE GENERATOR (OKTA & MANDA)
# ==============================================================================
def get_safe_action_code(is_manda=False):
    user_name = 'manda' if is_manda else 'okta'
    env_agenda = '$env.GCAL_MANDA_AGENDA' if is_manda else '$env.GCAL_OKTA_AGENDA'
    env_tugas = '$env.GCAL_MANDA_TUGAS' if is_manda else '$env.GCAL_OKTA_TUGAS'
    env_kuliah = '$env.GCAL_MANDA_KULIAH' if is_manda else '$env.GCAL_OKTA_KULIAH'
    user_tz = 'Asia/Makassar' if is_manda else 'Asia/Jakarta'
    fetch_pending_node = '[PG] Manda Fetch Pending Selection' if is_manda else '[PG] Fetch Pending Selection'
    fetch_kuliah_node = 'Manda Fetch GCal Kuliah For Match' if is_manda else 'Fetch GCal Kuliah For Match'
    fetch_agenda_node = 'Manda Fetch GCal Agenda For Match' if is_manda else 'Fetch GCal Agenda For Match'
    fetch_tugas_node = 'Manda Fetch GCal Tugas For Match' if is_manda else 'Fetch GCal Tugas For Match'

    return f"""const waData = $('[Code] Get WA Data').first().json || {{}};
const rawText = (waData.pesanWA || '').trim();
const textLower = (waData.pesanWALower || '').trim();
const targetNumber = waData.targetNumber || '';
const userName = '{user_name}';
const envAgenda = {env_agenda};
const envTugas = {env_tugas};
const envKuliah = {env_kuliah};
const userTz = '{user_tz}';

// Check if user is replying to a pending selection
let pendingItem = null;
try {{
  const p = $('{fetch_pending_node}').first().json;
  if (p && p.action_type && p.candidates) {{
    pendingItem = p;
    if (typeof pendingItem.candidates === 'string') {{
      pendingItem.candidates = JSON.parse(pendingItem.candidates);
    }}
  }}
}} catch (e) {{}}

const isCancel = ['batal', 'cancel', '/batal', '/cancel'].includes(textLower);
const numMatch = textLower.match(/^(?:hapus\\s+|selesai\\s+|edit\\s+|reschedule\\s+|pilih\\s+|#)?(\\d+)$/i);

// -------------------------------------------------------------
// 1. HANDLE SELECTION REPLY (IF PENDING ACTION EXISTS)
// -------------------------------------------------------------
if (pendingItem && (isCancel || numMatch)) {{
  const deletePg = `DELETE FROM user_pending_actions WHERE user_name = '${{userName}}' AND room_jid = '${{targetNumber}}';`;

  if (isCancel) {{
    return [{{
      json: {{
        decision: 'REPLY_ONLY',
        message: '❌ Permintaan dibatalkan. Tidak ada agenda atau tugas yang diubah.',
        pgQuery: deletePg
      }}
    }}];
  }}

  const selectedIdx = parseInt(numMatch[1], 10);
  const candidates = Array.isArray(pendingItem.candidates) ? pendingItem.candidates : [];
  
  if (selectedIdx < 1 || selectedIdx > candidates.length) {{
    return [{{
      json: {{
        decision: 'REPLY_ONLY',
        message: `⚠️ Nomor pilihan tidak valid. Silakan balas dengan angka *1* s/d *${{candidates.length}}*, atau ketik *batal*.`,
        pgQuery: 'SELECT 1;'
      }}
    }}];
  }}

  const selected = candidates[selectedIdx - 1];
  const act = selected.actionType || pendingItem.action_type;

  if (act === 'hapus') {{
    return [{{
      json: {{
        decision: 'EXECUTE_DELETE',
        calendarId: selected.calendarId,
        eventId: selected.eventId,
        message: `🗑️ Agenda/Tugas *${{selected.summary}}* telah berhasil dihapus dari Google Calendar!`,
        pgQuery: deletePg
      }}
    }}];
  }} else if (act === 'reschedule') {{
    const newSummary = selected.newSummary || selected.summary;
    return [{{
      json: {{
        decision: 'EXECUTE_UPDATE',
        calendarId: selected.calendarId,
        eventId: selected.eventId,
        newSummary: newSummary,
        newStart: selected.newStart,
        newEnd: selected.newEnd,
        message: `🕒 Jadwal/Tugas *${{selected.summary}}* berhasil direschedule!\\n\\n📌 *Sebelumnya:* ${{selected.timeText}}\\n➡️ *Menjadi:* ${{selected.newTimeText || selected.newStart}}`,
        pgQuery: deletePg
      }}
    }}];
  }} else if (act === 'edit' || act === 'edit judul') {{
    const newSummary = selected.newSummary || 'Agenda';
    return [{{
      json: {{
        decision: 'EXECUTE_UPDATE',
        calendarId: selected.calendarId,
        eventId: selected.eventId,
        newSummary: newSummary,
        message: `✏️ Judul Agenda/Tugas berhasil diperbarui di Google Calendar!\\n\\n📌 *Lama:* ${{selected.summary}}\\n➡️ *Baru:* ${{newSummary}}`,
        pgQuery: deletePg
      }}
    }}];
  }} else {{
    // Selesai / Done
    const origSummary = selected.summary || 'Agenda';
    const newSummary = origSummary.startsWith('[SELESAI]') ? origSummary : `[SELESAI] ${{origSummary}}`;
    return [{{
      json: {{
        decision: 'EXECUTE_UPDATE',
        calendarId: selected.calendarId,
        eventId: selected.eventId,
        newSummary: newSummary,
        message: `✅ Agenda/Tugas *${{origSummary}}* telah ditandai *[SELESAI]* di Google Calendar! 🎉`,
        pgQuery: deletePg
      }}
    }}];
  }}
}}

// -------------------------------------------------------------
// 2. HANDLE /edit-kuliah
// -------------------------------------------------------------
const isEditKuliah = textLower.startsWith('/edit-kuliah') || textLower.startsWith('/edit kuliah');
if (isEditKuliah) {{
  const cleanCmd = rawText.replace(/^\\/edit-?kuliah\\s*/i, '').trim();
  const parts = cleanCmd.split(/\\s+/);
  
  if (parts.length < 2) {{
    return [{{
      json: {{
        decision: 'REPLY_ONLY',
        message: `⚠️ Format tidak lengkap!\\n\\n*Format:* \\`/edit-kuliah [matkul] [ruang / LIBUR]\\`\\n*Contoh:*\\n• \\`/edit-kuliah comvis F3.11\\`\\n• \\`/edit-kuliah comvis [LIBUR]\\``,
        pgQuery: 'SELECT 1;'
      }}
    }}];
  }}

  const updateVal = parts[parts.length - 1].trim();
  const matkulQuery = parts.slice(0, -1).join(' ').toLowerCase().trim();

  let kuliahEvents = [];
  try {{ kuliahEvents = $('{fetch_kuliah_node}').all(); }} catch (e) {{}}

  let matchedKuliah = null;
  for (const item of kuliahEvents) {{
    const d = item.json;
    if (!d || !d.id || !d.summary) continue;
    const sLower = d.summary.toLowerCase();
    if (sLower.includes(matkulQuery) || matkulQuery.includes(sLower)) {{
      matchedKuliah = d;
      break;
    }}
  }}

  if (!matchedKuliah) {{
    return [{{
      json: {{
        decision: 'REPLY_ONLY',
        message: `⚠️ Jadwal kuliah *\"${{matkulQuery}}\"* tidak ditemukan di kalender Kuliah.`,
        pgQuery: 'SELECT 1;'
      }}
    }}];
  }}

  const oldSummary = matchedKuliah.summary;
  let newSummary = oldSummary;

  if (updateVal.toUpperCase().includes('LIBUR')) {{
    newSummary = oldSummary.includes('[LIBUR]') ? oldSummary : `[LIBUR] ${{oldSummary}}`;
  }} else {{
    const roomUpper = updateVal.toUpperCase();
    if (/\\b[A-Za-z]\\d+\\.\\d+\\b/.test(oldSummary)) {{
      newSummary = oldSummary.replace(/\\b[A-Za-z]\\d+\\.\\d+\\b/g, roomUpper);
    }} else {{
      newSummary = `[${{roomUpper}}] ${{oldSummary}}`;
    }}
  }}

  return [{{
    json: {{
      decision: 'EXECUTE_UPDATE',
      calendarId: envKuliah,
      eventId: matchedKuliah.id,
      newSummary: newSummary,
      message: `✅ Jadwal kuliah berhasil diperbarui:\\n📚 *${{oldSummary}}* ➡️ *${{newSummary}}*`,
      pgQuery: 'SELECT 1;'
    }}
  }}];
}}

// -------------------------------------------------------------
// 3. HANDLE /reschedule, /edit-jadwal, /hapus, /done
// -------------------------------------------------------------
const isReschedule = textLower.startsWith('/reschedule') || textLower.startsWith('/edit-waktu') || textLower.startsWith('/ganti-waktu') || textLower.startsWith('/undur') || textLower.startsWith('/majukan');
const isEdit = (textLower.startsWith('/edit-jadwal') || textLower.startsWith('/edit-agenda') || textLower.startsWith('/edit-tugas') || textLower.startsWith('/edit ')) && !isReschedule;
const isDelete = textLower.startsWith('/hapus') || textLower.startsWith('/delete');
const isDone = textLower.startsWith('/done') || textLower.startsWith('/selesai');

let rawQuery = '';
let editOldQuery = '';
let editNewTitle = '';

let rescheduleStart = '';
let rescheduleEnd = '';
let rescheduleTimeText = '';
let rescheduleNewTitle = '';

if (isReschedule) {{
  let cleanResched = rawText.replace(/^\\/(?:reschedule|edit-waktu|ganti-waktu|undur|majukan)(?:-jadwal|-tugas)?\\s*/i, '').trim();
  cleanResched = cleanResched.replace(/^(?:manda|okta)\\s*/i, '').trim();

  const parts = cleanResched.split('|').map(s => s.trim());
  rawQuery = parts[0] || '';
  rescheduleStart = parts[1] || '';
  rescheduleEnd = parts[2] || '';
  rescheduleTimeText = parts[3] || '';
  rescheduleNewTitle = parts[4] || '';

  // Auto-fill end time if start is valid ISO and end is missing
  if (rescheduleStart && !rescheduleEnd) {{
    try {{
      const dt = new Date(rescheduleStart);
      if (!isNaN(dt.getTime())) {{
        const endDt = new Date(dt.getTime() + 60 * 60 * 1000);
        rescheduleEnd = endDt.toISOString();
      }}
    }} catch (e) {{}}
  }}

  // Auto-format time text if missing
  if (!rescheduleTimeText && rescheduleStart) {{
    try {{
      const dt = new Date(rescheduleStart);
      rescheduleTimeText = dt.toLocaleString('id-ID', {{
        timeZone: userTz,
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      }}) + (userTz === 'Asia/Jakarta' ? ' WIB' : ' WITA');
    }} catch (e) {{}}
  }}

  if (!rawQuery || !rescheduleStart) {{
    return [{{
      json: {{
        decision: 'REPLY_ONLY',
        message: `⚠️ Format reschedule belum lengkap!\\n\\n*Format:* \\`/reschedule [nama] | [waktu ISO mulai] | [waktu ISO selesai] | [keterangan waktu]\\`\\n*Contoh:* \\`/reschedule meet TSA | 2026-10-22T20:00:00+07:00 | 2026-10-22T21:00:00+07:00 | Kamis 20.00 WIB\\``,
        pgQuery: 'SELECT 1;'
      }}
    }}];
  }}
}} else if (isEdit) {{
  let cleanEdit = rawText.replace(/^\\/edit-(?:jadwal|agenda|tugas)?\\s*/i, '').trim();
  cleanEdit = cleanEdit.replace(/^\\/edit\\s+/i, '').trim();
  cleanEdit = cleanEdit.replace(/^(?:manda|okta)\\s*/i, '').trim();

  if (cleanEdit.includes('|')) {{
    const p = cleanEdit.split('|');
    editOldQuery = p[0].trim();
    editNewTitle = p.slice(1).join('|').trim();
  }} else if (cleanEdit.includes('->')) {{
    const p = cleanEdit.split('->');
    editOldQuery = p[0].trim();
    editNewTitle = p.slice(1).join('->').trim();
  }} else if (cleanEdit.toLowerCase().includes(' jadi ')) {{
    const p = cleanEdit.split(/\\s+jadi\\s+/i);
    editOldQuery = p[0].trim();
    editNewTitle = p.slice(1).join(' jadi ').trim();
  }} else {{
    editOldQuery = cleanEdit;
  }}

  rawQuery = editOldQuery;

  if (!editOldQuery || !editNewTitle) {{
    return [{{
      json: {{
        decision: 'REPLY_ONLY',
        message: `⚠️ Format edit belum lengkap!\\n\\n*Format:* \\`/edit-jadwal [nama lama] | [nama baru]\\`\\n*Contoh:* \\`/edit-jadwal meet tanoto | [Meeting] TSA - Meet Lead Other\\``,
        pgQuery: 'SELECT 1;'
      }}
    }}];
  }}
}} else if (isDelete) {{
  rawQuery = rawText.replace(/^\\/hapus(-jadwal)?\\s*/i, '').trim();
  rawQuery = rawQuery.replace(/^(manda|okta)\\s*/i, '').trim();
}} else if (isDone) {{
  rawQuery = rawText.replace(/^(\\/done|\\/selesai)\\s*/i, '').trim();
  rawQuery = rawQuery.replace(/^(manda|okta)\\s*/i, '').trim();
}}

if (!rawQuery) {{
  if (/^\\d+$/.test(textLower)) {{
    return [{{ json: {{ decision: 'IGNORE', message: '', pgQuery: 'SELECT 1;' }} }}];
  }}
  return [{{
    json: {{
      decision: 'REPLY_ONLY',
      message: `⚠️ Mohon sertakan nama agenda atau tugas yang ingin diproses.\\n_Contoh:_ \\`/done PPT\\` atau \\`/edit-jadwal meet tanoto | Meeting TSA\\``,
      pgQuery: 'SELECT 1;'
    }}
  }}];
}}

// Helper to format event date/time
function formatEventTime(d) {{
  if (d.start?.date) return `${{d.start.date}} (Seharian)`;
  if (d.start?.dateTime) {{
    const dt = new Date(d.start.dateTime);
    return dt.toLocaleDateString('id-ID', {{ weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: userTz }});
  }}
  return '-';
}}

function getEventTimestamp(d) {{
  const t = d.start?.dateTime || d.start?.date;
  return t ? new Date(t).getTime() : 0;
}}

function cleanString(str) {{
  return (str || '')
    .toLowerCase()
    .replace(/\\[.*?\\]/g, ' ')
    .replace(/[^a-z0-9\\s]/g, ' ')
    .replace(/\\s+/g, ' ')
    .trim();
}}

const stopWords = new Set([
  'tugas', 'agenda', 'jadwal', 'pr', 'kegiatan', 'acara', 'meeting', 'meet',
  'ku', 'mu', 'nya', 'punyaku', 'punya', 'milik',
  'dong', 'ya', 'nih', 'ini', 'itu', 'kelar', 'selesai', 'hapus', 'edit',
  'reschedule', 'undur', 'majukan', 'geser', 'ganti', 'waktu', 'tanggal',
  'sudah', 'udah', 'tolong', 'bantu', 'yang', 'sih', 'deh', 'lah',
  'di', 'ke', 'dari', 'pada', 'buat', 'untuk'
]);

const cleanedTokens = cleanString(rawQuery)
  .split(' ')
  .filter(w => w.length > 0 && !stopWords.has(w));

const queryTokens = cleanedTokens.length > 0
  ? cleanedTokens
  : cleanString(rawQuery).split(' ').filter(w => w.length > 0);

const cleanQueryStr = queryTokens.join(' ');

// Check if query matches Jadwal Kuliah only
let kuliahEvents = [];
try {{ kuliahEvents = $('{fetch_kuliah_node}').all(); }} catch (e) {{}}

let matchedKuliahName = '';
for (const item of kuliahEvents) {{
  const d = item.json;
  if (!d || !d.id || !d.summary) continue;
  const cSum = cleanString(d.summary);
  if (cSum.includes(cleanQueryStr) || (queryTokens.length > 0 && queryTokens.every(t => cSum.includes(t)))) {{
    matchedKuliahName = d.summary;
    break;
  }}
}}

// Collect all events from Agenda and Tugas
const allEvents = [];

let agendaEvents = [];
try {{ agendaEvents = $('{fetch_agenda_node}').all(); }} catch (e) {{}}
for (const item of agendaEvents) {{
  const d = item.json;
  if (!d || !d.id || !d.summary) continue;
  allEvents.push({{
    calendarType: 'Agenda',
    calendarId: envAgenda,
    eventId: d.id,
    summary: d.summary,
    cleanSummary: cleanString(d.summary),
    timeText: formatEventTime(d),
    timeMs: getEventTimestamp(d),
    isDone: d.summary.toUpperCase().includes('[SELESAI]'),
    actionType: isReschedule ? 'reschedule' : isEdit ? 'edit' : isDelete ? 'hapus' : 'selesai',
    newSummary: editNewTitle || rescheduleNewTitle || d.summary
  }});
}}

let tugasEvents = [];
try {{ tugasEvents = $('{fetch_tugas_node}').all(); }} catch (e) {{}}
for (const item of tugasEvents) {{
  const d = item.json;
  if (!d || !d.id || !d.summary) continue;
  allEvents.push({{
    calendarType: 'Tugas',
    calendarId: envTugas,
    eventId: d.id,
    summary: d.summary,
    cleanSummary: cleanString(d.summary),
    timeText: formatEventTime(d),
    timeMs: getEventTimestamp(d),
    isDone: d.summary.toUpperCase().includes('[SELESAI]'),
    actionType: isReschedule ? 'reschedule' : isEdit ? 'edit' : isDelete ? 'hapus' : 'selesai',
    newSummary: editNewTitle || rescheduleNewTitle || d.summary
  }});
}}

// Filter eligible events: if isDone, exclude already [SELESAI] items
const eligibleEvents = allEvents.filter(ev => isDone ? !ev.isDone : true);

// Step 1: High confidence matches (full substring or all query tokens match)
let candidates = eligibleEvents.filter(ev => {{
  const cSum = ev.cleanSummary;
  const rawSum = ev.summary.toLowerCase();
  return cSum.includes(cleanQueryStr) || rawSum.includes(cleanQueryStr) ||
         (queryTokens.length > 0 && queryTokens.every(t => cSum.includes(t) || rawSum.includes(t)));
}});

// Step 2: Partial token matches if no full match found and query has multiple words
if (candidates.length === 0 && queryTokens.length > 1) {{
  candidates = eligibleEvents.filter(ev => {{
    const cSum = ev.cleanSummary;
    const rawSum = ev.summary.toLowerCase();
    return queryTokens.some(t => t.length >= 3 && (cSum.includes(t) || rawSum.includes(t)));
  }});
}}

// Case 1: Matched Jadwal Kuliah only, and 0 matches in Agenda/Tugas -> Protected!
if (matchedKuliahName && candidates.length === 0) {{
  return [{{
    json: {{
      decision: 'REPLY_ONLY',
      message: `⚠️ *Jadwal kuliah dilindungi dan tidak dapat diubah namanya atau direschedule sembarangan.*\\n\\nMatakuliah: *${{matchedKuliahName}}*\\n\\nUntuk mengubah ruang kelas atau menandai libur, gunakan perintah:\\n👉 */edit-kuliah [matkul] [ruang / LIBUR]*\\n_Contoh:_ \\`/edit-kuliah ${{cleanQueryStr || rawQuery}} F3.11\\``,
      pgQuery: 'SELECT 1;'
    }}
  }}];
}}

// Case 2: Exactly 1 match -> Execute immediately!
if (candidates.length === 1) {{
  const single = candidates[0];
  const deletePg = `DELETE FROM user_pending_actions WHERE user_name = '${{userName}}' AND room_jid = '${{targetNumber}}';`;
  
  if (isReschedule) {{
    const finalSummary = rescheduleNewTitle || single.summary;
    return [{{
      json: {{
        decision: 'EXECUTE_UPDATE',
        calendarId: single.calendarId,
        eventId: single.eventId,
        newSummary: finalSummary,
        newStart: rescheduleStart,
        newEnd: rescheduleEnd,
        message: `🕒 Jadwal/Tugas *${{single.summary}}* berhasil direschedule!\\n\\n📌 *Sebelumnya:* ${{single.timeText}}\\n➡️ *Menjadi:* ${{rescheduleTimeText || rescheduleStart}}${{rescheduleNewTitle ? `\\n✏️ *Judul Baru:* ${{rescheduleNewTitle}}` : ''}}`,
        pgQuery: deletePg
      }}
    }}];
  }} else if (isEdit) {{
    return [{{
      json: {{
        decision: 'EXECUTE_UPDATE',
        calendarId: single.calendarId,
        eventId: single.eventId,
        newSummary: editNewTitle,
        message: `✏️ Judul Agenda/Tugas berhasil diperbarui di Google Calendar!\\n\\n📌 *Lama:* ${{single.summary}}\\n➡️ *Baru:* ${{editNewTitle}}`,
        pgQuery: deletePg
      }}
    }}];
  }} else if (isDelete) {{
    return [{{
      json: {{
        decision: 'EXECUTE_DELETE',
        calendarId: single.calendarId,
        eventId: single.eventId,
        message: `🗑️ Agenda/Tugas *${{single.summary}}* telah berhasil dihapus dari Google Calendar!`,
        pgQuery: deletePg
      }}
    }}];
  }} else {{
    // Selesai
    const origSummary = single.summary || 'Agenda';
    const newSummary = origSummary.startsWith('[SELESAI]') ? origSummary : `[SELESAI] ${{origSummary}}`;
    return [{{
      json: {{
        decision: 'EXECUTE_UPDATE',
        calendarId: single.calendarId,
        eventId: single.eventId,
        newSummary: newSummary,
        message: `✅ Agenda/Tugas *${{origSummary}}* telah ditandai *[SELESAI]* di Google Calendar! 🎉`,
        pgQuery: deletePg
      }}
    }}];
  }}
}}

// Case 3: Multiple matches (> 1) -> Prompt selection and store in user_pending_actions
if (candidates.length > 1) {{
  candidates.sort((a, b) => a.timeMs - b.timeMs);
  const numberedList = candidates.map((c, i) => `${{i + 1}}️⃣ *[${{c.calendarType}}]* ${{c.summary}} _(${{c.timeText}})_`).join('\\n');
  const actionLabel = isReschedule ? 'reschedule' : isEdit ? 'edit judul' : isDelete ? 'hapus' : 'selesai';

  const promptMsg = isReschedule
    ? `🔍 Ditemukan *${{candidates.length}}* item yang cocok dengan *\"${{rawQuery}}\"*:\\n\\n${{numberedList}}\\n\\nKetik nomor (contoh: *1*, *2*) untuk mereschedule ke *${{rescheduleTimeText || rescheduleStart}}*, atau ketik *batal*.`
    : isEdit
    ? `🔍 Ditemukan *${{candidates.length}}* item yang cocok dengan *\"${{rawQuery}}\"*:\\n\\n${{numberedList}}\\n\\nKetik nomor untuk mengubah judulnya menjadi *\"${{editNewTitle}}\"*, atau ketik *batal*.`
    : `🔍 Ditemukan *${{candidates.length}}* item yang cocok dengan *\"${{rawQuery}}\"*:\\n\\n${{numberedList}}\\n\\nKetik nomor (contoh: *1*, *2*) untuk konfirmasi *${{actionLabel}}*, atau ketik *batal*.`;

  if (isReschedule) {{
    candidates.forEach(c => {{
      c.actionType = 'reschedule';
      c.newStart = rescheduleStart;
      c.newEnd = rescheduleEnd;
      c.newTimeText = rescheduleTimeText;
      c.newSummary = rescheduleNewTitle || c.summary;
    }});
  }} else if (isEdit) {{
    candidates.forEach(c => {{ c.newSummary = editNewTitle; c.actionType = 'edit'; }});
  }}

  const candJsonStr = JSON.stringify(candidates).replace(/'/g, "''");
  const escapedQuery = (isReschedule
    ? `${{rawQuery}} | ${{rescheduleStart}}`
    : isEdit
    ? `${{rawQuery}} | ${{editNewTitle}}`
    : rawQuery
  ).replace(/'/g, "''");

  const insertPendingPg = `INSERT INTO user_pending_actions (user_name, room_jid, action_type, query_text, candidates, created_at)
VALUES ('${{userName}}', '${{targetNumber}}', '${{actionLabel}}', '${{escapedQuery}}', '${{candJsonStr}}'::jsonb, NOW())
ON CONFLICT (user_name, room_jid) DO UPDATE SET
  action_type = EXCLUDED.action_type,
  query_text = EXCLUDED.query_text,
  candidates = EXCLUDED.candidates,
  created_at = NOW();`;

  return [{{
    json: {{
      decision: 'REPLY_ONLY',
      message: promptMsg,
      pgQuery: insertPendingPg
    }}
  }}];
}}

// Case 4: 0 matches found -> Provide fallback list of all active upcoming tasks & agendas!
const activeUpcoming = eligibleEvents.filter(ev => !ev.isDone);
activeUpcoming.sort((a, b) => a.timeMs - b.timeMs);
const fallbackList = activeUpcoming.slice(0, 8);

if (fallbackList.length > 0) {{
  const actionLabel = isReschedule ? 'reschedule' : isEdit ? 'edit judul' : isDelete ? 'hapus' : 'selesai';
  const numberedList = fallbackList.map((c, i) => `${{i + 1}}️⃣ *[${{c.calendarType}}]* ${{c.summary}} _(${{c.timeText}})_`).join('\\n');

  const promptMsg = isReschedule
    ? `⚠️ Agenda atau tugas *\"${{rawQuery}}\"* tidak ditemukan secara spesifik.\\n\\nBerikut daftar agenda & tugas aktif kamu saat ini:\\n\\n${{numberedList}}\\n\\nKetik nomor (1 - ${{fallbackList.length}}) untuk mereschedule ke *${{rescheduleTimeText || rescheduleStart}}*, atau ketik *batal*.`
    : isEdit
    ? `⚠️ Agenda atau tugas *\"${{rawQuery}}\"* tidak ditemukan secara spesifik.\\n\\nBerikut daftar agenda & tugas aktif kamu saat ini:\\n\\n${{numberedList}}\\n\\nKetik nomor (1 - ${{fallbackList.length}}) untuk mengubah judulnya menjadi *\"${{editNewTitle}}\"*, atau ketik *batal*.`
    : `⚠️ Agenda atau tugas *\"${{rawQuery}}\"* tidak ditemukan secara spesifik.\\n\\nBerikut daftar agenda & tugas aktif kamu saat ini:\\n\\n${{numberedList}}\\n\\nKetik nomor (1 - ${{fallbackList.length}}) untuk konfirmasi *${{actionLabel}}*, atau ketik *batal*.`;

  if (isReschedule) {{
    fallbackList.forEach(c => {{
      c.actionType = 'reschedule';
      c.newStart = rescheduleStart;
      c.newEnd = rescheduleEnd;
      c.newTimeText = rescheduleTimeText;
      c.newSummary = rescheduleNewTitle || c.summary;
    }});
  }} else if (isEdit) {{
    fallbackList.forEach(c => {{ c.newSummary = editNewTitle; c.actionType = 'edit'; }});
  }}

  const candJsonStr = JSON.stringify(fallbackList).replace(/'/g, "''");
  const escapedQuery = (isReschedule
    ? `${{rawQuery}} | ${{rescheduleStart}}`
    : isEdit
    ? `${{rawQuery}} | ${{editNewTitle}}`
    : rawQuery
  ).replace(/'/g, "''");

  const insertPendingPg = `INSERT INTO user_pending_actions (user_name, room_jid, action_type, query_text, candidates, created_at)
VALUES ('${{userName}}', '${{targetNumber}}', '${{actionLabel}}', '${{escapedQuery}}', '${{candJsonStr}}'::jsonb, NOW())
ON CONFLICT (user_name, room_jid) DO UPDATE SET
  action_type = EXCLUDED.action_type,
  query_text = EXCLUDED.query_text,
  candidates = EXCLUDED.candidates,
  created_at = NOW();`;

  return [{{
    json: {{
      decision: 'REPLY_ONLY',
      message: promptMsg,
      pgQuery: insertPendingPg
    }}
  }}];
}}

// If completely 0 events in calendar
return [{{
  json: {{
    decision: 'REPLY_ONLY',
    message: `⚠️ Agenda atau tugas *\"${{rawQuery}}\"* tidak ditemukan, dan saat ini tidak ada agenda maupun tugas aktif di Google Calendar.`,
    pgQuery: 'SELECT 1;'
  }}
}}];
"""


# ==============================================================================
# 2. UPGRADE GCAL ASSISTANTS (OKTA & MANDA)
# ==============================================================================
def upgrade_gcal_workflow(wf, is_manda=False):
    prefix = "Manda " if is_manda else ""
    safe_proc_name = f"{prefix}Process Safe Calendar Action"
    update_node_name = f"{prefix}Update Safe GCal Event"

    for node in wf["nodes"]:
        # A. Switch1 Routing Guard
        if node["name"] == "Switch1":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            for r in rules:
                key = r.get("outputKey", "").lower()
                conds = r.get("conditions", {}).get("conditions", [])
                if not conds:
                    continue

                # Guard /jadwal
                if "/jadwal" in key:
                    conds[0]["leftValue"] = (
                        "={{\n"
                        "  !$json.pesanWALower.startsWith('/edit') &&\n"
                        "  !$json.pesanWALower.startsWith('/reschedule') &&\n"
                        "  !$json.pesanWALower.startsWith('/hapus') &&\n"
                        "  !$json.pesanWALower.startsWith('/done') &&\n"
                        "  !$json.pesanWALower.startsWith('/selesai') &&\n"
                        "  (\n"
                        "    $json.pesanWALower.startsWith('/jadwal') ||\n"
                        "    ($json.pesanWALower.startsWith('/agenda') && !['/agenda', '/agenda okta', '/agenda manda'].includes($json.pesanWALower))\n"
                        "  )\n"
                        "}}"
                    )
                # Guard /tugas
                elif "/tugas xxx" in key or "buat tugas" in key:
                    conds[0]["leftValue"] = (
                        "={{\n"
                        "  !$json.pesanWALower.startsWith('/edit') &&\n"
                        "  !$json.pesanWALower.startsWith('/reschedule') &&\n"
                        "  !$json.pesanWALower.startsWith('/hapus') &&\n"
                        "  !$json.pesanWALower.startsWith('/done') &&\n"
                        "  !$json.pesanWALower.startsWith('/selesai') &&\n"
                        "  $json.pesanWALower.startsWith('/tugas') &&\n"
                        "  !['/tugas', '/tugas okta', '/tugas manda'].includes($json.pesanWALower)\n"
                        "}}"
                    )
                # Lifecycle: /done, /hapus, /edit, /reschedule
                elif "kelola status agenda" in key or "/done atau /hapus" in key:
                    conds[0]["leftValue"] = (
                        "={{\n"
                        "  $json.pesanWALower.startsWith('/done') ||\n"
                        "  $json.pesanWALower.startsWith('/selesai') ||\n"
                        "  $json.pesanWALower.startsWith('/hapus') ||\n"
                        "  $json.pesanWALower.startsWith('/delete') ||\n"
                        "  $json.pesanWALower.startsWith('/edit') ||\n"
                        "  $json.pesanWALower.startsWith('/reschedule') ||\n"
                        "  /^(?:hapus\\s+|selesai\\s+|edit\\s+|reschedule\\s+|pilih\\s+|#)?\\d+$/i.test($json.pesanWALower) ||\n"
                        "  ['batal', 'cancel', '/batal', '/cancel'].includes($json.pesanWALower)\n"
                        "}}"
                    )

        # B. Process Safe Calendar Action Code
        elif node["name"] == safe_proc_name:
            node["parameters"]["jsCode"] = get_safe_action_code(is_manda)

        # C. Update Safe GCal Event (add start & end)
        elif node["name"] == update_node_name:
            node["parameters"]["updateFields"] = {
                "summary": f"={{{{ $('{safe_proc_name}').first().json.newSummary || undefined }}}}",
                "start": f"={{{{ $('{safe_proc_name}').first().json.newStart || undefined }}}}",
                "end": f"={{{{ $('{safe_proc_name}').first().json.newEnd || undefined }}}}"
            }


# ==============================================================================
# 3. UPGRADE MASTER ROUTER WEBHOOK
# ==============================================================================
def upgrade_master_router(wf):
    for node in wf["nodes"]:
        if node["name"] == "Switch":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            for i, r in enumerate(rules):
                conds = r.get("conditions", {}).get("conditions", [])
                if not conds:
                    continue
                left = conds[0].get("leftValue", "")

                # Rule 6: Lifecycle Switch
                if "isLifecycleCmd" in left:
                    conds[0]["leftValue"] = (
                        "={{ (() => {\n"
                        "  const data = $json.body?.data || {};\n"
                        "  const msg = data.message || {};\n"
                        "  const raw = (msg.conversation || msg.extendedTextMessage?.text || \"\").trim();\n"
                        "  const cleaned = raw.replace(/@[a-zA-Z0-9_\\-\\.]+\\s*/g, \"\").trim().toLowerCase();\n\n"
                        "  const isLifecycleCmd = cleaned.startsWith('/done') ||\n"
                        "                         cleaned.startsWith('/selesai') ||\n"
                        "                         cleaned.startsWith('/hapus') ||\n"
                        "                         cleaned.startsWith('/delete') ||\n"
                        "                         cleaned.startsWith('/edit') ||\n"
                        "                         cleaned.startsWith('/reschedule');\n\n"
                        "  const isSelectionReply = /^(?:hapus\\s+|selesai\\s+|edit\\s+|reschedule\\s+|pilih\\s+|#)?\\d+$/i.test(cleaned) ||\n"
                        "                           ['batal', 'cancel', '/batal', '/cancel'].includes(cleaned);\n\n"
                        "  return Boolean(isLifecycleCmd || isSelectionReply);\n"
                        "})() }}"
                    )

                # Rule 23: Catch-all WA Conversation Router
                elif "explicitCommands" in left:
                    # Make sure /reschedule and /edit are in explicitCommands so they don't get eaten by conversational catch-all
                    if '"/reschedule"' not in left:
                        left = left.replace(
                            '"/edit kuliah",',
                            '"/edit kuliah", "/edit", "/reschedule", "/delete",'
                        )
                        conds[0]["leftValue"] = left

        # Help message update
        elif node["name"] == "[Script] Message Builder":
            js = node["parameters"].get("jsCode", "")
            if "• */edit-jadwal" not in js:
                # Add edit-jadwal and reschedule descriptions
                old_section = "• */hapus [judul]* atau */hapus-jadwal [judul]*"
                new_section = (
                    "• */edit-jadwal [nama lama] | [nama baru]*\n"
                    "  Ganti nama agenda/tugas yang sudah ada tanpa membuat jadwal duplikat.\n"
                    "• */reschedule [nama] | [waktu]*\n"
                    "  Jadwalkan ulang / ganti tanggal & jam agenda atau deadline tugas.\n"
                    "• */hapus [judul]* atau */hapus-jadwal [judul]*"
                )
                node["parameters"]["jsCode"] = js.replace(old_section, new_section)


# ==============================================================================
# 4. UPGRADE WA-CONVERSATION
# ==============================================================================
def upgrade_wa_conversation(wf):
    for node in wf["nodes"]:
        if node["name"] == "[HTTP] Gemini Build Message":
            # Add Reschedule instruction to Gemini prompt
            json_body = node["parameters"].get("jsonBody", "")
            if "ACTION:RESCHEDULE" not in json_body:
                # Insert after LIFECYCLE TUGAS/AGENDA KALENDER
                target_marker = "2. LIFECYCLE TUGAS/AGENDA KALENDER (SELESAI / HAPUS / EDIT) & PERLINDUNGAN KULIAH:"
                replacement = (
                    "2. LIFECYCLE TUGAS/AGENDA KALENDER (SELESAI / HAPUS / EDIT) & PERLINDUNGAN KULIAH:\n"
                    "   <<<ACTION:DONE|TARGET|JUDUL>>>                      -> tandai tugas/jadwal sebagai [SELESAI] di kalender.\n"
                    "   <<<ACTION:DELETE|TARGET|JUDUL>>>                    -> hapus tugas/jadwal dari kalender.\n"
                    "   <<<ACTION:EDIT|TARGET|JUDUL_LAMA|JUDUL_BARU>>>      -> ralat/ubah nama agenda atau tugas yang sudah ada.\n"
                    "   <<<ACTION:RESCHEDULE|TARGET|JUDUL|START_ISO|END_ISO|WAKTU_TEXT>>> -> ganti tanggal/jam atau jadwalkan ulang agenda/tugas.\n"
                    "   TARGET: \"okta\" atau \"manda\"\n"
                    "   START_ISO: ISO string waktu mulai UTC+7 (contoh: 2026-10-22T20:00:00+07:00)\n"
                    "   END_ISO: ISO string waktu selesai UTC+7 (contoh: 2026-10-22T21:00:00+07:00)\n"
                    "   WAKTU_TEXT: Deskripsi waktu baru (contoh: \"Kamis, 22 Okt 2026 jam 20.00 WIB\")\n"
                    "   \n"
                    "   ⚠️ ATURAN KETAT RESCHEDULE & GANTI TANGGAL/JAM:\n"
                    "   - JIKA PENGGUNA INGIN MENGUNDUR, MEMAJUKAN, ATAU MENGGANTI TANGGAL/JAM AGENDA ATAU TUGAS:\n"
                    "     - DILARANG KERAS MENGELUARKAN <<<ACTION:JADWAL>>> ATAU <<<ACTION:TUGAS>>> karena itu akan MEMBUAT JADWAL BARU (DUPLIKAT)!\n"
                    "     - WAJIB mengeluarkan tag <<<ACTION:RESCHEDULE|TARGET|JUDUL|START_ISO|END_ISO|WAKTU_TEXT>>>.\n"
                    "     - Contoh:\n"
                    "       User: \"rapat TSA diundur besok jam 8 malam\"\n"
                    "       Baris terakhir: <<<ACTION:RESCHEDULE|okta|TSA|2026-10-22T20:00:00+07:00|2026-10-22T21:00:00+07:00|Kamis, 22 Okt 2026 jam 20.00 WIB>>>\n"
                    "       User: \"deadline tugas metopen ganti jadi jumat 23.59\"\n"
                    "       Baris terakhir: <<<ACTION:RESCHEDULE|okta|metopen|2026-10-23T23:59:00+07:00|2026-10-23T23:59:00+07:00|Jumat, 23 Okt 2026 jam 23.59 WIB>>>\n"
                )
                node["parameters"]["jsonBody"] = json_body.replace(target_marker, replacement, 1)

        elif node["name"] == "Process AI Output & Actions":
            # Update jsCode in Process AI Output & Actions
            code = node["parameters"].get("jsCode", "")
            if "reschedule" not in code.lower():
                # Update actionRegex
                code = re.sub(
                    r"const actionRegex = /<<<ACTION:\(.*?\)\(?:\\\|\(.*?\)\)\?>>>/gi;",
                    "const actionRegex = /<<<ACTION:(TUGAS|JADWAL|DONE|DELETE|EDIT|RESCHEDULE|NOTE_ADD|NOTE_EDIT|NOTE_DONE|PRESENSI|EXPENSE_ADD)(?:\\|(.*?))?>>>/gi;",
                    code
                )
                if "ACTION:(TUGAS|JADWAL|DONE|DELETE|EDIT|RESCHEDULE" not in code:
                    code = code.replace(
                        "ACTION:(TUGAS|JADWAL|DONE|DELETE|EDIT|",
                        "ACTION:(TUGAS|JADWAL|DONE|DELETE|EDIT|RESCHEDULE|"
                    )

                # Add reschedule branch
                resched_branch = (
                    "  } else if (actionType === 'reschedule') {\n"
                    "    const target = (parts[0] || 'okta').toLowerCase();\n"
                    "    const query = parts[1] || '';\n"
                    "    const startIso = parts[2] || '';\n"
                    "    const endIso = parts[3] || '';\n"
                    "    const timeText = parts[4] || '';\n"
                    "    const newTitle = parts[5] || '';\n"
                    "    const commandText = target === 'manda'\n"
                    "      ? `/reschedule manda ${query} | ${startIso} | ${endIso} | ${timeText} | ${newTitle}`.trim()\n"
                    "      : `/reschedule ${query} | ${startIso} | ${endIso} | ${timeText} | ${newTitle}`.trim();\n"
                    "    actions.push({\n"
                    "      actionType: 'reschedule',\n"
                    "      target,\n"
                    "      query,\n"
                    "      startIso,\n"
                    "      endIso,\n"
                    "      timeText,\n"
                    "      newTitle,\n"
                    "      detail: `${query} -> ${timeText || startIso}`,\n"
                    "      commandText\n"
                    "    });\n"
                )
                code = code.replace(
                    "  } else if (actionType === 'edit') {",
                    resched_branch + "  } else if (actionType === 'edit') {"
                )

                # Update hasCalendarActions
                code = code.replace(
                    "['tugas', 'jadwal', 'done', 'delete', 'edit'].includes(a.actionType)",
                    "['tugas', 'jadwal', 'done', 'delete', 'edit', 'reschedule'].includes(a.actionType)"
                )

                node["parameters"]["jsCode"] = code


# ==============================================================================
# 5. UPDATE README.MD
# ==============================================================================
def update_readme():
    content = README_PATH.read_text(encoding="utf-8")
    if "`/reschedule`" not in content:
        old_table_row = "| `/edit-jadwal` | All | Ralat / ubah nama agenda atau tugas yang sudah ada in-place |"
        new_table_row = (
            "| `/edit-jadwal` | All | Ralat / ubah nama agenda atau tugas yang sudah ada in-place |\n"
            "| `/reschedule` | All | Jadwalkan ulang tanggal & jam agenda atau deadline tugas tanpa duplikasi |"
        )
        content = content.replace(old_table_row, new_table_row)
        README_PATH.write_text(content, encoding="utf-8")
        print("✅ Updated README.md")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def main():
    print("🚀 Applying Reschedule feature across all workflows...")

    # 1. wa-to-gcal-assistant
    update_json_file(OKTA_GCAL_PATH, OKTA_GCAL_PATH, lambda wf: upgrade_gcal_workflow(wf, is_manda=False))
    update_json_file(OKTA_GCAL_PATH, OKTA_GCAL_N8N, lambda wf: upgrade_gcal_workflow(wf, is_manda=False))

    # 2. manda-gcal-assistant
    update_json_file(MANDA_GCAL_PATH, MANDA_GCAL_PATH, lambda wf: upgrade_gcal_workflow(wf, is_manda=True))
    update_json_file(MANDA_GCAL_PATH, MANDA_GCAL_N8N, lambda wf: upgrade_gcal_workflow(wf, is_manda=True))

    # 3. master-router-webhook
    update_json_file(ROUTER_PATH, ROUTER_PATH, upgrade_master_router)
    update_json_file(ROUTER_PATH, ROUTER_N8N, upgrade_master_router)

    # 4. wa-conversation
    update_json_file(WA_CONV_PATH, WA_CONV_PATH, upgrade_wa_conversation)
    update_json_file(WA_CONV_PATH, WA_CONV_N8N, upgrade_wa_conversation)

    # 5. README.md
    update_readme()

    print("🎉 All files updated successfully!")


if __name__ == "__main__":
    main()
