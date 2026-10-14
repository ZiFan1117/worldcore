# 实测（作者令）：**A2UI 官方渲染器 `genui` 在虚拟机上跑通并渲染出图**

| 阶段 | 环 | 维 | 版本 |
|---|---|---|---|
| S3 | 执行 | 五 证据 | **1.0（跑通，两条路都出图）** |

> **作者令（逐字）**：「**必须把 genUI 给我弄出来**」；「**你是要进入的是虚拟机**，那个运行不了的问题，**派个智能体去解决呀**」

---

## 一、★★★ 四要素读数（智能体 `genui-vm` 现报）

| 项 | ★ 读数 |
|---|---|
| **环境** | ★ `openSUSE Leap 16.0 (x86_64)`，kernel `6.12.0-160000.38-default`；★ **原本无任何 X、无 Xvfb** ⇒ `zypper` 装 `xorg-x11-server-Xvfb`／`xwd`／`ImageMagick`／`scrot` ＋ `gtk3-devel`／`clang`／`cmake`／`ninja`／`pkg-config` ＋ **`google-noto-sans-cjk-fonts`** ＋ `gstreamer-devel` |
| **版本** | ★★ `Flutter 3.47.7 stable (revision abaf9c5237)` ＋ `Dart 3.13.5` ＋ `genui ^0.10.4`（实际 **0.10.4**，依赖 **`a2ui_core 0.1.1`**） |
| **工程** | ★ `/root/gui`（`pubspec name=wc_gui`）：`lib/main.dart` 86 行／`lib/a2ui_frames.dart` 34／`lib/a2ui_render.dart` 75／`test/render_test.dart` 117／`run_window.sh` 32 |
| **跑法 A（headless）** | ★★ `flutter test --name "P[0-2]" test/render_test.dart` ⇒ **`TEST_RC=0, All tests passed!`** |
| **跑法 B（真窗口）** | ★★ `bash /root/gui/run_window.sh` ⇒ **`RUN_RC=0`**（`Xvfb :99 1280x900x24` ＋ `/usr/local/wc_gui`，GTK／Impeller OpenGLESSDF；`APP_ALIVE`、`app.log` 无错、`import -window root` 截图 RC=0） |
| **产物** | ★ `/root/gui/shot.png` ↔ 宿主 `shot.png`（**41,455 B，1640×1240**）；`/root/gui/shot_window.png` ↔ 宿主 `shot_window.png`（**24,813 B，1280×900**）；★ **VM 与宿主 sha256 已核对一致** |

## 二、★★★★★ 渲染出来的（`read_image` 逐项确认）

| ★ 控件 | ★ 画出来了吗 |
|---|---|
| ★ **Text**（标题） | ★★ 「**新建作业（流程第 1 步）**」✓ |
| ★ **TextField** | ★★ 「作业名字」＋ 下划线输入框 ✓ |
| ★ **CheckBox** | ★★ 「开启时通知我」（未勾选）✓ |
| ★ **Button** | ★★ 「**job.start**」—— ★★ **本体在册的动作名落在真窗口上** ✓ |
| ★ 中文 | ★★★ **不是豆腐块**（装了 Noto CJK 字体）✓ |
| ★ 窗口版状态行 | ★★ `A2UI parsed OK: CreateSurfaceMessage, UpdateComponentsMessage  surface=world/system` ✓ |

## 三、★★★ 关键：**先写会红的反例**（智能体的做法，符合本仓口径）

```
★ P0（逐字喂原帧）⇒ 被拒：A2uiValidationException:
   "A2UI message must have version 'v0.9' (got 'v1.0')."
★★ P2（适配帧）⇒ parsed=[CreateSurfaceMessage, UpdateComponentsMessage],
   activeSurfaces=[world/system], errorCount=0
```
⇒ ★★★ **它先把"原样喂进去会红"钉住了，再改到绿** ✓ —— ★ 这正是硬约束 9 的做法。

## 四、★★★★★ 为跑通做的 delta（6 条，逐条都有定性）

| # | ★ delta | ★ 性质 |
|---|---|---|
| **1** | ★ 版本 `v1.0` → `v0.9` | ★★★ **版本面**：`a2ui_core 0.1.1` 硬校验（`core/messages.dart:31`）；★ **我们按 v1.0 写，官方渲染器现在只认 v0.9** |
| **2** | ★ `catalogId` `…/v1_0/…` → `…/v0_9/…` | ★★★ **同上一处**（genui 0.10.4 只有 `v0_9` 那个 id） |
| **3** | ★ 批量信封 `{"version","messages":[…]}` → **拆成两条 JSONL** | ★★ **形状面**：`A2uiMessage.fromJson` **一次只吃一条** |
| **4** | ★ `TextField` 的 `{"@path":"/name"}` → `{"path":"/name"}` | ★★★ **这一条是我们写错了**（不是版本问题） |
| **5** | ★ `Button` 补 **required 的 `action:{"event":{"name":"job.start"}}`** | ★★★ **这一条是我们的帧缺必填**（`schema required:[child, action]`） |
| **6** | ★★ **我们自定义的 `_action`／`_function` 保留后 schema 不报错** | ★★★ **结论**：★ **真正拦路的是「缺 action」，不是「有自定义字段」** ⇒ ★★ **A2UI 允许我们挂自己的字段** ✓ |

## 五、★ 卡点记录（如实）

| # | ★ 卡点 | ★ 处置 |
|---|---|---|
| **1** | ★ `flutter build linux` 首次 **BRC=1**：`audioplayers_linux` 缺 **gstreamer-1.0** | ★ 装 `gstreamer-devel` ＋ `gstreamer-plugins-base-devel` ⇒ **BRC=0** |
| **2** | ★★ **编译产物没被组装进 `build/linux/x64/release/bundle/`** —— `CMakeCache` 里 `CMAKE_INSTALL_PREFIX` 被缓存成 `/usr/local`（第一次 configure 失败留下的），`cmake --install` 把 app 装到了 `/usr/local/wc_gui` | ★ 该布局本身合法（exe 同级有 `lib/`／`data/`）⇒ 据此跑通；★ 并拷成标准 bundle |
| **3** | ★ 只测 4 个 case 时 `flutter_tools` 在 teardown 挂 5-7 分钟（`Bad state: Cannot close sink while adding stream`） | ★ **widget test 与 binding 混跑的 harness 问题，不是渲染失败**；拆开只跑 P0-P2 ⇒ `RC=0` |
| **4** | ★ `~/.dart-tool` 坑（宿主上踩过） | ★ VM 上 `/root` 下该目录**原本不存在** ⇒ `mkdir -p` ＋ `touch` ⇒ **未踩坑** |

## 六、★★ 本件的边界（如实）

1. ★★★ **这是"单进程内喂一帧渲染"** —— ★ **GUI 进程还没接上 Zenoh 总线**（★ 即：不是"总线来一帧 ⇒ 渲染一帧"的活体回路）；
2. ★★ **6 条 delta 是"适配帧"** ⇒ ★ **我们产帧的那一侧（`worldcore-bus` 的 `individual`）还没按 v0.9 改**；
3. ★ **没接交互**（点按钮不会真的发动作）；
4. ★ **没做无头之外的持续运行**（Xvfb 那次是单次截图）；
5. ★ **工程住在 VM `/root/gui`** ⇒ ★ **尚未进本仓 `crates/`**；
6. ★★ **本席在过程中撞过车**（15:35 的 `flutter create` 覆盖了智能体 15:27 建好的工程，删了它 4 个文件）⇒ ★ **已认错并停手**；★ 最终成果是智能体那一路的 ✓。
