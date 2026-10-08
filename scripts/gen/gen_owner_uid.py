# -*- coding: utf-8 -*-
"""部署面映射生成器：`owner`（**名字**）→ `uid`（**数字**）。

判据正文见 `D:\\Code\\heavy-archive\\语义世界-架构-退役-2026-10-06\\规程-接入载体.md` §3 第 4 条与 §5 AC-6；
本件是它的**生产者**（唯一）。

## 一个事实一个载体

- **唯一载体**：`deploy/listener_uids.json`（形状由渲染器 `scripts/gen/render_channel.py` 定死）
  `{"channel":1,"uids":{"<socket 绝对路径>":<uid 整数或 null>, ...}}`
- **生产者**（本件）／**消费者**（`render_channel.py`，只读）／**安装**（`scripts/release/install.sh` 调本件）。
- ★**为什么必须有一个映射件**：法律（`policy.json.listeners`）写的是 `owner`＝**名字**
  （`world-core`／`dsh`／`omarchy`…），而受理要的是 `uid`＝**数字**
  （`channel.rs::bind()` 用 `chown`，套接字 0600 ⇒ **只有那个 uid 连得上**）。
  名字→数字这一步**不许靠猜**，也不许在渲染器里各写一遍。

## 口径（会红的都列在这里）

1. ★**只许列法律里已有的 socket**：映射里多一条 ⇒ 红（`ext.world.Channel.UndeclaredListener`）。
2. ★**法律里的口必须有行**：缺一行 ⇒ 红。值要么是**整数**，要么是**显式 `null`**。
3. ★**`null` ＝「在册未上线」**（机器上没有这个用户 ⇒ 没有 uid 可填）⇒ **不红，但必须报出来**。
   ★**不许**把"查不到"写成 0 或编一个数（那会让套接字 chown 到 root，是**提权**）。
4. ★**法律读不出来** ⇒ rc=2（`无法判定`），**不许**当成"没有口"。

## 用法

```text
python3 scripts/gen/gen_owner_uid.py --out deploy/listener_uids.json [--policy policy.json]   # 生成
python3 scripts/gen/gen_owner_uid.py --check [--out …] [--policy …]                            # 只核对，不写
python3 scripts/gen/gen_owner_uid.py --self-test                                               # 自证：反例必红
```

退出码：`0` 通过 ／ `1` 核对失败（多口／缺行／uid 不符）／ `2` 输入不可用（法律读不到）。

★**本件不写 `/etc`**：装到现役载体上由 `install.sh` 复制（本件只产出仓内那一份）。
★**本件不伪造**：查不到的 owner 一律 `null` ＋ 报告，**绝不**写 0。
"""
import io
import json
import os
import shutil
import sys
import tempfile

try:                     # ★ 名字 → uid 是 **POSIX 专有**（Windows 无 `pwd`）
    import pwd
except ImportError:      # pragma: no cover —— 非 POSIX 主机
    pwd = None

HAS_PWD = pwd is not None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                                   # 
DEFAULT_POLICY = os.path.join(ROOT, 'policy.json')
DEFAULT_OUT = os.path.join(ROOT, 'deploy', 'listener_uids.json')

UNDECLARED = 'ext.world.Channel.UndeclaredListener'


def read_json(path):
    with io.open(path, encoding='utf-8') as f:
        return json.load(f)


def law_listeners(policy_path):
    """法律里的在册口：`[(socket, actor, owner_or_None)]`；读不出来 ⇒ `None`（不可判定）。"""
    try:
        pol = read_json(policy_path)
    except Exception:
        return None
    ls = pol.get('listeners')
    if not isinstance(ls, list):
        return None
    out = []
    for x in ls:
        if not isinstance(x, dict) or not isinstance(x.get('socket'), str):
            return None
        owner = x.get('owner')
        out.append((x['socket'], x.get('actor'), owner if isinstance(owner, str) else None))
    return out


def resolve(owner):
    """名字 → uid。★查不到返 `None`（**不是 0**）；`owner` 缺、或本机不是 POSIX ⇒ 也叫查不到。"""
    if not owner or not HAS_PWD:
        return None
    try:
        return pwd.getpwnam(owner).pw_uid
    except KeyError:
        return None


