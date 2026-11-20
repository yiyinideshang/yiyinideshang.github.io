#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Incrementally add new words from the corrected 26_1.md to words.md.

Existing lines are never replaced. Use --dry-run first.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import migrate as mig  # noqa: E402
from enrich import split_line  # noqa: E402
from fix_source import is_entry_line, line_rest, norm_head  # noqa: E402

SOURCE = Path("/mnt/d/Typora/英语/26_1.md")
WORDS = ROOT / "words.md"
FAMILY_FILE = Path(__file__).resolve().parent.parent / "references" / "family-groups.md"

POS_SET = {"n", "v", "vt", "vi", "adj", "adv", "prep", "pron", "conj", "num",
           "art", "phr", "idm", "aux", "int", "det", "phrv", "vlink"}

RENAME = {
    "batch": "bath",
    "essary": "essay",
    "dooted": "dotted",
    "efficent": "efficient",
    "intervence": "intervention",
    "learning": "leaning",
    "stick-stuck": "stick",
    "observe observe": "observe",
    "bibical": "biblical",
    "cyperspace": "cyberspace",
    "evently": "evenly",
    "fabirc": "fabric",
    "fuction": "function",
    "variat": "variant",
    "carryout": "carry out",
}

DROP_WORDS = {"x", "chips", "geese", "teeth", "footn"}

POS_OVERRIDES = {
    "tray": "n", "bride": "n", "victory": "n", "dealing": "n",
    "spokesperson": "n", "outcome": "n",
    "aeroplane": "n", "airplane": "n", "artistically": "adv",
    "busy": "adj", "cautious": "adj", "clumsy": "adj",
    "definitely": "adv", "destructive": "adj", "disgusting": "adj",
    "distinct": "adj", "distinctive": "adj", "distinguishable": "adj",
    "earnest": "adj", "existing": "adj", "figurative": "adj",
    "flawless": "adj", "guilty": "adj", "ignorant": "adj",
    "illusory": "adj", "illustrative": "adj", "infinite": "adj",
    "innovative": "adj", "invariably": "adv", "large": "adj",
    "largely": "adv", "lawful": "adj", "legal": "adj",
    "magnetic": "adj", "magnificent": "adj", "measurable": "adj",
    "messy": "adj", "mostly": "adv", "occasional": "adj",
    "overwhelming": "adj", "painful": "adj", "planetary": "adj",
    "pleasant": "adj", "pleasing": "adj", "primitive": "adj",
    "prominent": "adj", "protective": "adj", "respectable": "adj",
    "respectful": "adj", "respective": "adj", "robotic": "adj",
    "ruinous": "adj", "selfish": "adj", "significant": "adj",
    "simple": "adj", "stable": "adj", "surgical": "adj",
    "wary": "adj", "weary": "adj",
    "wheelchair": "n", "lion": "n", "aeroplane": "n", "airplane": "n",
    "art": "n", "yell": "v", "foremost": "adj",
}

SENSE_OVERRIDES = {
    "appear": [("vi", "出现，起源，问世，演出"), ("v", "似乎，好像")],
    "insurance": [("n", "保险")],
    "isolation": [("n", "隔绝，孤独，孤立")],
    "lower": [("adj", "下面的，下方的，底部的"), ("vt", "把…放低，把…降下"), ("v", "减少，缩小，降低")],
    "X-ray": [("n", "X光检查")],
    "carry out": [("phr", "实施(计划)，兑现(诺言)，完成(任务)")],
    "make sure": [("phr", "查明，核实，确保")],
    "distance": [("n", "远处，疏远，隔阂，距离"), ("v", "疏远")],
    "leap": [("v", "跳跃，突然做某事"), ("n", "跳跃，激增，猛涨")],
    "businessman": [("n", "商人")],
    "spoil": [("v", "毁坏，破坏，宠坏，溺爱"), ("vi", "(食物)变质")],
}


def norm_word(w: str) -> str:
    w = w.lower().strip().replace("’", "'")
    toks = w.split()
    while len(toks) > 1 and toks[-1] in POS_SET:
        toks.pop()
    w = " ".join(toks)
    m = re.match(r"^([a-z]+)-([a-z]+)(?:-([a-z]+))?$", w)
    if m:
        w = m.group(1)
    else:
        m = re.match(r"^([a-z]+)-[a-z]+(?:/[a-z]+)?$", w)
        if m:
            w = m.group(1)
    return w


def clean_gloss(g: str) -> str:
    g = str(g or "").strip().lstrip(".．。… ")
    g = re.sub(r"\s+", " ", g)
    g = g.replace(",", "，").replace(";", "；")
    g = re.sub(r"[，；、]{2,}", lambda m: m.group(0)[0], g)
    return g.strip("，；、。 ")


