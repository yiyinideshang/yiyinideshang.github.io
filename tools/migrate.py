#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 sources/*.md 迁移成 words.md（一词一条）。

用法：
    python3 tools/migrate.py
产出：
    words.md          唯一词库
    迁移报告.md        重复词、无释义、未归类笔记、自动词组
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "sources"
OUT = ROOT / "words.md"
REPORT = ROOT / "迁移报告.md"
BUILD = ROOT / "build"

CJK = re.compile(r"[\u4e00-\u9fff]")
POS_TOKEN = r"(?:vt|vi|adj|adv|prep|pron|conj|num|art|phr|idm|aux|int|n|v)"
POS = re.compile(rf"(?<![A-Za-z])({POS_TOKEN}(?:\.?/{POS_TOKEN})?)\.", re.I)
POS_LOOSE = re.compile(
    rf"(?<![A-Za-z])({POS_TOKEN})(?=[.\s\u4e00-\u9fff/])", re.I
)
IPA = re.compile(r"/\s*([^/\n]{1,40}?)\s*/")
TAG = re.compile(r"\[(族|混|近):([^\]]*)\]")
LABELS = {"passage", "section", "translation", "part", "unit", "chapter", "contents"}
NOTE_PREFIXES = (
    "辨析", "例", "记", "错", "近义", "相似", "搭配", "注意",
    "变形", "来源", "备注", "词根", "联想", "发音", "用法",
)

STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "have", "has", "had",
    "was", "were", "are", "but", "not", "you", "your", "they", "their", "them",
    "his", "her", "she", "him", "its", "our", "who", "what", "when", "where",
    "why", "how", "all", "any", "can", "may", "will", "would", "should",
    "could", "must", "etc", "sb", "sth", "one", "two", "three", "some", "such",
    "than", "then", "there", "these", "those", "into", "over", "under", "about",
}
INLINE = re.compile(
    r"(?<![A-Za-z])([a-z][a-z'’\-]{2,})\s*"
    r"(?=(?:n|v|vt|vi|adj|adv|prep|pron|conj|num)\.?(?=[\s\u4e00-\u9fff])|[\u4e00-\u9fff])"
)

SUFFIXES = sorted(
    [
        "ically", "ization", "isation", "ational", "astic", "ation", "ition",
        "ality", "ivity", "ility", "ment", "ness", "ship", "hood", "ism",
        "ist", "ity", "ive", "ous", "ful", "less", "able", "ible", "ance",
        "ence", "ant", "ent", "ary", "ory", "ate", "ify", "ize", "ise",
        "ing", "ed", "er", "or", "al", "ic", "ly", "y", "asm", "ety", "ar", "e",
        "ion",
    ],
    key=len,
    reverse=True,
)

