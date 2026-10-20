import json
import uuid

def uid():
    return str(uuid.uuid4())

# ==========================================
# 1. UPDATE master-router-webhook.json
# ==========================================
with open("workflow/master-router-webhook.json") as f:
    raw = json.load(f)
    wf_router = raw[0] if isinstance(raw, list) else raw

switch_node = next(n for n in wf_router["nodes"] if n["name"] == "Switch")
rules = switch_node["parameters"]["rules"]["values"]

# Add Rule 22: okta_pc if not present
rule_22_exists = any(r.get("outputKey") == "okta_pc" for r in rules)
if not rule_22_exists:
    new_rule_okta_pc = {
        "conditions": {
            "options": {
                "caseSensitive": False,
                "leftValue": "",
                "typeValidation": "loose",
                "version": 3
            },
            "conditions": [
                {
                    "id": uid(),
                    "leftValue": "={{ (() => { const jid = $json.body?.data?.key?.remoteJid || ''; const part = $json.body?.data?.key?.participant || ''; const isGroup = jid.endsWith('@g.us'); const isOkta = jid.includes($env.MY_WA_NUMBER) || part.includes($env.MY_WA_NUMBER); return Boolean(!isGroup && isOkta); })() }}",
                    "rightValue": "",
                    "operator": {
                        "type": "boolean",
                        "operation": "true",
                        "singleValue": True
                    }
                }
            ],
            "combinator": "and"
        },
        "renameOutput": True,
        "outputKey": "okta_pc"
    }
    rules.append(new_rule_okta_pc)
    print("Added Rule 22 (okta_pc) to Switch")

call_wac_node = next(n for n in wf_router["nodes"] if n["name"] == "Call 'wa-conversation'")
switch_conn = wf_router["connections"]["Switch"]["main"]
while len(switch_conn) <= 22:
    switch_conn.append([])

if not any(c.get("node") == "Call 'wa-conversation'" for c in switch_conn[22]):
    switch_conn[22].append({
        "node": "Call 'wa-conversation'",
        "type": "main",
        "index": 0
    })
    print("Connected Switch output 22 to Call 'wa-conversation'")

with open("workflow/master-router-webhook.json", "w") as f:
    json.dump(wf_router, f, indent=2)
with open("n8n/workflow/master-router-webhook.json", "w") as f:
    json.dump(wf_router, f, indent=2)
print("master-router-webhook.json updated successfully!")


# ==========================================
# 2. UPDATE wa-conversation.json
# ==========================================
with open("workflow/wa-conversation.json") as f:
    raw = json.load(f)
    wf_wac = raw[0] if isinstance(raw, list) else raw

# Node 1: Normalize WA Context JS Code
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
const botLids = ["171619058196619@lid", "195095164887244@lid"];
const isMentionBot =
  currentText.includes("@171619058196619") ||
  currentText.includes("@195095164887244") ||
  mentionedJid.some(j => botLids.some(b => j.includes(b.split("@")[0])));

const isAskCommand = textLower.startsWith("/ask");
const isStickerCommand = textLower.startsWith("/stiker") || textLower.startsWith("/sticker");

const cleanText = currentText
  .replace(/@171619058196619/g, "")
  .replace(/@195095164887244/g, "")
  .replace(/^\\/ask/i, "")
  .replace(/^\\/stiker/i, "")
  .replace(/^\\/sticker/i, "")
  .trim();

const remoteJid = data.key?.remoteJid || "";
const participant = data.key?.participant || data.key?.participantAlt || remoteJid;
const isGroup = remoteJid.endsWith("@g.us");

const isManda = remoteJid.includes($env.MANDA_WA_NUMBER) || participant.includes($env.MANDA_WA_NUMBER);
const isOkta = remoteJid.includes($env.MY_WA_NUMBER) || participant.includes($env.MY_WA_NUMBER);

