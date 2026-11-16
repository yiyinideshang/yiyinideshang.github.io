#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 words.md 加 A-Z 一级标题。

- 只动标题和分组顺序，不改词条内容
- 可重复运行；已经存在的 `# A` 标题会先被去掉再重建
- 每个字母内部按单词排序
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDS = ROOT / "words.md"


def entry_word(block: list[str]) -> str:
    for line in block:
        s = line.strip()
        if s and not s.startswith(("-", "#", ">")):
            return s.split()[0]
    return ""


def main() -> None:
    lines = WORDS.read_text(encoding="utf-8").splitlines()
    header: list[str] = []
    blocks: list[list[str]] = []
    cur: list[str] = []
    in_header = True

    for line in lines:
        s = line.strip()
        if in_header:
            if re.fullmatch(r"#\s*[A-Z]", s):
                in_header = False
            elif not s or s.startswith("#") or s.startswith(">"):
                header.append(line)
                continue
            else:
                in_header = False

        if re.fullmatch(r"#\s*[A-Z]", s):
            if cur:
                blocks.append(cur)
                cur = []
            continue
        if not s:
            if cur:
                blocks.append(cur)
                cur = []
            continue
        if s.startswith("#"):
            if cur:
                blocks.append(cur)
                cur = []
            continue
        cur.append(line)

    if cur:
        blocks.append(cur)

    while header and not header[-1].strip():
        header.pop()
    header.append("")

    groups: dict[str, list[list[str]]] = {}
    for b in blocks:
        w = entry_word(b)
        if not w:
            continue
        letter = w[0].upper() if w[0].isalpha() else "#"
        groups.setdefault(letter, []).append(b)

    for letter in groups:
        groups[letter].sort(key=lambda b: b[0].strip().lower())

    out = list(header)
    letters = [chr(c) for c in range(ord("A"), ord("Z") + 1) if chr(c) in groups]
    for letter in letters:
        out.append(f"# {letter}")
        out.append("")
        for b in groups[letter]:
            out.extend(b)
            out.append("")
    if "#" in groups:
        out.append("# Other")
        out.append("")
        for b in groups["#"]:
            out.extend(b)
            out.append("")

    WORDS.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"{len(blocks)} 个词条，{len(letters)} 个字母分组")
    print(" ".join(f"{k}:{len(v)}" for k, v in sorted(groups.items())))


if __name__ == "__main__":
    main()
