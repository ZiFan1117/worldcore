# -*- coding: utf-8 -*-
"""★ 把一帧 JSON 灌进自包含 HTML（★ 无 CORS、无服务器，直接 file:// 就能开）。

    ★ 作者令（逐字）：「我们要做的是 A2UI 的这种，语言格式不限……**我们要在虚拟机上执行**」。

    ★ 用法：python3 make-standalone.py frame.json > out.html
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(HERE, "a2ui-standalone.template.html")


def main():
    frame_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "frame-sample.json")
    with open(frame_path, "r", encoding="utf-8") as f:
        raw = f.read()
    json.loads(raw)  # ★ 先验是合法 JSON
    with open(TPL, "r", encoding="utf-8") as f:
        tpl = f.read()
    # ★ 防止 </script> 提前闭合
    safe = raw.replace("</", "<\\/")
    sys.stdout.write(tpl.replace("__FRAME_JSON__", safe))


if __name__ == "__main__":
    main()