// Deteksi Titip Pesan Dua Arah
const isTitipPesanToOkta = !isOkta && /titip|bilang|kasih tau|suruh|ingetin okta|sampaikan ke okta|pesan buat okta/i.test(currentText);
const isTitipPesanToManda = isOkta && /titip|bilang|kasih tau|suruh|ingetin manda|sampaikan ke manda|pesan buat manda/i.test(currentText);
const isTitipPesan = isTitipPesanToOkta || isTitipPesanToManda;
const titipTargetNumber = isTitipPesanToOkta ? $env.MY_WA_NUMBER : isTitipPesanToManda ? $env.MANDA_WA_NUMBER : null;
const titipTitle = isTitipPesanToOkta ? "💌 *Titip Pesan dari Kak Manda untuk Okta:*" : "💌 *Titip Pesan dari Okta untuk Kak Manda:*";

const hasAudio = selectedMedia?.type === "audio";
const isScheduleQuery = /jadwal|agenda|kuliah|tugas|uas|kelas|acara|free|kosong|sibuk|kegiatan|ngapain/i.test(currentText);

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

        currentText,
        quotedText,
        cleanText,

        isMentionBot,
        isAskCommand,
        isStickerCommand,
        isTitipPesan,
        isTitipPesanToOkta,
        isTitipPesanToManda,
        titipTargetNumber,
        titipTitle,

        hasAudio,
        isScheduleQuery,

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

norm_node = next(n for n in wf_wac["nodes"] if n["name"] == "Normalize WA Context")
norm_node["parameters"]["jsCode"] = norm_code

# Update Gemini Build Message1 (Kak Manda Persona)
manda_prompt = """={{
  {
    "contents": [
      {
        "parts": [
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
5. Jika Kak Manda menitipkan pesan untuk Okta (misal: "titip pesan", "bilang ke okta", "ingetin okta"):
   - Beritahu dengan manis bahwa pesan Kak Manda sudah kamu catat dan sudah otomatis kamu teruskan ke WhatsApp pribadi Okta sekarang juga.
6. KEMAMPUAN SISTEM (VISION KAMU):
   - Kamu bisa memeriksa jadwal kuliah dan agenda Okta maupun Kak Manda di Google Calendar.
   - Kamu bisa membuatkan stiker WA otomatis (cukup kirim foto/video/GIF dengan caption /stiker).
   - Kamu bisa meneruskan pesan titipan langsung ke WA Okta secara otomatis.
   - Jika Kak Manda bertanya jadwal Okta atau agenda bersama, jelaskan secara ramah dan informatif.

RIWAYAT PERCAKAPAN SEBELUMNYA:
${$json.memoryContext || "(Belum ada riwayat sebelumnya)"}

INFORMASI SAAT INI:
- Waktu Sekarang: ${$json.wa.dateTime}
- Pesan Masuk dari Kak Manda: "${$json.wa.currentText || $json.wa.cleanText || ($json.wa.hasAudio ? '[Pesan Suara / Voice Note]' : '[Media]')}"
- Pesan yang Di-quote: "${$json.wa.quotedText || '-'}"

Jawablah pesan Kak Manda dengan ramah, hangat, dan to-the-point sebagai asisten perwakilan Okta:`
          }
        ]
      }
    ]
  }
}}"""

gemini_manda = next(n for n in wf_wac["nodes"] if n["name"] == "[HTTP] Gemini Build Message1")
gemini_manda["parameters"]["url"] = "=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={{ $json.selected_key }}"
gemini_manda["parameters"]["jsonBody"] = manda_prompt

# Update Gemini Build Message (Okta & General Persona)
general_prompt = """={{
  {
    "contents": [
      {
        "parts": [
          {
            "text": `Kamu adalah AI Asisten Cerdas untuk WhatsApp.

LOGIKA PERAN:
1. JIKA PENGIRIM ADALAH OKTA (${$env.MY_WA_NUMBER}):
   - Kamu adalah co-pilot developer & asisten pribadi Okta.
   - Bersikap sigap, efisien, to-the-point, santai (panggil "bro" atau "Okta").
   - Jika Okta menitipkan pesan untuk Kak Manda (misal: "titip pesan ke manda", "bilang ke manda"):
     - Konfirmasi bahwa pesan untuk Kak Manda sudah dicatat dan langsung otomatis diteruskan ke WhatsApp Kak Manda!
   - Kamu memiliki vision tentang seluruh fitur: Google Calendar Okta & Manda, VPS CLI runner (/vps, /agent), Sticker Generator (/stiker), dan Notifier Akademik (Brone, SIAM).

2. JIKA DI GRUP ATAU PENGIRIM LAIN:
   - Bersikap ramah, santai, solutif, ringkas, dan menyesuaikan obrolan.

RIWAYAT PERCAKAPAN SEBELUMNYA:
${$json.memoryContext || "(Belum ada riwayat sebelumnya)"}

INFORMASI SAAT INI:
- Pengirim: ${$json.wa.pushName || "User"} (${$json.wa.participant || $json.wa.remoteJid})
- Waktu: ${$json.wa.dateTime}
- Pesan: "${$json.wa.currentText || $json.wa.cleanText || ($json.wa.hasAudio ? '[Pesan Suara / Voice Note]' : '[Media]')}"
- Quoted: "${$json.wa.quotedText || '-'}"

Jawablah dengan ringkas dan solutif:`
          }
        ]
      }
    ]
  }
}}"""