def build(policy_path):
    """算出映射 `{"channel":1,"uids":{…}}`；法律不可判定 ⇒ `None`。"""
    ls = law_listeners(policy_path)
    if ls is None:
        return None
    uids = {}
    for sock, _actor, owner in ls:
        uids[sock] = resolve(owner)
    return {'channel': 1, 'uids': uids}


def compare(want, got_path):
    """`want`（算出来的）vs `got_path`（件上的）⇒ `(reds, notes)`。"""
    reds, notes = [], []
    try:
        got = read_json(got_path)
    except Exception as e:
        return ['映射件读不出来：%s' % e], []
    gu = got.get('uids')
    if not isinstance(gu, dict):
        return ['映射件没有 `uids` 对象'], []
    wu = want['uids']
    extra = sorted(k for k in gu if k not in wu)
    if extra:
        reds.append('%s：映射里多了法律里没有的口 %s' % (UNDECLARED, extra))
    miss = sorted(k for k in wu if k not in gu)
    if miss:
        reds.append('%s：法律里的口在映射里缺行 %s' % (UNDECLARED, miss))
    for k in sorted(set(gu) & set(wu)):
        if gu[k] != wu[k]:
            # ★ null（在册未上线）与"写成 0"必须分开：0 是**提权**，不是"没上线"
            reds.append('%s：%s 的 uid 不符（法律侧算得 %r，映射里 %r）'
                        % (UNDECLARED, k, wu[k], gu[k]))
    for k in sorted(wu):
        if wu[k] is None:
            notes.append('在册未上线（名字解析不到 uid，写 null）：%s' % k)
    return reds, notes


