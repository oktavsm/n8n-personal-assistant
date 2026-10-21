#!/usr/bin/env python3
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
# 1. GENERATE SAFE CALENDAR ACTION CODE (OKTA & MANDA)
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
const numMatch = textLower.match(/^(?:hapus\\s+|selesai\\s+|edit\\s+|pilih\\s+|#)?(\\d+)$/i);

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
// 3. HANDLE /edit-jadwal, /edit-agenda, /edit-tugas, /hapus, /done
// -------------------------------------------------------------
const isEdit = textLower.startsWith('/edit-jadwal') || textLower.startsWith('/edit-agenda') || textLower.startsWith('/edit-tugas') || textLower.startsWith('/edit ');
const isDelete = textLower.startsWith('/hapus');
const isDone = textLower.startsWith('/done') || textLower.startsWith('/selesai');

let rawQuery = '';
let editOldQuery = '';
let editNewTitle = '';

if (isEdit) {{
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
    actionType: isEdit ? 'edit' : isDelete ? 'hapus' : 'selesai',
    newSummary: editNewTitle || ''
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
    actionType: isEdit ? 'edit' : isDelete ? 'hapus' : 'selesai',
    newSummary: editNewTitle || ''
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
      message: `⚠️ *Jadwal kuliah dilindungi dan tidak dapat diubah namanya sembarangan.*\\n\\nMatakuliah: *${{matchedKuliahName}}*\\n\\nUntuk mengubah ruang kelas atau menandai libur, gunakan perintah:\\n👉 */edit-kuliah [matkul] [ruang / LIBUR]*\\n_Contoh:_ \\`/edit-kuliah ${{cleanQueryStr || rawQuery}} F3.11\\``,
      pgQuery: 'SELECT 1;'
    }}
  }}];
}}

