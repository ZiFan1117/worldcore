#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染链的主人：把**在册表**（法律）＋**部署面 uid 映射**渲成 `channel.json`。

## 它解决的那个洞

「哪个口＝哪个身份」只许有**一处权威**：`policy.json` 的 `listeners`（法律）。
但受理路径只读 `channel.json`（**渲染物**），而 `ChannelConfig::load` 又要求每条带 `uid`
（法律里那三格是 `socket`／`actor`／`owner`，**没有** `uid`）⇒ 「法律 → 渲染物」这一跳
长期以来**没有主人、没有门禁、不在版本控制**里 ⇒ 渲染物事实上是**第二在册**：
往里凭空加一行映射，口就能起，而法律里查不到，**没有任何东西会红**。

本脚本就是那一跳的主人，并把它做成**会红**的：多一条法律里没有的映射 ⇒ 非零退出。

## 为什么 uid 不写进法律（一条裁定的落点）

`uid` 是**部署面**的数（本机给谁哪个数字），不是世界的法条；写进法律会把载体专有信息
带进「谁都能读的那份法律」。⇒ 另立 `--uids` 一份**部署面映射**（哪个 socket 归哪个 uid），
由部署方给、随部署环境走。法律那三格**一字不动**。

## 三个用法

```sh
# ① 生成渲染物（默认写 stdout；部署方重定向到 /etc/world-core/channel.json）
python3 scripts/gen/render_channel.py --policy policy.json --uids deploy/listener_uids.json

# ② 对账：渲染物逐条必须能在法律里解析到（司法那条判据的**权威落点**）
python3 scripts/gen/render_channel.py --check /etc/world-core/channel.json --policy policy.json

# ③ 自测：正控必绿 ＋ 反例必红（反例＝往渲染物里加一行法律里没有的映射）
python3 scripts/gen/render_channel.py --self-test
```

## `deploy/listener_uids.json` 的形状（部署面件，**法律里不存这个数**）

```json
{ "channel": 1,
  "uids": { "/run/world-core/world.sock": 965,
            "/run/world-core/omarchy.sock": 1001,
            "/run/world-core/dsh.sock": null } }
```
`null` ＝ **该口在册但今天不渲染**（例如它的系统身份还没建）——生成时跳过并**如实列出**，
**不算红**（「在册未上线」是合法状态；把它当成红就等于禁止「先声明、后使用」）。

## 它与 Rust 侧的分工（一处事实一个载体）

