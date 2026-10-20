import json
import uuid

def generate_id():
    return str(uuid.uuid4())

path = 'workflow/wa-conversation.json'
with open(path) as f:
    data = json.load(f)

wf = data[0] if isinstance(data, list) else data

# 1. Update Normalize WA Context
for n in wf['nodes']:
    if n['name'] == 'Normalize WA Context':
        code = n['parameters']['jsCode']
        
        # Add isExpenseQuery and isExpenseCmd
        if 'isExpenseQuery' not in code:
            old_kw = 'const isNoteCmd = textLower.startsWith("/catat") || textLower.startsWith("/notes") || textLower.startsWith("/catatan");'
            new_kw = '''const isNoteCmd = textLower.startsWith("/catat") || textLower.startsWith("/notes") || textLower.startsWith("/catatan");
const isExpenseCmd = textLower.startsWith("/expense") || textLower.startsWith("/pengeluaran");
const isExpenseQuery = Boolean(/expense|pengeluaran|biaya|struk|nota|belanja|jajan/i.test(currentText) || isExpenseCmd);'''
            code = code.replace(old_kw, new_kw)
            
            # Update return wa object
            code = code.replace(
                'isNoteCmd,',
                'isNoteCmd,\n        isExpenseCmd,\n        isExpenseQuery,'
            )
        
        n['parameters']['jsCode'] = code

# 2. Add rule for expense in Switch Vision Query
for n in wf['nodes']:
    if n['name'] == 'Switch Vision Query':
        rules = n['parameters']['rules']['values']
        # Check if expense rule already exists
        if not any(r.get('outputKey') == 'expense' for r in rules):
            expense_rule = {
                'conditions': {
                    'options': {
                        'caseSensitive': True,
                        'leftValue': '',
                        'typeValidation': 'loose',
                        'version': 3
                    },
                    'conditions': [
                        {
                            'id': generate_id(),
                            'leftValue': "={{ $('Normalize WA Context').item.json.wa.isExpenseQuery }}",
                            'rightValue': '',
                            'operator': {
                                'type': 'boolean',
                                'operation': 'true',
                                'singleValue': True
                            }
                        }
                    ],
                    'combinator': 'and'
                },
                'renameOutput': True,
                'outputKey': 'expense'
            }
            # Insert at index 4 (before none)
            rules.insert(4, expense_rule)

# 3. Create nodes: [PG] Fetch Recent Expenses & Format Expense Vision
fetch_expenses_node = {
    'parameters': {
        'operation': 'executeQuery',
        'query': "SELECT id, user_name, amount, category, merchant, items_detail, created_at FROM user_expenses WHERE created_at >= NOW() - INTERVAL '30 days' ORDER BY created_at DESC LIMIT 25;"
    },
    'type': 'n8n-nodes-base.postgres',
    'typeVersion': 2.5,
    'position': [
        80,
        380
    ],
    'id': 'pgFetchExpenses0001',
    'name': '[PG] Fetch Recent Expenses',
    'credentials': {
        'postgres': {
            'id': 'pgChatMemory0001',
            'name': 'Postgres Chat Memory'
        }
    }
}

format_expense_vision_node = {
    'parameters': {
        'jsCode': '''const rows = $input.all().map(i => i.json).filter(r => r && r.id);
const oktaExpenses = rows.filter(r => r.user_name === 'okta');
const mandaExpenses = rows.filter(r => r.user_name === 'manda');

function calcTotal(list) {
  return list.reduce((acc, cur) => acc + (parseFloat(cur.amount) || 0), 0);
}

const totalOkta = calcTotal(oktaExpenses);
const totalManda = calcTotal(mandaExpenses);

let txt = "🧾 DATA PENGELUARAN KEUANGAN 30 HARI TERAKHIR (DATABASE):\\n";
txt += `\\n• Total Pengeluaran Okta: Rp ${totalOkta.toLocaleString('id-ID')}\\n`;
if (oktaExpenses.length === 0) {
  txt += "  (Belum ada riwayat pengeluaran tercatat)\\n";
} else {
  oktaExpenses.slice(0, 10).forEach((e, idx) => {
    const d = new Date(e.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
    txt += `  ${idx + 1}. [${d}] Rp ${(parseFloat(e.amount)||0).toLocaleString('id-ID')} - ${e.merchant || 'Umum'} (${e.category || 'makan'}): ${e.items_detail || '-'}\\n`;
  });
}

txt += `\\n• Total Pengeluaran Kak Manda: Rp ${totalManda.toLocaleString('id-ID')}\\n`;
if (mandaExpenses.length === 0) {
  txt += "  (Belum ada riwayat pengeluaran tercatat)\\n";
} else {
  mandaExpenses.slice(0, 10).forEach((e, idx) => {
    const d = new Date(e.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' });
    txt += `  ${idx + 1}. [${d}] Rp ${(parseFloat(e.amount)||0).toLocaleString('id-ID')} - ${e.merchant || 'Umum'} (${e.category || 'makan'}): ${e.items_detail || '-'}\\n`;
  });
}

let prev = {};
try { prev = $('Format Memory Context').item.json; } catch (e) {}

return [{
  json: {
    ...prev,
    visionContext: txt
  }
}];'''
    },
    'type': 'n8n-nodes-base.code',
    'typeVersion': 2,
    'position': [
        280,
        380
    ],
    'id': 'formatExpenseVision01',
    'name': 'Format Expense Vision'
}

