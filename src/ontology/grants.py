# -*- coding: utf-8 -*-
"""★ 许可条文的归一（`who`/`scope` 同词两义）—— 2026-10-19 起**条文本身住在声明件** `world.json`。

★ 本件只剩一件事：从声明件装进来的条文，若只有 `who`（历史形态）就补 `scope`、把 `who` 归位成授权者。
  （sysknife 的只读动作仍由映射表补条文，所以这步在两个装载器之后跑。）
"""
# ★ 说明：人侧动作的**定义与条文**已全部搬进 `src/ontology/world.json`（定义方式抄借书平台）；
#   本模块不再持有任何动作/条文，避免「一个事实两个载体」。


def normalize_grants(o):
    """★ 修「who/scope 同词两义」：`who`＝授权者，`scope`＝生效许可（can_execute 只读 scope）。

    ★ 必须在【两个装载器都跑完】之后调用（声明件 ＋ sysknife 映射表）。
    """
    grants = (o.metadata.setdefault("permissions", {})).setdefault("grants", {})
    for name, g in grants.items():
        if name.startswith("_") or not isinstance(g, dict) or g.get("scope"):
            continue
        g["scope"] = list(g.get("who") or [])
        g["who"] = ["world://user"]
        g["_note"] = "who＝授权者（占位）；scope＝生效许可（can_execute 读 scope）"
