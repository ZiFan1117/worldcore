# -*- coding: utf-8 -*-
'''反假勾审计（v3）——`cover-*` 的 10.1 用它核「已勾条目引用的断言名与路径是否真实存在」。

用法：`python scripts/gen/audit_checked_refs.py`（**在仓内任意 cwd 下都能跑**）

反假勾审计（v3，**重写**）：把 `cover-*` 里**已勾**条目引用的断言名与路径抽出来，核它们在仓内真实存在。
设计要点（v1／v2 的教训都写在这里）：
 · v1 误报 12 条：**把缩写当全名**比对（`d02` vs 真名 `d02_…`）⇒ 改**前缀匹配**；
 · v2 的"块级赦免"更坏：一个块里提一句"不存在"，就把该块**所有**引用都放过（连明明存在的 `policy.json` 也赦免）⇒
   那是**遮羞布**。⇒ v3 一律**按"这条引用所在的那一行"**裁定，且**逐条打印排除原因**（不静默放过）。
排除面**不写死类数**——**以输出里逐条打印的"原因串"为准**（写死就会烂：本文件自己就曾写"只有四种"，
而当时的实际原因已有六类；改法是把类数交给输出）。判据写在代码里、可复核。
'''
import io, re, sys
from pathlib import Path

# ★ 仓根按**脚本自身位置**推（本文件在 `scripts/gen/` 下 ⇒ 仓根＝上两级）；
#   原版写死了 `D:\Code\...`，那是「闸在版本控制之外」的同族问题（skill §九）。
R = Path(__file__).resolve().parent.parent.parent
def _resolve_cov() -> Path:
    """被审对象：**在役的第一个 `cover-*`；没有就取归档里最后一个 `cover-*`**。

    ★ 为什么不再写死（2026-09-28）：本工具曾把路径写死成
    `ninedim/06-变更/cover-unimplemented-capabilities/tasks.md`——那个 change **归档后**路径变了 ⇒ 工具直接崩
    （`FileNotFoundError`）。这与本仓「引用写命令＋步骤名、不写行号」是同一个坑：**写死的坐标会烂**。
    """
    # **优先归档件**：本工具的用处是核「已完成那件」的每个已勾条目的引用能不能解析；
    # 在役件通常还没勾几条（拿它当默认会把读数变成"已勾 0 条"，没有信息量）⇒ 用 `--cov` 显式指定。
    arch = sorted((R / 'ninedim/06-变更/archive').glob('*cover-*/tasks.md'))
    if arch:
        return arch[-1]
    live = sorted((R / 'changes').glob('cover-*/tasks.md'))
    if live:
        return live[0]
    raise SystemExit('[FAIL] 找不到任何 `cover-*/tasks.md`（在役或归档）——本工具的被审对象不在仓内')


COV = Path(sys.argv[sys.argv.index('--cov') + 1]) if '--cov' in sys.argv else _resolve_cov()
t = io.open(COV, encoding='utf-8', newline='').read()

fn_names = set()
for p in list((R / 'src').rglob('*.rs')) + list((R / 'tests').rglob('*.rs')):
    fn_names |= set(re.findall(r'fn\s+([a-z][a-z0-9_]*)',
                               io.open(p, encoding='utf-8', errors='replace').read()))

# ★ 2026-09-28 补强：**Python 的 `def` 名也收**。
# 为什么：本在册件里引的判据名（`j13_secmap_freshness`／`j14_judges_all_claimed`）真身在
# `scripts/verify/spec_bridge.py`，而上面那段只收 Rust 的 `fn` ⇒ 它们被误判"对不上"（**审计器的面太窄**）。
# 判据与守卫是 Python 写的，名字当然要能在 Python 里解析到。
for p in list((R / 'tools').rglob('*.py')) + list((R / 'tools').rglob('*.py')):
    fn_names |= set(re.findall(r'def\s+([a-z][a-z0-9_]*)',
                               io.open(p, encoding='utf-8', errors='replace').read()))

OUTSIDE = ('audit_checked_refs.py', 'audit_refs_v3.py', 'build_specmap.py', 'build_html.py', 'sync-vm.ps1',
           'push-vm.ps1', 'final_verify.ps1', 'signoff.py', 'check.sh', 'group6_verify.py', 'trace_matrix.py')
NEG = ('不存在', '（无此 delta）', '无此文件', '零命中')
EXPL = ('简称', '内部编号', '真名是', '真名', '映射到')


