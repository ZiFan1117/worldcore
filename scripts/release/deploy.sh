#!/bin/bash
# ★★★ AI-OS 部署：把【仓里】的东西推到【这台机器】上（幂等，可反复跑）
#
# ★ 作者令（逐字）：「把我们现在本地改好的那个源文件，全部推到虚拟机上」
#
# 用法（在 VM 上，仓已 scp 到 /root/aios）：
#   bash /root/aios/distro/deploy.sh            # 只装文件 + 重启
#   bash /root/aios/distro/deploy.sh --no-restart
#
# ★ 幂等：重复跑不会出事；旧件先备份成 *.bak-<时分>。
set -u

REPO="${REPO:-/root/aios}"
PREFIX="/usr/lib/aios"
UNITDIR="/etc/systemd/system"
TS=$(date +%H%M)
RESTART=1
[ "${1:-}" = "--no-restart" ] && RESTART=0

echo "=== 0 来源 ==="
echo "  REPO=$REPO"
echo "  PREFIX=$PREFIX"

echo "=== 1 我方源码 src/ ==="
rm -rf "$PREFIX/src"
mkdir -p "$PREFIX/src"
cp -a "$REPO/src/." "$PREFIX/src/"
# ★★ 旧代码【不部署】—— src/legacy/ 只是归档（★ 作者令：统一放到一个地方，而且没啥用了）
rm -rf "$PREFIX/src/legacy"
find "$PREFIX/src" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
echo "  py: $(find "$PREFIX/src" -name '*.py' | wc -l) 个"

echo "=== 2 数据（映射表 ／ 本体法 ／ sysknife 件）==="
mkdir -p "$PREFIX"
for f in "$REPO"/distro/computer/*; do
  b=$(basename "$f")
  [ -f "$PREFIX/$b" ] && cp -a "$PREFIX/$b" "$PREFIX/$b.bak-$TS"
  cp -a "$f" "$PREFIX/$b"
  echo "  $b  $(stat -c%s "$f") 字节"
done
# ★ command-map.jsonl 必须用【156 条】那份（distro/computer/command-map-sysknife.jsonl）
if [ -f "$PREFIX/command-map-sysknife.jsonl" ]; then
  cp -a "$PREFIX/command-map.jsonl" "$PREFIX/command-map.jsonl.bak-$TS" 2>/dev/null || true
  cp -a "$PREFIX/command-map-sysknife.jsonl" "$PREFIX/command-map.jsonl"
  echo "  command-map.jsonl ← sysknife版（$(wc -l < "$PREFIX/command-map.jsonl") 条）"
fi
if [ -f "$REPO/crates/aios-ontology/data/ontology.json" ]; then
  [ -f "$PREFIX/ontology.json" ] && cp -a "$PREFIX/ontology.json" "$PREFIX/ontology.json.bak-$TS"
  cp -a "$REPO/crates/aios-ontology/data/ontology.json" "$PREFIX/ontology.json"
  echo "  ontology.json  $(stat -c%s "$PREFIX/ontology.json") 字节"
fi

echo "=== 3 systemd 单元 ==="
for u in aios-bus aios-ontology aios-computer aios-presentation aios-presentation-render aios-space aios-agent; do
  s="$REPO/distro/systemd/$u.service"
  if [ -f "$s" ]; then
    [ -f "$UNITDIR/$u.service" ] && cp -a "$UNITDIR/$u.service" "/etc/systemd/system/$u.service.bak-$TS"
    cp -a "$s" "$UNITDIR/$u.service"
    echo "  $u.service"
  fi
done
# ★ aios-bus 的 ws 端点覆盖（★ 只在本机加）
if [ -d /etc/systemd/system/aios-bus.service.d ]; then
  echo "  aios-bus 的 override.conf 保留不动"
fi
# ★★ 修 SELinux 那个坑：cp -a 会把源文件的上下文带过来（admin_home_t）⇒
#    systemd 读不了单元、进程也读不了 /usr/lib/aios 的数据。
#    必须 chmod 644 ＋ restorecon（现取：不加就报 "Failed to open …: Permission denied"）。
chmod 644 /etc/systemd/system/aios-*.service 2>/dev/null || true
restorecon -R /etc/systemd/system/aios-*.service 2>/dev/null || true
restorecon -R "$PREFIX/src" "$PREFIX"/*.json "$PREFIX"/command-map*.jsonl 2>/dev/null || true
echo "  SELinux 上下文已恢复"
systemctl daemon-reload

echo "=== 4 校验：python 能不能编 ==="
BAD=0
for f in $(find "$PREFIX/src" -name '*.py'); do
  python3 -m py_compile "$f" 2>/dev/null || { echo "  ✗ 编不过: $f"; BAD=1; }
done
[ $BAD -eq 0 ] && echo "  ★ 全部编译通过 ✓" || echo "  ✗ 有文件编不过"
find "$PREFIX/src" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

if [ $RESTART -eq 0 ]; then echo "=== 5 不重启（--no-restart）==="; exit 0; fi

echo "=== 5 重启 ==="
systemctl stop aios-carrier 2>/dev/null || true
systemctl disable aios-carrier 2>/dev/null || true
for u in aios-bus aios-ontology aios-computer aios-presentation aios-presentation-render aios-space aios-agent; do
  systemctl restart "$u" 2>/dev/null || systemctl start "$u" 2>/dev/null || true
  sleep 1
done
sleep 4
for u in aios-bus aios-ontology aios-computer aios-presentation aios-presentation-render aios-space aios-agent; do
  printf '  %-24s %s\n' "$u" "$(systemctl is-active "$u")"
done

echo "=== 6 日志尾 ==="
journalctl -u aios-computer --no-pager -n 4 2>&1 | tail -4
journalctl -u aios-ontology --no-pager -n 4 2>&1 | tail -4
echo "=== ★ 部署完成 ==="
