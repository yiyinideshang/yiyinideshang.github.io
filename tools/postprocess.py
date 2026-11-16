#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清洗 build/words.raw.json，输出 words.md。

- 修错词、合并同义词条
- 去掉释义里粘连的词头
- 合并重复义项
- 补几条最关键的易混记忆
- 生成待办报告
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from migrate import merge_into, render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "build" / "words.raw.json"
OUT = ROOT / "words.md"
REPORT = ROOT / "迁移报告.md"

# 词头修正：(新词, 触发条件；None 表示无条件)
RENAME: dict[str, tuple[str, str | None]] = {
    "batch": ("bath", "洗澡"),
    "essary": ("essay", None),
    "learning": ("leaning", "倾向"),
    "dooted": ("dotted", None),
    "efficent": ("efficient", None),
    "intervence": ("intervention", None),
    "southwast": ("southwest", None),
    "practic": ("practical", None),
    "lazyness": ("laziness", None),
    "on in five": ("one in five", None),
    "bound on": ("bound for", None),
    "enterpriing": ("enterprising", None),
    "observe observe": ("observe", None),
}

DROP_WORDS = {"little", "stick-stuck", "pron"}

# 人工覆盖有问题的释义
OVERRIDE: dict[str, list[tuple[str, str]]] = {
    "clinical": [("adj", "临床的")],
    "fluency": [("n", "流利，流畅")],
    "affection": [("n", "喜爱；关爱；感情")],
    "deny": [("v", "否认；拒绝")],
    "frighten": [("v", "使惊恐，使惊吓")],
    "intervention": [("n", "干涉，介入；打断")],
    "career": [("n", "职业；事业；生涯"), ("adj", "就业的；职业的")],
    "prospect": [("n", "前景；可能性；希望"), ("v", "勘探；寻找")],
    "claim": [("v", "声称；索取；要求；夺去（生命）"), ("n", "声称；索赔；权利")],
    "content": [("n", "内容；目录；含量"), ("adj", "满足的"), ("v", "使满足")],
    "survey": [("n", "调查；测量；概述"), ("v", "调查；审视；测量")],
    "police": [("n", "警察，警方")],
    "cancer": [("n", "癌症；社会恶习")],
    "least": [("adj", "一点儿，最小的，最微不足道的（little 的最高级）"), ("adv", "最低程度地，最少，至少"), ("n", "最不重要的事物，起码"), ("pron", "最少量，起码")],
    "lean": [("vi", "倾斜身体，倚靠"), ("adj", "精瘦的")],
    "southwest": [("n", "西南方，西南部"), ("adv", "向西南"), ("adj", "西南部的")],
    "lost": [("adj", "迷路的，失去的")],
    "phase": [("n", "阶段，时期")],
    "tight": [("adj", "紧的，紧身的，严格的，拮据的")],
}

# 原文只出现了词头、没有释义的，手工补
EXTRA: dict[str, list[tuple[str, str]]] = {
    "policeman": [("n", "警察")],
    "lean": [("vi", "倾斜身体，倚靠"), ("adj", "精瘦的")],
}

# 自动词族里的误报，直接从这些词上摘掉标签
FAMILY_DROP: dict[str, set[str]] = {
    "former": {"form"},
    "scar": {"scar"},
    "scare": {"scar"},
    "survey": {"surv"},
    "survive": {"surv"},
    "interval": {"interv"},
    "intervention": {"interv"},
    "experience": {"experi"},
    "experiment": {"experi"},
    "integrity": {"integr"},
}

# 补几条最值钱的辨析/记忆
MANUAL_NOTES: dict[str, list[str]] = {
    "career": [
        "记: career 开头像 care（care + er），职业要用心经营。",
        "错: 与 cancer 混；career 结尾 -reer，重音在后。",
    ],
    "cancer": [
        "记: can + cer，中间是 n。",
        "错: 与 career 混；cancer 结尾 -ncer，重音在前。",
    ],
    "desert": [
        "记: desert 单 s，沙漠/抛弃；dessert 双 s，多一份甜。",
    ],
    "dessert": [
        "记: dessert 双 s，多一份甜。",
    ],
    "principle": [
        "记: principle 结尾 -ple，原则；principal 结尾 -pal，可指校长/主要的。",
    ],
    "principal": [
        "记: principal 结尾 -pal，可指校长/主要的；principle 结尾 -ple，原则。",
    ],
    "adapt": [
        "辨析: adapt 适应/改编；adopt 采纳/收养；adept 熟练的。",
    ],
    "adopt": [
        "辨析: adopt 采纳/收养；adapt 适应/改编；adept 熟练的。",
    ],
    "affect": [
        "辨析: affect 动词“影响”；effect 名词“效果”。",
    ],
    "effect": [
        "辨析: effect 名词“效果”；affect 动词“影响”。",
    ],
    "quiet": [
        "辨析: quiet 安静；quite 相当；quit 放弃。",
    ],
    "quite": [
        "辨析: quite 相当；quiet 安静；quit 放弃。",
    ],
    "lean": [
        "变形: leaned, leant",
    ],
    "stick": [
        "变形: stuck",
    ],
    "lost": [
        "变形: lose 的过去式/过去分词",
    ],
}

LONG_LIMIT = 70


