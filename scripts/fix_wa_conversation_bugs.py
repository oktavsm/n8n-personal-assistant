#!/usr/bin/env python3
"""
Fix two bugs in wa-conversation:
1. Switch Vision Query missing connection for output 5 ('none' / general chat & image questions)
2. Backtick syntax error in [HTTP] Gemini Build Message and [HTTP] Gemini Build Message1
3. Ensure Switch in wa-conversation passes images (hasImage) even if text is empty
"""

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PROMPT_TEXT_CLEAN = """Kamu adalah AI Asisten Cerdas untuk WhatsApp.

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
      - Kalender kuliah dilindungi penuh. Jika user meminta hapus jadwal kuliah, TOLAK dengan sopan dan jelaskan bahwa jadwal kuliah dilindungi, namun ruang kelas bisa diubah atau ditandai libur via perintah '/edit-kuliah [matkul] [ruang / LIBUR]'. DILARANG MENGELUARKAN '<<<ACTION:DELETE>>>' untuk mata kuliah!
   b. JANGAN BERHALUSINASI MENYATAKAN SUDAH BERHASIL MENGHAPUS SEBELUM SISTEM MEMPROSES!
      - Katakan "Oke bro, aku bantu proses di kalender..." bukan "Udah aku hapus ya".
   c. TUGAS/AGENDA DUPLIKAT:
      - Jika user menyebut ada tugas ganda / duplikat dan ingin menghapus salah satunya (contoh: "hapus salah satu tugas comvis"), keluarkan tag '<<<ACTION:DELETE|okta|comvis>>>'. Sistem backend akan otomatis memeriksa dan mengirimkan menu nomor pilihan kepada user jika terdapat duplikat!

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

JSON_BODY_EXPR = """={{
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
            "text": `""" + PROMPT_TEXT_CLEAN + """`
          }
        ]
      }
    ],
    "generationConfig": {
      ...( ($json.base64Audio || $json.base64Image) ? { "thinkingConfig": { "thinkingBudget": 0 } } : { "maxOutputTokens": 1024 } )
    }
  }
}}"""

# Test JS syntax of JSON_BODY_EXPR with Node.js
test_code = """
const $json = {
  base64Audio: null,
  base64Image: "abc",
  imageMimetype: "image/jpeg",
  memoryContext: "halo",
  visionContext: "jadwal ada",
  wa: {
    pushName: "Okta",
    participant: "6285750583867@s.whatsapp.net",
    dateTimeWib: "2026-10-20 17:30",
    currentText: "menurutmu ini diagram apa bro",
    cleanText: "menurutmu ini diagram apa bro",
    hasImage: true
  }
};
const $env = {
  MY_WA_NUMBER: "6285750583867"
};
const parsed = (""" + JSON_BODY_EXPR[3:-2].strip() + """);
console.log("SUCCESS: evaluated object with " + parsed.contents[0].parts.length + " parts");
"""

with open("/tmp/verify_expr.js", "w", encoding="utf-8") as f:
    f.write(test_code)

res = subprocess.run(["node", "/tmp/verify_expr.js"], capture_output=True, text=True)
if res.returncode != 0:
    print(f"❌ Syntax validation FAILED:\n{res.stderr}")
    exit(1)
print(f"✅ Node.js syntax verification PASSED: {res.stdout.strip()}")

# Apply fixes to workflow files
files_to_fix = [
    REPO_ROOT / "workflow" / "wa-conversation.json",
    REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json"
]

for fp in files_to_fix:
    if not fp.exists(): continue
    with open(fp, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    nodes = data.get("nodes", [])
    conns = data.get("connections", {})

    # 1. Fix Switch Vision Query
    for n in nodes:
        if n.get("name") == "Switch Vision Query":
            rules = n["parameters"]["rules"]["values"]
            while len(rules) < 6:
                rules.append({})
            rules[5] = {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 3},
                    "conditions": [
                        {
                            "id": "switch-vision-none-cond",
                            "leftValue": "={{ !$('Normalize WA Context').item.json.wa.isScheduleQuery && !$('Normalize WA Context').item.json.wa.isAnnouncementQuery && !$('Normalize WA Context').item.json.wa.isPresensiQuery && !$('Normalize WA Context').item.json.wa.isNotesQuery && !$('Normalize WA Context').item.json.wa.isExpenseQuery }}",
                            "rightValue": "",
                            "operator": {"type": "boolean", "operation": "true", "singleValue": True}
                        }
                    ],
                    "combinator": "and"
                },
                "renameOutput": True,
                "outputKey": "none"
            }
            n["parameters"]["fallbackOutput"] = 5
            print(f"[{fp.name}] Set fallbackOutput = 5 on Switch Vision Query")

        # 2. Fix Switch (image support)
        if n.get("name") == "Switch":
            rules = n.get("parameters", {}).get("rules", {}).get("values", [])
            # Rule 2: ada chat - grup
            if len(rules) > 2:
                rules[2]["conditions"]["conditions"][0]["leftValue"] = """={{ ($('Normalize WA Context').item.json.wa.isMentionBot || $('Normalize WA Context').item.json.wa.isReplyingToBot || $('Normalize WA Context').item.json.wa.isDevGroup) && (!!$('Normalize WA Context').item.json.wa.cleanText || $('Normalize WA Context').item.json.wa.hasAudio || $('Normalize WA Context').item.json.wa.hasImage) }}"""
            # Rule 4: ada chat - pc
            if len(rules) > 4:
                rules[4]["conditions"]["conditions"][0]["leftValue"] = """={{ ($('Normalize WA Context').item.json.wa.isOkta || $('Normalize WA Context').item.json.wa.isAskCommand) && (!!$('Normalize WA Context').item.json.wa.cleanText || $('Normalize WA Context').item.json.wa.hasAudio || $('Normalize WA Context').item.json.wa.hasImage) }}"""
            print(f"[{fp.name}] Updated Switch rules to support hasImage")

    # Connect Switch Vision Query Output 5 to Format Default Vision
    if "Switch Vision Query" in conns and "main" in conns["Switch Vision Query"]:
        main_outputs = conns["Switch Vision Query"]["main"]
        while len(main_outputs) <= 5:
            main_outputs.append([])
        main_outputs[5] = [{"node": "Format Default Vision", "type": "main", "index": 0}]
        print(f"[{fp.name}] Connected Switch Vision Query output 5 -> Format Default Vision")

    # 3. Fix prompt backticks in Gemini Build Message and Gemini Build Message1
    for n in nodes:
        if "Gemini Build Message" in n.get("name", ""):
            n["parameters"]["jsonBody"] = JSON_BODY_EXPR
            print(f"[{fp.name}] Cleaned backticks in {n['name']}")

    with open(fp, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Saved {fp.name}")

print("\n🚀 Ready for deployment!")
