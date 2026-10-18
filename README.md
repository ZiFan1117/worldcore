# world-core · 语义世界

★ **别人的 OS 管进程和文件；我们管【谁是、能干什么、干了什么、长什么样】。**

本仓是**能跑起来的那一半**：★ 六个进程 ＋ 一个本体数据文件 ＋ 七个 systemd 单元 ＋ 一个部署脚本。
★ **不包含**上游那套发行版的其余部分（39 个 crate／三版规格／站点／工具）—— ★ 我们只借用了
`foundry-ontology` 的**目录形状**，其余全部自己写。

---

## 一、跑起来是什么样

```
★ 开机 ⇒ 登录界面（AI-OS，用户名 zhang，密码 0）
★ 人点登录 ⇒ 本体【认】⇒ 发一张票 ⇒ 凭票进个人空间 ⇒ 桌面出屏
★ 甲登录只能看甲的；乙登录只能看乙的（★ 票的 scope 说了算）
```

★★ **这条链【已经端到端跑通并通过判据】**（见 §四）。

---

## 二、六个进程 ＋ 一个借来的总线

| 进程 | 是什么 | 干什么 |
|---|---|---|
| **aios-bus** | 总线（zenohd） | ★ 借来的。所有进程只通过它说话 |
| **aios-ontology** | ★★ **本体** | ★ 只做四件：**认**（认证／发票）／**盖章**（记账）／**转**（分派）／**记**（查） |
| **aios-computer** | 计算机 | 执行器。156 条命令行映射（`distro/computer/`）；★ 只执行，不裁决 |
| **aios-presentation** | ★★ **呈现** | 合成器 ＋ 4 个动作 ＋ 本机 TCP 桥（7450） |
| **aios-presentation-render** | 呈现的**渲染半** | Flutter ＋ `genui`（A2UI 官方渲染器）；按 `layout` 叠、画上屏 |
| **aios-space** | 个人空间 | 出桌面画布 ＋ 给布局 |
| **aios-agent** | 智能体 | 模型在环：每轮问世界 ⇒ 决定 ⇒ 出帧 |

★★ **为什么呈现是两个进程**：`genui` 是 Flutter 包，跑不进 Python、也不会说 zenoh ⇒ 只能分两半；
**但它们合起来才是一个「呈现」**（★ 所以单元名带 `presentation`）。

---

## 三、怎么装

```sh
# 目标机需要：openSUSE Leap 16 / systemd / python3 / zenohd / Flutter（渲染半）
sudo REPO=. bash distro/deploy.sh
```

★ `deploy.sh` 做四件：拷 `src/` ＋ 本体数据 ＋ 命令行映射 ⇒ 装单元 ⇒ 恢复 SELinux 上下文 ⇒ 重启。
★★ **幂等**：★ 可以反复跑。

---

## 四、证明了什么（★ 每条都有现取日志／截图，不是"应该能行"）

| # | 判据 | 现取 |
|---|---|---|
| 1 | ★ 密码错 ⇒ 拒 | `{"why": "身份凭据不对（★ 测试账号 zhang ／ 0）"}` |
| 2 | ★ 密码对 ⇒ 发票 | `{"ticket": "tk-…", "who": "world://user/zhang"}` |
| 3 | ★ 无票查空间 ⇒ 拒 | `没有票／票不存在（★ 先 identity.authenticate）` |
| 4 | ★ **凭票查空间 ⇒ 通** | `{"layers": []}` |
| 5 | ★ 票过期后查 ⇒ 拒 | `{"why": "票过期了"}` |
| 6 | ★ **甲的票查乙的空间 ⇒ 拒** | `票里没有 space:lisi（★ 这张票只能看 ['space:zhang']）` |
| 7 | ★ **画布过本体** | `[本体] 宣告 a2ui.frame（…）⇒ 转给界面（to=space:zhang）` |
| 8 | ★ 呈现凭票对 ⇒ 拒冒充者 | `lisi 的画布在不在 ⇒ 不在（✓ 票过滤生效）` |
| 9 | ★★ **登录 ⇒ 切桌面** | 屏上从「登录界面」变成「zhang 的个人空间」 |
| 10 | ★ `surface` 类撤销生效 | `[本体] 进程上报 surface ⇒ 拒：类不在册` |

★★ **截图证据**：★ 在本仓的 `render/`（★ 不进 git，见 `.gitignore`）。

---

## 五、一条最重要的设计决定

### ★★ 认证和授权分开（学 PAM／OIDC／Kerberos）

```
★ 呈现（只出脸、只交凭据）
★   ↓ identity.authenticate {user, secret}
★ 本体（★ 密码只在这里；认过 ⇒ 发【票】）
★   ↓ 票 {who, expires_at, scope}
★ 呈现（拿票）── space.login {ticket} ──▶ 本体（验票）──▶ 空间（凭票进，★ 不碰密码）
```
★★★ **⇒ 空间【一个 `pw` 都没有】**；★ **谁登录就看谁的** —— 票的 `scope` 说了算。

### ★★ 画布必须过本体

```
★ 空间/智能体 ── world/notice ──▶ **本体**（认 / 盖章 / 盖 `to` / 转）── world/ui/frame ──▶ 呈现
```
★★ **本体【不碰信纸】**（`frame` 原样带），★ **只盖信封**（章 ＋ 给谁看）。

---

## 六、目录

```
src/
  ontology/       ★ 本体：定义（类/关系/动作/许可）＋ 进程 ＋ identity（认/发票/查票/销票）
  computer/       ★ 计算机：执行器（读 distro/computer/ 的 156 条映射）
  presentation/   ★ 呈现：合成器 ＋ 4 动作 ＋ TCP 桥；login_frame（登录画布）；render_main.dart（Flutter 半）
  space/          ★ 个人空间：桌面画布 ＋ 布局
  agent/          ★ 智能体：模型在环
  foundry_ontology/   ★ 本体的对象模型（目录形状借自 Palantir foundry-ontology）

distro/
  systemd/        ★ 七个单元
  computer/       ★ 156 条命令行映射
  desktop/aios-session   ★ X 会话（只挂会话，不起渲染器）
  deploy.sh       ★ 幂等部署

crates/aios-ontology/data/ontology.json   ★ 本体数据（11 类 / 5 关系 / 172 动作 / 25 许可）
```

---

## 七、许可

见 `LICENSE`。
