import sys, json
data = json.load(sys.stdin)
for r in data.get("workflow_runs", [])[:20]:
    print(f"Run {r['id']}: {r['event']} - {r['conclusion']} ({r['created_at']})")