# 人工整理的易混组：只有 >=2 个词在当前词库里时才会生效
CONFUSABLE_GROUPS: list[list[str]] = [
    ["career", "cancer", "carrier"],
    ["desert", "dessert", "deserve", "desire", "detect"],
    ["amaze", "amuse", "assume", "resume", "consume"],
    ["adapt", "adopt", "adept"],
    ["affect", "effect", "effort"],
    ["quiet", "quite", "quit"],
    ["principle", "principal"],
    ["stationary", "stationery"],
    ["breath", "breathe"],
    ["loose", "lose", "loss", "lost"],
    ["compliment", "complement"],
    ["immigrate", "emigrate"],
    ["sensible", "sensitive", "sensational"],
    ["economic", "economical"],
    ["historic", "historical"],
    ["considerable", "considerate"],
    ["credible", "credulous", "creditable"],
    ["industrial", "industrious"],
    ["comprehensive", "comprehensible"],
    ["intelligent", "intelligible"],
    ["major", "mayor", "minor", "motor"],
    ["regular", "regulate"],
    ["loan", "lend", "load", "leak", "lean", "leaning"],
    ["pitch", "patch", "ditch"],
    ["acquire", "require", "inquire", "inquiry"],
    ["injure", "insure", "insurance"],
    ["abuse", "accuse", "acute"],
    ["pierce", "fierce", "force", "forge"],
    ["conquer", "capture", "commuter"],
    ["concentrate", "compensate", "cooperate", "concrete"],
    ["prove", "approve", "improve", "provide", "confirm"],
    ["opt", "option", "optional"],
    ["grab", "grasp"],
    ["stretch", "strike", "stick", "strict"],
    ["altitude", "attitude", "aptitude", "latitude"],
    ["angle", "angel"],
    ["contact", "contract", "contrast", "context", "content", "contest"],
    ["decorate", "dedicate", "delicate", "indicate"],
    ["faint", "feint", "paint", "saint"],
    ["moral", "morale", "mortal"],
    ["personal", "personnel"],
    ["council", "counsel", "consul"],
    ["site", "sight", "cite"],
    ["weather", "whether"],
    ["through", "thorough", "though", "thought"],
    ["expect", "inspect", "aspect", "respect", "suspect", "prospect"],
    ["attribute", "contribute", "distribute"],
    ["assemble", "resemble", "dissemble"],
    ["reserve", "preserve", "observe", "deserve"],
    ["consist", "insist", "resist", "persist", "assist"],
    ["attract", "distract", "extract", "contract"],
    ["include", "exclude", "conclude", "preclude"],
    ["infer", "refer", "prefer", "confer", "transfer"],
    ["reject", "inject", "object", "subject", "project"],
    ["produce", "reduce", "induce", "introduce", "deduce"],
    ["admit", "submit", "permit", "commit", "omit"],
    ["access", "assess", "excess", "asset"],
    ["accident", "incident", "coincidence"],
    ["capital", "capitol"],
    ["dairy", "diary"],
    ["decent", "descent", "dissent"],
    ["device", "devise"],
    ["ensure", "insure", "assure"],
    ["envelop", "envelope"],
    ["especially", "specially"],
    ["farther", "further", "father"],
    ["flame", "blame"],
    ["floor", "flour"],
    ["hard", "hardly"],
    ["hear", "here"],
    ["human", "humane"],
    ["idle", "idol", "ideal"],
    ["later", "latter", "latest"],
    ["lay", "lie"],
    ["lead", "led"],
    ["lessen", "lesson"],
    ["light", "slight", "flight", "fight"],
    ["medal", "meddle", "metal"],
    ["peace", "piece"],
    ["plain", "plane"],
    ["pray", "prey"],
    ["price", "prize", "praise"],
    ["profit", "prophet"],
    ["role", "roll"],
    ["root", "route"],
    ["sale", "sail"],
    ["scene", "seen"],
    ["sense", "since", "scent"],
    ["sole", "soul"],
    ["some", "sum"],
    ["son", "sun"],
    ["stair", "stare"],
    ["steal", "steel"],
    ["straight", "strait"],
    ["tale", "tail"],
    ["vain", "vein", "van"],
    ["waist", "waste"],
    ["wait", "weight"],
    ["weak", "week"],
    ["wear", "where"],
    ["whole", "hole"],
    ["wood", "would"],
    ["worth", "worthy", "worthwhile"],
]