# 4. Create [PG] Execute Expense Action & If Has Expense Actions
execute_expense_node = {
    'parameters': {
        'operation': 'executeQuery',
        'query': '''={{ (() => {
  const actions = $json.actions || [];
  const expActions = actions.filter(a => a.actionType === 'expense_add');
  if (expActions.length === 0) return "SELECT 1;";
  
  const queries = [];
  for (const act of expActions) {
    const user = act.target === 'manda' ? 'manda' : 'okta';
    const amount = parseFloat(act.amount) || 0;
    const category = (act.category || 'makan').replace(/'/g, "''");
    const merchant = (act.merchant || 'Umum').replace(/'/g, "''");
    const items = (act.itemsDetail || act.detail || '').replace(/'/g, "''");
    queries.push(`INSERT INTO user_expenses (user_name, amount, category, merchant, items_detail) VALUES ('${user}', ${amount}, '${category}', '${merchant}', '${items}');`);
  }
  return queries.length > 0 ? queries.join('\\n') : "SELECT 1;";
})() }}'''
    },
    'type': 'n8n-nodes-base.postgres',
    'typeVersion': 2.5,
    'position': [
        2580,
        640
    ],
    'id': 'pgExecuteExpenseAction01',
    'name': '[PG] Execute Expense Action',
    'credentials': {
        'postgres': {
            'id': 'pgChatMemory0001',
            'name': 'Postgres Chat Memory'
        }
    }
}

if_has_expense_node = {
    'parameters': {
        'conditions': {
            'options': {
                'caseSensitive': True,
                'leftValue': '',
                'typeValidation': 'loose',
                'version': 3
            },
            'conditions': [
                {
                    'id': generate_id(),
                    'leftValue': '={{ $json.hasExpenseActions }}',
                    'rightValue': '',
                    'operator': {
                        'type': 'boolean',
                        'operation': 'true',
                        'singleValue': True
                    }
                }
            ],
            'combinator': 'and'
        }
    },
    'type': 'n8n-nodes-base.if',
    'typeVersion': 2.3,
    'position': [
        2380,
        640
    ],
    'id': 'ifHasExpenseActions01',
    'name': 'If Has Expense Actions'
}

wf['nodes'].extend([
    fetch_expenses_node,
    format_expense_vision_node,
    execute_expense_node,
    if_has_expense_node
])

# Wire up Switch Vision Query output 4 (expense) -> Fetch Recent Expenses -> Format Expense Vision -> If Has Audio
while len(wf['connections']['Switch Vision Query']['main']) <= 4:
    wf['connections']['Switch Vision Query']['main'].append([])
wf['connections']['Switch Vision Query']['main'][4] = [
    {'node': '[PG] Fetch Recent Expenses', 'type': 'main', 'index': 0}
]
wf['connections']['[PG] Fetch Recent Expenses'] = {
    'main': [[{'node': 'Format Expense Vision', 'type': 'main', 'index': 0}]]
}
wf['connections']['Format Expense Vision'] = {
    'main': [[{'node': 'If Has Audio', 'type': 'main', 'index': 0}]]
}

# Connect Process AI Output & Actions to If Has Expense Actions
for proc_name in ['Process AI Output & Actions', 'Process AI Output & Actions1']:
    proc_conns = wf['connections'][proc_name]['main'][0]
    proc_conns.append({'node': 'If Has Expense Actions', 'type': 'main', 'index': 0})

wf['connections']['If Has Expense Actions'] = {
    'main': [
        [{'node': '[PG] Execute Expense Action', 'type': 'main', 'index': 0}],
        []
    ]
}

# 5. Update prompt in Gemini nodes to recognize receipts & expenses
expense_instruction = '''
5. PENCATATAN PENGELUARAN & EXPENSE TRACKER (DARI FOTO STRUK ATAU TEKS):
   - Jika pengguna mengirim foto struk/nota belanjaan ATAU mengetik pengeluaran (misal: "catat pengeluaran makan 25rb di warteg", "rekap struk indomaret ini"):
     - Baca total harga, nama tempat/toko, dan rincian belanjaan secara akurat.
     - Di akhir responmu, sertakan tag aksi:
       <<<ACTION:EXPENSE_ADD|TARGET|AMOUNT|CATEGORY|MERCHANT|ITEMS>>>
       TARGET: "okta" atau "manda"
       AMOUNT: Angka murni tanpa titik/koma (misal: 25000)
       CATEGORY: "makan", "transport", "belanja", "tagihan", atau "lainnya"
       MERCHANT: Nama toko / warung / merchant
       ITEMS: Ringkasan barang yang dibeli
       Contoh: <<<ACTION:EXPENSE_ADD|okta|85000|belanja|Indomaret|Susu, Roti, Kopi>>>
'''

