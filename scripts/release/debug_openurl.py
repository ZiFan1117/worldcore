import json, subprocess, time, urllib.request

def post(payload):
    data=json.dumps(payload).encode()
    req=urllib.request.Request("http://127.0.0.1:8765/cmd",data=data,headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=40) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok":False,"why":str(e)}

def sh(a): return subprocess.run(a,capture_output=True,text=True).stdout
print("ping",post({"op":"ping"}))
print("login",post({"op":"login","user":"zhang","secret":"0"}))
r=post({"op":"ask","action":"app.open_url","params":{"url":"http://127.0.0.1:8765/dsh?user=zhang&secret=0"}})
print("ask open_url",json.dumps(r,ensure_ascii=False)[:1500])
time.sleep(3)
log=sh(["journalctl","-u","aios-computer","--since","-2min","--no-pager"])
print("computer log tail")
print(log[-3000:])
print("firefox",sh(["pgrep","-af","firefox"])[:1000])
