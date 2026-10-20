import json
import uuid

def uid():
    return str(uuid.uuid4())

wf = {
    "id": "memHousekeep01",
    "name": "memory-housekeeping-cron",
    "active": True,
    "nodes": [
        {
            "parameters": {
                "rule": {
                    "interval": [
                        {
                            "field": "cronExpression",
                            "expression": "0 3 * * 0"
                        }
                    ]
                }
            },
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [-300, 0],
            "id": uid(),
            "name": "Weekly Sunday 3AM Trigger"
        },
        {
            "parameters": {
                "operation": "executeQuery",
                "query": "DELETE FROM wa_chat_memory WHERE created_at < NOW() - INTERVAL '30 days';"
            },
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.5,
            "position": [-80, 0],
            "id": uid(),
            "name": "[PG] Prune Old Chat Memory",
            "credentials": {
                "postgres": {
                    "id": "pgChatMemory0001",
                    "name": "Postgres Chat Memory"
                }
            }
        }
    ],
    "connections": {
        "Weekly Sunday 3AM Trigger": {
            "main": [
                [
                    {
                        "node": "[PG] Prune Old Chat Memory",
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

with open("workflow/memory-housekeeping-cron.json", "w") as f:
    json.dump(wf, f, indent=2)

with open("n8n/workflow/memory-housekeeping-cron.json", "w") as f:
    json.dump(wf, f, indent=2)

print("memory-housekeeping-cron.json created successfully!")
