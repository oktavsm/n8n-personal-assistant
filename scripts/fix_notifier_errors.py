import json
from pathlib import Path

repo_root = Path('/home/oktaavsm/Code/github.com/n8n-personal-assistant')

for base_dir in [repo_root / 'workflow', repo_root / 'n8n' / 'workflow']:
    # 1. automatic-brone-task-notifier.json
    brone_path = base_dir / 'automatic-brone-task-notifier.json'
    with open(brone_path) as f:
        data = json.load(f)
    wf = data[0] if isinstance(data, list) else data
    for node in wf['nodes']:
        if node['name'] == '[HTTP Whatsapp]6':
            for p in node['parameters']['bodyParameters']['parameters']:
                if p['name'] == 'text':
                    p['value'] = '={{ $json.message }}'
        elif node['name'] == '[HTTP] Gemini Build Message':
            node['onError'] = 'continueRegularOutput'
            node['retryOnFail'] = True
            node['maxTries'] = 3
            node['waitBetweenTries'] = 3000
        elif node['name'] == 'Code in JavaScript':
            node['parameters']['jsCode'] = """const items = $input.all();

const messages = items.map(item => {
  return item.json.candidates?.[0]?.content?.parts?.[0]?.text || item.json.message || "";
}).filter(msg => msg.trim() !== "");

if (messages.length === 0) {
  try {
    const rawEvents = $('Split Out').all();
    if (rawEvents.length > 0) {
      const fallbackList = rawEvents.map(e => {
        const j = e.json;
        return `🚨 *DEADLINE TUGAS: ${j.coursefullname || j.coursename || '-'}*\\n📚 *Tugas:* ${j.name || '-'}\\n⏰ *Batas Waktu:* ${j.formattedtime || '-'}\\n🔗 ${j.action?.url || j.url || '-'}`;
      }).join("\\n\\n━━━━━━━━━━━━━━\\n\\n");
      return [{
        json: {
          message: `📢 *Reminder Tugas Brone!*\\n\\n${fallbackList}`,
          mode: "combined"
        }
      }];
    }
  } catch (e) {}

  return [
    {
      json: {
        message: "🎉 Nggak ada tugas Brone yang aktif coi! Santai dulu aja 😴"
      }
    }
  ];
}

const combined = messages.join("\\n\\n━━━━━━━━━━━━━━\\n\\n");
return [
  {
    json: {
      message: combined,
      mode: "combined"
    }
  }
];"""
    with open(brone_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('Enhanced & saved:', brone_path)

    # 2. siam-announcement-notifier.json
    siam_ann_path = base_dir / 'siam-announcement-notifier.json'
    with open(siam_ann_path) as f:
        data = json.load(f)
    wf = data[0] if isinstance(data, list) else data
    for node in wf['nodes']:
        if node['name'] == '[HTTP Whatsapp]6':
            for p in node['parameters']['bodyParameters']['parameters']:
                if p['name'] == 'text':
                    p['value'] = '={{ $json.text }}'
    with open(siam_ann_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('Enhanced & saved:', siam_ann_path)

    # 3. siam-presensi-notifier.json
    siam_pres_path = base_dir / 'siam-presensi-notifier.json'
    with open(siam_pres_path) as f:
        data = json.load(f)
    wf = data[0] if isinstance(data, list) else data
    for node in wf['nodes']:
        if node['name'] == '[HTTP Whatsapp]6':
            for p in node['parameters']['bodyParameters']['parameters']:
                if p['name'] == 'text':
                    p['value'] = '={{ $json.text }}'
        elif node['name'] == '[WA] Grup1':
            for p in node['parameters']['bodyParameters']['parameters']:
                if p['name'] == '=number':
                    p['name'] = 'number'
        elif node['name'] == 'cek cmd':
            for cond in node['parameters']['conditions']['conditions']:
                if cond.get('id') == 'cond-cmd-text':
                    old_v = cond.get('leftValue', '')
                    cond['leftValue'] = old_v.replace('(.body', '($json.body').replace('|| .body', '|| $json.body')
    with open(siam_pres_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('Enhanced & saved:', siam_pres_path)

    # 4. automatic-email-notifier-workflow.json
    email_path = base_dir / 'automatic-email-notifier-workflow.json'
    with open(email_path) as f:
        data = json.load(f)
    wf = data[0] if isinstance(data, list) else data
    for node in wf['nodes']:
        if node['name'] == 'Code in JavaScript':
            node['parameters']['jsCode'] = """const envKeys = $env.GEMINI_API_KEY || '';
const apiKeys = envKeys.split(',').map(k => k.trim()).filter(Boolean);

for (const item of $input.all()) {
  const randomKey = apiKeys.length > 0 
    ? apiKeys[Math.floor(Math.random() * apiKeys.length)] 
    : '';
  item.json.selected_key = randomKey;
}

return $input.all();"""
        elif node['name'] == '[HTTP] Gemini Email':
            node['onError'] = 'continueRegularOutput'
            node['retryOnFail'] = True
            node['maxTries'] = 3
            node['waitBetweenTries'] = 3000
            node['parameters']['options']['timeout'] = 60000
            if 'ISI: ${$json.textPlain}' in node['parameters']['jsonBody']:
                node['parameters']['jsonBody'] = node['parameters']['jsonBody'].replace(
                    'ISI: ${$json.textPlain}',
                    'ISI: ${($json.textPlain || "").slice(0, 5000)}'
                )
        elif node['name'] == '[HTTP Whatsapp]':
            node['parameters']['options']['timeout'] = 60000
            for p in node['parameters']['bodyParameters']['parameters']:
                if p['name'] == 'text':
                    p['value'] = """={{ $json.candidates?.[0]?.content?.parts?.[0]?.text || ('📧 *ADA EMAIL BARU!*\\n📌 *PENGIRIM:* ' + ($('Email Trigger (IMAP)').item.json.from || '-') + '\\n📝 *SUBJEK:* ' + ($('Email Trigger (IMAP)').item.json.subject || '-') + '\\n\\n' + (($('Email Trigger (IMAP)').item.json.textPlain || '').slice(0, 300)) + '...') }}"""
        elif node['name'] == 'Discord':
            node['parameters']['content'] = """={{ $json.candidates?.[0]?.content?.parts?.[0]?.text || ('📧 **ADA EMAIL BARU!**\\n**PENGIRIM:** ' + ($('Email Trigger (IMAP)').item.json.from || '-') + '\\n**SUBJEK:** ' + ($('Email Trigger (IMAP)').item.json.subject || '-')) }}"""
    with open(email_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')
    print('Enhanced & saved:', email_path)
