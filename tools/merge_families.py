#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并被拆开的词族标签。

只改指定词的 [族:...] 标签，不重跑迁移，不动其他内容。
可重复运行：已经是目标标签的行会跳过。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from enrich import split_line  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORDS = ROOT / "words.md"

# 词 -> 合并后的族名
MERGE = {
    "amusing": "amuse",
    "communicate": "commun",
    "communicative": "commun",
    "effective": "effect",
    "effectively": "effect",
    "extremist": "extreme",
    "format": "form",
    "formula": "form",
    "horrible": "horr",
    "horribly": "horr",
    "horrify": "horr",
    "horrifying": "horr",
    "instinctive": "instinct",
    "instinctively": "instinct",
    "pessimist": "pessim",
    "pessimistic": "pessim",
    "practicality": "practic",
    "productive": "product",
    "productivity": "product",
    "excitation": "excite",
    "excitedly": "excite",
}


def main() -> None:
    lines = WORDS.read_text(encoding="utf-8").splitlines()
    changed: list[tuple[str, str]] = []

    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith(("#", ">", "-", "<!--", "|")):
            continue
        r = split_line(s)
        if not r:
            continue
        word = r[0]
        new = MERGE.get(word)
        if not new:
            continue
        if f"[族:{new}]" in line:
            continue
        if "[族:" in line:
            new_line = re.sub(r"\[族:[^\]]*\]", f"[族:{new}]", line, count=1)
        else:
            new_line = line.rstrip() + f" [族:{new}]"
        if new_line != line:
            lines[i] = new_line
            changed.append((word, new))

    WORDS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"修改 {len(changed)} 行")
    for w, n in changed:
        print(f"  {w} -> [族:{n}]")


if __name__ == "__main__":
    main()
