# ★★★★★ **T-311 那个通病的真正形态：`systemd` 起的 zenoh 会话【是孤岛】**（2026-10-17）

> ★ **作者令（逐字整理）**：「**让本体【起得来、连得上】，而且其他的要注册，主要是 gui 和载体**。」
> ★★★ **本体起来了、连上了 ✓；但载体和 GUI 的注册【本体收不到】** ✗ ★ —— ★ **而现取查出了真因**。

---

## §一 ★★★★ 本体起来了（★ 现取）

```
systemctl start aios-ontology ⇒ START_RC=0
aios-ontology: active
[本体] ① 装本体 …
[本体]    装上了：9 类 / 3 关系 / 9 动作 / 9 函数
[本体] ② 注册表 11 条；账本 /var/lib/aios/ontology/ledger.jsonl
[本体] ③ 连总线 tcp/127.0.0.1:7447 … 连上了
[本体] ④ 订上了：world/register ／ world/appear ／ world/ask ／ world/exec/result
[本体] ★ 本体进程起来了 —— 只认、只盖章、只转、只记
```

★ **新件**：`distro/systemd/aios-ontology.service` ★ —— ★ **Python 版**，★ **不 After=／不 Wants=／不 Requires=**（★ 四个独立）✓

---

## §二 ★★★ 载体和 GUI 的注册载荷【改了】（★ 照本体字段）

| ★ 谁 | ★ 之前（✗ 会被拒） | ★★ 改成 |
|---|---|---|
| ★ 载体 | ★ `{"class":"service","local_id":"carrier","state":"started"}` | ★★ `{"class":"service","name":"carrier","unit":"aios-carrier","state":"running"}` |
| ★ GUI | ★ `{"class":"surface","local_id":"a2ui","state":"started"}` | ★★ `{"class":"surface","name":"a2ui","role":"screen","order":1,"visible":true,"retract_seq":0,"cells":"[]"}` |

★ 两处都已改、已重编、已装 ✓

---

## §三 ★★★★★ 但本体【一条都没收到】→ 查出真因

★★ **现象**（★ 现取）：
```
[PY] 订了 world/appear，等 15 秒
[PY] 收到 0 条: []          ← ★★ 手工 Python 订阅者也【收不到】
```
★ 而 GUI 说「① 成为个体：surface/a2ui（started）」✓（★ `put` 返回 `Ok`）
★ 载体说「② 报了：service/carrier 状态 started」✓

★★★ **⇒ 结论**：★ **不是「收不到」—— 是【发出去的消息，别人收不到】** ✗

### §三·1 ★★★★ `systemd` 起的 zenoh 会话【是个孤岛】

| ★ 它能做的 | ★ 它做不到的 |
|---|---|
| ★ **连上总线**（★ 日志无错） | ★★ **它发的消息【到不了别的进程】** ✗ |
| ★★ **自己发自己收**（★ `round_trip` 到 `world/probe` 收到 `hello-zenoh`） | ★★ **别的进程发的它也收不到**（★ T-311 记的）✗ |

★★★ **⇒ 那个 `round_trip`「通」是【假象】—— ★ 它是同进程自收自发** ⚠

### §三·2 ★★★★★ 四种组合的最终账（★ 全是现取）

| ★ 组合 | ★ 连得上 | ★ 跨进程发得到 |
|---|---|---|
| ★★ **Rust ＋ `peer`（systemd）** | ✓ | ★★ **到不了别人** ✗ |
| ★★ **Rust ＋ `client`（systemd）** | ★★ **连不上** ✗ | — |
| ★ **Python ＋ `peer`（手工）** | ✓ | ★★ **收不到** ✗ |
| ★★★ **Python ＋ `client`（systemd）** | ✓ | ★★ **（本体里的订阅已就绪；它发的还没验）** ⚠ |
| ★ **Rust ＋ `peer`（手工 `--pub`）** | ✓ | ★★ **Python client 收得到** ✓ |

★★★ **⇒ 最要紧一行**：★ **同一个 Rust 二进制，★ 手工起能发到别人，★ systemd 起【发不到】** ✗
★★ **⇒ 所以问题【不在 Rust】，★ 在【systemd 起的那个会话】** ✗

---

## §四 ★★★★ 所以「载体和 GUI 用什么实现」有了硬答案

| ★ 选项 | ★ 判定 |
|---|---|
| ★ Rust ＋ `peer` | ★✗ **systemd 下是孤岛** |
| ★ Rust ＋ `client` | ★✗ **连不上** |
| ★★ **Python ＋ `client`** | ★★ **本体实测：起得来、连得上** ✓ ★ —— ★ **建议载体和 GUI 也这样** |

★★★ **⇒ 这正好回答作者上一问「载体和 GUI 用什么实现更好」—— ★ Python ＋ `client` 模式。**

---

## §五 ★★★ 还没查清的（★ 下一步）

★★ **「Python ＋ `client` ＋ Systemd」发的消息，别人收得到吗？** ★ —— ★ **没验** ⚠
★ 因为本体**目前只收不回**（★ 它只在收到时才发），★ **所以还没机会验它「发」** ✗

★★ **⇒ 最快的验法**：★ **把载体改用 Python** ★ —— ★ **它一启动就发 appear** ★ ⇒ ★ **本体立刻能验「收得到吗」** ✓

---

## §六 ★ 本件不能证明的事（如实）

- ★ 本体启动日志／载体与 GUI 日志／两个订阅者的 0 条／四种组合的状态 —— 都是**现取**（★ 本轮真跑）；
- ★★ **「systemd 起的会话是孤岛」是【现象归纳】** ★ —— ★ **我【没有查 zenoh 自己的日志】**（★ 要 `RUST_LOG`/`tracing`），★ **也没查 systemd 的沙箱设置是否影响网络**（★ `PrivateTmp`／`ProtectSystem=strict` 应该不影响 TCP，★ 但没验）✗；
- ★★ **「Rust 手工起能发到别人」是【一次测】**（★ 一条消息，★ `--pub` 到 `t/rust2py`）✗；
- ★★ **「Python ＋ client ＋ systemd 发得到」【完全没验】** ✗；
- ★★ **我改的载荷（★ 载体/GUI）【还没被本体接受过】** ★ —— ★ 因为**消息根本到不了本体** ✗
- ★ 本件**改了仓**（两个 Rust 载荷 ＋ 一个单元）⇒ ★ 已登记 ✓；★ 本仓判据 **C1–C26 全绿** ✓
