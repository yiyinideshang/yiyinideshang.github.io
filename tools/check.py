#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 words.md 的格式、重复、缺失引用。推送前跑一下。

用法：
    python3 tools/check.py          # 只报告
    python3 tools/check.py --strict # 有错误时退出码 1
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from enrich import split_line  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORDS = ROOT / "words.md"
TAG = re.compile(r"\[(族|混|近):([^\]]*)\]")


def main() -> None:
    lines = WORDS.read_text(encoding="utf-8").splitlines()
    entries = []
    bad = []
    heading = None
    wrong_heading = []
    for line in lines:
        s = line.strip()
        m = re.fullmatch(r"#\s*([A-Z])", s)
        if m:
            heading = m.group(1)
            continue
        if not s or s.startswith(("#", ">", "-", "<!--", "|")):
            continue
        r = split_line(s)
        if not r:
            bad.append(s)
            continue
        word, senses, ipa, tags = r
        tag_map = {k: [x for x in re.split(r"[,，、\s]+", v) if x] for k, v in TAG.findall(tags)}
        entries.append({
            "word": word,
            "senses": senses,
            "ipa": ipa,
            "tags": tag_map,
        })
        if heading and word and word[0].upper() != heading:
            wrong_heading.append((word, heading))

    keys = [e["word"].lower() for e in entries]
    dup = {k: n for k, n in Counter(keys).items() if n > 1}
    known = set(keys)
    missing = []
    self_ref = []
    for e in entries:
        for tag in ("混", "近"):
            for t in e["tags"].get(tag, []):
                if t.lower() == e["word"].lower():
                    self_ref.append((e["word"], tag))
                elif t.lower() not in known:
                    missing.append((e["word"], tag, t))
    no_pos = [e["word"] for e in entries if not re.match(r"^(vt|vi|adj|adv|n|v|prep|pron|conj|num|art|det|phr|idm|aux|int)\.", e["senses"])]
    no_ipa = [e["word"] for e in entries if not e["ipa"]]
    todo = [e["word"] for e in entries if "待补" in e["senses"]]
    long_gloss = [(e["word"], len(e["senses"])) for e in entries if len(e["senses"]) > 100]

    print(f"词条：{len(entries)}")
    print(f"无法解析：{len(bad)}")
    print(f"重复词头：{len(dup)}")
    print(f"缺失引用：{len(missing)}")
    print(f"自引用：{len(self_ref)}")
    print(f"缺词性：{len(no_pos)}")
    print(f"缺音标：{len(no_ipa)}")
    print(f"待补释义：{len(todo)}")
    print(f"字母分组放错：{len(wrong_heading)}")
    print(f"超长释义（>100 字）：{len(long_gloss)}")

    if bad:
        print("\n[无法解析]")
        for x in bad[:30]:
            print("  " + x)
    if dup:
        print("\n[重复词头]")
        for k, n in sorted(dup.items(), key=lambda x: (-x[1], x[0]))[:30]:
            print(f"  {k}: {n} 条")
    if missing:
        print("\n[缺失引用]")
        for a, tag, b in missing[:30]:
            print(f"  {a} 的 [{tag}] 指向 {b}，词库里没有")
    if self_ref:
        print("\n[自引用]")
        for a, tag in self_ref[:20]:
            print(f"  {a} 的 [{tag}] 指向自己")
    if todo:
        print("\n[待补释义]")
        print("  " + ", ".join(todo[:40]))
    if wrong_heading:
        print("\n[字母分组放错]")
        for w, h in wrong_heading[:30]:
            print(f"  {w} 放在 # {h} 下")
    if long_gloss:
        print("\n[超长释义]")
        for w, n in sorted(long_gloss, key=lambda x: -x[1])[:20]:
            print(f"  {w}: {n} 字")

    errors = len(bad) + len(dup) + len(self_ref) + len(todo) + len(wrong_heading)
    if "--strict" in sys.argv and errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