def merge_senses(old, new):
    out = list(old)
    for pos, gloss in new:
        gloss = clean_gloss(gloss)
        if not gloss:
            continue
        if (pos, gloss) not in out:
            out.append((pos, gloss))
    return out


def current_keys():
    keys = set()
    for line in WORDS.read_text(encoding="utf-8").splitlines():
        r = split_line(line)
        if r:
            keys.add(r[0].lower())
    return keys


def load_family_tags():
    tags = {}
    if not FAMILY_FILE.exists():
        return tags
    text = FAMILY_FILE.read_text(encoding="utf-8")
    m = re.search(r"```text\n(.*?)```", text, re.S)
    if not m:
        return tags
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        fam, words = line.split(":", 1)
        fam = fam.strip()
        for w in words.split(","):
            w = w.strip()
            if w:
                tags[w] = fam
    return tags


FAMILY_TAGS = load_family_tags()


def infer_pos(word: str, senses):
    if word in SENSE_OVERRIDES:
        senses = SENSE_OVERRIDES[word]
    if word in POS_OVERRIDES and not any(p for p, _ in senses):
        return [(POS_OVERRIDES[word], g) for _, g in senses]
    out = []
    for pos, gloss in senses:
        if pos:
            out.append((pos, gloss))
            continue
        g = gloss or ""
        if " " in word:
            p = "phr"
        elif g.endswith("的"):
            p = "adj"
        elif g.endswith("地"):
            p = "adv"
        elif re.search(r"(tion|sion|ment|ness|ity|ance|ence|ship|hood|ism|ist|er|or)$", word):
            p = "n"
        elif word.endswith("ly"):
            p = "adv"
        elif re.search(r"(ous|ful|less|able|ible|al|ic|ive|ent|ant)$", word):
            p = "adj"
        elif re.search(r"(ize|ise|ify|ate)$", word):
            p = "v"
        else:
            p = ""
        out.append((p, gloss))
    return out


def collect_new():
    entries = mig.split_inline_entries(mig.migrate_file(SOURCE)[0])
    current = current_keys()
    merged = OrderedDict()
    for e in entries:
        w = norm_word(e["word"])
        w = RENAME.get(w, w)
        if not w or w in DROP_WORDS or w in current:
            continue
        if w not in merged:
            merged[w] = {"word": w, "senses": [], "notes": []}
        merged[w]["senses"] = merge_senses(merged[w]["senses"], e["senses"])
        for n in e.get("notes", []):
            n = str(n).strip()
            if n and not n.startswith("*参考") and len(n) <= 160 and n not in merged[w]["notes"]:
                merged[w]["notes"].append(n)

    if "x" in merged:
        x = merged.pop("x")
        merged["X-ray"] = {"word": "X-ray", "senses": [("n", "X光检查")], "notes": x["notes"]}
    if "carry out" not in merged and "carry out" not in current:
        merged["carry out"] = {"word": "carry out", "senses": [("phr", "实施(计划)，兑现(诺言)，完成(任务)")], "notes": []}
    if "make sure" not in merged and "make sure" not in current:
        merged["make sure"] = {"word": "make sure", "senses": [("phr", "查明，核实，确保")], "notes": []}

    # Tolerant pass for entries the main parser skipped, especially blockquote
    # word lists such as "> leading ..." and irregular-verb lines.
    for line in SOURCE.read_text(encoding="utf-8").splitlines():
        m = is_entry_line(line)
        if not m:
            continue
        w = norm_head(m.group("word"))
        w = RENAME.get(w, w)
        if not w or w in DROP_WORDS or w in current or w in merged:
            continue
        rest = line_rest(line)
        senses, ipa = mig.parse_senses(rest, w)
        senses = [(p, mig.clean_gloss(g, w)) for p, g in senses if mig.clean_gloss(g, w)]
        if not senses:
            continue
        merged[w] = {"word": w, "senses": senses, "notes": []}
    return merged


def render_line(e):
    senses = infer_pos(e["word"], e["senses"])
    parts = []
    for pos, gloss in senses:
        gloss = clean_gloss(gloss)
        if not gloss:
            continue
        parts.append((pos + ". " if pos else "") + gloss)
    if not parts:
        parts = ["待补"]
    line = e["word"] + " " + "；".join(parts)
    fam = FAMILY_TAGS.get(e["word"])
    if fam:
        line += f" [族:{fam}]"
    return line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    new = collect_new()
    lines = [render_line(e) for e in new.values()]
    print(f"new entries: {len(lines)}")
    for line in lines:
        print(line)
    if args.write:
        text = WORDS.read_text(encoding="utf-8").rstrip() + "\n\n"
        text += "\n\n".join(lines) + "\n"
        WORDS.write_text(text, encoding="utf-8")
        print(f"appended {len(lines)} entries to {WORDS}")


if __name__ == "__main__":
    main()