def _neg_adjacent(line: str, tok: str, window: int = 60) -> bool:
    """该引用**紧后面**（同一行、`window` 个字符内）是不是"它不存在"的声明。

    ★ 为什么必须"相邻"（2026-09-28，第三席实证的【洞①】）：旧版只要**行内任意位置**出现
    `不存在/无此文件/零命中/（无此 delta）` 就把**该行所有引用**一并赦免 ⇒
    一行里只要提一句"某某不存在"，**同行的真缺口也被放过**（实证：`zz99_ghost_assert` 全仓不存在，
    却因该行有"不存在"三字被计入"被排除"）。改成相邻窗口后，赦免只覆盖"它"说的那一个引用。
    """
    i = line.find('`%s`' % tok)
    if i < 0:
        return False
    tail = line[i + len(tok) + 2: i + len(tok) + 2 + window]
    # 只看**同一子句**：截到最近的子句分隔符（`；`／`。`／`——`／`|`）为止
    for sep in ('；', '。', '——', '|'):
        k = tail.find(sep)
        if k >= 0:
            tail = tail[:k]
    return any(w in tail for w in ('不存在', '无此文件', '零命中', '（无此 delta）'))


# 命令串的**首词**白名单（**认形态，不认空格**——见 `_looks_like_command` 的说明）
_CMD_HEADS = ('git', 'python', 'python3', 'bash', 'sh', 'cargo', 'cd', 'ls', 'run_tail', 'wc',
              'grep', 'sed', 'awk', 'tar', 'ssh', 'scp', 'echo', 'cat', 'head', 'tail')


def _looks_like_command(p: str) -> bool:
    """`p` 是不是一条**命令串**（而不是一个路径）。

    ★ 为什么必须"认形态"（2026-09-28，第三席实证的【洞②】）：旧判据是 `' ' in p` ——
    **路径里只要有空格就整类排除**。于是 `src/ghost file.rs`（一个**不存在**的幽灵路径）
    会被当成"仓外命令串"放过，**连"排除原因"都印成仓库外**，而它其实是个仓库内的坏路径。
    ⚠ 这条兜底是**承重**的：`python scripts/verify/module_graph.py`／`git ls-files …` 这类
    **真命令串**现在全靠它才不被当成路径去追存在性 ⇒ **不能简单删**，只能改认形态。
    """
    p = p.strip()
    if not p:
        return False
    if any(ch in p for ch in ('$(', '|', '>', '&&', ';')) or '"' in p or '`' in p:
        return True
    head = p.split()[0] if ' ' in p else ''
    return head in _CMD_HEADS


def _expl_adjacent(line: str, tok: str, window: int = 30) -> bool:
    """该引用**紧后面**（同一子句内）是不是"这是简称／内部编号／真名"的说明。

    ★ 为什么（2026-09-28，第三席点出的【洞④】，与洞①同形）：旧判据只要**行内任意位置**出现
    `简称/内部编号/真名/映射到`，就把该行**所有**引用赦免 ⇒ 一行里解释一句"`c23a` 是内部编号"，
    同行的幽灵引用（实证 `zz77_ghost_assert`，全仓不存在）也被放过。
    """
    i = line.find('`%s`' % tok)
    if i < 0:
        return False
    tail = line[i + len(tok) + 2: i + len(tok) + 2 + window]
    for sep in ('；', '。', '——', '|'):
        k = tail.find(sep)
        if k >= 0:
            tail = tail[:k]
    return any(w in tail for w in ('简称', '内部编号', '真名', '映射到'))


SHA = re.compile(r'^[0-9a-f]{7,40}$')
blocks = re.split(r'(?m)^(?=- \[[ x]\] \d+\.\d+)', t)
rows = []
for b in blocks:
    m = re.match(r'- \[([ x])\] (\d+\.\d+)', b)
    if m:
        rows.append((m.group(2), m.group(1) == 'x', b))

