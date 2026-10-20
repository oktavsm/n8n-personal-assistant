import json

# 1. Update master-router-webhook.json
path_mr = 'workflow/master-router-webhook.json'
with open(path_mr) as f:
    data_mr = json.load(f)

wf_mr = data_mr[0] if isinstance(data_mr, list) else data_mr

for n in wf_mr['nodes']:
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

        # Rule 21: vps_agent
        rules[21]['conditions']['conditions'][0]['leftValue'] = '''={{ (() => {
  const data = $json.body?.data || {};
  const msg = data.message || {};
  const raw = (msg.conversation || msg.extendedTextMessage?.text || "").trim();
  const cleaned = raw.replace(/@[a-zA-Z0-9_\\-\\.]+\\s*/g, "").trim();
  const lower = cleaned.toLowerCase();
  const jid = data.key?.remoteJid || "";
  const part = data.key?.participant || data.key?.participantAlt || "";
  const fromMe = Boolean(data.key?.fromMe);

  // Authorize: fromMe (Okta account) or Okta phone number or Okta LID
  const isOkta = fromMe ||
                 jid.includes($env.MY_WA_NUMBER) ||
                 part.includes($env.MY_WA_NUMBER) ||
                 part.includes("158613192614132");

  const isGroup = jid.endsWith("@g.us");
  const allowedGroups = ($env.ALLOWED_AGENT_GROUPS || "").split(",").map(s => s.trim()).filter(Boolean);
  const knownGroups = [
    "120363415512376146@g.us", // [General] Okta & Manda
    "120363426033987537@g.us", // WA_GROUP_SHARED
    "120363336434287340@g.us", // WA_GROUP_DEV
    "120363413257057355@g.us", // WA_GROUP_NOTIF
    $env.WA_GROUP_DEV,
    $env.WA_GROUP_SHARED,
    $env.WA_GROUP_NOTIF
  ].filter(Boolean);

  const isAllowedChat = !isGroup ||
                        allowedGroups.length === 0 ||
                        allowedGroups.some(g => jid.includes(g) || g.includes(jid)) ||
                        knownGroups.some(g => jid.includes(g) || g.includes(jid));

  return Boolean(isOkta && isAllowedChat && (lower.startsWith("/vps") || lower.startsWith("/agent")));
})() }}'''

with open(path_mr, 'w') as f:
    json.dump([wf_mr] if isinstance(data_mr, list) else wf_mr, f, indent=2)

print('Updated master-router-webhook.json successfully')

# 2. Update vps-cli-runner.json
path_vps = 'workflow/vps-cli-runner.json'
with open(path_vps) as f:
    data_vps = json.load(f)

wf_vps = data_vps[0] if isinstance(data_vps, list) else data_vps

for n in wf_vps['nodes']:
    if n['name'] == 'Normalize & Extract Task':
        n['parameters']['jsCode'] = '''const item = $input.first().json;
const data = item.body?.data || item.data || item;
const msg = data.message || {};
const remoteJid = data.key?.remoteJid || '';
const participant = data.key?.participant || data.key?.participantAlt || remoteJid;
const messageId = data.key?.id || '';

const rawText = (msg.conversation || msg.extendedTextMessage?.text || '').trim();
// Strip any mention tags (@n8n, @bot, @158613192614132, etc.)
const cleanedText = rawText.replace(/@[a-zA-Z0-9_\\-\\.]+\\s*/g, '').trim();
const prompt = cleanedText.replace(/^(\\/vps|\\/agent)\\s*/i, '').trim();

return [{
  json: {
    remoteJid,
    participant,
    messageId,
    rawText,
    prompt: prompt || 'Cek status VPS, disk, dan container docker secara ringkas'
  }
}];'''

with open(path_vps, 'w') as f:
    json.dump([wf_vps] if isinstance(data_vps, list) else wf_vps, f, indent=2)

print('Updated vps-cli-runner.json successfully')

# 3. Update wa-conversation.json
path_wac = 'workflow/wa-conversation.json'
with open(path_wac) as f:
    data_wac = json.load(f)

wf_wac = data_wac[0] if isinstance(data_wac, list) else data_wac

for n in wf_wac['nodes']:
    if n['name'] == 'Normalize WA Context':
        code = n['parameters']['jsCode']
        
        # Replace mention stripping in cleanText
        code = code.replace(
            'const cleanText = currentText\n  .replace(/@171619058196619/g, "")\n  .replace(/@195095164887244/g, "")\n  .replace(/@158613192614132/g, "")\n  .replace(/@6283130151476/g, "")\n  .replace(/^\\/ask/i, "")\n  .replace(/^\\/stiker/i, "")\n  .replace(/^\\/sticker/i, "")\n  .trim();',
            'const cleanText = currentText\n  .replace(/@[a-zA-Z0-9_\\-\\.]+\\s*/g, "")\n  .replace(/^\\/ask/i, "")\n  .replace(/^\\/stiker/i, "")\n  .replace(/^\\/sticker/i, "")\n  .trim();'
        )
        
        # Replace isMentionBot logic
        code = code.replace(
            '''const isMentionBot =
  botLids.some(b => currentText.includes("@" + b)) ||
  mentionedJid.some(j => botLids.some(b => j.includes(b)));''',
            '''const isMentionBot =
  botLids.some(b => b && currentText.includes("@" + b)) ||
  mentionedJid.some(j => botLids.some(b => b && j.includes(b))) ||
  textLower.includes("@n8n") ||
  textLower.includes("@bot") ||
  isNoteCmd ||
  isDoneCmd;'''
        )
        
        # Replace isOkta logic
        code = code.replace(
            'const isOkta = remoteJid.includes($env.MY_WA_NUMBER) || participant.includes($env.MY_WA_NUMBER);',
            'const isOkta = Boolean(data.key?.fromMe) || remoteJid.includes($env.MY_WA_NUMBER) || participant.includes($env.MY_WA_NUMBER) || participant.includes("158613192614132");'
        )

        n['parameters']['jsCode'] = code

with open(path_wac, 'w') as f:
    json.dump([wf_wac] if isinstance(data_wac, list) else wf_wac, f, indent=2)

print('Updated wa-conversation.json successfully')
