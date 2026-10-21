#!/usr/bin/env python3
import json
import re
from pathlib import Path

def update_morning_briefing():
    files = ["workflow/morning-audio-briefing.json", "n8n/workflow/morning-audio-briefing.json"]
    for fpath in files:
        p = Path(fpath)
        if not p.exists(): continue
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        target = data[0] if isinstance(data, list) else data
        for node in target.get("nodes", []):
            if "Gemini Audio Script" in node.get("name", ""):
                node["onError"] = "continueRegularOutput"
                node["retryOnFail"] = True
                node["maxTries"] = 3
                node["waitBetweenTries"] = 2000
                print(f"Fixed error handling on {node['name']} in {fpath}")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Updated {fpath}")

def update_wa_conversation():
    files = ["workflow/wa-conversation.json", "n8n/workflow/wa-conversation.json"]
    for fpath in files:
        p = Path(fpath)
        if not p.exists(): continue
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        target = data[0] if isinstance(data, list) else data
        nodes = target.get("nodes", [])

        # 1. Update Gemini Prompts
        image_and_tts_prompt_okta = """
5. PRESENSI KULIAH UB:
   <<<ACTION:PRESENSI|hadir>>> -> jika Okta meminta absen ("@n8n tolong absenkan kelas sekarang").

6. GENERASI GAMBAR & ILUSTRASI AI (FLUX.1):
   Jika pengguna meminta kamu membuatkan/menggambar/ilustrasi gambar (misal: "buatin gambar...", "bikinin ilustrasi...", "generate image..."):
   <<<ACTION:IMAGE_GEN|TARGET|ENHANCED_ENGLISH_PROMPT|CAPTION>>>
   TARGET: "okta" atau "manda"
   ENHANCED_ENGLISH_PROMPT: Prompt bahasa Inggris yang sangat detail, spesifik, artistik, dan sinematik untuk model FLUX.1.
   CAPTION: Deskripsi singkat bahasa Indonesia untuk caption gambar.
   Contoh:
   User: "buatin gambar kucing cyberpunk lagi ngoding"
   -> <<<ACTION:IMAGE_GEN|okta|A highly detailed cinematic shot of a cool cyberpunk cat wearing neon goggles, coding on a glowing laptop in a dark neo-tokyo alley with rain reflections, 8k octane render|Kucing cyberpunk lagi ngoding di laptop neon!>>>

7. BALAS DENGAN PESAN SUARA / VOICE NOTE (TTS ENGINE):
   Jika pengguna meminta kamu menjawab dengan suara / voice note (misal: "balas pake vn", "ngomong dong", "jelasin lewat vn", "kirim vn"):
   <<<ACTION:VOICE_NOTE|TARGET|TEKS_AUDIO>>>
   TARGET: "okta" atau "manda"
   TEKS_AUDIO: Teks murni percakapan santai yang akan dibacakan oleh mesin suara (DILARANG menggunakan simbol markdown tebal * atau _ atau bullet points di TEKS_AUDIO ini).
   Contoh:
   User: "bro bales pake vn dong jelasin uas manda"
   -> <<<ACTION:VOICE_NOTE|okta|Halo bro Okta, buat besok jadwal UAS Kak Manda ada dua matkul, yaitu Farmakoterapi jam satu siang dan Farmasi Industri jam tiga sore. Semangat ya bro!>>>"""

        image_and_tts_prompt_manda = """
5. PENCATATAN PENGELUARAN & EXPENSE TRACKER:
   <<<ACTION:EXPENSE_ADD|TARGET|AMOUNT|CATEGORY|MERCHANT|ITEMS>>>
   TARGET: "manda"

6. GENERASI GAMBAR & ILUSTRASI AI (FLUX.1):
   Jika pengguna meminta membuat gambar/ilustrasi (misal: "buatin gambar...", "bikinin ilustrasi..."):
   <<<ACTION:IMAGE_GEN|TARGET|ENHANCED_ENGLISH_PROMPT|CAPTION>>>
   TARGET: "manda" atau "okta"
   ENHANCED_ENGLISH_PROMPT: Detailed artistic English prompt for FLUX.1 model.
   CAPTION: Deskripsi singkat bahasa Indonesia.

7. BALAS DENGAN PESAN SUARA / VOICE NOTE (TTS ENGINE):
   Jika pengguna meminta menjawab dengan voice note ("balas pake vn", "kirim vn"):
   <<<ACTION:VOICE_NOTE|TARGET|TEKS_AUDIO>>>
   TARGET: "manda" atau "okta"
   TEKS_AUDIO: Teks murni percakapan tanpa markdown tebal/bullet points."""

        for node in nodes:
            name = node.get("name", "")
            if name == "[HTTP] Gemini Build Message":
                body = node.get("parameters", {}).get("jsonBody", "")
                if "ACTION:IMAGE_GEN" not in body:
                    # Append after PRESENSI
                    target_str = "5. PRESENSI KULIAH UB:\n   <<<ACTION:PRESENSI|hadir>>> -> jika Okta meminta absen (\"@n8n tolong absenkan kelas sekarang\")."
                    if target_str in body:
                        body = body.replace(target_str, image_and_tts_prompt_okta.strip())
                        node["parameters"]["jsonBody"] = body
                        print(f"Added IMAGE_GEN & VOICE_NOTE prompt to {name} in {fpath}")

            elif name == "[HTTP] Gemini Build Message1":
                body = node.get("parameters", {}).get("jsonBody", "")
                if "ACTION:IMAGE_GEN" not in body:
                    target_str = "5. PENCATATAN PENGELUARAN & EXPENSE TRACKER (DARI FOTO STRUK ATAU TEKS):"
                    if target_str in body:
                        # Append before Jawablah dengan
                        body = body.replace("Jawablah dengan manis,", image_and_tts_prompt_manda.strip() + "\n\nJawablah dengan manis,")
                        node["parameters"]["jsonBody"] = body
                        print(f"Added IMAGE_GEN & VOICE_NOTE prompt to {name} in {fpath}")

            # 2. Update Process AI Output & Actions and Process AI Output & Actions1
            if name in ["Process AI Output & Actions", "Process AI Output & Actions1"]:
                js = node.get("parameters", {}).get("jsCode", "")
                # Update regex to include IMAGE_GEN and VOICE_NOTE
                js = re.sub(
                    r'<<<ACTION:\(TUGAS\|JADWAL\|DONE\|DELETE\|EDIT\|RESCHEDULE\|NOTE_ADD\|NOTE_EDIT\|NOTE_DONE\|PRESENSI\|EXPENSE_ADD\)',
                    r'<<<ACTION:(IMAGE_GEN|VOICE_NOTE|TUGAS|JADWAL|DONE|DELETE|EDIT|RESCHEDULE|NOTE_ADD|NOTE_EDIT|NOTE_DONE|PRESENSI|EXPENSE_ADD)',
                    js
                )
                
                # Insert handlers for image_gen and voice_note if not present
                if "actionType === 'image_gen'" not in js:
                    handler_code = """  if (actionType === 'image_gen') {
    const target = (parts[0] || 'okta').toLowerCase();
    const prompt = parts[1] || '';
    const caption = parts.slice(2).join('|').trim() || prompt || 'Gambar AI';
    actions.push({
      actionType: 'image_gen',
      target,
      prompt,
      caption
    });
  } else if (actionType === 'voice_note') {
    const target = (parts[0] || 'okta').toLowerCase();
    const text = parts.slice(1).join('|').trim() || rawText.replace(/<<<ACTION:[A-Z_]+(?:\\|.*?)?>>>/gi, '').trim();
    actions.push({
      actionType: 'voice_note',
      target,
      text
    });
  } else if (actionType === 'expense_add') {"""
                    js = js.replace("  if (actionType === 'expense_add') {", handler_code)

                # Add flags
                if "hasImageGenActions" not in js:
                    js = js.replace(
                        "const hasExpenseActions = actions.some(a => a.actionType === 'expense_add');",
                        "const hasExpenseActions = actions.some(a => a.actionType === 'expense_add');\nconst hasImageGenActions = actions.some(a => a.actionType === 'image_gen');\nconst hasVoiceNoteActions = actions.some(a => a.actionType === 'voice_note');"
                    )
                    js = js.replace(
                        "    hasExpenseActions,",
                        "    hasExpenseActions,\n    hasImageGenActions,\n    hasVoiceNoteActions,"
                    )
                node["parameters"]["jsCode"] = js
                print(f"Updated action parsing in {name} in {fpath}")

            # 3. Update If Should Send Chat Reply (suppress text if voice note action)
            if name in ["If Should Send Chat Reply", "If Should Send Chat Reply Manda"]:
                conds = node.get("parameters", {}).get("conditions", {}).get("conditions", [])
                if len(conds) == 1 and conds[0].get("id", "").startswith("should-send-reply"):
                    conds[0]["leftValue"] = "={{ $json.hasCalendarActions || $json.hasVoiceNoteActions }}"
                    print(f"Updated suppression condition in {name} in {fpath}")

        # 4. Add Image Gen Nodes and Voice Note Nodes if not existing
        existing_names = {n.get("name") for n in nodes}

        if "If Has Image Actions" not in existing_names:
            if_img_node = {
                "parameters": {
                    "conditions": {
                        "options": {
                            "caseSensitive": True,
                            "leftValue": "",
                            "typeValidation": "strict",
                            "version": 3
                        },
                        "conditions": [
                            {
                                "id": "cond-img-action-01",
                                "leftValue": "={{ $json.hasImageGenActions }}",
                                "rightValue": "",
                                "operator": {
                                    "type": "boolean",
                                    "operation": "true",
                                    "singleValue": True
                                }
                            }
                        ],
                        "combinator": "and"
                    }
                },
                "type": "n8n-nodes-base.if",
                "typeVersion": 2.2,
                "position": [4720, 700],
                "id": "ifHasImageActions01",
                "name": "If Has Image Actions"
            }
            nodes.append(if_img_node)
            print(f"Added If Has Image Actions in {fpath}")

        if "[Code] Prepare Image Gen Payload" not in existing_names:
            code_img_node = {
                "parameters": {
                    "jsCode": """const parent = $input.first().json;
const wa = parent.wa || {};
const actions = parent.actions || [];
const imgActions = actions.filter(a => a.actionType === 'image_gen');
if (!imgActions || imgActions.length === 0) return [];

const items = [];
for (const act of imgActions) {
  const prompt = act.prompt || 'artistic illustration';
  const caption = act.caption || 'Gambar AI';
  const imageUrl = `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?model=flux&width=1024&height=1024&nologo=true`;

  items.push({
    json: {
      number: wa.remoteJid,
      mediatype: 'image',
      mimetype: 'image/jpeg',
      caption: `🎨 *Hasil Gambar AI (FLUX.1)*\\n\\n${caption}\\n\\n_Prompt: ${prompt}_`,
      media: imageUrl
    }
  });
}
return items;"""
                },
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [4960, 700],
                "id": "prepImagePayload01",
                "name": "[Code] Prepare Image Gen Payload"
            }
            nodes.append(code_img_node)
            print(f"Added [Code] Prepare Image Gen Payload in {fpath}")

        if "[HTTP] Send Generated Image" not in existing_names:
            http_img_node = {
                "parameters": {
                    "method": "POST",
                    "url": "http://evolution-api:8080/message/sendMedia/okta_wa",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "=httpHeaderAuth",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\n  \"number\": \"{{ $json.number }}\",\n  \"mediatype\": \"image\",\n  \"mimetype\": \"image/jpeg\",\n  \"caption\": {{ JSON.stringify($json.caption) }},\n  \"media\": \"{{ $json.media }}\"\n}",
                    "options": {}
                },
                "retryOnFail": True,
                "maxTries": 3,
                "waitBetweenTries": 2000,
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.4,
                "position": [5200, 700],
                "id": "httpSendGenImage01",
                "name": "[HTTP] Send Generated Image",
                "credentials": {
                    "httpHeaderAuth": {
                        "id": "GEmHpHffIDZKhtvn",
                        "name": "Header Auth account"
                    }
                }
            }
            nodes.append(http_img_node)
            print(f"Added [HTTP] Send Generated Image in {fpath}")

        if "If Has Voice Note Actions" not in existing_names:
            if_vn_node = {
                "parameters": {
                    "conditions": {
                        "options": {
                            "caseSensitive": True,
                            "leftValue": "",
                            "typeValidation": "strict",
                            "version": 3
                        },
                        "conditions": [
                            {
                                "id": "cond-vn-action-01",
                                "leftValue": "={{ $json.hasVoiceNoteActions }}",
                                "rightValue": "",
                                "operator": {
                                    "type": "boolean",
                                    "operation": "true",
                                    "singleValue": True
                                }
                            }
                        ],
                        "combinator": "and"
                    }
                },
                "type": "n8n-nodes-base.if",
                "typeVersion": 2.2,
                "position": [4720, 860],
                "id": "ifHasVoiceNoteActions01",
                "name": "If Has Voice Note Actions"
            }
            nodes.append(if_vn_node)
            print(f"Added If Has Voice Note Actions in {fpath}")

        if "[Code] Prepare Voice Note Command" not in existing_names:
            code_vn_node = {
                "parameters": {
                    "jsCode": """const parent = $input.first().json;
const wa = parent.wa || {};
const actions = parent.actions || [];
const vnActions = actions.filter(a => a.actionType === 'voice_note');
if (!vnActions || vnActions.length === 0) return [];

const items = [];
for (const act of vnActions) {
  let speechText = (act.text || '').replace(/[*_#`~]/g, '').replace(/\\n+/g, ' ').trim();
  if (!speechText) speechText = 'Halo, pesan suara berhasil diproses.';

  const isManda = act.target === 'manda' || wa.isManda;
  const voiceName = isManda ? 'id-ID-GadisNeural' : 'id-ID-ArdiNeural';

  const ts = Date.now();
  const tmpFile = `/tmp/wa_vn_${ts}.mp3`;
  const escaped = JSON.stringify(speechText);
  const cmd = `/home/dev/.local/bin/edge-tts --voice ${voiceName} --text ${escaped} --write-media ${tmpFile} && base64 -w 0 ${tmpFile} && rm -f ${tmpFile}`;

  items.push({
    json: {
      number: wa.remoteJid,
      speechText,
      cmd
    }
  });
}
return items;"""
                },
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [4960, 860],
                "id": "prepVnCommand01",
                "name": "[Code] Prepare Voice Note Command"
            }
            nodes.append(code_vn_node)
            print(f"Added [Code] Prepare Voice Note Command in {fpath}")

        if "[SSH] Synthesize WA Audio" not in existing_names:
            ssh_vn_node = {
                "parameters": {
                    "resource": "command",
                    "operation": "execute",
                    "authentication": "privateKey",
                    "command": "={{ $json.cmd }}"
                },
                "type": "n8n-nodes-base.ssh",
                "typeVersion": 1.1,
                "position": [5200, 860],
                "id": "sshSynthWaAudio01",
                "name": "[SSH] Synthesize WA Audio",
                "credentials": {
                    "sshPrivateKey": {
                        "id": "sshHostDev0001",
                        "name": "SSH Host Dev"
                    }
                }
            }
            nodes.append(ssh_vn_node)
            print(f"Added [SSH] Synthesize WA Audio in {fpath}")

        if "[HTTP] Send WA Voice Note" not in existing_names:
            http_vn_node = {
                "parameters": {
                    "method": "POST",
                    "url": "http://evolution-api:8080/message/sendWhatsAppAudio/okta_wa",
                    "authentication": "genericCredentialType",
                    "genericAuthType": "=httpHeaderAuth",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\n  \"number\": \"{{ $('[Code] Prepare Voice Note Command').item.json.number }}\",\n  \"audio\": \"{{ $json.stdout.trim() }}\",\n  \"delay\": 1200\n}",
                    "options": {}
                },
                "retryOnFail": True,
                "maxTries": 2,
                "waitBetweenTries": 1500,
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.4,
                "position": [5440, 860],
                "id": "httpSendWaAudio01",
                "name": "[HTTP] Send WA Voice Note",
                "credentials": {
                    "httpHeaderAuth": {
                        "id": "GEmHpHffIDZKhtvn",
                        "name": "Header Auth account"
                    }
                }
            }
            nodes.append(http_vn_node)
            print(f"Added [HTTP] Send WA Voice Note in {fpath}")

        # 5. Connect the nodes in connections
        conns = target.get("connections", {})

        # Connect Process AI Output & Actions to new If nodes
        for proc_node in ["Process AI Output & Actions", "Process AI Output & Actions1"]:
            if proc_node in conns:
                proc_targets = conns[proc_node]["main"][0]
                if not any(t.get("node") == "If Has Image Actions" for t in proc_targets):
                    proc_targets.append({"node": "If Has Image Actions", "type": "main", "index": 0})
                if not any(t.get("node") == "If Has Voice Note Actions" for t in proc_targets):
                    proc_targets.append({"node": "If Has Voice Note Actions", "type": "main", "index": 0})

        # Image chain: If Has Image Actions -> Prepare -> Send
        conns["If Has Image Actions"] = {
            "main": [
                [{"node": "[Code] Prepare Image Gen Payload", "type": "main", "index": 0}],
                []
            ]
        }
        conns["[Code] Prepare Image Gen Payload"] = {
            "main": [
                [{"node": "[HTTP] Send Generated Image", "type": "main", "index": 0}]
            ]
        }

        # Voice Note chain: If Has Voice Note Actions -> Prepare -> SSH -> Send
        conns["If Has Voice Note Actions"] = {
            "main": [
                [{"node": "[Code] Prepare Voice Note Command", "type": "main", "index": 0}],
                []
            ]
        }
        conns["[Code] Prepare Voice Note Command"] = {
            "main": [
                [{"node": "[SSH] Synthesize WA Audio", "type": "main", "index": 0}]
            ]
        }
        conns["[SSH] Synthesize WA Audio"] = {
            "main": [
                [{"node": "[HTTP] Send WA Voice Note", "type": "main", "index": 0}]
            ]
        }

        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully wrote updates to {fpath}")

update_morning_briefing()
update_wa_conversation()