- **本脚本**：构建期把「法律 → 渲染物」这一跳判死（`--check` 非零退出）。
- **`src/channel.rs::ChannelConfig::load_checked`**：受理期把同一件事再判一次，账外口**拒启**。
- 两处的错误码**同一个词**（`ext.world.Channel.UndeclaredListener`）——操作者看到的是一套话。
"""

import argparse
import io
import json
import os
import shutil
import sys
import tempfile

CODE_UNDECLARED = 'ext.world.Channel.UndeclaredListener'
CODE_NO_LAW = 'ext.world.Channel.NoDeclaredListeners'
CODE_BAD_UIDS = 'ext.world.Channel.BadUidMap'


def read_json(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def declared_listeners(policy_path):
    """从法律读在册表。**唯一**的对账基准。"""
    try:
        pol = read_json(policy_path)
    except Exception as e:                                      # 法律读不出来也是红
        raise SystemExit('%s: 读不出 %s：%s' % (CODE_NO_LAW, policy_path, e))
    listeners = pol.get('listeners')
    if not isinstance(listeners, list) or not listeners:
        raise SystemExit(
            '%s: %s 里没有 `listeners` 或它是空的——'
            '没有身份映射的通道等于无门之门' % (CODE_NO_LAW, policy_path))
    out = []
    for item in listeners:
        if not isinstance(item, dict):
            raise SystemExit('%s: %s 的 listeners 元素不是对象' % (CODE_NO_LAW, policy_path))
        sock = item.get('socket')
        actor = item.get('actor')
        if not isinstance(sock, str) or not isinstance(actor, str):
            raise SystemExit(
                '%s: %s 有一条监听项缺 socket 或 actor' % (CODE_NO_LAW, policy_path))
        out.append((sock, actor))
    return out


def load_uids(uids_path):
    try:
        m = read_json(uids_path)
    except Exception as e:
        raise SystemExit('%s: 读不出 %s：%s' % (CODE_BAD_UIDS, uids_path, e))
    uids = m.get('uids')
    if not isinstance(uids, dict) or not uids:
        raise SystemExit(
            '%s: %s 里没有 `uids` 或它是空的' % (CODE_BAD_UIDS, uids_path))
    for k, v in uids.items():
        if v is not None and (not isinstance(v, int) or isinstance(v, bool) or v < 0):
            raise SystemExit(
                '%s: %s 的 uids[%s] 不是非负整数（也不是 null）' % (CODE_BAD_UIDS, uids_path, k))
    return uids


def render(law, uids):
    """在册表 ＋ uid 映射 ⇒ 渲染物（与 `ChannelConfig::load` 认的形状逐字一致）。"""
    # ① 映射里不许有法律里没有的 socket —— **账外口，生成期就红**。
    law_socks = set(s for s, _ in law)
    extra = sorted(k for k in uids if k not in law_socks)
    if extra:
        raise SystemExit(
            '%s: 部署面映射里有 %d 个 socket 不在法律 %s 的 listeners 里：%s——'
            '身份映射只许有一处权威（法律），账外口一律不成' % (
                CODE_UNDECLARED, len(extra), 'policy.json', extra))
    rows, skipped = [], []
    for sock, actor in law:
        if sock not in uids:
            raise SystemExit(
                '%s: 法律里的口 %s 在 uid 映射里没有一行——'
                '要么给它一个 uid，要么显式写 null（＝在册未上线、今天不渲染）' % (
                    CODE_BAD_UIDS, sock))
        uid = uids[sock]
        if uid is None:
            skipped.append(sock)
            continue
        rows.append({'socket': sock, 'actor': actor, 'uid': uid})
    if not rows:
        raise SystemExit(
            '%s: 法律里每条口都写了 null ⇒ 渲染出来是空的，'
            '而没有身份映射的通道等于无门之门' % CODE_NO_LAW)
    return rows, skipped


def check(render_path, law, uids=None):
    """对账：渲染物逐条必须能在法律里解析到（socket 与 actor 同时相同）。"""
    try:
        got = read_json(render_path)
    except Exception as e:
        raise SystemExit(
            '%s: 读不出渲染物 %s：%s' % (CODE_UNDECLARED, render_path, e))
    rows = got.get('listeners')
    if not isinstance(rows, list) or not rows:
        raise SystemExit(
            '%s: 渲染物 %s 里没有 `listeners` 或它是空的' % (CODE_UNDECLARED, render_path))
    law_pairs = set(law)
    bad = []
    for item in rows:
        if not isinstance(item, dict):
            bad.append(('未成对象', repr(item)))
            continue
        pair = (item.get('socket'), item.get('actor'))
        if pair not in law_pairs:
            bad.append(pair)
        elif uids is not None and pair[0] in uids and uids[pair[0]] != item.get('uid'):
            bad.append(('%s 的 uid 与部署面映射不符（渲染物 %r，映射 %r）' % (
                pair[0], item.get('uid'), uids[pair[0]]), ''))
    if bad:
        lines = '\n'.join('    · %r' % (b,) for b in bad)
        raise SystemExit(
            '%s: 渲染物 %s 里有 %d 条在法律里解析不到（账外口）：\n%s\n'
            '  => 受理路径只读渲染物；不拦下来，总线上就会多出一条法律里没有的映射。'
            % (CODE_UNDECLARED, render_path, len(bad), lines))
    return len(rows)


def self_test():
    """正控必绿 ＋ 反例必红。反例的形态＝**往渲染物里加一行映射**（真实违规形态）。"""
    d = tempfile.mkdtemp(prefix='render-channel-')
    rc = 0
    try:
        pol = os.path.join(d, 'policy.json')
        uidm = os.path.join(d, 'uids.json')
        ren = os.path.join(d, 'channel.json')
        io.open(pol, 'w', encoding='utf-8').write(json.dumps({
            'listeners': [
                {'socket': '/run/world-core/world.sock', 'actor': 'world://core',
                 'owner': 'world-core'},
                {'socket': '/run/world-core/omarchy.sock',
                 'actor': 'world://presence/omarchy', 'owner': 'omarchy'},
            ]}, ensure_ascii=False))
        io.open(uidm, 'w', encoding='utf-8').write(json.dumps({
            'channel': 1,
            'uids': {'/run/world-core/world.sock': 965,
                     '/run/world-core/omarchy.sock': 1001}}, ensure_ascii=False))
        law = declared_listeners(pol)
        rows, skipped = render(law, load_uids(uidm))
        print('  正控 · 生成：%d 条渲染、%d 条在册未渲染（跳过 %r）' % (len(rows), len(skipped), skipped))
        io.open(ren, 'w', encoding='utf-8').write(json.dumps(
            {'channel': 1, 'listeners': rows}, ensure_ascii=False))
        n = check(ren, law, load_uids(uidm))
        print('  [ok  ] 正控 · --check 绿（%d 条全在法律里）' % n)

        # 反例 A：渲染物里凭空多一条法律里没有的映射（真实违规形态＝加一行）
        ghost = os.path.join(d, 'channel-ghost.json')
        io.open(ghost, 'w', encoding='utf-8').write(json.dumps({'channel': 1, 'listeners': [
            {'socket': '/run/world-core/world.sock', 'actor': 'world://core', 'uid': 965},
            {'socket': '/run/ghost.sock', 'actor': 'world://ghost', 'uid': 965},
        ]}, ensure_ascii=False))
        rc_a = probe(lambda: check(ghost, law, load_uids(uidm)))
        ok_a = rc_a != 0
        print('  [%s] 反例 A · 渲染物多一行账外映射 ⇒ 非零退出（实得 rc=%d）'
              % ('ok  ' if ok_a else 'FAIL', rc_a))
        rc = rc or (0 if ok_a else 1)

        # 反例 B：部署面映射里多一条法律里没有的 socket（生成期就该红）
        baduid = os.path.join(d, 'uids-extra.json')
        io.open(baduid, 'w', encoding='utf-8').write(json.dumps({
            'channel': 1,
            'uids': {'/run/world-core/world.sock': 965,
                     '/run/world-core/omarchy.sock': 1001,
                     '/run/ghost.sock': 965}}, ensure_ascii=False))
        rc_b = probe(lambda: render(law, load_uids(baduid)))
        ok_b = rc_b != 0
        print('  [%s] 反例 B · uid 映射多一条账外 socket ⇒ 非零退出（实得 rc=%d）'
              % ('ok  ' if ok_b else 'FAIL', rc_b))
        rc = rc or (0 if ok_b else 1)

        # 反例 C：uid 映射漏一条法律里的口（不写 null 就是漏）
        miss = os.path.join(d, 'uids-miss.json')
        io.open(miss, 'w', encoding='utf-8').write(json.dumps({
            'channel': 1, 'uids': {'/run/world-core/world.sock': 965}},
            ensure_ascii=False))
        rc_c = probe(lambda: render(law, load_uids(miss)))
        ok_c = rc_c != 0
        print('  [%s] 反例 C · 映射漏一条在册口 ⇒ 非零退出（实得 rc=%d）'
              % ('ok  ' if ok_c else 'FAIL', rc_c))
        rc = rc or (0 if ok_c else 1)

        # 正控 D：在册未上线（显式 null）⇒ 不许红
        nullm = os.path.join(d, 'uids-null.json')
        io.open(nullm, 'w', encoding='utf-8').write(json.dumps({
            'channel': 1,
            'uids': {'/run/world-core/world.sock': 965,
                     '/run/world-core/omarchy.sock': None}}, ensure_ascii=False))
        try:
            rows2, skip2 = render(law, load_uids(nullm))
            ok_d = len(rows2) == 1 and skip2 == ['/run/world-core/omarchy.sock']
        except SystemExit:
            ok_d = False
        print('  [%s] 正控 D · 在册未上线（显式 null）⇒ 不红、且如实列为未渲染'
              % ('ok  ' if ok_d else 'FAIL'))
        rc = rc or (0 if ok_d else 1)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print('  ---- 自测结论：%s ----' % ('全通过' if rc == 0 else '有红'))
    return rc


def probe(fn):
    """跑一个会 `SystemExit` 的分支，把它的退出码取回来（**不吞掉**）。"""
    try:
        fn()
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) and e.code != 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument('--policy', default='src/gate/policy.json')
    ap.add_argument('--uids', default='deploy/listener_uids.json')
    ap.add_argument('--check', '--channel', dest='check', metavar='RENDER_JSON',
                    help='对账：渲染物每条必须在法律里解析到（--channel 是它的别名）')
    ap.add_argument('--out', default='-')
    ap.add_argument('--self-test', action='store_true')
    a = ap.parse_args(argv)
    # 控制台编码与本工具无关：本机是 GBK 时，一句含非 GBK 字符的**报错**会变成 traceback，
    # 于是"红"看起来像"崩"。⇒ 输出一律降级替换，绝不让编码问题冒充判据。
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors='replace')
        except Exception:
            pass

    if a.self_test:
        return self_test()

    law = declared_listeners(a.policy)

    if a.check:
        # ★ 机器契约（供门禁调用，别用"有没有输出"判成败）：
        #   0 = PASS ／ 1 = FAIL（账外口、uid 与映射不符）／ 2 = SKIP（**未校验**：渲染物不存在）
        #   —— G18：渲染物不在时**不许判绿**，"文件不在"不得被读成"合规"。
        if not os.path.isfile(a.check):
            sys.stdout.write('STATUS=SKIP\n')
            sys.stdout.write('渲染物不存在：%s —— **未校验**（不是绿）。\n' % a.check)
            sys.stdout.write('  处置：先由部署方生成它（本工具不带 --check 直接跑即可生成）。\n')
            return 2
        uids = load_uids(a.uids) if os.path.isfile(a.uids) else None
        try:
            n = check(a.check, law, uids)
        except SystemExit as e:
            sys.stdout.write('STATUS=FAIL\n')
            sys.stdout.write('%s\n' % (e.code,))
            return 1
        sys.stdout.write('STATUS=PASS\n')
        sys.stdout.write('渲染物对账通过：%d 条，全部解析到 %s 的 listeners\n' % (n, a.policy))
        return 0

    rows, skipped = render(law, load_uids(a.uids))
    text = json.dumps({
        'channel': 1,
        '_source': 'policy.json 的 listeners 段的渲染物；本文件不是第二权威'
                   '（由 scripts/gen/render_channel.py 生成，勿手改）',
        'listeners': rows,
    }, ensure_ascii=False, indent=2, sort_keys=False) + '\n'
    if a.out == '-':
        sys.stdout.write(text)
    else:
        with io.open(a.out, 'w', encoding='utf-8') as f:
            f.write(text)
        sys.stdout.write('已写 %s（%d 条）\n' % (a.out, len(rows)))
    if skipped:
        sys.stdout.write('在册未渲染（部署面映射写了 null，如实列出）：%s\n'
                         % ', '.join(skipped))
    return 0


if __name__ == '__main__':
    sys.exit(main())
