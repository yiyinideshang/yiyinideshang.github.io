#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild A-Z headings in words.md and apply family spacing.

- Keeps the file header and all entry/note content.
- Removes old `# A` ... `# Z` headings.
- Groups entries by first letter and sorts within each letter.
- Applies the shared family spacing rules from tools/family_spacing.py:
  * 3 blank lines before/after a family group
  * 1 blank line inside a family group
  * 1 blank line between ordinary entries
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from family_spacing import format_lines, merge_note_blocks, split_blocks, split_header  # noqa: E402

WORDS = ROOT / "words.md"
HEADING_RE = re.compile(r"^#\s*[A-Z]$")


def entry_word(block: list[str]) -> str:
    for line in block:
        s = line.strip()
        if s and not s.startswith(("-", "#", ">")):
            return s.split()[0]
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(WORDS))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = Path(args.file)

    lines = path.read_text(encoding="utf-8").splitlines()
    header, rest = split_header(lines)
    blocks = merge_note_blocks(split_blocks(rest))
    entries = [b for b in blocks if not HEADING_RE.fullmatch(b[0].strip())]

    groups: dict[str, list[list[str]]] = {}
    for block in entries:
        word = entry_word(block)
        if not word:
            continue
        letter = word[0].upper() if word[0].isalpha() else "#"
        groups.setdefault(letter, []).append(block)

    for letter in groups:
        groups[letter].sort(key=lambda b: b[0].strip().lower())

    out = list(header)
    if out and out[-1].strip():
        out.append("")
    for letter in [chr(c) for c in range(ord("A"), ord("Z") + 1) if chr(c) in groups]:
        out.extend([f"# {letter}", ""])
        for block in groups[letter]:
            out.extend(block)
            out.append("")
    if "#" in groups:
        out.extend(["# Other", ""])
        for block in groups["#"]:
            out.extend(block)
            out.append("")

    out = format_lines(out)
    print(f"{len(entries)} entries, {len(groups)} letter groups")
    print(" ".join(f"{k}:{len(v)}" for k, v in sorted(groups.items())))
    if args.dry_run:
        print("dry run; not written")
        return
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