for n in wf['nodes']:
    if n['name'] in ['[HTTP] Gemini Build Message', '[HTTP] Gemini Build Message1']:
        curr_body = n['parameters']['jsonBody']
        if 'EXPENSE_ADD' not in curr_body:
            curr_body = curr_body.replace(
                '4. PRESENSI KULIAH UB:',
                expense_instruction + '\n4. PRESENSI KULIAH UB:'
            )
            n['parameters']['jsonBody'] = curr_body

# 6. Update Process AI Output & Actions to parse EXPENSE_ADD
new_parser_code = '''const geminiRaw = $input.first().json;
let rawText = "";
try {
  rawText = geminiRaw.candidates[0].content.parts[0].text || "";
} catch (e) {}

// Regex for action tags:
// <<<ACTION:TUGAS|TARGET|DETAIL>>>
// <<<ACTION:JADWAL|TARGET|DETAIL>>>
// <<<ACTION:DONE|TARGET|JUDUL>>>
// <<<ACTION:DELETE|TARGET|JUDUL>>>
// <<<ACTION:NOTE_ADD|TARGET|DETAIL>>>
// <<<ACTION:NOTE_DONE|ID>>>
// <<<ACTION:PRESENSI|hadir>>>
// <<<ACTION:EXPENSE_ADD|TARGET|AMOUNT|CATEGORY|MERCHANT|ITEMS>>>
const actionRegex = /<<<ACTION:(TUGAS|JADWAL|DONE|DELETE|NOTE_ADD|NOTE_DONE|PRESENSI|EXPENSE_ADD)(?:\\|(.*?))?>>>/gi;
const actions = [];
let match;

while ((match = actionRegex.exec(rawText)) !== null) {
  const actionType = match[1].toLowerCase();
  const rawParams = match[2] || '';
  const parts = rawParams.split('|').map(s => s.trim());

  if (actionType === 'expense_add') {
    const target = (parts[0] || 'okta').toLowerCase();
    const amount = parseFloat(parts[1]) || 0;
    const category = parts[2] || 'makan';
    const merchant = parts[3] || 'Umum';
    const itemsDetail = parts.slice(4).join(', ') || '-';
    actions.push({
      actionType: 'expense_add',
      target,
      amount,
      category,
      merchant,
      itemsDetail,
      detail: `${merchant} - Rp ${amount}`
    });
  } else {
    const target = (parts[0] || 'okta').toLowerCase();
    const detail = parts.slice(1).join('|') || parts[0] || '';
    
    let commandText = '';
    if (actionType === 'tugas') {
      commandText = target === 'manda' ? `/tugas manda ${detail}` : `/tugas ${detail}`;
    } else if (actionType === 'jadwal') {
      commandText = target === 'manda' ? `/jadwal manda ${detail}` : `/jadwal ${detail}`;
    } else if (actionType === 'done') {
      commandText = target === 'manda' ? `/done manda ${detail}` : `/done ${detail}`;
    } else if (actionType === 'delete') {
      commandText = target === 'manda' ? `/hapus-jadwal manda ${detail}` : `/hapus-jadwal ${detail}`;
    } else if (actionType === 'note_add') {
      commandText = `/catat ${detail}`;
    } else if (actionType === 'note_done') {
      commandText = `/catat done ${detail || target}`;
    } else if (actionType === 'presensi') {
      commandText = `/presensi ${detail || 'hadir'}`;
    }

    actions.push({
      actionType,
      target,
      detail: detail || target,
      commandText
    });
  }
}

// Clean user response by removing action tags
const cleanText = rawText.replace(/<<<ACTION:[A-Z_]+(?:\\|.*?)?>>>/gi, '').trim();

let waData = {};
try {
  waData = $('Normalize WA Context').item.json.wa || {};
} catch (e) {}

const hasCalendarActions = actions.some(a => ['tugas', 'jadwal', 'done', 'delete'].includes(a.actionType));
const hasNoteActions = actions.some(a => ['note_add', 'note_done'].includes(a.actionType));
const hasPresensiActions = actions.some(a => a.actionType === 'presensi');
const hasExpenseActions = actions.some(a => a.actionType === 'expense_add');

return [{
  json: {
    cleanText,
    hasActions: actions.length > 0,
    hasCalendarActions,
    hasNoteActions,
    hasPresensiActions,
    hasExpenseActions,
    actions,
    wa: waData,
    candidates: [
      {
        content: {
          parts: [
            { text: cleanText }
          ]
        }
      }
    ]
  }
}];'''

for n in wf['nodes']:
    if n['name'] in ['Process AI Output & Actions', 'Process AI Output & Actions1']:
        n['parameters']['jsCode'] = new_parser_code

with open(path, 'w') as f:
    json.dump([wf] if isinstance(data, list) else wf, f, indent=2)

print('Updated wa-conversation.json with Expense Tracker successfully!')
