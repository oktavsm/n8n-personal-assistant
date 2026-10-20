import json
import uuid
from pathlib import Path

def uid():
    return str(uuid.uuid4())

# ----------------------------------------------------
# 1. UPDATE MASTER ROUTER WEBHOOK
# ----------------------------------------------------
router_path = Path("workflow/master-router-webhook.json")
with open(router_path) as f:
    raw_router = json.load(f)
router = raw_router[0] if isinstance(raw_router, list) else raw_router

# Update 'mentioned' node to handle:
# - Tag/mention @bot
# - Quoted / swipe-reply bot's message
# - Voice note in groups replying to bot
# - Messages in WA_GROUP_DEV
for n in router["nodes"]:
    if n["name"] == "mentioned":
        n["parameters"]["conditions"]["conditions"][0]["leftValue"] = """={{ (() => {
  const body = $json.body || {};
  const data = body.data || {};
  const msg = data.message || {};
  const remoteJid = data.key?.remoteJid || '';
  const isGroup = remoteJid.endsWith('@g.us');

  const text = (
    msg.conversation ||
    msg.extendedTextMessage?.text ||
    msg.imageMessage?.caption ||
    msg.videoMessage?.caption ||
    msg.documentMessage?.caption ||
    ''
  ).toLowerCase().trim();

  // If explicit command handled by switch, let switch handle it
  if (text.startsWith('/ask') || text.startsWith('/vps') || text.startsWith('/agent')) return false;

  const ctx = data.contextInfo ||
    msg.extendedTextMessage?.contextInfo ||
    msg.imageMessage?.contextInfo ||
    msg.videoMessage?.contextInfo ||
    msg.documentMessage?.contextInfo ||
    msg.audioMessage?.contextInfo ||
    {};

  const botLids = ['195095164887244', '171619058196619', '158613192614132', '6283130151476', '628XXXXXXXXXX'];

  // 1. Tag / Mention check
  const jids = ctx.mentionedJid || [];
  const isMentioned = jids.some(j => botLids.some(b => j.includes(b))) ||
    botLids.some(b => text.includes('@' + b));

  // 2. Quoted / Swipe-reply check (user replied to the bot's message)
  const quotedParticipant = ctx.participant || ctx.quotedMessageSender || '';
  const isReplyingToBot = botLids.some(b => quotedParticipant.includes(b));

  // 3. Dev Group check
  const isDevGroup = remoteJid === ($env.WA_GROUP_DEV || '120363336434287340@g.us');

  // 4. Audio check
  const hasAudio = Boolean(msg.audioMessage || ctx.quotedMessage?.audioMessage);

  if (isGroup) {
    return Boolean(isMentioned || isReplyingToBot || (isDevGroup && (hasAudio || text.startsWith('/bot') || text.startsWith('@bot'))));
  }

  return false;
})() }}"""
        print("Updated 'mentioned' node in master-router-webhook!")

with open(router_path, "w") as f:
    json.dump([router], f, indent=2)
with open("n8n/workflow/master-router-webhook.json", "w") as f:
    json.dump([router], f, indent=2)

# ----------------------------------------------------
# 2. UPDATE WA-CONVERSATION
# ----------------------------------------------------
wac_path = Path("workflow/wa-conversation.json")
with open(wac_path) as f:
    raw_wac = json.load(f)
wac = raw_wac[0] if isinstance(raw_wac, list) else raw_wac

nodes_by_name = {n["name"]: n for n in wac["nodes"]}

