---
type: script
---
set -e
f=$(ls *.jsonl 2>/dev/null | head -1); [ -n "$f" ] || { echo "no .jsonl produced"; exit 1; }
python3 - "$f" <<'PY'
import json, re, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
def payload(r): return r.get("item") or r.get("data") or r.get("payload") or {}
ok = True
def fail(msg):
    global ok; ok = False; print("FAIL:", msg)
blob = json.dumps(rows)
if re.search(r'"created_at":\s*1\d{12}\b', blob): fail("epoch-millisecond created_at left in the file")
if not re.search(r'"created_at":\s*"\d{4}-\d{2}-\d{2}T', blob): fail("no RFC3339 created_at found")
reactions = [r for r in rows if r.get("type") == "reaction"]
if len(reactions) < 3: fail("expected >= 3 reaction rows (one per user), got %d" % len(reactions))
for r in rows:
    if r.get("type") == "channel":
        cid = payload(r).get("id") or ""
        if len(cid) > 64: fail("channel id longer than 64 chars: %s" % cid[:70])
users = [r for r in rows if r.get("type") == "user"]
if len(users) < 3: fail("expected 3 user rows, got %d" % len(users))
print("rows:", len(rows), "reactions:", len(reactions), "users:", len(users))
sys.exit(0 if ok else 1)
PY

