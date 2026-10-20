import json
import re
from pathlib import Path

# 1. Update personal-porto-chatbot.json
path_porto_chat = Path("workflow/personal-porto-chatbot.json")
if path_porto_chat.exists():
    with open(path_porto_chat) as f:
        d = json.load(f)
    wf = d[0] if isinstance(d, list) else d
    for n in wf["nodes"]:
        if "generativelanguage" in json.dumps(n):
            url = n["parameters"].get("url", "")
            n["parameters"]["url"] = url.replace("gemini-3.1-flash-lite", "gemini-3.5-flash-lite")
            print("Updated personal-porto-chatbot to gemini-3.5-flash-lite")
    with open(path_porto_chat, "w") as f:
        json.dump([wf], f, indent=2)
    with open("n8n/workflow/personal-porto-chatbot.json", "w") as f:
        json.dump([wf], f, indent=2)

# 2. Update personal-porto-generate-article.json
path_porto_art = Path("workflow/personal-porto-generate-article.json")
if path_porto_art.exists():
    with open(path_porto_art) as f:
        d = json.load(f)
    wf = d[0] if isinstance(d, list) else d
    for n in wf["nodes"]:
        if "generativelanguage" in json.dumps(n):
            url = n["parameters"].get("url", "")
            n["parameters"]["url"] = url.replace("gemini-3.1-flash-lite", "gemini-3.5-flash-lite")
            print("Updated personal-porto-generate-article to gemini-3.5-flash-lite")
    with open(path_porto_art, "w") as f:
        json.dump([wf], f, indent=2)
    with open("n8n/workflow/personal-porto-generate-article.json", "w") as f:
        json.dump([wf], f, indent=2)

# 3. Update wa-conversation.json
path_wac = Path("workflow/wa-conversation.json")
with open(path_wac) as f:
    d = json.load(f)
wf_wac = d[0] if isinstance(d, list) else d

# Updated Prompts with conditional generationConfig
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
      ...( $json.base64Audio ? { "thinkingConfig": { "thinkingBudget": 0 } } : { "maxOutputTokens": 1024 } )
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
      ...( $json.base64Audio ? { "thinkingConfig": { "thinkingBudget": 0 } } : { "maxOutputTokens": 1024 } )
    }
  }
}}"""

# Dynamic URL: use gemini-2.5-flash for audio, and gemini-3.5-flash-lite for text (500 RPD)
dynamic_url = "=https://generativelanguage.googleapis.com/v1beta/models/{{ $json.base64Audio ? 'gemini-2.5-flash' : 'gemini-3.5-flash-lite' }}:generateContent?key={{ $json.selected_key }}"

for n in wf_wac["nodes"]:
    if n["name"] == "[HTTP] Gemini Build Message1":
        n["parameters"]["url"] = dynamic_url
        n["parameters"]["jsonBody"] = manda_prompt
        print("Updated [HTTP] Gemini Build Message1 with Gemini 3.5 Flash Lite + VN routing")
    elif n["name"] == "[HTTP] Gemini Build Message":
        n["parameters"]["url"] = dynamic_url
        n["parameters"]["jsonBody"] = general_prompt
        print("Updated [HTTP] Gemini Build Message with Gemini 3.5 Flash Lite + VN routing")

with open(path_wac, "w") as f:
    json.dump([wf_wac], f, indent=2)
with open("n8n/workflow/wa-conversation.json", "w") as f:
    json.dump([wf_wac], f, indent=2)

print("All workflows successfully upgraded to Gemini 3.5 Flash Lite!")