def cmd_build(policy_path, out_path):
    if not HAS_PWD:
        # ★ fail-closed：非 POSIX 主机解析不了名字 ⇒ **拒绝生成**，
        #   免得产出一份"全是 null"的映射件被当成真件（那是"没做到写成做到了"）。
        print('ext.world.Channel.NoNameResolver: 本机不是 POSIX（没有 `pwd`）⇒ '
              '无法把 `owner` 解析成 uid ⇒ **拒绝生成**（不产出全是 null 的映射件）。rc=2')
        return 2
    want = build(policy_path)
    if want is None:
        print('ext.world.Channel.LawUnreadable: %s 里读不出 `listeners` ⇒ 无法判定（rc=2）' % policy_path)
        return 2
    text = json.dumps(want, ensure_ascii=False, indent=2, sort_keys=True) + '\n'
    d = os.path.dirname(os.path.abspath(out_path))
    if d:
        try:
            os.makedirs(d)
        except OSError:
            pass
    with io.open(out_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    nulls = [k for k, v in want['uids'].items() if v is None]
    print('已写 %s（%d 条；其中在册未上线 %d 条%s）'
          % (out_path, len(want['uids']), len(nulls),
             '：' + ','.join(sorted(nulls)) if nulls else ''))
    return 0


def cmd_check(policy_path, out_path):
    want = build(policy_path)
    if want is None:
        print('ext.world.Channel.LawUnreadable: %s 里读不出 `listeners` ⇒ 无法判定（rc=2）' % policy_path)
        return 2
    if not os.path.isfile(out_path):
        print('STATUS=SKIP')
        print('映射件 %s 不存在 ⇒ **未校验**（不是通过）' % out_path)
        return 2
    reds, notes = compare(want, out_path)
    print('命令 = python scripts/gen/gen_owner_uid.py --check --policy %s --out %s' % (policy_path, out_path))
    print('法律在册 %d 条；映射件 %s' % (len(want['uids']), out_path))
    for n in notes:
        print('  [报告] %s' % n)
    for r in reds:
        print('  [FAIL] %s' % r)
    if reds:
        print('STATUS=FAIL')
        return 1
    print('STATUS=PASS')
    return 0


def self_test():
    """反例：每条口径都要会红（多口／缺行／uid 不符／法律读不出）。"""
    print('== 自测：每条口径都要会红 ==')
    tmp = tempfile.mkdtemp(prefix='owner-uid-')
    bad = 0
    try:
        pol = os.path.join(tmp, 'policy.json')
        out = os.path.join(tmp, 'listener_uids.json')
        me = pwd.getpwuid(os.getuid()).pw_name if HAS_PWD else '<non-posix>'
        with io.open(pol, 'w', encoding='utf-8', newline='\n') as f:
            json.dump({'listeners': [
                {'socket': '/run/x/a.sock', 'actor': 'world://core', 'owner': me},
                {'socket': '/run/x/nobody.sock', 'actor': 'world://presence/nobody',
                 'owner': 'no-such-user-ac-xyz'},
            ]}, f)

        want = build(pol)
        good = want['uids']['/run/x/a.sock']
        ok_null = want['uids']['/run/x/nobody.sock'] is None
        if HAS_PWD:
            print('  [%s] 名字解析：本机用户 %s ⇒ uid=%r；不存在的名字 ⇒ null=%s'
                  % ('OK' if (isinstance(good, int) and ok_null) else '★错', me, good, ok_null))
            if not (isinstance(good, int) and ok_null):
                bad += 1
        else:
            # ★ G18：环境不成立（非 POSIX）⇒ 这一档**未校验**，**不判绿也不判红**
            print('  [SKIP] 名字解析：本机不是 POSIX（无 `pwd`）⇒ 这一档**未校验**（不是通过）；'
                  '`--build` 已 fail-closed 拒写')
            print('  STATUS=SKIP(name-resolution)')

        def write(uids):
            with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
                json.dump({'channel': 1, 'uids': uids}, f)

        def want_red(tag, uids, needle):
            write(uids)
            reds, _ = compare(want, out)
            hit = any(needle in r for r in reds)
            print('  [%s] %s -> %s' % ('红-OK' if hit else '★没红', tag, reds or '无'))
            return 0 if hit else 1

        write(want['uids'])
        reds, notes = compare(want, out)
        print('  [%s] 正控：与法律一致 -> %s%s'
              % ('绿-OK' if not reds else '★假红', reds or '无',
                 ('；报告=%s' % notes) if notes else ''))
        if reds:
            bad += 1

        bad += want_red('多一条法律里没有的口', dict(want['uids'], **{'/run/x/evil.sock': 0}),
                        UNDECLARED)
        d = dict(want['uids'])
        d.pop('/run/x/a.sock')
        bad += want_red('法律里的口缺行', d, UNDECLARED)
        d2 = dict(want['uids'])
        d2['/run/x/nobody.sock'] = 0                    # ★ 把"在册未上线"写成 0 ＝ 提权
        bad += want_red('把 null 写成 0（提权）', d2, UNDECLARED)

        with io.open(pol, 'w', encoding='utf-8', newline='\n') as f:
            f.write('{"policy":1}')
        rc = cmd_check(pol, out)
        print('  [%s] 法律读不出 listeners -> rc=%d（期望 2）' % ('OK' if rc == 2 else '★错', rc))
        if rc != 2:
            bad += 1

        print('自测结论 = %s' % ('通过' if bad == 0 else '有 %d 条没红/出错' % bad))
        return 0 if bad == 0 else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def parse(argv):
    pol, out, mode = DEFAULT_POLICY, DEFAULT_OUT, 'build'
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--policy' and i + 1 < len(argv):
            pol = argv[i + 1]; i += 2; continue
        if a == '--out' and i + 1 < len(argv):
            out = argv[i + 1]; i += 2; continue
        if a == '--check':
            mode = 'check'; i += 1; continue
        if a == '--build':
            mode = 'build'; i += 1; continue
        print('未知参数：%s\n用法：python3 scripts/gen/gen_owner_uid.py [--build|--check] '
              '[--policy <path>] [--out <path>] | --self-test' % a, file=sys.stderr)
        return None, None, None
    return pol, out, mode


def main():
    if '--self-test' in sys.argv:
        return self_test()
    pol, out, mode = parse(sys.argv[1:])
    if mode is None:
        return 1
    return cmd_check(pol, out) if mode == 'check' else cmd_build(pol, out)


if __name__ == '__main__':
    sys.exit(main())