SYNONYM_GROUPS: list[list[str]] = [
    ["career", "job", "profession", "occupation", "vocation"],
    ["thin", "lean", "slim", "slender", "skinny"],
    ["viewer", "audience", "spectator"],
    ["choose", "opt", "select", "pick", "elect"],
    ["grab", "grasp", "seize", "snatch"],
    ["focus", "concentrate"],
    ["vital", "crucial", "essential", "indispensable", "significant"],
    ["confirm", "prove", "verify", "testify"],
    ["suppose", "assume", "presume", "postulate"],
    ["entertain", "amuse", "delight", "please"],
    ["remote", "distant", "faraway", "isolated"],
    ["resolve", "solve", "settle", "determine"],
    ["promote", "advance", "boost", "further"],
    ["relate", "connect", "associate", "link"],
    ["conquer", "defeat", "overcome", "capture"],
    ["compensate", "offset", "balance"],
    ["major", "primary", "principal", "chief", "main"],
    ["minor", "secondary", "subordinate"],
    ["improve", "enhance", "better", "promote"],
    ["provide", "supply", "offer", "furnish"],
    ["approve", "agree", "consent", "endorse"],
    ["option", "choice", "alternative", "selection"],
    ["ability", "capacity", "capability", "competence"],
    ["opportunity", "chance", "occasion"],
    ["community", "society", "neighborhood"],
    ["opponent", "rival", "competitor", "enemy"],
    ["honor", "glory", "privilege", "credit"],
    ["appropriate", "proper", "suitable", "fitting"],
    ["appreciate", "enjoy", "value", "treasure"],
    ["appetite", "desire", "craving", "hunger"],
    ["current", "present", "contemporary", "modern"],
    ["charge", "cost", "fee", "expense", "price"],
    ["fluent", "smooth", "fluid"],
    ["expense", "expenditure", "cost"],
    ["terminal", "final", "ultimate", "end"],
    ["trial", "test", "experiment"],
    ["native", "local", "indigenous"],
    ["congratulate", "celebrate", "compliment"],
    ["firm", "company", "corporation", "enterprise"],
    ["harm", "damage", "injury", "hurt"],
    ["perform", "execute", "conduct", "fulfill"],
    ["determine", "decide", "resolve", "settle"],
    ["critical", "crucial", "vital", "essential"],
    ["candidate", "applicant", "nominee"],
    ["sharp", "keen", "acute", "pointed"],
    ["dull", "boring", "tedious", "monotonous"],
    ["efficient", "effective", "efficacious"],
    ["speculate", "guess", "conjecture", "surmise"],
    ["medium", "media", "means", "channel"],
    ["precise", "accurate", "exact", "correct"],
    ["prediction", "forecast", "projection"],
    ["recession", "depression", "downturn", "slump"],
    ["beg", "plead", "implore", "request"],
    ["resolve", "determination", "resolution"],
    ["promote", "encourage", "motivate", "inspire"],
    ["nasty", "unpleasant", "disgusting", "offensive"],
    ["cooperate", "collaborate", "coordinate"],
    ["prove", "demonstrate", "verify", "confirm"],
    ["opt", "choose", "select", "elect"],
    ["grab", "grasp", "seize", "clutch"],
]


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------

def strip_bullet(s: str) -> str:
    t = s.strip()
    t = re.sub(r"^(?:>\s*)+", "", t)
    t = re.sub(r"^[-*+•]\s*", "", t)
    return t.strip()


def first_cjk(s: str) -> int:
    m = CJK.search(s)
    return m.start() if m else -1


def clean_head(h: str) -> str:
    h = IPA.sub(" ", h)
    h = h.replace("**", "").replace("==", "")
    h = re.sub(r"[：:，,。；;、\s]+$", "", h)
    h = re.sub(r"^[\s\-–—*>]+", "", h)
    return h.strip()


def clean_gloss(g: str, word: str) -> str:
    g = re.sub(r"\s+", " ", g)
    g = g.replace("...", "…").replace("。。。", "…")
    g = re.sub(r"\b" + re.escape(word) + r"\b\s*$", "", g, flags=re.I)
    g = g.strip(" \t:：;；,，。.、")
    return g


def normalize_pos(s: str) -> str:
    def rep(m: re.Match) -> str:
        return m.group(1) + ("" if s[m.end():m.end() + 1] == "." else ".")
    return POS_LOOSE.sub(rep, s)


