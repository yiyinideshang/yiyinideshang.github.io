#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给 words.md 补音标和缺失的词性。

- 音标来源：api.dictionaryapi.dev（免费、无需 key）
- 结果缓存到 tools/ipa-cache.json，重复运行不会重复请求
- 只补空缺，不覆盖你手写的音标
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORDS = ROOT / "words.md"
CACHE = ROOT / "tools" / "ipa-cache.json"

TAGS = re.compile(r"\[(?:族|混|近):[^\]]*\]")
IPA_END = re.compile(r"/([^/\n]{1,40})/\s*$")
IPA_MID = re.compile(r"(?<=\s)/([^/\n\u4e00-\u9fff]{1,40})/")
POS_ANY = re.compile(
    r"(?<![A-Za-z])(vt|vi|adj|adv|prep|pron|conj|num|art|phr|idm|aux|int|n|v)"
    r"(?:\.?/(?:vt|vi|adj|adv|n|v))?\.",
    re.I,
)
POS_START = re.compile(
    r"^(vt|vi|adj|adv|prep|pron|conj|num|art|phr|idm|aux|int|n|v)"
    r"(?:\.?/(?:vt|vi|adj|adv|n|v))?\.",
    re.I,
)
CJK = re.compile(r"[\u4e00-\u9fff]")

POS_MAP = {
    "noun": "n", "verb": "v", "adjective": "adj", "adverb": "adv",
    "preposition": "prep", "pronoun": "pron", "conjunction": "conj",
    "determiner": "det", "numeral": "num", "interjection": "int",
    "article": "art", "exclamation": "int",
}


def load_cache() -> dict:
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def fetch(word: str) -> dict:
    url = "https://api.dictionaryapi.dev/api/v2/entries/en/" + urllib.parse.quote(word)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cet4-vocab/1.0"})
            with urllib.request.urlopen(req, timeout=12) as r:
                data = json.loads(r.read().decode("utf-8"))
            if not isinstance(data, list) or not data:
                return {"_fail": True}
            ipa = ""
            for item in data:
                if item.get("phonetic"):
                    ipa = item["phonetic"]
                    break
                for p in item.get("phonetics", []):
                    if p.get("text"):
                        ipa = p["text"]
                        break
                if ipa:
                    break
            pos = ""
            for item in data:
                meanings = item.get("meanings", [])
                if meanings:
                    pos = POS_MAP.get(meanings[0].get("partOfSpeech", ""), "")
                    if pos:
                        break
            ipa = ipa.replace("ɹ", "r").strip()
            if ipa and not ipa.startswith("/"):
                ipa = "/" + ipa.strip("/") + "/"
            return {"ipa": ipa, "pos": pos}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(2 + attempt * 2)
                continue
            return {"_fail": True}
        except Exception:
            if attempt < 2:
                time.sleep(1.5)
                continue
            return {"_fail": True}
    return {"_fail": True}


def split_line(line: str) -> tuple[str, str, str, str] | None:
    """返回 (word, senses, ipa, tags)。"""
    if not line or line.startswith(("#", ">", "-")):
        return None
    tags = " ".join(TAGS.findall(line))
    body = TAGS.sub("", line).strip()
    ipa = ""
    m = IPA_END.search(body) or IPA_MID.search(body)
    if m:
        ipa = "/" + m.group(1).strip() + "/"
        body = (body[: m.start()] + " " + body[m.end():]).strip()
    # word 的结束位置：取“词性标记”和“第一个中文”中更早的那个
    m2 = POS_ANY.search(body)
    m3 = CJK.search(body)
    if m2 and (not m3 or m2.start() < m3.start()):
        cut = m2.start()
    elif m3:
        cut = m3.start()
    else:
        return None
    word = body[:cut].strip()
    senses = body[cut:].strip()
    if not word or not senses:
        return None
    return word, senses, ipa, tags


def infer_pos(gloss: str, api_pos: str) -> str:
    """中文释义结尾比词典第一个义项更可靠时，用后缀修正词性。"""
    g = gloss.strip()
    if g.endswith("的") and api_pos != "adj":
        return "adj"
    if g.endswith("地") and api_pos != "adv":
        return "adv"
    return api_pos


def main() -> None:
    lines = WORDS.read_text(encoding="utf-8").splitlines()
    parsed: list[tuple[int, str, str, str, str]] = []
    for i, line in enumerate(lines):
        r = split_line(line)
        if r:
            parsed.append((i, *r))

    cache = load_cache()
    todo = sorted({
        w for _, w, _, _, _ in parsed
        if " " not in w and w not in cache
    })
    print(f"词条 {len(parsed)}，待查询 {len(todo)}（缓存 {len(cache)}）")

    if todo:
        done = 0
        with ThreadPoolExecutor(max_workers=3) as ex:
            futs = {ex.submit(fetch, w): w for w in todo}
            for f in as_completed(futs):
                w = futs[f]
                try:
                    cache[w] = f.result()
                except Exception:
                    cache[w] = {"_fail": True}
                done += 1
                if done % 50 == 0:
                    print(f"  {done}/{len(todo)}")
                    save_cache(cache)
        save_cache(cache)

    added_ipa = added_pos = 0
    fails = []
    for i, word, senses, ipa, tags in parsed:
        info = cache.get(word, {})
        new_ipa = ipa
        new_senses = senses
        if not new_ipa and info.get("ipa"):
            new_ipa = info["ipa"]
            added_ipa += 1
        if not POS_START.match(new_senses):
            if " " in word:
                new_senses = "phr. " + new_senses
                added_pos += 1
            elif info.get("pos"):
                pos = infer_pos(new_senses, info["pos"])
                new_senses = pos + ". " + new_senses
                added_pos += 1
        if not new_ipa and not info.get("ipa"):
            fails.append(word)
        lines[i] = f"{word} {new_senses}" + (f" {new_ipa}" if new_ipa else "") + (f" {tags}" if tags else "")

    WORDS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"补音标 {added_ipa}，补词性 {added_pos}")
    if fails:
        print(f"没查到音标 {len(fails)} 个：" + ", ".join(fails[:40]))


if __name__ == "__main__":
    main()
