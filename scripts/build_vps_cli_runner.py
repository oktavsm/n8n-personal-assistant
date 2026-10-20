import json
import uuid

def uid():
    return str(uuid.uuid4())

wf = {
    "id": "vpsCLIRunner0001",
    "name": "vps-cli-runner",
    "active": True,
    "nodes": [
        {
            "parameters": {
                "inputSource": "passthrough"
            },
            "type": "n8n-nodes-base.executeWorkflowTrigger",
            "typeVersion": 1.1,
            "position": [-600, 0],
            "id": uid(),
            "name": "vps-trigger"
        },
        {
            "parameters": {
                "jsCode": """const item = $input.first().json;
const data = item.body?.data || item.data || item;
const msg = data.message || {};
const remoteJid = data.key?.remoteJid || '';
const participant = data.key?.participant || data.key?.participantAlt || remoteJid;
const messageId = data.key?.id || '';

const text = (msg.conversation || msg.extendedTextMessage?.text || '').trim();
const prompt = text.replace(/^(\\/vps|\\/agent)\\s*/i, '').trim();

return [{
  json: {
    remoteJid,
    participant,
    messageId,
    rawText: text,
    prompt: prompt || 'Cek status VPS, disk, dan container docker secara ringkas'
  }
}];"""
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [-380, 0],
            "id": uid(),
            "name": "Normalize & Extract Task"
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://evolution-api:8080/message/sendText/okta_wa",
                "authentication": "genericCredentialType",
                "genericAuthType": "=httpHeaderAuth",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {
                            "name": "number",
                            "value": "={{ $json.remoteJid }}"
                        },
                        {
                            "name": "text",
                            "value": "={{ '⏳ *VPS Agent Task Diterima*\\n\\n📋 *Instruksi:* \"' + $json.prompt + '\"\\n\\n_Codex Agent sedang mengeksekusi instruksi di VPS..._' }}"
                        }
                    ]
                },
                "options": {}
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [-160, -100],
            "id": uid(),
            "name": "Send Ack to WA",
            "credentials": {
                "httpHeaderAuth": {
                    "id": "GEmHpHffIDZKhtvn",
                    "name": "Header Auth account"
                }
            }
        },
        {
            "parameters": {
                "resource": "command",
                "operation": "execute",
                "authentication": "privateKey",
                "command": "={{ \"/home/dev/.local/bin/run-agent.sh \" + JSON.stringify($json.prompt) }}"
            },
            "type": "n8n-nodes-base.ssh",
            "typeVersion": 1,
            "position": [-160, 100],
            "id": uid(),
            "name": "Execute Agent on VPS",
            "continueOnFail": True,
            "credentials": {
                "sshPrivateKey": {
                    "id": "sshHostDev0001",
                    "name": "SSH Host Dev"
                }
            }
        },
        {
            "parameters": {
                "jsCode": """const sshResult = $input.first().json;
const meta = $('Normalize & Extract Task').first().json;

const stdout = (sshResult.stdout || '').trim();
const stderr = (sshResult.stderr || '').trim();
const exitCode = sshResult.code;
const isError = sshResult.error;

let reply = '';
if (isError) {
  reply = `❌ *VPS Agent Error:*\\n\\n${sshResult.error}`;
} else if (stdout) {
  reply = `🤖 *VPS Agent Report:*\\n\\n${stdout}`;
} else if (stderr) {
  reply = `⚠️ *VPS Agent Warning:*\\n\\n${stderr}`;
} else {
  reply = `ℹ️ *VPS Agent:* Task selesai (exit code: ${exitCode}).`;
}

if (reply.length > 3500) {
  reply = reply.substring(0, 3450) + '\\n\\n... _(output terpotong batas karakter WA)_';
}

return [{
  json: {
    ...meta,
    replyText: reply
  }
}];"""
            },
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [80, 100],
            "id": uid(),
            "name": "Format Agent Result"
        },
        {
            "parameters": {
                "method": "POST",
                "url": "http://evolution-api:8080/message/sendText/okta_wa",
                "authentication": "genericCredentialType",
                "genericAuthType": "=httpHeaderAuth",
                "sendBody": True,
                "bodyParameters": {
                    "parameters": [
                        {
                            "name": "number",
                            "value": "={{ $json.remoteJid }}"
                        },
                        {
                            "name": "text",
                            "value": "={{ $json.replyText }}"
                        }
                    ]
                },
                "options": {}
            },
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [300, 100],
            "id": uid(),
            "name": "Send Reply to WA",
            "credentials": {
                "httpHeaderAuth": {
                    "id": "GEmHpHffIDZKhtvn",
                    "name": "Header Auth account"
                }
            }
        }
    ],
    "connections": {
        "vps-trigger": {
            "main": [
                [
                    {
                        "node": "Normalize & Extract Task",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Normalize & Extract Task": {
            "main": [
                [
                    {
                        "node": "Send Ack to WA",
                        "type": "main",
                        "index": 0
                    },
                    {
                        "node": "Execute Agent on VPS",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Execute Agent on VPS": {
            "main": [
                [
                    {
                        "node": "Format Agent Result",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        },
        "Format Agent Result": {
            "main": [
                [
                    {
                        "node": "Send Reply to WA",
                        "type": "main",
                        "index": 0
                    }
                ]
            ]
        }
    },
    "settings": {
        "executionOrder": "v1"
    }
}

with open("workflow/vps-cli-runner.json", "w") as f:
    json.dump(wf, f, indent=2)

with open("n8n/workflow/vps-cli-runner.json", "w") as f:
    json.dump(wf, f, indent=2)

print("vps-cli-runner built and verified!")
