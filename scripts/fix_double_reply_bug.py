#!/usr/bin/env python3
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# 1. Update master-router-webhook.json
mr_paths = [
    REPO_ROOT / "workflow" / "master-router-webhook.json",
    REPO_ROOT / "n8n" / "workflow" / "master-router-webhook.json"
]

for p in mr_paths:
    if not p.exists():
        continue
    with open(p, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    # A. In connections: remove 'mentioned' from Webhook output, and remove 'mentioned' source
    if "Webhook" in data.get("connections", {}):
        webhook_main = data["connections"]["Webhook"].get("main", [])
        if webhook_main and len(webhook_main) > 0:
            # Filter out any connection to 'mentioned'
            new_targets = [t for t in webhook_main[0] if t.get("node") != "mentioned"]
            data["connections"]["Webhook"]["main"] = [new_targets]
            print(f"[{p.name}] Webhook connections updated: {new_targets}")

    if "mentioned" in data.get("connections", {}):
        del data["connections"]["mentioned"]
        print(f"[{p.name}] Removed 'mentioned' from connections")

    # B. In nodes: remove node 'mentioned'
    nodes_before = len(data.get("nodes", []))
    data["nodes"] = [n for n in data.get("nodes", []) if n.get("name") != "mentioned"]
    nodes_after = len(data["nodes"])
    print(f"[{p.name}] Nodes count: {nodes_before} -> {nodes_after}")

    # C. Update Switch Rule 17 (ask)
    for node in data.get("nodes", []):
        if node.get("name") == "Switch":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            if len(rules) > 17:
                rule_17_code = """={{ (() => {
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
    "/brone", "/pengumuman", "/presensi", "/help", "/stiker", "/sticker",
    "/agent", "/vps"
  ];
  if (explicitCommands.some(cmd => cleaned.startsWith(cmd))) {
    return false;
  }
  if (["hadir", "absen", "absen hadir", "hadir daring", "hadir online"].includes(cleaned)) {
    return false;
  }

  // 2. Ask command
  const isAsk = cleaned.startsWith("/ask");

  // 3. Mentions in group
  const isMention = botNumbers.some(b => b && raw.includes("@" + b)) ||
                    mentionedJid.some(j => botNumbers.some(b => b && j.includes(b))) ||
                    raw.toLowerCase().includes("@n8n") ||
                    raw.toLowerCase().includes("@bot");

  // 4. Swipe / Quoted reply to bot in group
  const quotedParticipant = ctx.participant || ctx.quotedMessageSender || "";
  const isReplyingToBot = isGroup && botNumbers.some(b => b && quotedParticipant.includes(b));

  // 5. Notes, Done, Expense commands
  const isNoteCmd = cleaned.startsWith("/catat") || cleaned.startsWith("/notes") || cleaned.startsWith("/catatan");
  const isDoneCmd = cleaned.startsWith("/done") || cleaned.startsWith("/selesai") || cleaned.startsWith("/hapus-jadwal");
  const isExpenseCmd = cleaned.startsWith("/expense") || cleaned.startsWith("/pengeluaran");

  // 6. Voice note in dev group
  const isDevGroup = jid === ($env.WA_GROUP_DEV || "120363336434287340@g.us");
  const hasAudio = Boolean(msg.audioMessage || ctx.quotedMessage?.audioMessage);
  const isDevAudio = Boolean(isDevGroup && hasAudio);

  return Boolean(isAsk || isMention || isReplyingToBot || isNoteCmd || isDoneCmd || isExpenseCmd || isDevAudio);
})() }}"""
                rules[17]["conditions"]["conditions"][0]["leftValue"] = rule_17_code
                print(f"[{p.name}] Updated Switch Rule 17 (ask)")

    with open(p, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Saved {p}")

# 2. Update wa-conversation.json (Switch1 Rule 2)
wac_paths = [
    REPO_ROOT / "workflow" / "wa-conversation.json",
    REPO_ROOT / "n8n" / "workflow" / "wa-conversation.json"
]

for p in wac_paths:
    if not p.exists():
        continue
    with open(p, "r", encoding="utf-8") as f:
        wf = json.load(f)
    is_list = isinstance(wf, list)
    data = wf[0] if is_list else wf

    for node in data.get("nodes", []):
        if node.get("name") == "Switch1":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            if len(rules) >= 3:
                # Rule 2: Bukan Manda
                rules[2]["conditions"]["conditions"][0]["leftValue"] = "={{ !$('Normalize WA Context').item.json.wa.isManda }}"
                print(f"[{p.name}] Updated Switch1 Rule 2 (bukan manda)")

        if node.get("name") == "Switch Vision Query":
            rules = node.get("parameters", {}).get("rules", {}).get("values", [])
            if len(rules) >= 6:
                # Rule 5: None catch-all
                rules[5]["conditions"]["conditions"][0]["leftValue"] = (
                    "={{ !$('Normalize WA Context').item.json.wa.isScheduleQuery && "
                    "!$('Normalize WA Context').item.json.wa.isAnnouncementQuery && "
                    "!$('Normalize WA Context').item.json.wa.isPresensiQuery && "
                    "!$('Normalize WA Context').item.json.wa.isNotesQuery && "
                    "!$('Normalize WA Context').item.json.wa.isExpenseQuery }}"
                )
                print(f"[{p.name}] Updated Switch Vision Query Rule 5 (none)")

    with open(p, "w", encoding="utf-8") as f:
        json.dump([data] if is_list else data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"✅ Saved {p}")

print("\n🚀 All double-reply bugfixes applied successfully!")