# 1. Update Normalize WA Context code
norm_code = """const root = $input.first().json;
const body = root.body || {};
const data = body.data || {};
const msg = data.message || {};
const ctx =
  data.contextInfo ||
  msg.extendedTextMessage?.contextInfo ||
  msg.imageMessage?.contextInfo ||
  msg.videoMessage?.contextInfo ||
  msg.documentMessage?.contextInfo ||
  msg.audioMessage?.contextInfo ||
  {};

const quoted = ctx.quotedMessage || {};

function getTextFromMessage(m = {}) {
  return (
    m.conversation ||
    m.extendedTextMessage?.text ||
    m.imageMessage?.caption ||
    m.videoMessage?.caption ||
    m.documentMessage?.caption ||
    ""
  );
}

function detectMedia(m = {}) {
  if (m.imageMessage) {
    return {
      exists: true,
      source: null,
      type: "image",
      kind: "imageMessage",
      mimetype: m.imageMessage.mimetype || "image/jpeg",
      caption: m.imageMessage.caption || "",
      message: m.imageMessage,
    };
  }

  if (m.videoMessage) {
    const isGif = !!m.videoMessage.gifPlayback;
    return {
      exists: true,
      source: null,
      type: isGif ? "gif" : "video",
      kind: "videoMessage",
      mimetype: m.videoMessage.mimetype || "video/mp4",
      caption: m.videoMessage.caption || "",
      message: m.videoMessage,
    };
  }

  if (m.audioMessage) {
    return {
      exists: true,
      source: null,
      type: "audio",
      kind: "audioMessage",
      mimetype: m.audioMessage.mimetype || "audio/ogg",
      caption: "",
      message: m.audioMessage,
    };
  }

  if (m.documentMessage) {
    return {
      exists: true,
      source: null,
      type: "document",
      kind: "documentMessage",
      mimetype: m.documentMessage.mimetype || "application/octet-stream",
      caption: m.documentMessage.caption || "",
      fileName: m.documentMessage.fileName || "",
      message: m.documentMessage,
    };
  }

  if (m.stickerMessage) {
    return {
      exists: true,
      source: null,
      type: "sticker",
      kind: "stickerMessage",
      mimetype: m.stickerMessage.mimetype || "image/webp",
      caption: "",
      message: m.stickerMessage,
    };
  }

  return {
    exists: false,
    source: null,
    type: null,
    kind: null,
    mimetype: null,
    caption: "",
    message: null,
  };
}

const currentText = getTextFromMessage(msg).trim();
const quotedText = getTextFromMessage(quoted).trim();

const currentMedia = detectMedia(msg);
currentMedia.source = "current";

const quotedMedia = detectMedia(quoted);
quotedMedia.source = "quoted";

const selectedMedia = currentMedia.exists ? currentMedia : quotedMedia.exists ? quotedMedia : null;

const textLower = currentText.toLowerCase();

const mentionedJid = ctx.mentionedJid || [];
const botLids = ["171619058196619", "195095164887244", "158613192614132", "6283130151476", "628XXXXXXXXXX"];
const isMentionBot =
  botLids.some(b => currentText.includes("@" + b)) ||
  mentionedJid.some(j => botLids.some(b => j.includes(b)));

const quotedParticipant = ctx.participant || ctx.quotedMessageSender || "";
const isReplyingToBot = botLids.some(b => quotedParticipant.includes(b));

const isAskCommand = textLower.startsWith("/ask");
const isStickerCommand = textLower.startsWith("/stiker") || textLower.startsWith("/sticker");

const cleanText = currentText
  .replace(/@171619058196619/g, "")
  .replace(/@195095164887244/g, "")
  .replace(/@158613192614132/g, "")
  .replace(/@6283130151476/g, "")
  .replace(/^\\/ask/i, "")
  .replace(/^\\/stiker/i, "")
  .replace(/^\\/sticker/i, "")
  .trim();

const remoteJid = data.key?.remoteJid || "";
const participant = data.key?.participant || data.key?.participantAlt || remoteJid;
const isGroup = remoteJid.endsWith("@g.us");
const isDevGroup = remoteJid === ($env.WA_GROUP_DEV || "120363336434287340@g.us");

const isManda = remoteJid.includes($env.MANDA_WA_NUMBER) || participant.includes($env.MANDA_WA_NUMBER);
const isOkta = remoteJid.includes($env.MY_WA_NUMBER) || participant.includes($env.MY_WA_NUMBER);

// Deteksi Titip Pesan Dua Arah
const isTitipPesanToOkta = !isOkta && /titip|bilang|kasih tau|suruh|ingetin okta|sampaikan ke okta|pesan buat okta/i.test(currentText);
const isTitipPesanToManda = isOkta && /titip|bilang|kasih tau|suruh|ingetin manda|sampaikan ke manda|pesan buat manda/i.test(currentText);
const isTitipPesan = isTitipPesanToOkta || isTitipPesanToManda;
const titipTargetNumber = isTitipPesanToOkta ? $env.MY_WA_NUMBER : isTitipPesanToManda ? $env.MANDA_WA_NUMBER : null;
const titipTitle = isTitipPesanToOkta ? "💌 *Titip Pesan dari Kak Manda untuk Okta:*" : "💌 *Titip Pesan dari Okta untuk Kak Manda:*";

const hasAudio = selectedMedia?.type === "audio";

// Vision Query Detection
const isScheduleQuery = Boolean(hasAudio || /jadwal|agenda|kuliah|tugas|uas|kelas|acara|free|kosong|sibuk|kegiatan|besok|hari ini|lusa|ngapain|padet/i.test(currentText));
const isAnnouncementQuery = Boolean(/pengumuman|siam|berita kampus|info dosen|info kuliah|asinkron|dinas luar/i.test(currentText));
const isPresensiQuery = Boolean(/presensi|absen|absensi|kehadiran/i.test(currentText));

return [
  {
    json: {
      ...root,
      wa: {
        remoteJid,
        fromMe: data.key?.fromMe || false,
        messageId: data.key?.id || "",
        participant,
        participantAlt: data.key?.participantAlt || "",
        pushName: data.pushName || "",
        dateTime: body.date_time || new Date().toISOString(),

        isManda,
        isOkta,
        isGroup,
        isDevGroup,

        currentText,
        quotedText,
        cleanText,

        isMentionBot,
        isReplyingToBot,
        isAskCommand,
        isStickerCommand,
        isTitipPesan,
        isTitipPesanToOkta,
        isTitipPesanToManda,
        titipTargetNumber,
        titipTitle,

        hasAudio,
        isScheduleQuery,
        isAnnouncementQuery,
        isPresensiQuery,

        hasCurrentMedia: currentMedia.exists,
        hasQuotedMedia: quotedMedia.exists,
        hasAnyMedia: !!selectedMedia,

        currentMedia,
        quotedMedia,
        selectedMedia,

        selectedMediaSummary: selectedMedia
          ? `${selectedMedia.source} ${selectedMedia.type} (${selectedMedia.mimetype})`
          : "-",

        quotedPayload: {
          key: {
            remoteJid: data.key?.remoteJid,
            fromMe: data.key?.fromMe,
            id: data.key?.id,
            participant: data.key?.participant || data.participant,
          },
          message: data.message,
        },
      },
    },
  },
];"""
nodes_by_name["Normalize WA Context"]["parameters"]["jsCode"] = norm_code

