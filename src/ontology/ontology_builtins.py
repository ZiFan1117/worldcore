# -*- coding: utf-8 -*-
"""★ 本体内建动作（不需要外部提供者）：notice.* / job.* / presence.report。

★ 为什么有：法里声明了这些动作，但没有进程注册它们 ⇒ 原来请求会得到
  PROVIDER_NOT_DECLARED（“没有执行者路由”）。它们本质是本体自己的状态（通告静音、
  作业状态、在场记录），所以由本体本地执行、落账、回话。
★ 不可逆/违不变量动作（ledger.compact / world.rekey / world.migrate）不做；
  显式返回 UNSUPPORTED + 原因，不再伪装成“路由不存在”。
"""
import datetime
import uuid

NOTICE_SUBJECTS = ("change", "act", "notice", "job")
PRESENCE_SUBJECTS = ("human", "agent", "application", "service", "device", "workflow")
UNSUPPORTED = {
    "ledger.compact": "账只增不改（P4）；不提供压实",
    "world.rekey": "不可逆换钥材料；P1 不支持",
    "world.migrate": "世界迁移不可逆；P1 不支持",
}


def _state(w):
    st = getattr(w, "_builtin_state", None)
    if st is None:
        st = {"muted": set(), "jobs": {}, "presence": {}}
        w._builtin_state = st
    return st


def _now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def handled(name):
    return name in ("notice.mute", "notice.unmute", "job.start", "job.finish",
                    "job.cancel", "presence.report") or name in UNSUPPORTED


def dispatch(w, name, params=None, actor=None):
    """返回 (ok, body)。失败 body 是 {"code","why"}。"""
    params = params if isinstance(params, dict) else {}
    st = _state(w)
    subject = str(params.get("subject") or "")

    if name in UNSUPPORTED:
        return False, {"code": "UNSUPPORTED", "why": UNSUPPORTED[name]}

    if name == "notice.mute":
        if subject not in NOTICE_SUBJECTS:
            return False, {"code": "BAD_PARAM",
                           "why": "subject 不在册：%r（可选 %r）" % (subject, NOTICE_SUBJECTS)}
        st["muted"].add(subject)
        w.muted_notice_kinds = set(st["muted"])
        return True, {"subject": subject, "muted": sorted(st["muted"])}

    if name == "notice.unmute":
        if subject not in NOTICE_SUBJECTS:
            return False, {"code": "BAD_PARAM",
                           "why": "subject 不在册：%r（可选 %r）" % (subject, NOTICE_SUBJECTS)}
        st["muted"].discard(subject)
        w.muted_notice_kinds = set(st["muted"])
        return True, {"subject": subject, "muted": sorted(st["muted"])}

    if name == "job.start":
        jid = "job-" + uuid.uuid4().hex[:12]
        st["jobs"][jid] = {"job_id": jid, "subject": subject or jid, "state": "running",
                           "started_at": _now(), "started_by": actor or "?",
                           "finished_at": None}
        return True, dict(st["jobs"][jid])

    if name in ("job.finish", "job.cancel"):
        jid = subject or params.get("job_id") or ""
        job = st["jobs"].get(jid)
        if job is None:
            return False, {"code": "JOB_NOT_FOUND", "why": "作业不存在：%r" % jid}
        if job["state"] != "running":
            return False, {"code": "JOB_NOT_RUNNING",
                           "why": "作业不是 running：%r（%s）" % (jid, job["state"])}
        job["state"] = "finished" if name == "job.finish" else "cancelled"
        job["finished_at"] = _now()
        job["finished_by"] = actor or "?"
        return True, dict(job)

    if name == "presence.report":
        if subject not in PRESENCE_SUBJECTS:
            return False, {"code": "BAD_PARAM",
                           "why": "subject 不在册：%r（可选 %r）" % (subject, PRESENCE_SUBJECTS)}
        st["presence"][actor or "?"] = {"actor": actor, "subject": subject,
                                        "reported_at": _now()}
        return True, {"actor": actor, "subject": subject,
                      "presence": sorted(st["presence"].keys())}

    return False, {"code": "UNKNOWN_ACTION", "why": "不是内建动作：%s" % name}