// Case 2: Exactly 1 match -> Execute immediately!
if (candidates.length === 1) {{
  const single = candidates[0];
  const deletePg = `DELETE FROM user_pending_actions WHERE user_name = '${{userName}}' AND room_jid = '${{targetNumber}}';`;
  
  if (isEdit) {{
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
  const actionLabel = isEdit ? 'edit judul' : isDelete ? 'hapus' : 'selesai';

  const promptMsg = isEdit
    ? `🔍 Ditemukan *${{candidates.length}}* item yang cocok dengan *\"${{rawQuery}}\"*:\\n\\n${{numberedList}}\\n\\nKetik nomor untuk mengubah judulnya menjadi *\"${{editNewTitle}}\"*, atau ketik *batal*.`
    : `🔍 Ditemukan *${{candidates.length}}* item yang cocok dengan *\"${{rawQuery}}\"*:\\n\\n${{numberedList}}\\n\\nKetik nomor (contoh: *1*, *2*) untuk konfirmasi *${{actionLabel}}*, atau ketik *batal*.`;

  if (isEdit) {{
    candidates.forEach(c => {{ c.newSummary = editNewTitle; c.actionType = 'edit'; }});
  }}

  const candJsonStr = JSON.stringify(candidates).replace(/'/g, "''");
  const escapedQuery = (isEdit ? `${{rawQuery}} | ${{editNewTitle}}` : rawQuery).replace(/'/g, "''");

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
  const actionLabel = isEdit ? 'edit judul' : isDelete ? 'hapus' : 'selesai';
  const numberedList = fallbackList.map((c, i) => `${{i + 1}}️⃣ *[${{c.calendarType}}]* ${{c.summary}} _(${{c.timeText}})_`).join('\\n');

  const promptMsg = isEdit
    ? `⚠️ Agenda atau tugas *\"${{rawQuery}}\"* tidak ditemukan secara spesifik.\\n\\nBerikut daftar agenda & tugas aktif kamu saat ini:\\n\\n${{numberedList}}\\n\\nKetik nomor (1 - ${{fallbackList.length}}) untuk mengubah judulnya menjadi *\"${{editNewTitle}}\"*, atau ketik *batal*.`
    : `⚠️ Agenda atau tugas *\"${{rawQuery}}\"* tidak ditemukan secara spesifik.\\n\\nBerikut daftar agenda & tugas aktif kamu saat ini:\\n\\n${{numberedList}}\\n\\nKetik nomor (1 - ${{fallbackList.length}}) untuk konfirmasi *${{actionLabel}}*, atau ketik *batal*.`;

  if (isEdit) {{
    fallbackList.forEach(c => {{ c.newSummary = editNewTitle; c.actionType = 'edit'; }});
  }}

  const candJsonStr = JSON.stringify(fallbackList).replace(/'/g, "''");
  const escapedQuery = (isEdit ? `${{rawQuery}} | ${{editNewTitle}}` : rawQuery).replace(/'/g, "''");

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

# Update Okta Calendar Assistant
def update_okta_cal(wf):
    for node in wf["nodes"]:
        if node["name"] == "Process Safe Calendar Action":
            node["parameters"]["jsCode"] = get_safe_action_code(is_manda=False)
            print("  Updated 'Process Safe Calendar Action' in Okta GCal")

update_json_file(OKTA_GCAL_PATH, OKTA_GCAL_PATH, update_okta_cal)
update_json_file(OKTA_GCAL_PATH, OKTA_GCAL_N8N, update_okta_cal)

# Update Manda Calendar Assistant
def update_manda_cal(wf):
    for node in wf["nodes"]:
        if node["name"] in ["Manda Process Safe Calendar Action", "Process Safe Calendar Action"]:
            node["parameters"]["jsCode"] = get_safe_action_code(is_manda=True)
            print("  Updated 'Manda Process Safe Calendar Action' in Manda GCal")

update_json_file(MANDA_GCAL_PATH, MANDA_GCAL_PATH, update_manda_cal)
update_json_file(MANDA_GCAL_PATH, MANDA_GCAL_N8N, update_manda_cal)

# ==============================================================================
# 2. UPDATE wa-conversation.json (NOTES CRUD & EDIT CALENDAR ACTION)
# ==============================================================================
PROCESS_ACTIONS_JS = """const geminiRaw = $input.first().json;
let rawText = "";
try {
  rawText = geminiRaw.candidates[0].content.parts[0].text || "";
} catch (e) {}

// Regex for action tags:
// <<<ACTION:TUGAS|TARGET|DETAIL>>>
// <<<ACTION:JADWAL|TARGET|DETAIL>>>
// <<<ACTION:DONE|TARGET|JUDUL>>>
// <<<ACTION:DELETE|TARGET|JUDUL>>>
// <<<ACTION:EDIT|TARGET|JUDUL_LAMA|JUDUL_BARU>>>
// <<<ACTION:NOTE_ADD|TARGET|DETAIL>>>
// <<<ACTION:NOTE_EDIT|ID|KONTEN_BARU>>>
// <<<ACTION:NOTE_DONE|ID>>>
// <<<ACTION:PRESENSI|hadir>>>
// <<<ACTION:EXPENSE_ADD|TARGET|AMOUNT|CATEGORY|MERCHANT|ITEMS>>>
const actionRegex = /<<<ACTION:(TUGAS|JADWAL|DONE|DELETE|EDIT|NOTE_ADD|NOTE_EDIT|NOTE_DONE|PRESENSI|EXPENSE_ADD)(?:\\|(.*?))?>>>/gi;
const actions = [];
let match;

while ((match = actionRegex.exec(rawText)) !== null) {
  const actionType = match[1].toLowerCase();
  const rawParams = match[2] || '';
  const parts = rawParams.split('|').map(s => s.trim());

  if (actionType === 'expense_add') {
    const target = (parts[0] || 'okta').toLowerCase();
    const amount = parseFloat(parts[1]) || 0;
    const category = parts[2] || 'makan';
    const merchant = parts[3] || 'Umum';
    const itemsDetail = parts.slice(4).join(', ') || '-';
    actions.push({
      actionType: 'expense_add',
      target,
      amount,
      category,
      merchant,
      itemsDetail,
      detail: `${merchant} - Rp ${amount}`
    });
  } else if (actionType === 'note_edit') {
    const id = parseInt(parts[0]) || 0;
    const newContent = parts.slice(1).join('|').trim();
    actions.push({
      actionType: 'note_edit',
      id,
      newContent,
      detail: `${id}|${newContent}`,
      commandText: `/catat edit ${id} ${newContent}`
    });
  } else if (actionType === 'edit') {
    const target = (parts[0] || 'okta').toLowerCase();
    const oldTitle = parts[1] || '';
    const newTitle = parts.slice(2).join('|').trim();
    const commandText = target === 'manda'
      ? `/edit-jadwal manda ${oldTitle} | ${newTitle}`
      : `/edit-jadwal ${oldTitle} | ${newTitle}`;
    actions.push({
      actionType: 'edit',
      target,
      oldTitle,
      newTitle,
      detail: `${oldTitle} | ${newTitle}`,
      commandText
    });
  } else {
    const target = (parts[0] || 'okta').toLowerCase();
    const detail = parts.slice(1).join('|') || parts[0] || '';
    
    let commandText = '';
    if (actionType === 'tugas') {
      commandText = target === 'manda' ? `/tugas manda ${detail}` : `/tugas ${detail}` context;
    } else if (actionType === 'jadwal') {
      commandText = target === 'manda' ? `/jadwal manda ${detail}` : `/jadwal ${detail}`;
    } else if (actionType === 'done') {
      commandText = target === 'manda' ? `/done manda ${detail}` : `/done ${detail}`;
    } else if (actionType === 'delete') {
      commandText = target === 'manda' ? `/hapus-jadwal manda ${detail}` : `/hapus-jadwal ${detail}`;
    } else if (actionType === 'note_add') {
      commandText = `/catat ${detail}`;
    } else if (actionType === 'note_done') {
      commandText = `/catat done ${detail || target}`;
    } else if (actionType === 'presensi') {
      commandText = `/presensi ${detail || 'hadir'}`;
    }

    actions.push({
      actionType,
      target,
      detail: detail || target,
      commandText
    });
  }
}

// Clean user response by removing action tags
const cleanText = rawText.replace(/<<<ACTION:[A-Z_]+(?:\\|.*?)?>>>/gi, '').trim();

let waData = {};
try {
  waData = $('Normalize WA Context').item.json.wa || {};
} catch (e) {}

const hasCalendarActions = actions.some(a => ['tugas', 'jadwal', 'done', 'delete', 'edit'].includes(a.actionType));
const hasNoteActions = actions.some(a => ['note_add', 'note_done', 'note_edit'].includes(a.actionType));
const hasPresensiActions = actions.some(a => a.actionType === 'presensi');
const hasExpenseActions = actions.some(a => a.actionType === 'expense_add');

return [{
  json: {
    cleanText,
    hasActions: actions.length > 0,
    hasCalendarActions,
    hasNoteActions,
    hasPresensiActions,
    hasExpenseActions,
    actions,
    wa: waData,
    candidates: [
      {
        content: {
          parts: [
            { text: cleanText }
          ]
        }
      }
    ]
  }
}];"""

EXECUTE_NOTE_ACTION_JS = """const actions = $json.actions || [];
const noteActions = actions.filter(a => ['note_add', 'note_done', 'note_edit'].includes(a.actionType));
if (noteActions.length === 0) return "SELECT 1;";

const wa = $json.wa || {};
const queries = [];

for (const act of noteActions) {
  if (act.actionType === 'note_add') {
    const owner = act.target === 'manda' ? 'manda' : 'okta';
    const content = (act.detail || '').replace(/'/g, "''");
    const creatorJid = (wa.participant || wa.remoteJid || '').replace(/'/g, "''");
    const creatorName = (wa.pushName || 'User').replace(/'/g, "''");
    queries.push(`INSERT INTO user_notes (owner_user, creator_jid, creator_name, content, category, created_at, updated_at) VALUES ('${owner}', '${creatorJid}', '${creatorName}', '${content}', 'general', NOW(), NOW());`);
  } else if (act.actionType === 'note_edit') {
    const id = parseInt(act.id) || 0;
    const newContent = (act.newContent || act.detail || '').replace(/'/g, "''");
    if (id > 0 && newContent) {
      queries.push(`UPDATE user_notes SET content = '${newContent}', updated_at = NOW() WHERE id = ${id};`);
    }
  } else if (act.actionType === 'note_done') {
    const id = parseInt(act.detail) || 0;
    if (id > 0) {
      queries.push(`UPDATE user_notes SET is_done = TRUE, updated_at = NOW() WHERE id = ${id};`);
    }
  }
}

return queries.length > 0 ? queries.join('\\n') : "SELECT 1;";"""

FORMAT_NOTES_VISION_JS = """const rows = $input.all().map(i => i.json).filter(r => r && r.id);
const oktaNotes = rows.filter(r => r.owner_user === 'okta');
const mandaNotes = rows.filter(r => r.owner_user === 'manda');

function formatNoteTimestamp(createdStr, updatedStr, tz = 'Asia/Jakarta') {
  if (!createdStr) return '';
  const c = new Date(createdStr);
  const u = updatedStr ? new Date(updatedStr) : c;
  const isEdited = Math.abs(u.getTime() - c.getTime()) > 5000;
  const targetDate = isEdited ? u : c;

  const dateFormatted = targetDate.toLocaleDateString('id-ID', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    timeZone: tz
  });
  const timeFormatted = targetDate.toLocaleTimeString('id-ID', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: tz
  }).replace(':', '.');

  const tzLabel = tz.includes('Makassar') ? 'WITA' : 'WIB';
  return isEdited
    ? `${dateFormatted}, ${timeFormatted} ${tzLabel} (diedit)`
    : `${dateFormatted}, ${timeFormatted} ${tzLabel}`;
}

let txt = "📝 DATA CATATAN AKTIF PENGGUNA (REAL-TIME DATABASE):\\n";
txt += "\\n• Catatan Aktif Okta:\\n";
if (oktaNotes.length === 0) {
  txt += "  (Tidak ada catatan aktif)\\n";
} else {
  oktaNotes.forEach((n, idx) => {
    const ts = formatNoteTimestamp(n.created_at, n.updated_at, 'Asia/Jakarta');
    txt += `  ${idx + 1}. [ID: ${n.id}] ${n.content} — ${ts}\\n`;
  });
}

txt += "\\n• Catatan Aktif Kak Manda:\\n";
if (mandaNotes.length === 0) {
  txt += "  (Tidak ada catatan aktif)\\n";
} else {
  mandaNotes.forEach((n, idx) => {
    const ts = formatNoteTimestamp(n.created_at, n.updated_at, 'Asia/Makassar');
    txt += `  ${idx + 1}. [ID: ${n.id}] ${n.content} — ${ts}\\n`;
  });
}

let prev = {};
try {
  prev = $('Format Memory Context').item.json;
} catch (e) {}

return [{
  json: {
    ...prev,
    visionContext: txt
  }
}];"""

PREP_CAL_PAYLOADS_JS = """const parent = $input.first().json;
const wa = parent.wa || {};
const actions = parent.actions || [];

const calActions = actions.filter(a => ['tugas', 'jadwal', 'done', 'delete', 'edit'].includes(a.actionType));
if (!calActions || calActions.length === 0) {
  return [];
}

const items = [];
const defaultOktaNumber = $env.MY_WA_NUMBER || "";
const defaultMandaNumber = $env.MANDA_WA_NUMBER || "";

for (const act of calActions) {
  const isMandaTarget = act.target === 'manda';
  const senderNumber = isMandaTarget ? defaultMandaNumber : defaultOktaNumber;
  const remoteJid = wa.remoteJid || `${senderNumber}@s.whatsapp.net`;

  items.push({
    json: {
      target: act.target,
      actionType: act.actionType,
      detail: act.detail,
      commandText: act.commandText,
      body: {
        data: {
          key: {
            remoteJid: remoteJid,
            participant: `${senderNumber}@s.whatsapp.net`,
            participantAlt: `${senderNumber}@s.whatsapp.net`
          },
          message: {
            conversation: act.commandText
          }
        }
      }
    }
  });
}

return items;"""

def update_wa_conv(wf):
    for node in wf["nodes"]:
        # 1. Update [PG] Fetch Active Notes to select updated_at
        if node["name"] == "[PG] Fetch Active Notes":
            node["parameters"]["query"] = "SELECT id, owner_user, content, category, created_at, updated_at FROM user_notes WHERE is_done = FALSE ORDER BY id ASC;"
            print("  Updated '[PG] Fetch Active Notes' query")

        # 2. Update Format Notes Vision
        if node["name"] == "Format Notes Vision":
            node["parameters"]["jsCode"] = FORMAT_NOTES_VISION_JS
            print("  Updated 'Format Notes Vision' jsCode")

        # 3. Update Process AI Output & Actions (both Okta and Manda)
        if node["name"] in ["Process AI Output & Actions", "Process AI Output & Actions1"]:
            # Fix minor syntax in template
            code = PROCESS_ACTIONS_JS.replace("commandText = target === 'manda' ? `/tugas manda ${detail}` : `/tugas ${detail}` context;", "commandText = target === 'manda' ? `/tugas manda ${detail}` : `/tugas ${detail}`;")
            node["parameters"]["jsCode"] = code
            print(f"  Updated '{node['name']}' jsCode")

        # 4. Update Prepare Calendar Payloads
        if node["name"] == "Prepare Calendar Payloads":
            node["parameters"]["jsCode"] = PREP_CAL_PAYLOADS_JS
            print("  Updated 'Prepare Calendar Payloads' jsCode")

        # 5. Update [PG] Execute Note Action
        if node["name"] == "[PG] Execute Note Action":
            node["parameters"]["query"] = "={{ (() => {\n" + EXECUTE_NOTE_ACTION_JS + "\n})() }}"
            print("  Updated '[PG] Execute Note Action' query")

        # 6. Update Gemini Build Message prompts
        if node["name"] in ["[HTTP] Gemini Build Message", "[HTTP] Gemini Build Message1"]:
            body = node["parameters"].get("jsonBody", "")
            
            # Upgrade Section 2: Lifecycle & Edit
            new_sec_2 = """2. LIFECYCLE TUGAS/AGENDA KALENDER (SELESAI / HAPUS / EDIT) & PERLINDUNGAN KULIAH:
   <<<ACTION:DONE|TARGET|JUDUL>>>                      -> tandai tugas/jadwal sebagai [SELESAI] di kalender.
   <<<ACTION:DELETE|TARGET|JUDUL>>>                    -> hapus tugas/jadwal dari kalender.
   <<<ACTION:EDIT|TARGET|JUDUL_LAMA|JUDUL_BARU>>>      -> ralat/ubah nama agenda atau tugas yang sudah ada.
   TARGET: "okta" atau "manda"
   
   ⚠️ ATURAN KETAT EDIT & LIFECYCLE KALENDER:
   a. JIKA PENGGUNA INGIN MERALAT / MENGUBAH / MEMPERBAIKI NAMA AGENDA ATAU TUGAS:
      - DILARANG KERAS MENGELUARKAN <<<ACTION:JADWAL>>> ATAU <<<ACTION:TUGAS>>> karena itu akan MEMBUAT JADWAL BARU (DUPLIKAT)!
      - WAJIB mengeluarkan tag <<<ACTION:EDIT|TARGET|JUDUL_LAMA|JUDUL_BARU>>>.
      - Contoh:
        User: "meet lead other itu meet Tanoto bukan ICN" -> JUDUL_LAMA: "ICN", JUDUL_BARU: "[Meeting] Tanoto Scholars Association (TSA) - Meet Lead Other"
        User: "meet tanoto bisa edit jadi meet lead other gak tapi tetep meet tsa" -> JUDUL_LAMA: "meet tanoto", JUDUL_BARU: "[Meeting] Tanoto Scholars Association (TSA) - Meeting Lead Other"
        User: "ubah judul tugas ppt scope jadi ppt final" -> JUDUL_LAMA: "ppt scope", JUDUL_BARU: "[Tugas] PPT Final"
   b. JANGAN PERNAH MENYIMPULKAN / MENGKLAIM SUDAH SELESAI ATAU SUDAH TERHAPUS DI TEKS RESPON!
      - CUKUP balas singkat netral: "Oke bro, aku bantu proses di kalender ya..." atau serahkan ke sistem backend untuk mengirim laporan statusnya.
   c. JADWAL KULIAH TIDAK DAPAT DIHAPUS ATAU DIUBAH SEMBARANGAN!
      - Kalender kuliah dilindungi penuh. Jika user meminta hapus/edit jadwal kuliah, jelaskan bahwa ruang kelas atau status libur bisa diubah via /edit-kuliah [matkul] [ruang / LIBUR]. DILARANG mengeluarkan <<<ACTION:DELETE>>> untuk kuliah!"""

            # Upgrade Section 3: Notes CRUD with timestamps
            new_sec_3 = """3. PENCATATAN & TO-DO (NOTES SYSTEM):
   <<<ACTION:NOTE_ADD|TARGET|DETAIL>>>    -> catat memo/to-do baru tanpa jam terikat.
   <<<ACTION:NOTE_EDIT|ID|KONTEN_BARU>>>  -> perbarui/edit isi catatan yang sudah ada berdasarkan ID catatan.
   <<<ACTION:NOTE_DONE|ID>>>              -> tandai catatan selesai berdasarkan ID catatan.
   TARGET: "okta" atau "manda"

   ⚠️ ATURAN TAMPILAN & PENGELOLAAN NOTES:
   a. FORMAT MENAMPILKAN CATATAN:
      Saat pengguna meminta melihat catatan ("/notes", "/catatan", "catatan aktif", dsb):
      Tampilkan daftar catatan aktif dengan rapi menyertakan nomor, ID, isi, dan timestamp (tanggal & jam dibuat / diedit):
      Contoh format:
      📝 *CATATAN AKTIF KAMU:*
      1. *[ID: 4]* mandi nanti malam _(Sen, 20 Okt, 16.55 WIB)_
      2. *[ID: 6]* Perbaikan notes pakek timestamp _(Sel, 21 Okt, 10.17 WIB)_
      3. *[ID: 7]* tambahin fitur edit notes... _(Sel, 21 Okt, 10.22 WIB - diedit)_
   b. EDIT / UPDATE CATATAN:
      Jika user meminta mengedit catatan (contoh: "edit catatan 4 jadi mandi jam 8", "ubah catatan mandi jadi mandi jam 8", "/catat edit 4 mandi jam 8"):
      - Cari ID catatan dari konteks/vision.
      - Keluarkan tag: <<<ACTION:NOTE_EDIT|4|mandi jam 8>>>.
      - Berikan konfirmasi bahwa catatan berhasil diperbarui dan waktu terakhir diedit otomatis diperbarui."""

            # Substitute in body safely
            old_pattern_2 = r"2\.\s+LIFECYCLE TUGAS/AGENDA KALENDER.*?3\.\s+PENCATATAN & TO-DO"
            repl_2 = new_sec_2.strip() + "\n\n3. PENCATATAN & TO-DO"
            body = re.sub(old_pattern_2, repl_2, body, flags=re.DOTALL)

            old_pattern_3 = r"3\.\s+PENCATATAN & TO-DO \(NOTES SYSTEM\):.*?4\.\s+PENCATATAN PENGELUARAN"
            repl_3 = new_sec_3.strip() + "\n\n4. PENCATATAN PENGELUARAN"
            body = re.sub(old_pattern_3, repl_3, body, flags=re.DOTALL)

            node["parameters"]["jsonBody"] = body
            print(f"  Updated prompts in '{node['name']}'")

update_json_file(WA_CONV_PATH, WA_CONV_PATH, update_wa_conv)
update_json_file(WA_CONV_PATH, WA_CONV_N8N, update_wa_conv)

# ==============================================================================
# 3. UPDATE master-router-webhook.json (LIFECYCLE ROUTING & HELP MENU)
# ==============================================================================
def update_router(wf):
    for node in wf["nodes"]:
        if node["name"] == "Switch":
            rules = node["parameters"].get("rules", {}).get("values", [])
            for r in rules:
                if r.get("outputKey") == "lifecycle":
                    cond = r["conditions"]["conditions"][0]
                    cond["leftValue"] = """={{ (() => {
  const data = $json.body?.data || {};
  const msg = data.message || {};
  const raw = (msg.conversation || msg.extendedTextMessage?.text || "").trim();
  const cleaned = raw.replace(/@[a-zA-Z0-9_\\-\\.]+\\s*/g, "").trim().toLowerCase();

  const isLifecycleCmd = cleaned.startsWith('/done') ||
                         cleaned.startsWith('/selesai') ||
                         cleaned.startsWith('/hapus') ||
                         cleaned.startsWith('/edit-jadwal') ||
                         cleaned.startsWith('/edit-agenda') ||
                         cleaned.startsWith('/edit-tugas') ||
                         cleaned.startsWith('/edit-kuliah') ||
                         cleaned.startsWith('/edit kuliah');

  const isSelectionReply = /^(?:hapus\\s+|selesai\\s+|edit\\s+|pilih\\s+|#)?\\d+$/i.test(cleaned) ||
                           ['batal', 'cancel', '/batal', '/cancel'].includes(cleaned);

  return Boolean(isLifecycleCmd || isSelectionReply);
})() }}"""
                    print("  Updated 'Switch' lifecycle rule in master router")

        # Update Help Manual
        if node["name"] == "Code: Help Manual":
            js = node["parameters"].get("jsCode", "")
            # Add /edit-jadwal and /catat edit
            if "/edit-jadwal" not in js:
                js = js.replace(
                    "\\u2022 */hapus [judul]* atau */hapus-jadwal [judul]*\\n  Hapus agenda/tugas dari kalender (dilengkapi konfirmasi cerdas jika ada judul mirip/ganda).\\n",
                    "\\u2022 */edit-jadwal [lama] | [baru]* atau */edit-agenda*\\n  Ubah judul agenda/tugas tanpa membuat duplikat (contoh: `/edit-jadwal meet tanoto | Meet Lead Other`).\\n\\u2022 */hapus [judul]* atau */hapus-jadwal [judul]*\\n  Hapus agenda/tugas dari kalender (dilengkapi konfirmasi cerdas jika ada judul mirip/ganda).\\n"
                )
                js = js.replace(
                    "\\u2022 */catat done [id]*\\n  Tandai catatan selesai (contoh: `/catat done 1`).\\n",
                    "\\u2022 */catat edit [id] [isi baru]*\\n  Perbarui isi catatan (timestamp otomatis tercatat sebagai waktu terakhir diedit).\\n\\u2022 */catat done [id]*\\n  Tandai catatan selesai (contoh: `/catat done 1`).\\n"
                )
                node["parameters"]["jsCode"] = js
                print("  Updated 'Code: Help Manual' with new commands")

update_json_file(ROUTER_PATH, ROUTER_PATH, update_router)
update_json_file(ROUTER_PATH, ROUTER_N8N, update_router)

print("🎉 ALL IMPROVEMENTS APPLIED SUCCESSFULLY!")
