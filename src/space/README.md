> ## ★★★ 2026-10-18 晚 —— 本目录已实现
>
> ★ `space_process.py`：报 `space/<用户>`、开 3 动作（`space.login`／`set_layout`／`get_layout`）、出桌面画布（带 `layout`、`role: desktop`）。
> ★ `desktop_frame.py`：桌面画布（壁纸/顶栏/图标；★ 布局细节**不进本体**）。
> ★★ **画布不是类、不是个体** —— 它是呈现内部的一张表；`layout` 是我们的扩展（A2UI 规范没有这一层）。
> ★ 见 `ninedim/06-变更/2026-10-13-aios-semantic-plane/说明-画布合成层-A2UI不管的那一层-2026-10-18.md`。

---

# src/space —— 个人空间（space）进程

> ★ 状态：**目录已建，进程代码待写**（2026-10-18 作者令「space/ 也要建」）。
> ★ 本体侧已就绪：`space` 类（name／owner→human／state=inactive·active·closed）＋ `human-has-space`／`surface-in-space` 关系 ＋
>   `space.status`／`space.activate`／`space.deactivate`／`space.set_wallpaper` 四条许可（占位）。
> ★ 设计件：`ninedim/06-变更/2026-10-13-aios-semantic-plane/设计-个人空间-参考与详细要素-2026-10-18.md`。

## 一进程一夹的落位（照 `AGENTS.md` 第 11 条）

| 文件（计划） | 管什么 | 行数上限 |
|---|---|---|
| `space_process.py` | 进程骨架：连总线、`world/appear` 报 `space/<name>`、收 `world/exec` 分发、回 `world/exec/result` | ≤ 800（C27） |
| `space_store.py` | 数据：`profile.json` 读写；权威目录 `/var/lib/aios/spaces/<user>/`，运行时 `$XDG_RUNTIME_DIR/aios-space/` | ≤ 800 |
| `space_actions.py` | 四个动作的处理器：`status`／`activate`／`deactivate`／`set_wallpaper` | ≤ 800 |

★ 一个文件只管一件事；超 800 行就拆（C27）。桥这类“给谁用”的件不单独立夹（照 §一百四十九 的口径）。

## 二、开工前还差四个决定（作者拍）

1. space 数据权威位置：`/var/lib/aios/spaces/<user>/`（世界托管）还是用户 XDG 目录；
2. 登录/切换：自建最小接入，还是接 systemd-logind/PAM；
3. `space.*` 的 `registered_by_kind`：先用 `interface` 还是新增一类（改闭集要人审）；
4. `space.activate` 的 actor 是谁（接入进程？人？）。

## 三、不做什么

- 不画、不合成、不持画布（呈现/合成器是 presentation 的事）；
- 不认人、不签身份（登录是接入层）；
- 偏好/布局细节**不进本体**（只存 space 自己的数据）。
