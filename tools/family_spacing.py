#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared blank-line rules for words.md.

Rules:
- 3 blank lines before a family group
- 3 blank lines after a family group
- 1 blank line between members of the same family
- 1 blank line between ordinary entries

The function only changes separators; it never edits an entry or note line.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDS = ROOT / "words.md"
HEADING_RE = re.compile(r"^#\s*[A-Z]$")
FAMILY_RE = re.compile(r"\[族:([^\]]+)\]")


def split_header(lines: list[str]):
    for i, line in enumerate(lines):
        if HEADING_RE.fullmatch(line.strip()):
            return lines[:i], lines[i:]
    return [], lines


def split_blocks(lines: list[str]):
    blocks = []
    cur = []
    for line in lines:
        if not line.strip():
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append(cur)
    return blocks


def merge_note_blocks(blocks: list[list[str]]):
    """Attach note-only blocks (starting with - or >) to the previous entry."""
    out = []
    for block in blocks:
        first = block[0].strip() if block else ""
        if out and first.startswith(("-", ">")):
            out[-1].extend(block)
        else:
            out.append(block)
    return out


def annotate(blocks: list[list[str]]):
    blocks = merge_note_blocks(blocks)
    items = []
    for block in blocks:
        first = block[0].strip()
        heading = bool(HEADING_RE.fullmatch(first))
        family = ""
        if not heading:
            m = FAMILY_RE.search(block[0])
            if m:
                family = m.group(1).strip()
        items.append({
            "block": block,
            "heading": heading,
            "family": family,
            "group_size": 1,
        })

    i = 0
    while i < len(items):
        if items[i]["heading"] or not items[i]["family"]:
            i += 1
            continue
        j = i + 1
        while (
            j < len(items)
            and not items[j]["heading"]
            and items[j]["family"] == items[i]["family"]
        ):
            j += 1
        if j - i >= 2:
            for k in range(i, j):
                items[k]["group_size"] = j - i
        i = j
    return items


def format_lines(lines: list[str]) -> list[str]:
    header, rest = split_header(lines)
    items = annotate(split_blocks(rest))

    out = list(header)
    if out and out[-1].strip():
        out.append("")

    prev = None
    for idx, item in enumerate(items):
        if idx > 0:
            same_family = (
                item["family"]
                and prev["family"]
                and item["family"] == prev["family"]
                and item["group_size"] >= 2
            )
            if same_family:
                blanks = 1
            elif item["group_size"] >= 2 or prev["group_size"] >= 2:
                blanks = 3
            else:
                blanks = 1
            while out and not out[-1].strip():
                out.pop()
            out.extend([""] * blanks)
        out.extend(item["block"])
        prev = item

    while out and not out[-1].strip():
        out.pop()
    if prev and prev["group_size"] >= 2:
        out.extend(["", "", ""])
    return out


def check_spacing(lines: list[str]) -> dict:
    header, rest = split_header(lines)
    items = annotate(split_blocks(rest))
    # Map block start to line index.
    index = []
    line_no = len(header)
    for item in items:
        while line_no < len(lines) and not lines[line_no].strip():
            line_no += 1
        index.append(line_no)
        line_no += len(item["block"])

    bad_before = bad_after = bad_inside = 0
    runs = 0
    i = 0
    while i < len(items):
        if items[i]["heading"] or items[i]["group_size"] < 2:
            i += 1
            continue
        j = i
        while (
            j + 1 < len(items)
            and not items[j + 1]["heading"]
            and items[j + 1]["family"] == items[i]["family"]
        ):
            j += 1
        runs += 1
        start = index[i]
        before = 0
        k = start - 1
        while k >= 0 and not lines[k].strip():
            before += 1
            k -= 1
        end = index[j] + len(items[j]["block"])
        after = 0
        k = end
        while k < len(lines) and not lines[k].strip():
            after += 1
            k += 1
        if before < 3:
            bad_before += 1
        if after < 3:
            bad_after += 1
        for k in range(i, j):
            e = index[k] + len(items[k]["block"])
            inside = 0
            q = e
            while q < len(lines) and not lines[q].strip():
                inside += 1
                q += 1
            if inside != 1:
                bad_inside += 1
        i = j + 1
    return {
        "runs": runs,
        "bad_before": bad_before,
        "bad_after": bad_after,
        "bad_inside": bad_inside,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(WORDS))
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    path = Path(args.file)
    lines = path.read_text(encoding="utf-8").splitlines()
    formatted = format_lines(lines)
    stats = check_spacing(formatted)
    print(f"family groups: {stats['runs']}")
    print(f"bad before: {stats['bad_before']}")
    print(f"bad after: {stats['bad_after']}")
    print(f"bad inside: {stats['bad_inside']}")
    if args.write:
        path.write_text("\n".join(formatted) + "\n", encoding="utf-8")
        print(f"wrote {path}")
    else:
        print("dry run; add --write to save")


if __name__ == "__main__":
    main()