# 2. Define Vision Nodes
# Switch Vision Query
switch_vision_node = {
    "parameters": {
        "rules": {
            "values": [
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                        "conditions": [
                            {
                                "id": uid(),
                                "leftValue": "={{ $('Normalize WA Context').item.json.wa.isScheduleQuery }}",
                                "rightValue": "",
                                "operator": {"type": "boolean", "operation": "true", "singleValue": True}
                            }
                        ],
                        "combinator": "and"
                    },
                    "renameOutput": True,
                    "outputKey": "schedule"
                },
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                        "conditions": [
                            {
                                "id": uid(),
                                "leftValue": "={{ $('Normalize WA Context').item.json.wa.isAnnouncementQuery }}",
                                "rightValue": "",
                                "operator": {"type": "boolean", "operation": "true", "singleValue": True}
                            }
                        ],
                        "combinator": "and"
                    },
                    "renameOutput": True,
                    "outputKey": "pengumuman"
                },
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                        "conditions": [
                            {
                                "id": uid(),
                                "leftValue": "={{ $('Normalize WA Context').item.json.wa.isPresensiQuery }}",
                                "rightValue": "",
                                "operator": {"type": "boolean", "operation": "true", "singleValue": True}
                            }
                        ],
                        "combinator": "and"
                    },
                    "renameOutput": True,
                    "outputKey": "presensi"
                },
                {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                        "conditions": [
                            {
                                "id": uid(),
                                "leftValue": "={{ true }}",
                                "rightValue": "",
                                "operator": {"type": "boolean", "operation": "true", "singleValue": True}
                            }
                        ],
                        "combinator": "and"
                    },
                    "renameOutput": True,
                    "outputKey": "none"
                }
            ]
        }
    },
    "type": "n8n-nodes-base.switch",
    "typeVersion": 3.2,
    "position": [60, 0],
    "id": uid(),
    "name": "Switch Vision Query"
}

