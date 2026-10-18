# 上游的 systemd 单元（★ 不启用，归档在这里）

★★ 作者令（逐字，2026-10-18）：「这些代码，这于旧代码该清理的先清理了，或者是统一放到一个地方，而且没啥用了」

★ 这些单元是**上游 AI-Native-Linux 的**（$ grep 过：初始提交 `c6a78f0` 里就有）。
★ 它们的 `ExecStart` 全是 `/usr/lib/aios/aios-system` —— ★ **那个二进制不存在**（上游的 Rust 没编），
  ★ 所以**一个都起不来**。

★ **不用删**（★ 它们属于上游底盘，删了要往 C1 登记面上加一大串）；
  ★ **只挪到本目录**，★ 让 `distro/systemd/` 根下只剩【我们真正在跑的 6 个】。

## 根下留着的（★ 我们的）

| 单元 | 是什么 |
|---|---|
| `aios-bus.service` | 总线（zenohd） |
| `aios-ontology.service` | 本体 |
| `aios-computer.service` | 计算机 |
| `aios-presentation.service` | 呈现（Python 半） |
| `aios-presentation-render.service` | 呈现的渲染半（Flutter 半） |
| `aios-space.service` | 个人空间 |
| `aios-agent.service` | 智能体 |
