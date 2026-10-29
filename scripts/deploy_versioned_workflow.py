import subprocess, json, uuid

with open('/home/oktaavsm/Code/github.com/n8n-personal-assistant/workflow/lunar-hub-api.json') as f:
    wf = json.load(f)[0]

# Base nodes
base_node_names = [
    'Webhook', 'Create GCal Event',
    'Get GCal Kuliah', 'Collect Kuliah', 'Get GCal Agenda', 'Collect Agenda',
    'Get GCal Tugas', 'Collect Tugas', 'Get GCal PAPB', 'Collect PAPB',
    'HTTP Brone Auth', 'HTTP Brone Get Tasks', 'Aggregate & Format Agenda'
]
nodes = [n for n in wf['nodes'] if n['name'] in base_node_names]
connections = {}

switch_node = {
  "parameters": {
    "rules": {
      "values": [
        {
          "conditions": {
            "options": {
              "caseSensitive": True,
              "leftValue": "",
              "typeValidation": "strict",
              "version": 3
            },
            "conditions": [
              {
                "id": str(uuid.uuid4()),
                "leftValue": "={{ ($json.body?.action || '').trim() === 'create_event' }}",
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
          "outputKey": "create_event"
        },
        {
          "conditions": {
            "options": {
              "caseSensitive": True,
              "leftValue": "",
              "typeValidation": "strict",
              "version": 3
            },
            "conditions": [
              {
                "id": str(uuid.uuid4()),
                "leftValue": "={{ ($json.body?.action || '').trim() === 'check_presensi' }}",
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
          "outputKey": "check_presensi"
        },
        {
          "conditions": {
            "options": {
              "caseSensitive": True,
              "leftValue": "",
              "typeValidation": "strict",
              "version": 3
            },
            "conditions": [
              {
                "id": str(uuid.uuid4()),
                "leftValue": "={{ ($json.body?.action || '').trim() === 'submit_presensi' }}",
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
          "outputKey": "submit_presensi"
        }
      ]
    },
    "options": {
      "fallbackOutput": "extra"
    }
  },
  "type": "n8n-nodes-base.switch",
  "typeVersion": 3.4,
  "position": [-50, 200],
  "id": "node-action-router-switch",
  "name": "Switch: Action Router"
}

node_http_check_presensi = {
  "parameters": {
    "method": "POST",
    "url": "http://brone-auth:3000/get-siam-presensi",
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": "={\n  \"username\": \"{{ $env.BRONE_USERNAME }}\",\n  \"password\": \"{{ $env.BRONE_PASSWORD }}\"\n}",
    "options": {
      "timeout": 15000
    }
  },
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.4,
  "position": [250, 250],
  "id": "node-http-check-siam-presensi",
  "name": "HTTP Check SIAM Presensi",
  "retryOnFail": True,
  "maxTries": 2,
  "waitBetweenTries": 1000
}

node_format_presensi = {
  "parameters": {
    "jsCode": """const resData = $input.first().json;
const rawList = resData.data || [];
const presensiList = rawList.map(p => ({
  mata_kuliah: p.MATA_KULIAH || "",
  kode_materi: p.K_MATERI_AJAR || "",
  jam_mulai: p.JAM_MULAI || "",
  jam_selesai: p.JAM_SELESAI || "",
  ruang: p.RUANG || "",
  k_absensi: p.K_ABSENSI || "",
  sudah_absen: (p.K_ABSENSI || "").trim() !== ""
}));
const activeList = presensiList.filter(p => !p.sudah_absen);
return [{
  json: {
    status: "success",
    action: "check_presensi",
    has_active_presensi: activeList.length > 0,
    active_count: activeList.length,
    active_presensi: activeList,
    all_presensi: presensiList
  }
}];"""
  },
  "type": "n8n-nodes-base.code",
  "typeVersion": 2,
  "position": [500, 250],
  "id": "node-format-presensi-response",
  "name": "Format Presensi Response"
}

node_http_submit_presensi = {
  "parameters": {
    "method": "POST",
    "url": "http://brone-auth:3000/submit-siam-presensi",
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": "={\n  \"username\": \"{{ $env.BRONE_USERNAME }}\",\n  \"password\": \"{{ $env.BRONE_PASSWORD }}\",\n  \"kode_materi\": \"{{ $('Webhook').item.json.body?.kode_materi }}\",\n  \"kode_absensi\": \"{{ $('Webhook').item.json.body?.kode_absensi || 'H' }}\",\n  \"is_daring\": \"{{ $('Webhook').item.json.body?.is_daring || '0' }}\"\n}",
    "options": {
      "timeout": 20000
    }
  },
  "type": "n8n-nodes-base.httpRequest",
  "typeVersion": 4.4,
  "position": [250, 450],
  "id": "node-http-submit-siam-presensi",
  "name": "HTTP Submit SIAM Presensi",
  "retryOnFail": True,
  "maxTries": 2,
  "waitBetweenTries": 1000
}

node_format_submit = {
  "parameters": {
    "jsCode": """const res = $input.first().json;
return [{
  json: {
    status: "success",
    action: "submit_presensi",
    result: res
  }
}];"""
  },
  "type": "n8n-nodes-base.code",
  "typeVersion": 2,
  "position": [500, 450],
  "id": "node-format-submit-response",
  "name": "Format Submit Response"
}

format_event_created = {
  "parameters": {
    "jsCode": """const event = $input.first().json;
return [{
  json: {
    status: "success",
    action: "create_event",
    event: event
  }
}];"""
  },
  "type": "n8n-nodes-base.code",
  "typeVersion": 2,
  "position": [500, 50],
  "id": "node-format-event-created",
  "name": "Format Event Created"
}

unified_respond = {
  "parameters": {
    "respondWith": "json",
    "responseBody": "={{ $json }}",
    "options": {
      "responseCode": 200,
      "responseHeaders": {
        "entries": [
          {
            "name": "Content-Type",
            "value": "application/json"
          },
          {
            "name": "Access-Control-Allow-Origin",
            "value": "*"
          }
        ]
      }
    }
  },
  "type": "n8n-nodes-base.respondToWebhook",
  "typeVersion": 1.5,
  "position": [2650, 200],
  "id": "node-unified-respond",
  "name": "Respond to Webhook"
}

# Update Create GCal Event to resolve calendar based on category
for n in nodes:
    if n['name'] == 'Create GCal Event':
        n['parameters']['calendar']['value'] = "={{ ($json.body?.category === 'Kuliah' ? $env.GCAL_OKTA_KULIAH : ($json.body?.category === 'Tugas' ? $env.GCAL_OKTA_TUGAS : $env.GCAL_OKTA_AGENDA)) || $env.GCAL_OKTA_AGENDA }}"

# Assemble nodes
nodes.extend([
    switch_node,
    node_http_check_presensi,
    node_format_presensi,
    node_http_submit_presensi,
    node_format_submit,
    format_event_created,
    unified_respond
])

# Connections:
# Webhook -> Switch
connections['Webhook'] = {
    'main': [[{'node': 'Switch: Action Router', 'type': 'main', 'index': 0}]]
}

# Switch outputs:
# 0: create_event -> Create GCal Event -> Format Event Created -> Respond to Webhook
# 1: check_presensi -> HTTP Check SIAM Presensi -> Format Presensi Response -> Respond to Webhook
# 2: submit_presensi -> HTTP Submit SIAM Presensi -> Format Submit Response -> Respond to Webhook
# 3: fallback -> Get GCal Kuliah
connections['Switch: Action Router'] = {
    'main': [
        [{'node': 'Create GCal Event', 'type': 'main', 'index': 0}],
        [{'node': 'HTTP Check SIAM Presensi', 'type': 'main', 'index': 0}],
        [{'node': 'HTTP Submit SIAM Presensi', 'type': 'main', 'index': 0}],
        [{'node': 'Get GCal Kuliah', 'type': 'main', 'index': 0}]
    ]
}

connections['Create GCal Event'] = {
    'main': [[{'node': 'Format Event Created', 'type': 'main', 'index': 0}]]
}
connections['Format Event Created'] = {
    'main': [[{'node': 'Respond to Webhook', 'type': 'main', 'index': 0}]]
}

connections['HTTP Check SIAM Presensi'] = {
    'main': [[{'node': 'Format Presensi Response', 'type': 'main', 'index': 0}]]
}
connections['Format Presensi Response'] = {
    'main': [[{'node': 'Respond to Webhook', 'type': 'main', 'index': 0}]]
}

connections['HTTP Submit SIAM Presensi'] = {
    'main': [[{'node': 'Format Submit Response', 'type': 'main', 'index': 0}]]
}
connections['Format Submit Response'] = {
    'main': [[{'node': 'Respond to Webhook', 'type': 'main', 'index': 0}]]
}

# Agenda sync pipeline
connections['Get GCal Kuliah'] = {'main': [[{'node': 'Collect Kuliah', 'type': 'main', 'index': 0}]]}
connections['Collect Kuliah'] = {'main': [[{'node': 'Get GCal Agenda', 'type': 'main', 'index': 0}]]}
connections['Get GCal Agenda'] = {'main': [[{'node': 'Collect Agenda', 'type': 'main', 'index': 0}]]}
connections['Collect Agenda'] = {'main': [[{'node': 'Get GCal Tugas', 'type': 'main', 'index': 0}]]}
connections['Get GCal Tugas'] = {'main': [[{'node': 'Collect Tugas', 'type': 'main', 'index': 0}]]}
connections['Collect Tugas'] = {'main': [[{'node': 'Get GCal PAPB', 'type': 'main', 'index': 0}]]}
connections['Get GCal PAPB'] = {'main': [[{'node': 'Collect PAPB', 'type': 'main', 'index': 0}]]}
connections['Collect PAPB'] = {'main': [[{'node': 'HTTP Brone Auth', 'type': 'main', 'index': 0}]]}
connections['HTTP Brone Auth'] = {'main': [[{'node': 'HTTP Brone Get Tasks', 'type': 'main', 'index': 0}]]}
connections['HTTP Brone Get Tasks'] = {'main': [[{'node': 'Aggregate & Format Agenda', 'type': 'main', 'index': 0}]]}
connections['Aggregate & Format Agenda'] = {'main': [[{'node': 'Respond to Webhook', 'type': 'main', 'index': 0}]]}

# Save updated workflow
wf['nodes'] = nodes
wf['connections'] = connections

with open('/home/oktaavsm/Code/github.com/n8n-personal-assistant/workflow/lunar-hub-api.json', 'w') as f:
    json.dump([wf], f, indent=2)

wf_id = 'lunarHubApi2026'
nodes_json = json.dumps(wf['nodes'])
conn_json = json.dumps(wf['connections'])
new_version_id = str(uuid.uuid4())

# 1. Insert into workflow_history
insert_hist = f"""
INSERT INTO workflow_history ("versionId", "workflowId", authors, "createdAt", "updatedAt", nodes, connections, name, autosaved)
VALUES (
    '{new_version_id}',
    '{wf_id}',
    'oktaavsm',
    NOW(),
    NOW(),
    '{nodes_json.replace("'", "''")}',
    '{conn_json.replace("'", "''")}',
    'lunar-hub-api',
    false
);
"""

# 2. Update workflow_entity
update_wf = f"""
UPDATE workflow_entity
SET nodes = '{nodes_json.replace("'", "''")}',
    connections = '{conn_json.replace("'", "''")}',
    "versionId" = '{new_version_id}',
    "activeVersionId" = '{new_version_id}',
    "updatedAt" = NOW()
WHERE id = '{wf_id}';
"""

full_sql = insert_hist + update_wf

proc = subprocess.run(
    ['ssh', 'pg-bcc', 'docker exec -i notifier_db psql -U oktaavsm -d n8n_db -t -A'],
    input=full_sql,
    capture_output=True,
    text=True
)
print('DB Output:', proc.stdout.strip())
print(f'Deployed version {new_version_id} successfully!')
