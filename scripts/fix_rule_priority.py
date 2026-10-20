import json

path = 'workflow/master-router-webhook.json'
with open(path) as f:
    data = json.load(f)

wf = data[0] if isinstance(data, list) else data

for n in wf['nodes']:
    if n['name'] == 'Switch':
        rules = n['parameters']['rules']['values']
        
        # Rule 17: ask / mention / group conversation
        rules[17]['conditions']['conditions'][0]['leftValue'] = '''={{ (() => {
  const data = $json.body?.data || {};
  const msg = data.message || {};
  const raw = (msg.conversation || msg.extendedTextMessage?.text || "").trim();
  const cleaned = raw.replace(/@[a-zA-Z0-9_\\-\\.]+\\s*/g, "").trim().toLowerCase();
  const jid = data.key?.remoteJid || "";
  const ctx = msg.extendedTextMessage?.contextInfo || {};
  const mentionedJid = ctx.mentionedJid || [];
  const botNumbers = ["171619058196619", "195095164887244", "158613192614132", "6283130151476", $env.MY_WA_NUMBER];

  // If this is an agent or vps command, do NOT consume it here; let Rule 21 handle it
  if (cleaned.startsWith("/agent") || cleaned.startsWith("/vps")) {
    return false;
  }

  // If this is a presensi command, do NOT consume it here; let Rule 8 handle it
  if (cleaned.startsWith("/presensi") || ["hadir", "absen"].includes(cleaned)) {
    return false;
  }

  const isAsk = cleaned.startsWith("/ask");
  const isMention = botNumbers.some(b => b && raw.includes("@" + b)) ||
                    mentionedJid.some(j => botNumbers.some(b => b && j.includes(b))) ||
                    raw.toLowerCase().includes("@n8n") ||
                    raw.toLowerCase().includes("@bot");
  const isNoteCmd = cleaned.startsWith("/catat") || cleaned.startsWith("/notes") || cleaned.startsWith("/catatan");
  const isDoneCmd = cleaned.startsWith("/done") || cleaned.startsWith("/selesai") || cleaned.startsWith("/hapus-jadwal");
  const isExpenseCmd = cleaned.startsWith("/expense") || cleaned.startsWith("/pengeluaran");

  return Boolean(isAsk || isMention || isNoteCmd || isDoneCmd || isExpenseCmd);
})() }}'''

with open(path, 'w') as f:
    json.dump([wf] if isinstance(data, list) else wf, f, indent=2)

print('Updated Rule 17 priority in master-router-webhook.json successfully!')