bad, excl = [], []
for num, checked, blk in rows:
    if not checked:
        continue
    lines = blk.split('\n')
    refs, paths = set(), set()
    for m in re.finditer(r'`([^`]+)`', blk):
        tok = m.group(1).strip()
        if SHA.match(tok):
            continue
        if '::' in tok:
            cand = tok.split('::')[-1].strip()
            if re.fullmatch(r'[a-z][a-z0-9_]*', cand):
                refs.add(cand)
        elif re.fullmatch(r'[a-z][a-z0-9_]*\d{2}[a-z0-9_]*', tok):
            refs.add(tok)
        if re.search(r'\.(rs|py|sh|md|json|csv)$', tok):
            paths.add(tok)

    def line_of(tok):
        return [ln for ln in lines if '`%s`' % tok in ln]

    for n in sorted(refs):
        if n in fn_names or any(x.startswith(n + '_') for x in fn_names):
            continue
        ls = line_of(n)
        why = None
        if any(_expl_adjacent(ln, n) for ln in ls):
            why = '该引用**紧后面**就是「简称／内部编号 → 真名」的映射说明（**子句内**判定，不再整行赦免）'
        elif any(_neg_adjacent(ln, n) for ln in ls):
            why = '该引用**紧后面**就是"它不存在"的声明（**相邻**判定，不再按整行赦免）'
        if why:
            excl.append('%s ← 名字 `%s`：%s' % (num, n, why))
        else:
            bad.append((num, '名字 `%s`' % n, '；'.join(ls)[:110]))

    for p in sorted(paths):
        cands = [R / p, R / 'world-core' / p, R / 'openspec' / p,
                 R / 'ninedim/06-变更/cover-unimplemented-capabilities' / p]
        # ★ 【洞③】收紧（2026-09-28，第三席实证）：**不许**再用「按文件名在整棵树里 rglob」兜底——
        #   那会把「目录写错」也放过（实证：`docs/S9-别的/测试-WC-ST-001-v0.1.md` 该目录不存在，
        #   只因别处有同名件就被静默算作"对得上"）。现在**只认候选根下的真实路径**；
        #   裸文件名（无目录）另行白名单，`tests/*.rs` 允许按名匹配（条目里常只写文件名）。
        if any(c.exists() for c in cands):
            continue
        # **裸文件名**（条目里常只写 `pairing.rs`／`module_graph.py`）⇒ 按**全仓同名**解析即可（那是合法简写）；
        # **带目录的路径** ⇒ 必须落在上面那些候选根之一，**不许**再用"别处有同名件"兜底（那正是【洞③】）。
        if '/' not in p and (any(R.rglob(p)) or any((R / 'world-core').rglob(p))):
            continue
        # **通配模式**（含 `*`）不是路径 ⇒ 单列"模式引用"，不计入缺口
        if '*' in p or '?' in p:
            excl.append('%s ← 路径 `%s`：通配模式（不是具体路径，不追存在性）' % (num, p))
            continue
        # **带目录的简写**（`carrier/mod.rs` 实为 `src/carrier/mod.rs`）⇒ 允许**后缀匹配**
        if any(str(x).replace('\\', '/').endswith('/' + p) for x in R.rglob('*') if x.is_file()):
            excl.append('%s ← 路径 `%s`：带目录的简写（按后缀匹配到真件）' % (num, p))
            continue
        ls = line_of(p)
        why = None
        if '{' in p and '}' in p:
            stem, rest = p.split('{', 1)
            body, tail = rest.split('}', 1)
            cs = [stem + x.strip() + tail for x in body.split(',')]
            if all((R / c).exists() or (R / 'world-core' / c).exists()
                   or any((R / 'world-core').rglob(Path(c).name)) for c in cs):
                why = '花括号路径，展开后 %d 个都在' % len(cs)
        if why is None and (Path(p).name in OUTSIDE or _looks_like_command(p)):
            why = '仓外工具名或命令串'
        if why is None and any(_neg_adjacent(ln, p) for ln in ls):
            why = '该引用**紧后面**就是"它不存在"的声明（**相邻**判定）'
        if why:
            excl.append('%s ← 路径 `%s`：%s' % (num, p, why))
        else:
            bad.append((num, '路径 `%s`' % p, '；'.join(ls)[:110]))

print('=== 已勾条目里「引用对不上」的（逐条）===')
for num, what, ctx in bad:
    print('  [对不上] %s：%s' % (num, what))
    print('            出处行：%s' % ctx)
print('\n=== 被排除的引用（逐条打印原因，不静默放过）===')
for e in excl:
    print('  ' + str(e)[:150])
print('\n===== 汇总 =====')
print('已勾 %d 条；引用对不上 = %d 条；被排除 = %d 条（原因见上）'
      % (sum(1 for _, c, _ in rows if c), len(bad), len(excl)))
