import json, subprocess, urllib.request

def sh(args):
    return subprocess.run(args, capture_output=True, text=True).stdout

print("=== computer app.open_url ===")
log = sh(["journalctl","-u","aios-computer","--since","-2h","--no-pager"])
for line in log.splitlines():
    if "app.open_url" in line or "起不来" in line or "已打开" in line:
        print(line[-300:])
print("=== firefox procs ===")
print(sh(["pgrep","-af","firefox"])[:3000])
print("=== browser profile ===")
print(sh(["ls","-la","/tmp/worldcore-browser"])[:1500])
print("=== web ping ===")
def post(payload):
    data=json.dumps(payload).encode()
    req=urllib.request.Request("http://127.0.0.1:8765/cmd",data=data,headers={"Content-Type":"application/json"})
    try:
        return json.loads(urllib.request.urlopen(req,timeout=10).read())
    except Exception as e:
        return {"ok":False,"why":str(e)}
print(post({"op":"ping"}))
print(post({"op":"login","user":"zhang","secret":"0"}))
print(post({"op":"ask","action":"presentation.state","params":{}}))
print(post({"op":"ask","action":"agent.state","params":{}}))