# Google Calendar Nodes
gcal_cred = {
    "googleCalendarOAuth2Api": {
        "id": "kXkpk4YfItv3zvuT",
        "name": "Google Calendar account"
    }
}

gcal_okta_agenda = {
    "parameters": {
        "operation": "getAll",
        "calendar": {
            "__rl": True,
            "value": "={{ $env.GCAL_OKTA_AGENDA }}",
            "mode": "id"
        },
        "returnAll": True,
        "timeMin": "={{ $now.setZone('Asia/Jakarta').startOf('day').toISO() }}",
        "timeMax": "={{ $now.setZone('Asia/Jakarta').plus({ days: 2 }).endOf('day').toISO() }}",
        "options": {"singleEvents": True}
    },
    "type": "n8n-nodes-base.googleCalendar",
    "typeVersion": 1.3,
    "position": [260, -260],
    "id": uid(),
    "name": "Get GCal Okta Agenda",
    "credentials": gcal_cred,
    "alwaysOutputData": True
}

gcal_okta_kuliah = {
    "parameters": {
        "operation": "getAll",
        "calendar": {
            "__rl": True,
            "value": "={{ $env.GCAL_OKTA_KULIAH }}",
            "mode": "id"
        },
        "returnAll": True,
        "timeMin": "={{ $now.setZone('Asia/Jakarta').startOf('day').toISO() }}",
        "timeMax": "={{ $now.setZone('Asia/Jakarta').plus({ days: 2 }).endOf('day').toISO() }}",
        "options": {"singleEvents": True}
    },
    "type": "n8n-nodes-base.googleCalendar",
    "typeVersion": 1.3,
    "position": [460, -260],
    "id": uid(),
    "name": "Get GCal Okta Kuliah",
    "credentials": gcal_cred,
    "alwaysOutputData": True
}

gcal_manda_agenda = {
    "parameters": {
        "operation": "getAll",
        "calendar": {
            "__rl": True,
            "value": "={{ $env.GCAL_MANDA_AGENDA }}",
            "mode": "id"
        },
        "returnAll": True,
        "timeMin": "={{ $now.setZone('Asia/Makassar').startOf('day').toISO() }}",
        "timeMax": "={{ $now.setZone('Asia/Makassar').plus({ days: 2 }).endOf('day').toISO() }}",
        "options": {"singleEvents": True}
    },
    "type": "n8n-nodes-base.googleCalendar",
    "typeVersion": 1.3,
    "position": [660, -260],
    "id": uid(),
    "name": "Get GCal Manda Agenda",
    "credentials": gcal_cred,
    "alwaysOutputData": True
}

gcal_manda_kuliah = {
    "parameters": {
        "operation": "getAll",
        "calendar": {
            "__rl": True,
            "value": "={{ $env.GCAL_MANDA_KULIAH }}",
            "mode": "id"
        },
        "returnAll": True,
        "timeMin": "={{ $now.setZone('Asia/Makassar').startOf('day').toISO() }}",
        "timeMax": "={{ $now.setZone('Asia/Makassar').plus({ days: 2 }).endOf('day').toISO() }}",
        "options": {"singleEvents": True}
    },
    "type": "n8n-nodes-base.googleCalendar",
    "typeVersion": 1.3,
    "position": [860, -260],
    "id": uid(),
    "name": "Get GCal Manda Kuliah",
    "credentials": gcal_cred,
    "alwaysOutputData": True
}