def parse_senses(rest: str, word: str) -> tuple[list[tuple[str, str]], str]:
    rest = normalize_pos(rest)
    ipas = IPA.findall(rest)
    ipa = "/" + ipas[0].strip() + "/" if ipas else ""
    rest = IPA.sub(" ", rest)
    rest = TAG.sub(" ", rest)
    rest = rest.replace("**", "").replace("==", "")
    rest = rest.strip(" \t:：;；,，。")

    senses: list[tuple[str, str]] = []
    if not rest:
        return senses, ipa

    matches = list(POS.finditer(rest))
    if matches:
        if matches[0].start() > 0:
            pre = clean_gloss(rest[: matches[0].start()], word)
            if pre:
                senses.append(("", pre))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(rest)
            pos = m.group(1).lower()
            g = clean_gloss(rest[m.end():end], word)
            if g or not senses:
                senses.append((pos, g))
    else:
        g = clean_gloss(rest, word)
        if g:
            senses.append(("", g))

    senses = [(p, g) for p, g in senses if g]
    if not senses:
        senses = [("", "")]
    return senses, ipa


def parse_head(s: str, next_line: str | None = None) -> dict | None:
    t = s.strip()
    t = re.sub(r"^(?:>\s*)+", "", t)
    t = re.sub(r"^[-*+•]\s*", "", t)
    t = re.sub(r"^\d+[.、]\s*", "", t)
    t = t.replace("**", "").replace("==", "").strip()
    if not t or t.startswith("#"):
        return None
    t = normalize_pos(t)

    # 不规则动词：fight-fought-fought
    m = re.match(r"^([A-Za-z]+)-([A-Za-z]+)-([A-Za-z]+)\b(.*)$", t)
    if m and CJK.search(m.group(4)):
        return {
            "word": m.group(1).lower(),
            "rest": m.group(4).strip(),
            "forms": [m.group(2), m.group(3)],
        }

    posm = POS.search(t)
    cjk = CJK.search(t)
    if posm:
        head, rest = t[: posm.start()], t[posm.start():]
    elif cjk:
        head, rest = t[: cjk.start()], t[cjk.start():]
    else:
        candidate = clean_head(t)
        if not candidate:
            return None
        if not re.fullmatch(
            r"[A-Za-z][A-Za-z'’\-]*(?:\s+[A-Za-z][A-Za-z'’\-]*){0,3}", candidate
        ):
            return None
        if candidate.lower().split()[0] in LABELS:
            return None
        if next_line:
            nl = next_line.strip()
            m2 = POS.match(nl)
            if m2 or CJK.match(nl):
                return {"word": candidate.lower(), "rest": "", "forms": []}
        return None

    head = clean_head(head)
    if not head or len(head) > 45:
        return None
    toks = head.split()
    if not (1 <= len(toks) <= 5):
        return None
    if not all(re.fullmatch(r"[A-Za-z][A-Za-z'’\-]*", x) for x in toks):
        return None
    if toks[0].lower() in LABELS:
        return None
    return {"word": " ".join(toks).lower(), "rest": rest.strip(), "forms": []}


def is_translation(s: str) -> bool:
    t = s.strip()
    words = re.findall(r"[A-Za-z][A-Za-z'’\-]*", t)
    if len(words) >= 7 and not POS.search(t):
        return True
    if CJK.match(t) and len(t) >= 25:
        return True
    return False


def is_note_prefix(b: str) -> bool:
    return any(b.startswith(p) for p in NOTE_PREFIXES)


def normalize_note(b: str) -> str:
    b = b.replace("**", "").replace("==", "").strip()
    b = re.sub(r"^(近义词|相似词)\s*[：:]\s*", lambda m: ("近义" if m.group(1) == "近义词" else "相似") + ": ", b)
    b = re.sub(r"\s*[：:]\s*", ": ", b, count=1)
    return b.strip(" :：;；")


# --------------------------------------------------------------------------
# 迁移
# --------------------------------------------------------------------------

