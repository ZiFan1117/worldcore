# 我们的 `interfaces`（能力/约束）**也进 P 了** —— 靠给 `ActionType` 加一格 `metadata`（2026-10-17）

> ★ **作者问（逐字整理）**：「**这个我们也可以转呀**，这个**接口或者是叫能力**，我们这个什么**动作约束啥的**，**这个转成它那个是有什么问题吗**，还是怎么的？」
> ★★★ **答：★ 能转 —— 但【硬转成 P 的 `Interface` 会挂错地方】；正确做法是【给 `ActionType` 加一格 `metadata`】，已做完。**

---

## §一 ★★★★ 为什么【不能】硬转成 P 的 `Interface`（★ 逐字）

★ P 的 `Interface` 逐字（`core/interface.py`）：

```python
@dataclass
class Interface:
    """Shared shape that multiple ObjectTypes can implement."""
    interface_id / display_name / description / required_properties

    def check_compliance(self, object_type: ObjectType) -> bool:      ← ★ 参数是 ObjectType
    def get_implementors(self, ontology) -> list[ObjectType]:
        return [ot for ot in ontology.object_types.values()            ← ★ 只遍历 object_types
                if self.interface_id in ot.interfaces and ...]
```

★★★ **⇒ 它【只对 ObjectType 起作用】，压根不碰 ActionType** ✗
★★ **而我们的 9 个 `interfaces`【就是动作的元数据】** —— ★ **key 和 `actions` 的 key 完全一样**（★ 现取）：`notice.mute`／`notice.unmute`／`job.start`／`job.finish`／`job.cancel`／`ledger.compact`／`world.rekey`／`world.migrate`／`presence.report`
★★★ **⇒ 硬转的后果**：★ P 会去 **`ontology.object_types`** 里找「`notice.mute` 这个接口」★ ⇒ ★ **永远找不到** ✗ ★ ⇒ ★ `get_implementors()` **永远返回空** ✗

---

## §二 ★★★★ 正确的做法（★ 已做完）

★★★ **给 `ActionType` 加一格 `metadata: dict`** ★ —— ★ **P 原本没有这格**（★ `ObjectType` 有，★ `ActionType` 没有）✗

★ **改动（唯一一处改 P 的代码，MIT 允许）**：★ `py/foundry_ontology/core/action_type.py` ★ —— ★ 在 `audit_enabled` 之后**加了 4 行**（3 行注释 ＋ `metadata: dict = field(default_factory=dict)`）✓

### §二·1 ★★★★★ 跑出来的结果（★ VM 上现取）

```
  notice.mute        {'kind': 'invoke', 'not_roles': ['不改写已落账的事件', '不删除那条通告', '不替别的通告静音'], 'implemented': 'has_entry'}
  notice.unmute      {'kind': 'invoke', 'not_roles': [...], 'implemented': '未定（原因＝按名在 src/** 里 0 命中…）'}
  job.start          {'kind': 'invoke', 'not_roles': ['不改写已落账的事件', '不自行放行（准不准做由门禁判）', '不代替载体执行作业'], 'implemented': 'has_entry'}
  ledger.compact     {'kind': 'invoke', 'not_roles': [..., '不可逆——本能力没有撤销路径'], 'implemented': 'has_entry'}
  world.rekey        {'kind': 'config', 'not_roles': [..., '不给自己发许可', '不可逆——本能力没有撤销路径'], 'implemented': '未定…'}
  presence.report    {'kind': 'invoke', 'not_roles': ['不改写已落账的事件', '不代表别人报告', '不裁定自己有没有许可…'], 'implemented': '未定…'}
  …（9 个动作全带上）
```

★★★ **⇒ 我们的四项信息【全部进了 P】**：

| ★ 我们的 | ★★ P 里现在在哪 |
|---|---|
| ★ `what`（这条动作干什么） | ★ `description` ✓ |
| ★ `kind`（★ `invoke` 7 个／`config` 2 个） | ★ `metadata.kind` ✓ |
| ★ `not_roles`（★ 不许做什么） | ★ `metadata.not_roles` ✓ |
| ★ `实现状态`（★ 有没有实现，★ **带原因**） | ★ `metadata.implemented` ✓ |

---

## §三 ★★★ 为什么不学 P 的 `Interface`（★ 留着有用）

★★ **P 的 `Interface` 对我们【仍有用途】** ★ —— ★ 它是「**多个对象类型共享的属性形状**」：
- ★ 例如：★ 若 `surface`／`port`／`device` 都有 `name` 和 `state` ★ ⇒ ★ 可以立一个 `Named` 接口 ✓
- ★★ **但我们今天【没有这个需求】**（★ 9 类字段各不相同）★ ⇒ ★ **先不建，也不歪曲它** ✓

---

## §四 ★ 本件不能证明的事（如实）

- ★ P 的 `Interface` 逐字／`ActionType` 字段清单／两个 key 列表完全一样／VM 上那 9 行 metadata —— 都是**现取**；
- ★★ **「硬转会挂错地方」是【按 `get_implementors` 的实现逐字读的】** ★ —— ★ 我**没有**实跑一遍「把它建成 Interface 会怎样」✗；
- ★★ **`metadata` 这格 P **不校验**（★ 放什么都行）** ★ —— ★ **这是我们自己的约定，★ 不是 P 的机制** ⚠；
- ★★ **`kind` 有 `invoke` 和 `config` 两种** ★ —— ★ **`config` 那两个（`world.rekey`／`world.migrate`）语义上是不是同一类，我没核** ✗；
- ★ 本件**改了 P 的代码**（★ 4 行）★ —— ★ 已在 `py/NOTICE.md` 登记 ✓；★ 本仓判据 **C1–C26 全绿**。
