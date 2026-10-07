# -*- coding: utf-8 -*-
"""规格计数审计（**仓内可复算**，取代仓外那份 `D:\\Code\\_specmap\\count_13.py`）。

数什么（两类用途）：
  · `fc-2026-003` 的 **`1.3`**：逐能力数 `### Requirement` / `#### Scenario` / `- **证据` 三类行
    ——「改前改后逐能力计数相等」就按这三列判；
  · `fc-2026-003` 的 **`1.4`**：数"长 Requirement"（**标题行起**到下一个 `####`／`###` 之间 > 500 **字符**，含空白）。

用法：
    python scripts/verify/spec_length_audit.py               # 打表（并自动与改前快照比对）
    python scripts/verify/spec_length_audit.py --json        # 打 JSON（**数值现取，不手抄**）
    python scripts/verify/spec_length_audit.py --self-test   # 自证：夹具 ＋ 边界（500/501）＋ 快照对照

它为什么**不**接进 `check.sh`：
    `check.sh` 里的审计工具都是**常驻判据**（会红、红了就代表仓里出错）。本文具的两个面**都不是常驻判据**：
    `1.3` 面绑的是 `fc-2026-003` 的**改前快照**（"这一件不许动那三类行"的**临时**约束）；`1.4` 面 `openspec validate` 自己就会报。
    ⇒ **本件归档后，本文具应随件退役**（skill：不做额外件）。它现在在仓内的理由是：评审席与下一位动手的人要能在
    **仓里**复算 `fc-2026-003`，而不是去仓外某目录找脚本（skill §九：「闸在版本控制之外等于没有闸」）。

**口径的两个已知边界（写给读者）**：① 长 Requirement 的计数**含标题行与段间空行**（比"不含标题行"的口径大）；
② 三类行按**行首正则**（`^### Requirement: ` 等）⇒ 正文里缩进的同名字样不计。
"""
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / 'openspec' / 'specs'
SNAPSHOT = ROOT / 'openspec' / 'changes' / 'fc-2026-003-doc-consolidation' / 'spec-counts-before.json'

COLS = ('Requirement', 'Scenario', '证据行', '长Requirement(>500字)')
THREE = COLS[:3]          # `1.3` 只管这三列
LONG = COLS[3]            # `1.4` 管这一列


def count_in(text: str) -> dict:
    """对**一份规格文本**计数（抽成纯函数 ⇒ 自证可以喂夹具）。"""
    segs = re.split(r'(?m)^### Requirement: ', text)[1:]
    return {
        'Requirement': len(re.findall(r'(?m)^### Requirement: ', text)),
        'Scenario': len(re.findall(r'(?m)^#### Scenario: ', text)),
        '证据行': len(re.findall(r'(?m)^- \*\*证据', text)),
        LONG: sum(1 for s in segs if len(re.split(r'(?m)^#### |^### ', s, maxsplit=1)[0]) > 500),
    }


def measure(specs_dir: Path = SPECS) -> dict:
    return {p.parent.name: count_in(io.open(p, encoding='utf-8').read())
            for p in sorted(specs_dir.rglob('spec.md'))}


def self_test() -> int:
    """**判据自己会不会红**：夹具 ＋ 边界。按 skill §五，任何"检查通过"的结论都要说得出它**为什么可能失败**。"""
    bad = []
    # ① 三类行：只认行首；缩进的不算
    fixture = ('### Requirement: A\n' + 'x' * 400 + '\n#### Scenario: s\n- **证据**：a\n'
               '  ### Requirement: 缩进的不算\n#### Scenario: s2\n- **证据（待补）**：b\n')
    got = count_in(fixture)
    if (got['Requirement'], got['Scenario'], got['证据行']) != (1, 2, 2):
        bad.append('① 三类行计数：期望 (1,2,2) 实得 (%d,%d,%d)' % (got['Requirement'], got['Scenario'], got['证据行']))
    # ② 500／501 边界（含标题行的口径 ⇒ 正好 500 不算长、501 才算）
    for n, want in ((500, 0), (501, 1)):
        head = '### Requirement: T\n'
        pad = n - len(head)
        f2 = head + 'y' * pad + '#### Scenario: s\n'
        seg = re.split(r'(?m)^#### |^### ', re.split(r'(?m)^### Requirement: ', f2)[1], maxsplit=1)[0]
        if len(seg) != n:
            bad.append('② 夹具没造准：期望长度 %d 实得 %d' % (n, len(seg)))
        elif count_in(f2)[LONG] != want:
            bad.append('② %d 字符应判为%s长' % (n, '不' if want == 0 else ''))
    # ③ 快照对照可用（现取里出现了快照没有的能力 ⇒ 对照失效，必须红）
    if SNAPSHOT.exists():
        live = measure()
        miss = [c for c in live if c not in json.loads(SNAPSHOT.read_text(encoding='utf-8'))]
        if miss:
            bad.append('③ 现取里出现了快照没有的能力：%s' % '、'.join(miss))
    if bad:
        print('—— 自证失败 %d 项 ——' % len(bad))
        for b in bad:
            print('  ✗ %s' % b)
        return 1
    print('—— 自证通过（三类行夹具 1 组 ＋ 边界 2 例 ＋ 快照对照 1 项）——')
    return 0


def main() -> int:
    if '--self-test' in sys.argv:
        return self_test()
    out = measure()
    if '--json' in sys.argv:
        print(json.dumps(out, ensure_ascii=False))
        return 0
    print('=== 逐能力计数（`1.3` 的验收面 ＋ `1.4` 的长 Requirement）===')
    print('  %-24s %4s %4s %5s %6s' % ('能力', 'Req', 'Scen', '证据行', '长Req'))
    tot = dict.fromkeys(COLS, 0)
    for cap, d in out.items():
        print('  %-24s %4d %4d %5d %6d' % (cap, d['Requirement'], d['Scenario'], d['证据行'], d[LONG]))
        for k in COLS:
            tot[k] += d[k]
    print('  %-24s %4d %4d %5d %6d' % ('合计', tot['Requirement'], tot['Scenario'], tot['证据行'], tot[LONG]))
    if SNAPSHOT.exists():
        before = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
        bad = [c for c in out if c in before and any(out[c][k] != before[c].get(k) for k in THREE)]
        drift = [c for c in out if c in before and out[c][LONG] != before[c].get(LONG)]
        print('  —— 与改前快照比对：`1.3` 只比前 3 列（标题／Scenario／证据行）——')
        print('     `1.3` 面不符的能力：%s' % ('、'.join(bad) if bad else '无 ✓'))
        print('     `1.4` 面（长 Req 条数）变了的能力：%s（**这是 `1.4` 的成绩，不是 `1.3` 的违规**）'
              % ('、'.join(drift) if drift else '无'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
