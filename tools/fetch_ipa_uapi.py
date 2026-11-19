#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill missing IPA in words.md from uapis.cn dictionary lookup.

Usage:
    UAPI_API_KEY='uapi-...' python3 tools/fetch_ipa_uapi.py --dry-run
    UAPI_API_KEY='uapi-...' python3 tools/fetch_ipa_uapi.py --write

Only fills lines that currently have no IPA. Never overwrites a hand-written
IPA. Phrases (words containing spaces) are skipped. Results are cached in
tools/uapi-ipa-cache.json (gitignored).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from enrich import split_line  # noqa: E402

WORDS = ROOT / "words.md"
CACHE = ROOT / "tools" / "uapi-ipa-cache.json"
TAG_RE = re.compile(r"\s*\[(?:族|混|近):[^\]]*\]")

API = "https://uapis.cn/api/v1/dictionary/lookup"


class RateLimiter:
    def __init__(self, interval: float):
        self.interval = interval
        self.next = 0.0
        self.lock = threading.Lock()

    def wait(self):
        with self.lock:
            now = time.monotonic()
            delay = max(0.0, self.next - now)
            self.next = max(now, self.next) + self.interval
        if delay:
            time.sleep(delay)


def load_cache() -> dict:
    if CACHE.exists():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def call_api(word: str, key: str, limiter: RateLimiter):
    limiter.wait()
    url = API + "?word=" + word.replace(" ", "%20")
    cmd = [
        "curl", "-sS", "-m", "25", "-D", "-",
        "-H", f"Authorization: Bearer {key}",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        return None, "curl", ""
    raw = proc.stdout
    if "\r\n\r\n" in raw:
        head, body = raw.split("\r\n\r\n", 1)
    elif "\n\n" in raw:
        head, body = raw.split("\n\n", 1)
    else:
        return None, "bad-response", ""
    status = 0
    m = re.search(r"HTTP/\S+\s+(\d+)", head)
    if m:
        status = int(m.group(1))
    if status != 200:
        return status, "", head
    try:
        data = json.loads(body)
    except Exception:
        return status, "bad-json", head
    entry = data.get("entry") or {}
    ph = entry.get("phonetics") or {}
    uk = (ph.get("uk") or {}).get("text", "")
    us = (ph.get("us") or {}).get("text", "")
    text = (us or uk).strip()
    text = text.replace(";", "；").strip()
    if not text:
        return status, "no-phonetic", head
    if len(text) > 40:
        first = re.split(r"[；]", text)[0].strip()
        text = first if first else text[:40]
    return status, text, head


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--retry-failed", action="store_true")
    args = ap.parse_args()
    if not args.write and not args.dry_run:
        print("Use --dry-run or --write")
        return
    key = os.environ.get("UAPI_API_KEY", "").strip()
    if not key:
        print("Missing UAPI_API_KEY environment variable")
        sys.exit(1)

    lines = WORDS.read_text(encoding="utf-8").splitlines()
    todo = []
    skipped_phrase = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith(("#", ">", "-", "<!--", "|")):
            continue
        r = split_line(s)
        if not r:
            continue
        word, senses, ipa, tags = r
        if ipa:
            continue
        if " " in word:
            skipped_phrase += 1
            continue
        todo.append((i, word))
    if args.limit:
        todo = todo[: args.limit]
    cache = load_cache()
    pending = []
    for i, w in todo:
        c = cache.get(w)
        if c and (c.get("ipa") or (c.get("_fail") and not args.retry_failed)):
            continue
        pending.append((i, w))
    print(f"missing single words: {len(todo)}, skipped phrases: {skipped_phrase}, to fetch: {len(pending)}", flush=True)

    limiter = RateLimiter(0.17)  # ~5.8 requests/sec, below the 7 QPS limit
    results = {}
    for i, w in todo:
        c = cache.get(w) or {}
        ipa = str(c.get("ipa") or "").strip()
        if ipa:
            results[w] = ipa.strip("/")
    failures = []
    credits = 0
    lock = threading.Lock()
    done = 0

    def work(item):
        i, w = item
        status, text, head = call_api(w, key, limiter)
        if status == 200 and text and text not in {"bad-json", "no-phonetic"}:
            return i, w, status, text, head
        return i, w, status, None, head

    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(work, x) for x in pending]
        for f in as_completed(futs):
            i, w, status, text, head = f.result()
            done += 1
            with lock:
                if text:
                    cache[w] = {"ipa": "/" + text.strip("/") + "/", "source": "uapi"}
                    results[w] = text
                else:
                    cache[w] = {"_fail": True, "status": status}
                    failures.append((w, status))
                # Track credits from response headers when available.
                m = re.search(r"uapi-credits-charged:\s*(\d+)", head or "", re.I)
                if m:
                    credits += int(m.group(1))
                if done % 25 == 0:
                    save_cache(cache)
                    print(f"  {done}/{len(pending)}  ok={len(results)} fail={len(failures)} credits≈{credits}", flush=True)
    save_cache(cache)
    print(f"done: ok={len(results)}, failed={len(failures)}, credits≈{credits}", flush=True)

    if args.dry_run:
        for w, text in list(results.items())[:30]:
            print(f"  {w}: /{text}/")
        print("dry run: words.md not changed")
        return

    added = 0
    for i, w in todo:
        text = results.get(w)
        if not text:
            continue
        line = lines[i]
        ipa = "/" + text.strip("/") + "/"
        m = TAG_RE.search(line)
        if m:
            line = line[: m.start()] + f" {ipa}" + line[m.start():]
        else:
            line = line.rstrip() + f" {ipa}"
        lines[i] = line
        added += 1
    WORDS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"added IPA: {added}", flush=True)
    if failures:
        print("failed words:", ", ".join(f"{w}({s})" for w, s in failures[:80]), flush=True)


if __name__ == "__main__":
    main()
