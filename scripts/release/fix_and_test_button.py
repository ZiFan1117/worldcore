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
login=post({"op":"login","user":"zhang","secret":"0"})
print("login",login)
print("ping",post({"op":"ping"}))
# 拿票后同步给个人空间（否则 Space 还拿旧票）
token=""
try:
    import sqlite3
    # get ticket from server? /cmd login does not expose; ask identity.session? no.
    pass
except Exception: pass
# 用 /cmd 的 ask 无法读 ticket；从 web 进程 cookie? 直接走 identity.authenticate 拿票
def bus_ask(rid,action,params,ticket=""):
    # use HTTP /cmd op ask only; identity.authenticate returns ticket in result body
    return post({"op":"ask","action":action,"params":params})
r=bus_ask("fix-auth","identity.authenticate",{"user":"zhang","secret":"0"})
tk=((r.get("result") or {}).get("body") or {}).get("ticket") or ""
print("ticket",tk[:12],bool(tk))
r2=post({"op":"ask","action":"space.login","params":{"user":"zhang","ticket":tk}})
print("space.login",r2)
# 用同一张票请求一次，确认有效
r3=post({"op":"ask","action":"agent.state","params":{}})
print("state-before-restart",r3.get("ok"))
# 重启本体，验票仍在（持久化）
sh(["systemctl","restart","aios-ontology"])
time.sleep(8)
post({"op":"login","user":"zhang","secret":"0"})  # 给 web 进程重新拿一张，模拟浏览器自己的票
r4=post({"op":"ask","action":"agent.state","params":{}})
print("state-after-restart",r4.get("ok"),str(r4)[:200])
# 同步空间票（用新票）
r=post({"op":"ask","action":"identity.authenticate","params":{"user":"zhang","secret":"0"}})
tk=((r.get("result") or {}).get("body") or {}).get("ticket") or ""
post({"op":"ask","action":"space.login","params":{"user":"zhang","ticket":tk}})
# 模拟点智能体
msg={"action":{"event":{"name":"space.icon_clicked","context":{"icon":"ic_agent"}}}}
req=urllib.request.Request("http://127.0.0.1:8765/cmd",data=json.dumps({"op":"ui","surface":"surface/desktop-zhang","action":msg["action"],"component":"ic_agent_b"}).encode(),headers={"Content-Type":"application/json"})
try: urllib.request.urlopen(req,timeout=20).read()
except Exception as e: print("ui post err",e)
time.sleep(5)
log=sh(["journalctl","-u","aios-computer","--since","-2min","--no-pager"])
print("open_url lines:")
for line in log.splitlines():
    if "app.open_url" in line: print(line[-240:])
print("firefox:",sh(["pgrep","-af","firefox"])[:500])
print("state",post({"op":"ask","action":"agent.state","params":{}}).get("ok"))