def migrate_file(path: Path) -> tuple[list[dict], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    n = len(lines)
    entries: list[dict] = []
    trans: list[str] = []
    current: dict | None = None
    section = ""

    def next_nonempty(i: int) -> str | None:
        j = i + 1
        while j < n:
            if lines[j].strip():
                return lines[j].strip()
            j += 1
        return None

    def flush() -> None:
        nonlocal current
        if current:
            entries.append(current)
            current = None

    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s or s.startswith("<!--"):
            continue

        if re.match(r"^#{1,6}\s", s):
            section = s.lstrip("#").strip()
            flush()
            continue

        b = strip_bullet(s)

        # 1. 明确标注的补充笔记（辨析/例/记/错...）
        if is_note_prefix(b) and current is not None:
            note = normalize_note(b)
            if note and note not in current["notes"]:
                current["notes"].append(note)
            continue

        # 1.5 引用块里的联想/记忆（> - **career** 开头像 care...）
        if current is not None and re.match(r"^[-*>]", s):
            if not POS.search(b) and not IPA.search(b) and CJK.search(b):
                target = None
                bm = re.match(r"^\*\*([A-Za-z][A-Za-z'’\-]*)\*\*", b)
                if bm:
                    tw = bm.group(1).lower()
                    for e in reversed(entries):
                        if e["word"] == tw:
                            target = e
                            break
                if target is None and current["word"] in b.lower():
                    target = current
                if target is not None:
                    note = normalize_note(b)
                    if re.search(r"开头像|里有|想成|记成|联想", note) and not note.startswith("记"):
                        note = "记: " + note
                    if note and note not in target["notes"]:
                        target["notes"].append(note)
                continue

        # 2. 续行：词性行 / 缺释义时的中文行
        if current is not None:
            if POS.match(b) or (current["needs_def"] and CJK.match(b)):
                current["rawdef"] = (current.get("rawdef", "") + " " + b).strip()
                current["senses"], ipa = parse_senses(current["rawdef"], current["word"])
                current["ipa"] = current.get("ipa") or ipa
                current["needs_def"] = not any(g for _, g in current["senses"])
                continue

        # 3. 新词条
        h = parse_head(s, next_nonempty(i))
        if h:
            flush()
            current = {
                "word": h["word"],
                "rawdef": h["rest"],
                "senses": [],
                "ipa": "",
                "notes": [],
                "forms": h.get("forms", []),
                "section": section,
                "source": path.stem,
                "needs_def": False,
            }
            current["senses"], ipa = parse_senses(h["rest"], h["word"])
            current["ipa"] = ipa
            current["needs_def"] = not any(g for _, g in current["senses"])
            continue

        # 4. 其他
        if current is not None and re.match(r"^[-*>]", s):
            # 未标注的零散笔记，先丢掉，报告里留痕
            continue
        if is_translation(s):
            flush()
            trans.append(s)

    flush()
    return entries, trans


# --------------------------------------------------------------------------
# 拆开粘连词条：abandon vt.放弃 n.放任 abandonment n.抛弃
# --------------------------------------------------------------------------

def split_inline_entries(entries: list[dict]) -> list[dict]:
    out: list[dict] = []
    for e in entries:
        raw = e.get("rawdef", "")
        word = e["word"]
        if not raw:
            out.append(e)
            continue

        cuts: list[tuple[int, str]] = []
        for m in INLINE.finditer(raw):
            cand = m.group(1).lower()
            if cand == word or cand in STOP_WORDS:
                continue
            before = raw[: m.start()]
            # air conditioner 这类英文短语，不要从中间切开
            if re.search(r"[A-Za-z][A-Za-z'’\-]*\s+$", before):
                continue
            cuts.append((m.start(), cand))

        if not cuts:
            out.append(e)
            continue

        first_raw = raw[: cuts[0][0]].strip()
        cur = dict(e)
        cur["rawdef"] = first_raw
        cur["senses"], ipa = parse_senses(first_raw, word)
        cur["ipa"] = e.get("ipa") or ipa
        out.append(cur)

        for i, (start, cand) in enumerate(cuts):
            end = cuts[i + 1][0] if i + 1 < len(cuts) else len(raw)
            seg = raw[start:end].strip()
            rest = seg[len(cand):].strip()
            ne = {
                "word": cand,
                "rawdef": rest,
                "senses": [],
                "ipa": "",
                "notes": [],
                "forms": [],
                "section": e.get("section", ""),
                "source": e.get("source", ""),
                "needs_def": False,
            }
            ne["senses"], ipa2 = parse_senses(rest, cand)
            ne["ipa"] = ipa2
            out.append(ne)

    return out


# --------------------------------------------------------------------------
# 合并去重
# --------------------------------------------------------------------------

def norm_word(w: str) -> str:
    w = w.lower().replace("’", "'").strip()
    w = re.sub(r"\s+", " ", w)
    return w


def merge_into(dst: dict, src: dict) -> None:
    # senses
    for pos, gloss in src["senses"]:
        if not gloss:
            continue
        same = [(i, p, g) for i, (p, g) in enumerate(dst["senses"]) if p == pos]
        if not same:
            dst["senses"].append((pos, gloss))
            continue
        i, _, old = same[0]
        if gloss not in old and old not in gloss:
            dst["senses"][i] = (pos, old + "；" + gloss)
        else:
            dst["senses"][i] = (pos, old if len(old) >= len(gloss) else gloss)
    dst["senses"] = [(p, g) for p, g in dst["senses"] if g] or [("", "")]
    # ipa
    if not dst.get("ipa") and src.get("ipa"):
        dst["ipa"] = src["ipa"]
    # notes
    for note in src["notes"]:
        if note not in dst["notes"]:
            dst["notes"].append(note)
    # forms
    for f in src.get("forms", []):
        if f not in dst["forms"]:
            dst["forms"].append(f)


def stems_of(w: str) -> set[str]:
    out: set[str] = set()
    frontier = {w}
    for _ in range(2):
        nxt: set[str] = set()
        for x in frontier:
            for suf in SUFFIXES:
                if x.endswith(suf) and len(x) - len(suf) >= 4:
                    st = x[: -len(suf)]
                    out.add(st)
                    nxt.add(st)
                    if st.endswith("e") and len(st) - 1 >= 4:
                        out.add(st[:-1])
                        nxt.add(st[:-1])
        frontier = nxt
    return out


def build_families(words: list[str]) -> dict[str, str]:
    stems: dict[str, set[str]] = defaultdict(set)
    wordset = set(words)
    for w in words:
        if " " in w:
            continue
        for st in stems_of(w):
            stems[st].add(w)
            if st in wordset:
                stems[st].add(st)
    best: dict[str, str] = {}
    for st, ws in stems.items():
        if len(ws) < 2 or len(ws) > 12:
            continue
        for w in ws:
            if w not in best or len(st) > len(best[w]):
                best[w] = st
    return best


def apply_groups(
    words: dict[str, dict],
    groups: list[list[str]],
    tag: str,
) -> None:
    for group in groups:
        present = [w for w in group if w in words]
        if len(present) < 2:
            continue
        for w in present:
            others = [x for x in present if x != w]
            words[w]["tags"][tag].update(others)


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------

def sense_str(senses: list[tuple[str, str]]) -> str:
    parts = []
    for pos, g in senses:
        g = g.strip()
        if not g:
            continue
        if pos:
            p = pos if pos.endswith(".") else pos + "."
            parts.append(f"{p} {g}")
        else:
            parts.append(g)
    return "｜".join(parts) if parts else "待补"


def render(words: dict[str, dict]) -> str:
    out = [
        "# 四级词库",
        "",
        "> 格式：`word 词性. 中文释义 /音标/ [族:词根] [混:易混词] [近:近义词]`",
        "> 补充行：`- 辨析: ...` `- 例: ...` `- 记: ...` `- 错: ...`",
        "> 详细说明见 README.md",
        "",
    ]
    current_letter = None
    for key in sorted(words):
        letter = key[0].upper() if key[0].isalpha() else "Other"
        if letter != current_letter:
            out.append(f"# {letter}")
            out.append("")
            current_letter = letter
        e = words[key]
        tags = []
        if e["tags"]["族"]:
            tags.append("[族:" + ",".join(sorted(e["tags"]["族"])) + "]")
        if e["tags"]["混"]:
            tags.append("[混:" + ",".join(sorted(e["tags"]["混"])) + "]")
        if e["tags"]["近"]:
            tags.append("[近:" + ",".join(sorted(e["tags"]["近"])) + "]")
        line = f"{e['word']} {sense_str(e['senses'])}"
        if e.get("ipa"):
            line += f" {e['ipa']}"
        if tags:
            line += " " + " ".join(tags)
        out.append(line)
        for note in e["notes"]:
            out.append(f"- {note}")
        if e.get("forms"):
            out.append(f"- 变形: {', '.join(e['forms'])}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def main() -> None:
    files = [SRC / "26_1.md"]
    all_entries: list[dict] = []
    all_trans: list[str] = []
    for f in files:
        if not f.exists():
            print(f"跳过（不存在）：{f}")
            continue
        entries, trans = migrate_file(f)
        print(f"{f.name}: 条目 {len(entries)}，翻译块 {len(trans)}")
        all_entries.extend(entries)
        all_trans.extend(trans)

    db: dict[str, dict] = {}
    dups: list[tuple[str, str]] = []
    all_entries = split_inline_entries(all_entries)
    for e in all_entries:
        key = norm_word(e["word"])
        e["word"] = key
        e.setdefault("tags", {"族": set(), "混": set(), "近": set()})
        if key in db:
            dups.append((key, e["source"]))
            merge_into(db[key], e)
        else:
            db[key] = e

    words = list(db)
    families = build_families(words)
    for w, fam in families.items():
        db[w]["tags"]["族"].add(fam)
    apply_groups(db, CONFUSABLE_GROUPS, "混")
    apply_groups(db, SYNONYM_GROUPS, "近")

    BUILD.mkdir(exist_ok=True)
    dump = []
    for k in sorted(db):
        e = db[k]
        dump.append({
            "word": e["word"],
            "senses": e["senses"],
            "ipa": e.get("ipa", ""),
            "notes": e["notes"],
            "forms": e.get("forms", []),
            "tags": {t: sorted(v) for t, v in e["tags"].items()},
            "source": e.get("source", ""),
            "section": e.get("section", ""),
        })
    (BUILD / "words.raw.json").write_text(
        json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    OUT.write_text(render(db), encoding="utf-8")

    # 报告
    todo = [w for w, e in db.items() if not any(g for _, g in e["senses"])]
    fam_groups: dict[str, list[str]] = defaultdict(list)
    for w, fam in families.items():
        fam_groups[fam].append(w)
    dup_count: dict[str, int] = defaultdict(int)
    for k, _ in dups:
        dup_count[k] += 1

    lines = [
        "# 迁移报告",
        "",
        f"- 原始条目：{len(all_entries)}",
        f"- 唯一词条：{len(db)}",
        f"- 重复条目：{len(dups)}（涉及 {len(dup_count)} 个词）",
        f"- 无释义待补：{len(todo)}",
        f"- 自动词族：{len(fam_groups)} 组",
        f"- 翻译块（未进词库）：{len(all_trans)} 行",
        "",
        "## 重复最多的词",
        "",
    ]
    for w, c in sorted(dup_count.items(), key=lambda x: (-x[1], x[0]))[:40]:
        lines.append(f"- {w}: {c + 1} 条")
    lines += ["", "## 无释义待补", ""]
    lines += [f"- {w}" for w in sorted(todo)]
    lines += ["", "## 自动词族（供检查）", ""]
    for fam, ws in sorted(fam_groups.items()):
        lines.append(f"- `{fam}`: " + ", ".join(sorted(ws)))
    lines += ["", "## 易混组（已生效）", ""]
    for group in CONFUSABLE_GROUPS:
        present = [w for w in group if w in db]
        if len(present) >= 2:
            lines.append("- " + " / ".join(present))
    lines += ["", "## 近义组（已生效）", ""]
    for group in SYNONYM_GROUPS:
        present = [w for w in group if w in db]
        if len(present) >= 2:
            lines.append("- " + " / ".join(present))

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n写出 {OUT}（{len(db)} 词）")
    print(f"写出 {REPORT}")


if __name__ == "__main__":
    main()