gemini_general = next(n for n in wf_wac["nodes"] if n["name"] == "[HTTP] Gemini Build Message")
gemini_general["parameters"]["url"] = "=https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={{ $json.selected_key }}"
gemini_general["parameters"]["jsonBody"] = general_prompt

# Update Switch rules in wa-conversation to support Okta PC and Audio
wac_switch = next(n for n in wf_wac["nodes"] if n["name"] == "Switch")
wac_rules = wac_switch["parameters"]["rules"]["values"]

# Ensure Rule 0: manda-pc
wac_rules[0]["conditions"]["conditions"][0]["leftValue"] = "={{ $('Normalize WA Context').item.json.wa.isManda && !$('Normalize WA Context').item.json.wa.isGroup }}"
wac_rules[0]["conditions"]["conditions"][0]["operator"] = {"type": "boolean", "operation": "true", "singleValue": True}
wac_rules[0]["conditions"]["conditions"][0]["rightValue"] = ""

# Ensure Rule 4: ada chat - pc (supports Okta PC & ask)
wac_rules[4]["conditions"]["conditions"][0]["leftValue"] = "={{ ($('Normalize WA Context').item.json.wa.isOkta || $('Normalize WA Context').item.json.wa.isAskCommand) && (!!$('Normalize WA Context').item.json.wa.cleanText || $('Normalize WA Context').item.json.wa.hasAudio) }}"
wac_rules[4]["conditions"]["conditions"][0]["operator"] = {"type": "boolean", "operation": "true", "singleValue": True}
wac_rules[4]["conditions"]["conditions"][0]["rightValue"] = ""

for r in wac_rules:
    if "options" not in r["conditions"]:
        r["conditions"]["options"] = {}
    r["conditions"]["options"]["typeValidation"] = "loose"

# Update Two-Way Forward Note node
forward_node = next(n for n in wf_wac["nodes"] if "Forward Note" in n["name"])
forward_node["name"] = "[HTTP Whatsapp] Forward Note to Target"
forward_node["parameters"]["bodyParameters"]["parameters"] = [
    {
        "name": "number",
        "value": "={{ $('Normalize WA Context').item.json.wa.titipTargetNumber }}"
    },
    {
        "name": "text",
        "value": "={{ $('Normalize WA Context').item.json.wa.titipTitle + '\\n\\n\"' + ($('Normalize WA Context').item.json.wa.currentText || $('Normalize WA Context').item.json.wa.cleanText || '[Pesan Suara]') + '\"\\n\\n_Waktu: ' + $('Normalize WA Context').item.json.wa.dateTime + '_' }}"
    }
]

# Connect [HTTP Whatsapp] Send Message1 (Okta reply) also to If Titip Pesan
send_msg_1_conn = wf_wac["connections"]["[HTTP Whatsapp] Send Message1"]["main"][0]
if not any(c.get("node") == "If Titip Pesan" for c in send_msg_1_conn):
    send_msg_1_conn.append({
        "node": "If Titip Pesan",
        "type": "main",
        "index": 0
    })
    print("Connected Send Message1 to If Titip Pesan (Two-Way Forwarding enabled!)")

with open("workflow/wa-conversation.json", "w") as f:
    json.dump(wf_wac, f, indent=2)
with open("n8n/workflow/wa-conversation.json", "w") as f:
    json.dump(wf_wac, f, indent=2)
print("wa-conversation.json updated successfully with Two-Way Titip Pesan and Gemini 2.5 Flash!")
