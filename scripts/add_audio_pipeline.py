import json
import uuid

def uid():
    return str(uuid.uuid4())

with open("workflow/wa-conversation.json") as f:
    raw = json.load(f)
    wf = raw[0] if isinstance(raw, list) else raw

# Check if audio nodes already exist
if any(n["name"] == "If Has Audio" for n in wf["nodes"]):
    print("Audio nodes already exist!")
else:
    # 1. If Has Audio node
    if_audio_node = {
        "parameters": {
            "conditions": {
                "options": {
                    "caseSensitive": True,
                    "leftValue": "",
                    "typeValidation": "loose",
                    "version": 3
                },
                "conditions": [
                    {
                        "id": uid(),
                        "leftValue": "={{ $('Normalize WA Context').item.json.wa.hasAudio }}",
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
        "position": [60, 0],
        "id": uid(),
        "name": "If Has Audio"
    }

    # 2. Prepare Audio Payload node
    prep_audio_node = {
        "parameters": {
            "jsCode": """const item = $('Normalize WA Context').item.json;
const data = item.body?.data || {};
const wa = item.wa || {};

return [{
  json: {
    payload: {
      message: {
        key: data.key,
        message: data.message
      },
      convertToMp4: false
    }
  }
}];"""
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [240, -120],
        "id": uid(),
        "name": "Prepare Audio Payload"
    }

    # 3. [HTTP] Evolution Get Base64 Audio node
    get_audio_node = {
        "parameters": {
            "method": "POST",
            "url": "http://evolution-api:8080/chat/getBase64FromMediaMessage/okta_wa",
            "authentication": "genericCredentialType",
            "genericAuthType": "=httpHeaderAuth",
            "sendBody": True,
            "specifyBody": "json",
            "jsonBody": "={{ $json.payload }}",
            "options": {
                "timeout": 20000
            }
        },
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [440, -120],
        "id": uid(),
        "name": "[HTTP] Evolution Get Base64 Audio",
        "credentials": {
            "httpHeaderAuth": {
                "id": "GEmHpHffIDZKhtvn",
                "name": "Header Auth account"
            }
        }
    }

    # 4. Attach Audio Base64 node
    attach_audio_node = {
        "parameters": {
            "jsCode": """const audioResult = $input.first().json;
const memItem = $('Format Memory Context').item.json;
let b64 = audioResult.base64 || '';
if (b64.includes('base64,')) {
  b64 = b64.split('base64,')[1];
}

return [{
  json: {
    ...memItem,
    base64Audio: b64
  }
}];"""
        },
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [640, -120],
        "id": uid(),
        "name": "Attach Audio Base64"
    }

    wf["nodes"].extend([if_audio_node, prep_audio_node, get_audio_node, attach_audio_node])

    # Re-wire connections:
    # Format Memory Context -> If Has Audio
    wf["connections"]["Format Memory Context"] = {
        "main": [
            [
                {
                    "node": "If Has Audio",
                    "type": "main",
                    "index": 0
                }
            ]
        ]
    }

    # If Has Audio -> [True] Prepare Audio Payload, [False] Switch
    wf["connections"]["If Has Audio"] = {
        "main": [
            [
                {
                    "node": "Prepare Audio Payload",
                    "type": "main",
                    "index": 0
                }
            ],
            [
                {
                    "node": "Switch",
                    "type": "main",
                    "index": 0
                }
            ]
        ]
    }

    # Prepare Audio Payload -> [HTTP] Evolution Get Base64 Audio
    wf["connections"]["Prepare Audio Payload"] = {
        "main": [
            [
                {
                    "node": "[HTTP] Evolution Get Base64 Audio",
                    "type": "main",
                    "index": 0
                }
            ]
        ]
    }

    # [HTTP] Evolution Get Base64 Audio -> Attach Audio Base64
    wf["connections"]["[HTTP] Evolution Get Base64 Audio"] = {
        "main": [
            [
                {
                    "node": "Attach Audio Base64",
                    "type": "main",
                    "index": 0
                }
            ]
        ]
    }

    # Attach Audio Base64 -> Switch
    wf["connections"]["Attach Audio Base64"] = {
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

    print("Audio Voice Note pipeline successfully integrated into wa-conversation graph!")

with open("workflow/wa-conversation.json", "w") as f:
    json.dump(wf, f, indent=2)
with open("n8n/workflow/wa-conversation.json", "w") as f:
    json.dump(wf, f, indent=2)

print("Saved wa-conversation.json successfully!")