def clean_gloss_text(g: str, word: str) -> str:
    g = g.strip()
    if not g:
        return ""
    g = re.sub(
        r"[；;]\s*(?:---\s*)?[\w'’\-]*\s*的(?:现在分词|过去式|过去分词).*$", "", g
    )
    parts = [p.strip(" ，,、。;；") for p in re.split(r"[；;]", g)]
    parts = [p for p in parts if p]

    def items(p: str) -> set[str]:
        return {x for x in re.split(r"[，,、]", p) if x}

    kept: list[str] = []
    for p in parts:
        p = re.sub(rf"{re.escape(word)}\s*$", "", p, flags=re.I).strip(" ，,、。;；")
        if not p:
            continue
        np = re.sub(r"\s", "", p)
        if any(np == re.sub(r"\s", "", k) for k in kept):
            continue
        pi = items(p)
        if any(pi and pi <= items(k) for k in kept):
            continue
        kept = [k for k in kept if not (items(k) and items(k) <= pi)]
        kept.append(p)
    return "；".join(kept)


def clean_note(n: str) -> str:
    n = n.replace("**", "").strip(" :-：")
    n = re.sub(r"\s*[：:]\s*", ": ", n, count=1)
    return n.strip()


def merge_posless(senses: list[tuple[str, str]]) -> list[tuple[str, str]]:
    pos_set = {p for p, _ in senses if p}
    if len(pos_set) == 1 and any(not p for p, _ in senses):
        pos = next(iter(pos_set))
        return [(pos, "；".join(g for _, g in senses))]
    return senses


def dedupe_notes(notes: list[str]) -> list[str]:
    out: list[str] = []
    for n in notes:
        hit = None
        for i, f in enumerate(out):
            if SequenceMatcher(None, n, f).ratio() > 0.65:
                hit = i
                break
        if hit is None:
            out.append(n)
        elif len(n) > len(out[hit]):
            out[hit] = n
    return out


def main() -> None:
    raw = json.loads(RAW.read_text(encoding="utf-8"))

    # 1. 修词头
    renamed = 0
    for e in raw:
        w = e["word"]
        if w not in RENAME:
            continue
        new, cond = RENAME[w]
        gloss = "；".join(g for _, g in e["senses"])
        if cond and cond not in gloss:
            continue
        e["word"] = new
        renamed += 1
        if "source" in e:
            e["source"] = e["source"]
    print(f"修正词头：{renamed}")

    # 2. 合并（改名后可能撞车）
    db: dict[str, dict] = {}
    for e in raw:
        key = e["word"].lower().strip()
        e["word"] = key
        e["tags"] = {t: set(v) for t, v in e.get("tags", {}).items()}
        e.setdefault("tags", {})
        for t in ("族", "混", "近"):
            e["tags"].setdefault(t, set())
        e["senses"] = [(p, g) for p, g in e["senses"]]
        if key in db:
            merge_into(db[key], e)
        else:
            db[key] = e

    # 3. 清洗释义/笔记
    for w in DROP_WORDS:
        db.pop(w, None)
    for w, senses in EXTRA.items():
        if w not in db:
            db[w] = {
                "word": w,
                "senses": senses,
                "ipa": "",
                "notes": [],
                "forms": [],
                "tags": {"族": set(), "混": set(), "近": set()},
                "source": "manual",
                "section": "",
            }
    for w, e in db.items():
        if w in OVERRIDE:
            e["senses"] = OVERRIDE[w]
        cleaned = []
        for pos, g in e["senses"]:
            if re.fullmatch(
                r"(?:[\w'’\-]+\s*)?的(?:现在分词|过去式|过去分词)", g.strip()
            ):
                continue
            g = clean_gloss_text(g, w)
            if g:
                cleaned.append((pos, g))
        e["senses"] = cleaned or [("", "待补")]
        e["senses"] = merge_posless(e["senses"])
        if w in FAMILY_DROP:
            e["tags"]["族"] -= FAMILY_DROP[w]
        e["notes"] = [clean_note(n) for n in e["notes"]]
        e["notes"] = [n for n in e["notes"] if n and n not in {"近义", "相似", "辨析"}]
        seen: list[str] = []
        for n in e["notes"]:
            if n not in seen:
                seen.append(n)
        for n in MANUAL_NOTES.get(w, []):
            if n not in seen:
                seen.append(n)
        e["notes"] = dedupe_notes(seen)

    # 4. 输出
    OUT.write_text(render(db), encoding="utf-8")

    # 5. 报告
    long_gloss = []
    no_pos = []
    english_left = []
    for w, e in db.items():
        g = "；".join(g for _, g in e["senses"])
        if len(g) > LONG_LIMIT:
            long_gloss.append((len(g), w, g))
        if not any(p for p, _ in e["senses"]):
            no_pos.append(w)
        leftovers = [
            x for x in re.findall(r"[A-Za-z][A-Za-z'’\-]{2,}", g)
            if x.lower() != w and x.lower() not in {"the", "and", "for", "with"}
        ]
        if leftovers:
            english_left.append((w, sorted(set(leftovers)), g))

    long_gloss.sort(reverse=True)
    lines = [
        "# 迁移报告",
        "",
        f"- 唯一词条：{len(db)}",
        f"- 修正词头：{renamed}",
        f"- 长释义（>{LONG_LIMIT} 字，建议精简）：{len(long_gloss)}",
        f"- 缺词性：{len(no_pos)}",
        f"- 释义里还有英文残留：{len(english_left)}",
        "",
        "## 长释义（优先手工精简）",
        "",
    ]
    for n, w, g in long_gloss[:40]:
        lines.append(f"- **{w}**（{n}）：{g}")
    lines += ["", "## 缺词性（可由词典 API 补）", ""]
    lines += ["- " + w for w in sorted(no_pos)]
    lines += ["", "## 释义里的英文残留（检查是否还有粘连）", ""]
    for w, left, g in english_left[:60]:
        lines.append(f"- **{w}**: {', '.join(left)}  ← {g}")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"写出 {OUT}（{len(db)} 词）")
    print(f"长释义 {len(long_gloss)}，缺词性 {len(no_pos)}，英文残留 {len(english_left)}")


if __name__ == "__main__":
    main()