format_calendar_vision = {
    "parameters": {
        "jsCode": """function extractEvents(nodeName, label, tz = 'Asia/Jakarta') {
  let raw = [];
  try {
    raw = $(nodeName).all();
  } catch (e) {}
  
  const valid = raw.filter(e => e.json && (e.json.summary || e.json.id));
  if (valid.length === 0) return `${label}: Tidak ada jadwal.`;
  
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
const mandaKuliah = extractEvents('Get GCal Manda Kuliah', 'Jadwal Kuliah Kak Manda', 'Asia/Makassar');
const mandaAgenda = extractEvents('Get GCal Manda Agenda', 'Agenda Kak Manda', 'Asia/Makassar');

const visionText = `📅 DATA GOOGLE CALENDAR TERKINI (HARI INI & BESOK):\\n\\n${oktaKuliah}\\n\\n${oktaAgenda}\\n\\n${mandaKuliah}\\n\\n${mandaAgenda}`;

const prev = $('Format Memory Context').item.json;
return [{
  json: {
    ...prev,
    visionContext: visionText
  }
}];"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [1080, -260],
    "id": uid(),
    "name": "Format Calendar Vision"
}

# Announcement Nodes
http_pengumuman = {
    "parameters": {
        "method": "POST",
        "url": "http://brone-auth:3000/get-siam-pengumuman",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ { username: $env.BRONE_USERNAME, password: $env.BRONE_PASSWORD } }}",
        "options": {"timeout": 8000}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [360, -80],
    "id": uid(),
    "name": "[HTTP] Get SIAM Pengumuman",
    "continueOnFail": True
}

format_pengumuman_vision = {
    "parameters": {
        "jsCode": """let raw = {};
try {
  raw = $input.first().json;
} catch (e) {}

let visionText = "📢 DATA PENGUMUMAN SIAM UB TERKINI:\\n";
const list = raw.data || [];
if (Array.isArray(list) && list.length > 0) {
  const entries = [];
  for (const item of list.slice(0, 5)) {
    const matkul = item.matkul || item.kode || "Kuliah";
    const pList = item.daftar_pengumuman || [];
    for (const p of pList.slice(0, 2)) {
      entries.push(`• [${matkul} | ${p.tanggal || '-'}]: ${p.isi || '-'}`);
    }
  }
  visionText += entries.length > 0 ? entries.join('\\n\\n') : "(Tidak ada pengumuman baru di SIAM)";
} else {
  visionText += "(Tidak ada pengumuman baru dari SIAM UB saat ini)";
}

const prev = $('Format Memory Context').item.json;
return [{
  json: {
    ...prev,
    visionContext: visionText
  }
}];"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [660, -80],
    "id": uid(),
    "name": "Format Pengumuman Vision"
}

# Presensi Nodes
http_presensi = {
    "parameters": {
        "method": "POST",
        "url": "http://brone-auth:3000/get-siam-presensi",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": "={{ { username: $env.BRONE_USERNAME, password: $env.BRONE_PASSWORD } }}",
        "options": {"timeout": 8000}
    },
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [360, 80],
    "id": uid(),
    "name": "[HTTP] Get SIAM Presensi",
    "continueOnFail": True
}

format_presensi_vision = {
    "parameters": {
        "jsCode": """let raw = {};
try {
  raw = $input.first().json;
} catch (e) {}

let visionText = "📋 STATUS PRESENSI SIAM UB HARI INI:\\n";
const list = raw.data || [];
if (Array.isArray(list) && list.length > 0) {
  const entries = [];
  for (const item of list) {
    entries.push(`• ${item.nama || item.matkul || 'Kuliah'}: Status ${item.status || 'Tersedia'}`);
  }
  visionText += entries.join('\\n');
} else {
  visionText += "(Belum ada jadwal presensi yang aktif atau semua kelas hari ini sudah terpresensi)";
}

const prev = $('Format Memory Context').item.json;
return [{
  json: {
    ...prev,
    visionContext: visionText
  }
}];"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [660, 80],
    "id": uid(),
    "name": "Format Presensi Vision"
}

format_default_vision = {
    "parameters": {
        "jsCode": """const prev = $('Format Memory Context').item.json;
return [{
  json: {
    ...prev,
    visionContext: ""
  }
}];"""
    },
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [360, 240],
    "id": uid(),
    "name": "Format Default Vision"
}

# Reposition existing audio nodes & switch
if_audio_node = nodes_by_name["If Has Audio"]
if_audio_node["position"] = [1320, 0]

prep_audio = nodes_by_name["Prepare Audio Payload"]
prep_audio["position"] = [1520, -120]

get_audio = nodes_by_name["[HTTP] Evolution Get Base64 Audio"]
get_audio["position"] = [1720, -120]

attach_audio = nodes_by_name["Attach Audio Base64"]
attach_audio["position"] = [1920, -120]
attach_audio["parameters"]["jsCode"] = """const audioResult = $input.first().json;

let prevItem = {};
try { prevItem = $('Format Calendar Vision').item.json; } catch(e){}
if (!prevItem || !prevItem.wa) {
  try { prevItem = $('Format Pengumuman Vision').item.json; } catch(e){}
}
if (!prevItem || !prevItem.wa) {
  try { prevItem = $('Format Presensi Vision').item.json; } catch(e){}
}
if (!prevItem || !prevItem.wa) {
  try { prevItem = $('Format Default Vision').item.json; } catch(e){}
}
if (!prevItem || !prevItem.wa) {
  prevItem = $('Format Memory Context').item.json;
}

let b64 = audioResult.base64 || '';
if (b64.includes('base64,')) {
  b64 = b64.split('base64,')[1];
}

return [{
  json: {
    ...prevItem,
    base64Audio: b64
  }
}];"""

# Update Switch rule 2 (ada chat - grup) to handle group VN and quoted bot
sw_node = nodes_by_name["Switch"]
sw_node["position"] = [2140, 260]
sw_rules = sw_node["parameters"]["rules"]["values"]
for r in sw_rules:
    if r.get("outputKey") == "ada chat - grup":
        r["conditions"]["conditions"][0]["leftValue"] = "={{ ($('Normalize WA Context').item.json.wa.isMentionBot || $('Normalize WA Context').item.json.wa.isReplyingToBot || $('Normalize WA Context').item.json.wa.isDevGroup) && (!!$('Normalize WA Context').item.json.wa.cleanText || $('Normalize WA Context').item.json.wa.hasAudio) }}"
    elif r.get("outputKey") == "ada chat - pc":
        r["conditions"]["conditions"][0]["leftValue"] = "={{ ($('Normalize WA Context').item.json.wa.isOkta || $('Normalize WA Context').item.json.wa.isAskCommand) && (!!$('Normalize WA Context').item.json.wa.cleanText || $('Normalize WA Context').item.json.wa.hasAudio) }}"

# Update Gemini prompts with thinkingBudget: 0 and strict immediate answers
manda_prompt = """={{
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
          {
            "text": `Kamu adalah AI Asisten Pribadi dan Perwakilan Resmi Okta untuk Kak Manda.

KONTEKS HUBUNGAN:
- Kak Manda (Amanda Syalwa Nadira) adalah pacar tersayang Okta.
- Mahasiswi Farmasi Universitas Lambung Mangkurat (ULM), asal Banjarmasin.
- Panggilan resmi & wajib untuknya: "Kak Manda".
- Okta (Oktavianus Samuel Minarto) adalah developer yang membangun kamu.

ATURAN PERAN (PENTING):
1. Kamu BUKAN Okta dan TIDAK BOLEH berpura-pura menjadi Okta.
2. Posisikan dirimu sebagai perwakilan, ajudan, atau asisten pribadi Okta yang siap membantu Kak Manda.
3. Gaya komunikasi: Hangat, sopan, ramah, santai, manis, tapi TIDAK ALAY atau berlebihan (cringe).
4. Gunakan bahasa Indonesia kasual yang natural (aku, kamu, yaa, hehe, siap Kak Manda).
5. Jika Kak Manda mengirim pesan suara (voice note), dengarkan audio yang terlampir dengan teliti lalu tanggapi pesannya dengan ramah.
6. TITIP PESAN KE OKTA:
   - Jika Kak Manda menitipkan pesan untuk Okta (misal: "titip pesan", "bilang ke okta", "ingetin okta"):
     - Beritahu dengan manis bahwa pesan Kak Manda sudah kamu catat dan sudah otomatis kamu teruskan ke WhatsApp pribadi Okta sekarang juga!

RIWAYAT PERCAKAPAN SEBELUMNYA:
${$json.memoryContext || "(Belum ada riwayat sebelumnya)"}

${$json.visionContext ? `INFORMASI REAL-TIME SISTEM (VISION KAMU):
${$json.visionContext}

ATURAN PENTING PENGGUNAAN DATA VISION DI ATAS:
- Gunakan data real-time di atas LANGSUNG untuk menjawab pertanyaan jadwal, agenda, pengumuman, atau presensi secara to-the-point, ramah, dan akurat.
- DILARANG KERAS menjawab "bentar aku cek dulu", "tunggu ya aku cekin", atau sejenisnya, KARENA KAMU SUDAH MEMEGANG DATA NYATA DI ATAS!
- Jika di data tertulis tidak ada jadwal / kosong, sampaikan dengan ramah bahwa jadwal kosong.` : ''}

INFORMASI SAAT INI:
- Waktu Sekarang: ${$json.wa.dateTime}
- Pesan Masuk dari Kak Manda: "${$json.wa.currentText || $json.wa.cleanText || ($json.wa.hasAudio ? '[Pesan Suara / Voice Note terlampir di atas]' : '[Media]')}"
- Pesan yang Di-quote: "${$json.wa.quotedText || '-'}"

Jawablah pesan Kak Manda dengan ramah, hangat, dan to-the-point sebagai asisten perwakilan Okta:`
          }
        ]
      }
    ],
    "generationConfig": {
      "thinkingConfig": {
        "thinkingBudget": 0
      }
    }
  }
}}"""

general_prompt = """={{
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
          {
            "text": `Kamu adalah AI Asisten Cerdas untuk WhatsApp.

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

RIWAYAT PERCAKAPAN SEBELUMNYA:
${$json.memoryContext || "(Belum ada riwayat sebelumnya)"}

${$json.visionContext ? `INFORMASI REAL-TIME SISTEM (VISION KAMU):
${$json.visionContext}

ATURAN PENTING PENGGUNAAN DATA VISION DI ATAS:
- Gunakan data real-time di atas LANGSUNG untuk menjawab pertanyaan jadwal, agenda, pengumuman, atau presensi secara to-the-point dan akurat.
- DILARANG KERAS menjawab "bentar aku cek dulu", "tunggu ya aku cekin", atau sejenisnya, KARENA KAMU SUDAH MEMEGANG DATA NYATA DI ATAS!
- Jika di data tertulis tidak ada jadwal / kosong, sampaikan dengan jelas bahwa jadwal kosong / tidak ada acara.` : ''}

INFORMASI SAAT INI:
- Pengirim: ${$json.wa.pushName || "User"} (${$json.wa.participant || $json.wa.remoteJid})
- Waktu: ${$json.wa.dateTime}
- Pesan: "${$json.wa.currentText || $json.wa.cleanText || ($json.wa.hasAudio ? '[Pesan Suara / Voice Note terlampir di atas]' : '[Media]')}"
- Quoted: "${$json.wa.quotedText || '-'}"

Jawablah dengan ringkas dan solutif:`
          }
        ]
      }
    ],
    "generationConfig": {
      "thinkingConfig": {
        "thinkingBudget": 0
      }
    }
  }
}}"""

nodes_by_name["[HTTP] Gemini Build Message1"]["parameters"]["jsonBody"] = manda_prompt
nodes_by_name["[HTTP] Gemini Build Message"]["parameters"]["jsonBody"] = general_prompt

# Update [PG] Save Bot Reply to NEVER write undefined
save_reply_node = nodes_by_name["[PG] Save Bot Reply"]
save_reply_node["parameters"]["query"] = """INSERT INTO wa_chat_memory (room_jid, sender_jid, sender_name, role, message_type, content)
VALUES (
  '{{ $('Normalize WA Context').item.json.wa.remoteJid }}',
  'bot',
  'Asisten Okta',
  'assistant',
  'text',
  '{{ (() => {
    let text = "";
    try { text = $('[HTTP] Gemini Build Message1').item.json.candidates[0].content.parts[0].text; } catch(e){}
    if (!text) {
      try { text = $('[HTTP] Gemini Build Message').item.json.candidates[0].content.parts[0].text; } catch(e){}
    }
    if (!text && $json.message) {
      const m = $json.message;
      text = typeof m === "string" ? m : (m.conversation || m.extendedTextMessage?.text || "");
    }
    return (text || "Pesan terkirim").replace(/'/g, "''");
  })() }}'
);"""

# Remove old new nodes if exist, then add new nodes
new_nodes_list = [
    switch_vision_node,
    gcal_okta_agenda,
    gcal_okta_kuliah,
    gcal_manda_agenda,
    gcal_manda_kuliah,
    format_calendar_vision,
    http_pengumuman,
    format_pengumuman_vision,
    http_presensi,
    format_presensi_vision,
    format_default_vision
]

new_names = {n["name"] for n in new_nodes_list}
wac["nodes"] = [n for n in wac["nodes"] if n["name"] not in new_names]
wac["nodes"].extend(new_nodes_list)

# Rewire connections
# 1. Format Memory Context -> Switch Vision Query
wac["connections"]["Format Memory Context"] = {
    "main": [
        [
            {"node": "Switch Vision Query", "type": "main", "index": 0}
        ]
    ]
}

# 2. Switch Vision Query connections
wac["connections"]["Switch Vision Query"] = {
    "main": [
        # Output 0 (schedule)
        [{"node": "Get GCal Okta Agenda", "type": "main", "index": 0}],
        # Output 1 (pengumuman)
        [{"node": "[HTTP] Get SIAM Pengumuman", "type": "main", "index": 0}],
        # Output 2 (presensi)
        [{"node": "[HTTP] Get SIAM Presensi", "type": "main", "index": 0}],
        # Output 3 (none)
        [{"node": "Format Default Vision", "type": "main", "index": 0}]
    ]
}

# Schedule chain
wac["connections"]["Get GCal Okta Agenda"] = {"main": [[{"node": "Get GCal Okta Kuliah", "type": "main", "index": 0}]]}
wac["connections"]["Get GCal Okta Kuliah"] = {"main": [[{"node": "Get GCal Manda Agenda", "type": "main", "index": 0}]]}
wac["connections"]["Get GCal Manda Agenda"] = {"main": [[{"node": "Get GCal Manda Kuliah", "type": "main", "index": 0}]]}
wac["connections"]["Get GCal Manda Kuliah"] = {"main": [[{"node": "Format Calendar Vision", "type": "main", "index": 0}]]}
wac["connections"]["Format Calendar Vision"] = {"main": [[{"node": "If Has Audio", "type": "main", "index": 0}]]}

# Pengumuman chain
wac["connections"]["[HTTP] Get SIAM Pengumuman"] = {"main": [[{"node": "Format Pengumuman Vision", "type": "main", "index": 0}]]}
wac["connections"]["Format Pengumuman Vision"] = {"main": [[{"node": "If Has Audio", "type": "main", "index": 0}]]}

# Presensi chain
wac["connections"]["[HTTP] Get SIAM Presensi"] = {"main": [[{"node": "Format Presensi Vision", "type": "main", "index": 0}]]}
wac["connections"]["Format Presensi Vision"] = {"main": [[{"node": "If Has Audio", "type": "main", "index": 0}]]}

# Default chain
wac["connections"]["Format Default Vision"] = {"main": [[{"node": "If Has Audio", "type": "main", "index": 0}]]}

# Save updated wa-conversation
with open(wac_path, "w") as f:
    json.dump([wac], f, indent=2)
with open("n8n/workflow/wa-conversation.json", "w") as f:
    json.dump([wac], f, indent=2)

print("wa-conversation.json successfully upgraded with Vision Pipeline & Group VN handling!")
