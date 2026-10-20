# -*- coding: utf-8 -*-
"""★ 本体的**数据管道**（作者：数据管道应该在本体里接收信息、更新本体）。

★ 它做什么：接收 `world/appear`（提供者上报的事实）→ 类/字段/取值域校验 → 权威线校验
  → **个体不存在就建、已存在就更新**（同一事实重复上报=更新，不是重复建）→ 落账（有变化带 before）
  → 由 World.stamp 推 `world/event`。
★ 它不是什么：不裁决许可、不发凭证、不执行；那些在 ask_path / permit。
"""
import json

from gate import identity


def ingest_appear(world, smp, log=print):
    """★ 一个进程起来 ⇒ 照【类的字段】校验 ⇒ 成为个体 ⇒ 记账。

    ★ 作者令（逐字）：「**我们这个进程很明确是要就是读取其他进程的**」
    ★ 与「动作注册」的区别：★ 这条报的是【我这个人是谁】，★ 不是【我能干什么】。
    """
    try:
        msg = json.loads(smp.payload.to_string())
    except Exception as e:
        world.reject("BAD_MESSAGE", action="appear", why="不是 JSON（%s）" % e)
        return
    cls = msg.get("class") or ""
    # ★ 认：类在册吗？
    ot = world.ontology.object_types.get(cls)
    if ot is None:
        why = "类不在册（世界没有「%s」这一类）" % cls
        world.reject("APPEAR_CLASS_UNKNOWN", action="appear:" + cls, why=why, **{"class": cls})
        return
    # ★ 照类的字段校验：必填齐不齐、有没有多塞
    # ★★★ 先摘出【能力上报】—— 那不是 service 类的格（★ 塞进去会被「多塞了」拒）
    caps_avail = msg.get("actions_available")
    caps_unsup = msg.get("actions_unsupported")
    reporter = msg.get("reporter") or ""      # ★ 谁报的（权威线用；不参与字段校验）
    fields = {}
    for k, v in msg.items():
        if k in ("class", "actions_available", "actions_unsupported", "reporter"):
            continue
        fields[k] = v
    # ★ 兼容：上报方用 local_id，本体字段叫 name
    if "local_id" in fields and "name" not in fields:
        fields["name"] = fields.pop("local_id")
    declared = set(ot.properties.keys())
    extra = [k for k in fields if k not in declared]
    missing = [k for k, pr in ot.properties.items() if pr.required and k not in fields]
    # ★★ 取值域校验（本体声明了 options 的格，值必须在里面）
    bad_value = []
    for k, pr in ot.properties.items():
        if k in fields and pr.options and fields[k] not in pr.options:
            bad_value.append('%s=%r 不在 %s 里' % (k, fields[k], pr.options))
    if extra or missing or bad_value:
        why = []
        if extra:
            why.append("多塞了 %s（本体没声明的格）" % extra)
        if missing:
            why.append("缺必填 %s" % missing)
        if bad_value:
            why.append("取值域不对：" + "；".join(bad_value))
        why_s = "；".join(why)
        world.reject("APPEAR_FIELDS_INVALID", action="appear:" + cls, why=why_s,
                    **{"class": cls, "body": msg})
        return
    # ★★ 权威线（借自订单样板：有效性先于权威）：这个类的事实只许它的【提供者】报
    _ok, _why, _code = identity.authority_ok(cls, reporter, world.appeared, world.reporters)
    if not _ok:
        world.reject(_code, action="appear:" + cls, actor=reporter, why=_why, **{"class": cls})
        return
    # ★★ 数据管道：个体不存在就建，已存在就【更新】（同一份事实重复上报 ⇒ 更新，不是重复建）
    iid = "%s/%s" % (cls, fields.get("name", "?"))
    existing = world.store.get(iid) or next(
        iter(world.store.search(cls, {"name": fields.get("name", "")}) or []), None)
    before = dict(existing.properties) if existing is not None else None
    try:
        if existing is None:
            inst = world.store.create(cls, dict(fields), created_by="world")
        else:
            inst = world.store.update(existing.instance_id, dict(fields), updated_by="world")
    except Exception as e:
        why = "建/更新个体失败：%s" % e
        world.reject("APPEAR_CREATE_FAILED", action="appear:" + cls, why=why,
                    **{"class": cls, "body": msg})
        return
    # ★★ 计算机报到时带了「我能做什么」⇒ 记下来（★ 给模型看，★ 也给查世界答）
    if caps_avail or caps_unsup:
        world.computer_caps = {"available": caps_avail or [],
                             "unsupported": caps_unsup or [],
                             "by": "%s/%s" % (cls, fields.get("name", "?")),
                             "at": None}
        log("★ 计算机报了能力：可用 %d ／ 不支持 %d" % (
            len(world.computer_caps["available"]), len(world.computer_caps["unsupported"])))
    # ★ 记下「报过到」：之后它自称这个身份，本体要能核得上（闸②.5）
    world.appeared["%s/%s" % (cls, fields.get("name", "?"))] = True
    # ★ 盖章 ＋ 落账（个体出现 ＝ 世界状态变化 ⇒ family=change）
    _extra = {}
    if before is not None and before != dict(fields):
        _extra["before"] = before
    seq = world.stamp("change", kind_of="appear", actor=reporter,
                      **{"class": cls, "subject": iid, "after": dict(fields), **_extra})
    log("★ 数据管道：接收 %s ⇒ %s（%s，store id=%s）"
        % (iid, "更新" if before is not None else "新建", seq, inst.instance_id))
