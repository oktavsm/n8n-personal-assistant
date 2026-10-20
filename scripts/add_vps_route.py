import json
import uuid

with open("workflow/master-router-webhook.json") as f:
    raw = json.load(f)
    wf = raw[0] if isinstance(raw, list) else raw

# Find the main Switch node
switch_node = None
for node in wf["nodes"]:
    if node["type"] == "n8n-nodes-base.switch" and len(node["parameters"]["rules"]["values"]) >= 20:
        switch_node = node
        break

if not switch_node:
    raise Exception("Main switch node not found!")

# Check if rule 21 already exists
rules = switch_node["parameters"]["rules"]["values"]
rule_exists = any("vps" in str(r).lower() for r in rules)

rule_21_index = len(rules)
if not rule_exists:
    new_rule = {
        "conditions": {
            "options": {
                "caseSensitive": True,
                "leftValue": "",
                "typeValidation": "strict",
                "version": 2
            },
            "conditions": [
                {
                    "id": str(uuid.uuid4()),
                    "leftValue": "={{ (() => { const text = ($json.body?.data?.message?.conversation || $json.body?.data?.message?.extendedTextMessage?.text || '').trim(); const lower = text.toLowerCase(); const jid = $json.body?.data?.key?.remoteJid || ''; const part = $json.body?.data?.key?.participant || $json.body?.data?.key?.participantAlt || ''; const isOkta = jid.includes($env.MY_WA_NUMBER) || part.includes($env.MY_WA_NUMBER); return isOkta && (lower.startsWith('/vps') || lower.startsWith('/agent')); })() }}",
                    "rightValue": True,
                    "operator": {
                        "type": "boolean",
                        "operation": "equals"
                    }
                }
            ],
            "combinator": "and"
        },
        "renameOutput": True,
        "outputKey": "vps_agent"
    }
    rules.append(new_rule)
    print(f"Added rule 21 at index {rule_21_index}")
else:
    for i, r in enumerate(rules):
        if "vps" in str(r).lower():
            rule_21_index = i
            break
    print(f"Rule already exists at index {rule_21_index}")

# Check if Call 'vps-cli-runner' node exists
call_node_name = "Call 'vps-cli-runner'"
call_node = next((n for n in wf["nodes"] if n["name"] == call_node_name), None)

if not call_node:
    call_node = {
        "parameters": {
            "workflowId": {
                "__rl": True,
                "value": "vpsCLIRunner0001",
                "mode": "list",
                "cachedResultUrl": "/n8n/workflow/vpsCLIRunner0001",
                "cachedResultName": "vps-cli-runner"
            },
            "workflowInputs": {
                "mappingMode": "defineBelow",
                "value": {},
                "matchingColumns": [],
                "schema": [],
                "attemptToConvertTypes": False,
                "convertFieldsToString": True
            },
            "options": {}
        },
        "type": "n8n-nodes-base.executeWorkflow",
        "typeVersion": 1.2,
        "position": [440, 500],
        "id": str(uuid.uuid4()),
        "name": call_node_name
    }
    wf["nodes"].append(call_node)
    print("Added Call 'vps-cli-runner' node")

# Connect Switch rule_21_index to Call 'vps-cli-runner'
switch_conn = wf["connections"][switch_node["name"]]["main"]
while len(switch_conn) <= rule_21_index:
    switch_conn.append([])

# Ensure target is connected
if not any(c.get("node") == call_node_name for c in switch_conn[rule_21_index]):
    switch_conn[rule_21_index].append({
        "node": call_node_name,
        "type": "main",
        "index": 0
    })
    print(f"Connected Switch output {rule_21_index} to {call_node_name}")

with open("workflow/master-router-webhook.json", "w") as f:
    json.dump(wf, f, indent=2)

with open("n8n/workflow/master-router-webhook.json", "w") as f:
    json.dump(wf, f, indent=2)

print("master-router-webhook updated successfully!")
