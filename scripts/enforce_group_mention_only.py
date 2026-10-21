#!/usr/bin/env python3
import json
from pathlib import Path

def update_master_router(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"Skipping {file_path} (not found)")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_obj = data[0] if isinstance(data, list) else data

    # 1. Add Gate node if not exists
    gate_node_id = "gate-group-mention-01"
    gate_node_name = "Gate: Check Group Mention"
    
    gate_js_code = """const body = $input.first().json.body || {};
const data = body.data || {};
const key = data.key || {};
const remoteJid = key.remoteJid || "";
const isGroup = remoteJid.endsWith("@g.us");

// 1. Ignore messages sent by bot itself
if (key.fromMe) {
  return [];
}

// 2. If in a WhatsApp group, ONLY process if bot is explicitly tagged/mentioned!
if (isGroup) {
  const msg = data.message || {};
  const rawText = (
    msg.conversation ||
    msg.extendedTextMessage?.text ||
    msg.imageMessage?.caption ||
    msg.videoMessage?.caption ||
    msg.documentMessage?.caption ||
    ""
  ).trim();

  const ctx = data.contextInfo ||
    msg.extendedTextMessage?.contextInfo ||
    msg.imageMessage?.contextInfo ||
    msg.videoMessage?.contextInfo ||
    msg.documentMessage?.contextInfo ||
    msg.audioMessage?.contextInfo ||
    {};

  const mentionedJid = ctx.mentionedJid || [];
  const botIdentifiers = ["171619058196619", "195095164887244", "6283130151476"];

  const isMention =
    botIdentifiers.some(id => rawText.includes("@" + id)) ||
    mentionedJid.some(jid => botIdentifiers.some(id => jid.includes(id))) ||
    rawText.toLowerCase().includes("@n8n") ||
    rawText.toLowerCase().includes("@bot");

  if (!isMention) {
    // Drop group message! Not tagged to bot.
    return [];
  }
}

// Private chat or tagged group message -> proceed
return $input.all();"""

    # Check if gate node already exists
    nodes = target_obj.get("nodes", [])
    existing_gate = next((n for n in nodes if n.get("name") == gate_node_name), None)
    if not existing_gate:
        gate_node = {
            "parameters": {
                "jsCode": gate_js_code
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [0, 80],
            "id": gate_node_id,
            "name": gate_node_name
        }
        nodes.append(gate_node)
        print(f"Added {gate_node_name} to {file_path}")
    else:
        existing_gate["parameters"]["jsCode"] = gate_js_code
        print(f"Updated {gate_node_name} code in {file_path}")

    # Rewire connections: Webhook -> Gate -> Switch
    conns = target_obj.get("connections", {})
    conns["Webhook"] = {
        "main": [
            [
                {
                    "node": gate_node_name,
                    "type": "main",
                    "index": 0
                }
            ]
        ]
    }
    conns[gate_node_name] = {
        "main": [
            [
                {
                    "node": "Switch",
                    "type": "main",
                    "index": 0
                }
            ]
        ]
    }

    # 2. Update Switch Rule 18 (ask) to clean botNumbers and remove Okta's LID/number
    for node in nodes:
        if node.get("name") == "Switch":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            for r in rules:
                if r.get("outputKey") == "ask":
                    c = r["conditions"]["conditions"][0]
                    # Update Rule 18 leftValue code
                    c["leftValue"] = """={{ (() => {
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
  const botNumbers = ["171619058196619", "195095164887244", "6283130151476"];

  // 1. Explicit commands handled by other switch rules: DO NOT consume here!
  const explicitCommands = [
    "/agenda", "/besok", "/tugas", "/jadwal", "/cek", "/uas",
    "/done", "/selesai", "/hapus", "/edit-kuliah", "/edit kuliah", "/edit", "/reschedule", "/delete",
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

  // 3. Mentions in group
  const isMention = botNumbers.some(b => b && raw.includes("@" + b)) ||
                    mentionedJid.some(j => botNumbers.some(b => b && j.includes(b))) ||
                    raw.toLowerCase().includes("@n8n") ||
                    raw.toLowerCase().includes("@bot");

  // In a group, ONLY respond if mentioned!
  if (isGroup) {
    return isMention;
  }

  // Private chat triggers
  const isAsk = cleaned.startsWith("/ask");
  const isNoteCmd = cleaned.startsWith("/catat") || cleaned.startsWith("/notes") || cleaned.startsWith("/catatan");
  const isExpenseCmd = cleaned.startsWith("/expense") || cleaned.startsWith("/pengeluaran");

  return Boolean(isAsk || isMention || isNoteCmd || isExpenseCmd);
})() }}"""
                    print(f"Updated Switch Rule 18 (ask) in {file_path}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Successfully wrote updates to {file_path}")

def update_wa_conversation(file_path):
    path = Path(file_path)
    if not path.exists():
        print(f"Skipping {file_path} (not found)")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    target_obj = data[0] if isinstance(data, list) else data
    nodes = target_obj.get("nodes", [])

    # 1. Update Normalize WA Context
    for node in nodes:
        if node.get("name") == "Normalize WA Context":
            code = node.get("parameters", {}).get("jsCode", "")
            # Replace botLids definition
            old_botlids = 'const botLids = ["171619058196619", "195095164887244", "158613192614132", "6283130151476", "${$env.MY_WA_NUMBER}"];'
            new_botlids = 'const botLids = ["171619058196619", "195095164887244", "6283130151476"];'
            
            old_ismention = """const isMentionBot =
  botLids.some(b => b && currentText.includes("@" + b)) ||
  mentionedJid.some(j => botLids.some(b => b && j.includes(b))) ||
  textLower.includes("@n8n") ||
  textLower.includes("@bot") ||
  isNoteCmd ||
  isDoneCmd;"""

            new_ismention = """const isMentionBot =
  botLids.some(b => b && currentText.includes("@" + b)) ||
  mentionedJid.some(j => botLids.some(b => b && j.includes(b))) ||
  textLower.includes("@n8n") ||
  textLower.includes("@bot");"""

            if old_botlids in code:
                code = code.replace(old_botlids, new_botlids)
            else:
                # Try generic replace
                import re
                code = re.sub(r'const botLids = \[.*?\];', new_botlids, code)

            if old_ismention in code:
                code = code.replace(old_ismention, new_ismention)

            node["parameters"]["jsCode"] = code
            print(f"Updated Normalize WA Context in {file_path}")

        # 2. Update Switch Rule 2: ada chat - grup
        if node.get("name") == "Switch":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            for r in rules:
                if r.get("outputKey") == "ada chat - grup":
                    c = r["conditions"]["conditions"][0]
                    # Must strictly be isMentionBot in group!
                    c["leftValue"] = "={{ $('Normalize WA Context').item.json.wa.isMentionBot && (!!$('Normalize WA Context').item.json.wa.cleanText || $('Normalize WA Context').item.json.wa.hasAudio || $('Normalize WA Context').item.json.wa.hasImage) }}"
                    print(f"Updated Switch Rule 'ada chat - grup' in {file_path}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Successfully wrote updates to {file_path}")

# Run updates
update_master_router("workflow/master-router-webhook.json")
update_master_router("n8n/workflow/master-router-webhook.json")
update_wa_conversation("workflow/wa-conversation.json")
update_wa_conversation("n8n/workflow/wa-conversation.json")
