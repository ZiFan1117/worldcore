# rustfmt.ps1 —— 在 VM 内跑 rustfmt，把结果取回本机工作区
#
# ⚠️ 本文件含中文说明，**必须以 UTF-8 带 BOM 保存**。
#    原因（2026-09-26 实测踩到）：Windows PowerShell 5.1 对**无 BOM** 的 .ps1
#    按系统 ANSI 代码页（本机为 GBK）解码，中文注释变成乱码字节，
#    直接把解析器打崩——报 `Unrecognized token in source text`，行号还全指向
#    正则字面量，看起来像语法错，**实际是编码错**。PowerShell 7 无此问题。
#    故：`.ps1` 一律带 BOM。（`.sh` / `.py` 是 UTF-8 原生，不需要。）
#
# 为什么需要它：
#   本项目"本机只写、VM 内构建"（D:\Code 无 Rust 工具链）。而 CI 的 gate.yml
#   含 `cargo fmt --all -- --check`——**规范格式以 VM 内的 rustfmt 为准**。
#   于是任何 Rust 改动都必须经过"VM 内 fmt → 结果取回本机"，否则推送后 CI 必红。
#   （2026-09-26 第二轮：6 项测试、clippy 全绿，唯独 fmt 有 3 个文件差异，
#     就是漏了这一步。此脚本把该回路固化为资产，不再靠临时拼命令。）
#
# 前提：**本机 world-core 必须已提交且干净**，且 VM 签出区与本地 HEAD 一致。
#       理由：rustfmt 作用于 VM 的文件，VM 的文件 = 某次 push 的内容。
#       若本地有未提交改动或未推送提交，取回的补丁就对不上，宁可不做。
#
# 用法：
#   pwsh scripts/build/rustfmt.ps1            # 格式化并取回
#   pwsh scripts/build/rustfmt.ps1 -CheckOnly # 只检查，不修改（等价 CI 那一条）
#
# 退出码：0 = 已格式化/检查通过；1 = 前置条件不满足或检查未通过；2 = 传输失败
[CmdletBinding()]
param(
    [string]$Remote     = 'world',
    [string]$RemoteRepo = '/root/world.git',
    [string]$RemoteTree = '/root/world',
    [string]$SubDir     = 'world-core',
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [Text.Encoding]::UTF8

function Fail([string]$msg, [int]$code = 1) {
    Write-Host "[fmt] 中止：$msg" -ForegroundColor Red
    exit $code
}

# ── 1. 前置条件：本地干净 ────────────────────────────────────────────
$repoRoot = (git rev-parse --show-toplevel 2>$null)
if (-not $repoRoot) { Fail '不在 git 仓库内' }
$repoRoot = $repoRoot.Trim() -replace '/', '\'
Set-Location $repoRoot

$dirty = git status --porcelain -- $SubDir
if ($dirty) {
    Write-Host $dirty
    Fail "world-core 有未提交改动；先提交再 fmt（否则取回的补丁与工作区对不上）"
}

# ── 2. 前置条件：VM 签出区与本地 HEAD 一致 ──────────────────────────
$localHead = (git rev-parse HEAD).Trim()
$remoteHead = (ssh -o BatchMode=yes -o ConnectTimeout=15 $Remote `
        "git --git-dir=$RemoteRepo rev-parse HEAD" 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) { Fail "无法读取 VM HEAD：$remoteHead" 2 }
if ($remoteHead -ne $localHead) {
    Fail "VM HEAD($($remoteHead.Substring(0,8))) ≠ 本地 HEAD($($localHead.Substring(0,8)))；先 git push vm main"
}
Write-Host "[fmt] 本地与 VM 同处 $($localHead.Substring(0,8))，开始…" -ForegroundColor Cyan

# ── 3. 在 VM 内执行 rustfmt ─────────────────────────────────────────
if ($CheckOnly) {
    $script = "cd $RemoteTree/$SubDir || exit 9; cargo fmt --all -- --check"
    ssh -o BatchMode=yes -o ConnectTimeout=15 $Remote $script
    $rc = $LASTEXITCODE
    if ($rc -eq 0) { Write-Host '[fmt] 格式检查通过（与 CI 同口径）' -ForegroundColor Green }
    else { Write-Host "[fmt] 格式检查未通过 rc=$rc（上方为 rustfmt 差异）" -ForegroundColor Yellow }
    exit $rc
}

$script = @"
cd $RemoteTree/$SubDir || exit 9
cargo fmt --all || exit 8
export GIT_DIR=$RemoteRepo GIT_WORK_TREE=$RemoteTree
cd $RemoteTree
echo '@@@FILES@@@'; git diff --name-only -- $SubDir
echo '@@@PATCH@@@'; git diff -- $SubDir | base64 -w0; echo; echo '@@@END@@@'
"@
$script = $script -replace "`r`n", "`n"
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($script))
$out = (ssh -o BatchMode=yes -o ConnectTimeout=15 $Remote "echo $b64 | base64 -d | bash" 2>&1 | Out-String)

$files = [regex]::Match($out, '(?s)@@@FILES@@@(.*?)@@@PATCH@@@').Groups[1].Value.Trim()
$m = [regex]::Match($out, '(?s)@@@PATCH@@@\s*(\S+?)\s*@@@END@@@')
if (-not $m.Success) {
    # ⚠️ 空补丁 = VM 侧 rustfmt 无改动 = **成功**（2026-09-26 实测：这里曾误判为失败，
    #    因为哨兵之间的 base64 为空、正则 `(\S+?)` 匹配不到）。
    if ($out -match '@@@FILES@@@\s*@@@PATCH@@@\s*@@@END@@@') {
        Write-Host '[fmt] VM 侧 rustfmt 无改动——本机已是规范格式' -ForegroundColor Green
        exit 0
    }
    Write-Host $out
    Fail '未从 VM 取回补丁（rustfmt 失败或传输被截断）' 2
}

$bytes = [Convert]::FromBase64String($m.Groups[1].Value)
if ($bytes.Length -eq 0) {
    Write-Host '[fmt] VM 侧 rustfmt 无改动——本机已是规范格式' -ForegroundColor Green
    exit 0
}

$patch = Join-Path $env:TEMP 'world-core-rustfmt.patch'
[IO.File]::WriteAllBytes($patch, $bytes)
Write-Host "[fmt] 待回填文件：" -ForegroundColor Cyan
$files -split "`n" | Where-Object { $_ } | ForEach-Object { Write-Host "        $_" }

git apply --check $patch 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { Fail "补丁无法应用（工作区已变？）：$patch" 2 }
git apply $patch
if ($LASTEXITCODE -ne 0) { Fail "git apply 失败：$patch" 2 }

Write-Host '[fmt] 已回填本机工作区。请 git diff 复核后提交。' -ForegroundColor Green
Write-Host "[fmt] 补丁留档：$patch" -ForegroundColor DarkGray
exit 0
