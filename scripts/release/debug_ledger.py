import json
path="/var/lib/aios/ontology/ledger.jsonl"
rows=[]
try:
    for line in open(path,encoding="utf-8",errors="replace"):
        try: d=json.loads(line)
        except Exception: continue
        if d.get("action") in ("app.open_url","agent.launch") and str(d.get("at","")) >= "2026-10-21T17:30":
            rows.append(d)
except Exception as e:
    print("ERR",e)
for d in rows[-30:]:
    print(d.get("at"),d.get("action"),d.get("ok"),d.get("code"),d.get("why"),"actor=",d.get("actor"))
print("count",len(rows))
