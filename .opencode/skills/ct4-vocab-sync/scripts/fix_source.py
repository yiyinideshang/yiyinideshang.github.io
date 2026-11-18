#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix typos and duplicate headwords in the 26_1.md source note.

- Preserves CRLF line endings.
- Applies exact typo fixes.
- Groups entry lines by normalized headword.
- Keeps the first occurrence and merges senses/tags from later duplicates.
- Reports ambiguous duplicate blocks instead of guessing.
"""
from __future__ import annotations

import argparse
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "tools"))
import migrate as mig  # noqa: E402

DEFAULT_SOURCE = Path("/mnt/d/Typora/英语/26_1.md")

POS_SET = {"n", "v", "vt", "vi", "adj", "adv", "prep", "pron", "conj", "num",
           "art", "phr", "idm", "aux", "int", "det", "phrv", "vlink"}
CJK = re.compile(r"[\u4e00-\u9fff]")
TAG_RE = re.compile(r"\[(?:族|混|近):[^\]]*\]")
IPA_RE = re.compile(r"/[^/\n]{1,50}/")

# Exact typo/format fixes. Keys are compared with whitespace collapsed.
FIXES = {
    "regular 有规律的,频繁的,通常的 n.常客": "regular adj.有规律的，频繁的，通常的；n.常客",
    "regular 有规律的,频繁的,通常的n.常客": "regular adj.有规律的，频繁的，通常的；n.常客",
    "lazy 懒惰的 lazyness n.懒惰,懒散": "lazy adj.懒惰的；laziness n.懒惰，懒散",
    "- severe 严重的,严厉的,严峻的": "- severe adj.严重的，严厉的，严峻的",
    "slight 轻微的,微小的 n/vt.轻视,冷落": "slight adj.轻微的，微小的；n./vt.轻视，冷落",
    "intelligent 聪明的,智能的 intelligence n.智力,情报 intelligently adv.": "intelligent adj.聪明的，智能的；intelligence n.智力，情报；intelligently adv.聪明地",
    "- clever 聪敏的灵巧的,巧妙的": "- clever adj.聪明的，灵巧的，巧妙的",
    "lower 下面的,下方的,在底部的vt.把...放低,把...降下v.减少,缩小,降低": "lower adj.下面的，下方的，底部的；vt.把…放低，把…降下；v.减少，缩小，降低",
    "teen 青少年时期;adj.青少年的 teenager n.青少年": "teen n.青少年时期；adj.青少年的；teenager n.青少年",
    "hard 坚硬的,艰难的,费力的adv.努力地,艰难地,猛力地": "hard adj.坚硬的，艰难的，费力的；adv.努力地，艰难地，猛力地",
    "audio 录音的,音频的 n. 声音,音频": "audio adj.录音的，音频的；n.声音，音频",
    "fake 假装的,假的,伪造的n.假货,赝品 vt.伪造,冒充v.假装,装出": "fake adj.假装的，假的，伪造的；n.假货，赝品；vt.伪造，冒充；v.假装，装出",
    "gray 灰色的；昏暗的n.灰色，灰白色vi.(头发)变花白": "gray adj.灰色的，昏暗的；n.灰色，灰白色；vi.(头发)变花白",
    "command .命令,指挥,管辖,掌握,精通vt.应得,博得v.指挥": "command n.命令，指挥，管辖，掌握，精通；vt.应得，博得；v.指挥",
    "extra 额外的,附加的adv.额外,另外n.另外收费的事物": "extra adj.额外的，附加的；adv.额外，另外；n.另外收费的事物",
    "moderate 中等的,温和的,有节制的v缓和,使中和,调节,主持,n.持温和观点者": "moderate adj.中等的，温和的，有节制的；v.缓和，使中和，调节，主持；n.持温和观点者",
    "healthy (有益)健康的,合情理的": "healthy adj.(有益)健康的，合情理的",
    "present 当前的,在场的,存在的n.礼物,目前,现在vt.授予,提交展现,使经历": "present adj.当前的，在场的，存在的；n.礼物，目前，现在；vt.授予，提交，展现，使经历",
    "current 当前的,现在的,流行的n.水流,电流,气流": "current adj.当前的，现在的，流行的；n.水流，电流，气流",
    "native 出生地,本地的,n.出生某地的人": "native adj.出生地的，本地的；n.出生某地的人",
    "local 出生的本地的n.本地人": "local adj.出生的，本地的；n.本地人",
    "carry out phrv. 实施(计划),兑现(诺言),完成(任务)": "carry out phr. 实施(计划)，兑现(诺言)，完成(任务)",
    "ripe (时机)成熟的、(水果等)成熟的": "ripe adj.(时机)成熟的，(水果等)成熟的",
    "criminal 犯罪的,刑事的n.罪犯,犯人": "criminal adj.犯罪的，刑事的；n.罪犯，犯人",
    "dull 枯燥无味的,迟钝的v.是麻木,使迟钝": "dull adj.枯燥无味的，迟钝的；v.使麻木，使迟钝",
    "multimedia 多媒体的n.多媒体的使用": "multimedia adj.多媒体的；n.多媒体的使用",
    "steady 稳步的，稳定的，可靠的v.稳住，是平静；adv.稳定地，持续地": "steady adj.稳步的，稳定的，可靠的；v.稳住，使平静；adv.稳定地，持续地",
    "downward 向下的，下降的adv.向下": "downward adj.向下的，下降的；adv.向下",
    "senior 级别高的，老年的，成人的，中学的 n.毕业班学生": "senior adj.级别高的，老年的，成人的，中学的；n.毕业班学生",
    "junior 级别低的，青少年的n.大三学生": "junior adj.级别低的，青少年的；n.大三学生",
    "deadly 致命的，彻底的adv.彻底地，极其": "deadly adj.致命的，彻底的；adv.彻底地，极其",
    "negative 有害的，消极的，否定的 n.否等词，否定vt.否定，拒绝": "negative adj.有害的，消极的，否定的；n.否定词，否定；vt.否定，拒绝",
    "complete 完全的，全部的v.完成，结束，使完整": "complete adj.完全的，全部的；v.完成，结束，使完整",
    "following 接着的，下述的prep.在...之后，由于": "following adj.接着的，下述的；prep.在…之后，由于",
    "stiff 僵硬的，adv.极其，非常n.死尸": "stiff adj.僵硬的；adv.极其，非常；n.死尸",
    "revolutionary 革命性的，突破性的n.革命家": "revolutionary adj.革命性的，突破性的；n.革命家",
    "fine 精美的，健康的，满意的，细的 adv.很好，不错n.罚金，罚款 vt.对...处以罚款": "fine adj.精美的，健康的，满意的，细的；adv.很好，不错；n.罚金，罚款；vt.对…处以罚款",
    "sitting 现任的，在任期内的n.坐着(做某事)的一段n.一批，一轮，开会，开庭": "sitting adj.现任的，在任期内的；n.坐着(做某事)的一段时间；n.一批，一轮，开会，开庭",
    "conservative 保守的n.保守的人": "conservative adj.保守的；n.保守的人",
    "spare 闲置的，备用的，空闲的vt.留出，免去n.备用品": "spare adj.闲置的，备用的，空闲的；vt.留出，免去；n.备用品",
    "mere 仅仅，只不过，极小的，单单n.小湖，池塘": "mere adj.仅仅，只不过，极小的，单单；n.小湖，池塘",
    "bare 赤裸的，基本的，空的vt.使暴露": "bare adj.赤裸的，基本的，空的；vt.使暴露",
    "influential 有影响力的，有权势的，n. ...的人": "influential adj.有影响力的，有权势的；n.有影响力的人",
    "renewable 可再生的，可延期的;n.可再生能源": "renewable adj.可再生的，可延期的；n.可再生能源",
    "insure v(给...)投保;vt.确保 insurance n.保险 make sure 查明,核实,确保": "insure v.(给…)投保；vt.确保；insurance n.保险；make sure 查明，核实，确保",
    "major 主要的,重要的,打的; n.专业,vi主修 majority n.大部分,大多数": "major adj.主要的，重要的，大的；n.专业；vi.主修；majority n.大部分，大多数",
    "minor 较小的,次要的,轻微的n.未成年人;vi.辅修": "minor adj.较小的，次要的，轻微的；n.未成年人；vi.辅修",
    "batch n.洗澡,浴缸": "bath n.洗澡，浴缸",
    "intervence v.打断.vi.干涉,介入": "intervention n.干涉，介入；打断",
    "dooted 由点组成的,遍布的": "dotted adj.由点组成的，遍布的",
    "essary n.文章,论文,随笔vt.企图,尝试": "essay n.文章，论文，随笔；vt.企图，尝试",
    "efficent 效率高的": "efficient adj.效率高的",
    "fabirc n.织物，布料，结构，构造": "fabric n.织物，布料，结构，构造",
    "fuction n.功能，职能；vi.起作用，运转": "function n.功能，职能；vi.起作用，运转",
    "cyperspace n.忘路空间": "cyberspace n.网络空间",
    "evently 均匀地；平均地": "evenly adv.均匀地，平均地",
    "bibical 与《圣经》有关的；大规模的": "biblical adj.圣经的；大规模的",
    "palm n. 手掌，手心；棕桐树": "palm n.手掌，手心；棕榈树",
    "theory n.理论，学说，理论基础，管带你": "theory n.理论，学说，理论基础，观点",
    "attack n.攻击，袭击，抨击v.攻击，袭击;vt.破环，侵蚀": "attack n.攻击，袭击，抨击；v.攻击，袭击；vt.破坏，侵蚀",
    "slip vi.滑倒，溜走，变差，陷入;vt.悄悄赛v.(迅速且容易地)穿或脱n.差错，纸条": "slip vi.滑倒，溜走，变差，陷入；vt.悄悄塞；v.(迅速且容易地)穿或脱；n.差错，纸条",
    "learning n.倾向,偏爱": "leaning n.倾向，偏爱",
    "dean n.院长，系主任": "dean n.院长，系主任",
    "enterprise n.企业,项目,规划 enterpriing 有事业心的": "enterprise n.企业，项目，规划；enterprising adj.有事业心的",
    "> > - observe observe v观察,注视vt.注意到,遵守": "> > - observe v.观察，注视；vt.注意到，遵守",
    "X-ray n.x光检查": "X-ray n.X光检查",
    "bathe V.": "bathe v.洗澡，沐浴",
    "worthy 指的...的指得尊敬的": "worthy adj.值得的，值得尊敬的",
    "fluency n.": "fluency n.流利，流畅",
    "lower 下main的，下方的，在底部的vt.把...放低，使...降下v.减少，缩小，降低": "lower adj.下面的，下方的，底部的；vt.把…放低，使…降下；v.减少，缩小，降低",
    "loss n.丧失,损失,亏程,逝世": "loss n.丧失，损失，亏损，逝世",
    "emergency n.紧急事件,意外时间": "emergency n.紧急事件，意外情况",
    "consequent 因之而其的，作为结果的": "consequent adj.因之而起的，作为结果的",
    "Bible 圣经": "Bible n.《圣经》",
    "bubble n/vi. 起泡，气泡，经济泡沫，涌动": "bubble n./vi. 起泡，气泡，经济泡沫，涌动",
    "edit v/n 编辑，校订": "edit v./n. 编辑，校订",
    "pray v.祈祷，祷告adv.请问": "pray v.祈祷，祷告；adv.请，请问",
    "tight 紧的,紧身的,严格的,拮据的": "tight adj.紧的，紧身的，严格的，拮据的",
    "tough 艰难的,严厉的,强硬的,坚强的": "tough adj.艰难的，严厉的，强硬的，坚强的",
    "wealthy 富有的,富裕的": "wealthy adj.富有的，富裕的",
    "pot 锅,罐,壶vt.把...栽入盆中": "pot n.锅，罐，壶；vt.把…栽入盆中",
    "sitter 临时保姆，模特": "sitter n.临时保姆，模特",
    "serious 严重的,严肃的 seriousness n.严肃,严重": "serious adj.严重的，严肃的；seriousness n.严肃，严重",
    "inner 里面的,内部的,内心的": "inner adj.里面的，内部的，内心的",
    "tender 温柔的": "tender adj.温柔的",
    "regulate v(以规章)管理,约束 vt.调整,调节": "regulate v.(以规章)管理，约束；vt.调整，调节",
    "shift v.转移，挪动，换(档)vi.(情况等)改变vt.改变观点(态度等)n.改变，转变，轮班": "shift v.转移，挪动，换(档)；vi.(情况等)改变；vt.改变观点(态度等)；n.改变，转变，轮班",
    "harm n /vt. 伤害,损害": "harm n./vt. 伤害，损害",
    "determine vt.决定，查明，确定v.决意，下决心": "determine vt.决定，查明，确定；v.决意，下决心",
    "sit v.坐(落在)，被放在，担任vt.使就坐v.参加考试": "sit v.坐(落在)，被放在，担任；vt.使就坐；v.参加考试",
    "wake v.醒,唤醒 asleep 睡着的": "wake v.醒，唤醒；asleep adj.睡着的",
    "conquer vt.占领,征服,克服 conqueror n.征服者,占领者 unconquerable 不可战胜的": "conquer vt.占领，征服，克服；conqueror n.征服者，占领者；unconquerable adj.不可战胜的",
    "renovate vt.修复,改造,翻新 renovation n.修复,改造,翻新": "renovate vt.修复，改造，翻新；renovation n.修复，改造，翻新",
    "experiment n.实验，试验，尝试，实践vi.(用...)做实验，进行试验，试用": "experiment n.实验，试验，尝试，实践；vi.(用…)做实验，进行试验，试用",
    "vital 极其重要的,维持生命所必需的,充满活力的": "vital adj.极其重要的，维持生命所必需的，充满活力的",
    "employer 雇金": "employer n.雇主",
    "employee 雇员": "employee n.雇员",
    "colonize v在...建殖民地；动植物；在...聚局": "colonize v.在…建殖民地；动植物；在…聚居",
    "disgust n.y厌恶，反感vt.使厌恶，使方案": "disgust n.厌恶，反感；vt.使厌恶，使反感",
    "regret vt.为...感到后悔，对...改到抱歉n.懊悔，遗憾": "regret vt.为…感到后悔，对…感到抱歉；n.懊悔，遗憾",
    "colleague n.同事，通辽": "colleague n.同事，同行",
    "significant 重要的，数量的的": "significant adj.重要的，显著的；数量可观的",
    "variat n.变体，变化形式adj.变体的，不同的": "variant n.变体，变化形式；adj.变体的，不同的",
    "dare modal.敢于vt.激将n.挑战，激将": "dare v./modal.敢于；vt.激将；n.挑战，激将",
    "stale 不新鲜的，厌倦的v(使)变得不新鲜": "stale adj.不新鲜的，厌倦的；v.(使)变得不新鲜",
    "pain n.疼痛，痛苦vi.使疼痛，使痛苦": "pain n.疼痛，痛苦；vt.使疼痛，使痛苦",
}


def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def norm_head(w: str) -> str:
    w = w.lower().strip().replace("%E2%80%99", "'").replace("’", "'")
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


ENTRY_RE = re.compile(
    r"^(?P<prefix>\s*(?:>\s*)*[-*+•]?\s*)"
    r"(?P<word>[A-Za-z][A-Za-z'’\-]*(?:\s+[A-Za-z][A-Za-z'’\-]*){0,4})\b"
    r"(?P<rest>.*)$"
)


def is_entry_line(line: str):
    s = line.strip()
    if not s or s.startswith(("#", "<!--", "|")):
        return None
    if "**" in s:
        return None
    m = ENTRY_RE.match(line)
    if not m:
        return None
    word = m.group("word").lower()
    rest = m.group("rest")
    if not CJK.search(rest):
        return None
    if word.split()[0] in mig.STOP_WORDS:
        return None
    if word.split()[0] in {"passage", "section", "translation", "part", "unit", "chapter", "contents"}:
        return None
    # Blockquoted explanatory prose often starts with an English term and then
    # a long Chinese explanation. Do not treat those as dictionary entries.
    if s.startswith(">"):
        cjk = len(CJK.findall(rest))
        has_pos = bool(re.search(r"(?<![A-Za-z])(?:n|v|vt|vi|adj|adv|prep|pron|conj)\.", rest, re.I))
        if cjk > 60 and not has_pos:
            return None
        # Blockquoted prose often contains a colon or explanation words; a
        # dictionary entry in a blockquote is normally a short gloss.
        if re.search(r"[：:？?]|为什么|通常|表示|可以|指的是", rest):
            return None
    return m


def split_head_rest(m):
    """Split a regex head that may have swallowed a POS token."""
    toks = m.group("word").split()
    removed = []
    while len(toks) > 1 and toks[-1].lower() in POS_SET:
        removed.insert(0, toks.pop())
    head = " ".join(toks)
    rest = " ".join(removed + [m.group("rest").lstrip()]).strip()
    rest = re.sub(r"\s+([.．])", r"\1", rest)
    return head, rest


def line_rest(line: str):
    m = is_entry_line(line)
    if not m:
        return ""
    _, rest = split_head_rest(m)
    rest = rest.strip()
    rest = re.sub(r"^[：:，,、；;\s]+", "", rest).strip()
    return rest


def richness(line: str) -> int:
    rest = line_rest(line)
    return len(CJK.findall(rest)) + 3 * len(re.findall(r"(?<![A-Za-z])(?:n|v|vt|vi|adj|adv|prep|pron|conj)\.", rest, re.I))


def extract_tags(line: str):
    return TAG_RE.findall(line)


def ensure_tags(rest: str, tags):
    out = rest
    for tag in tags:
        if tag not in out:
            out += " " + tag
    return out.strip()


def detect_note_after(lines, idx):
    """Return True if the duplicate line is followed by a real note line."""
    j = idx + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    if j >= len(lines):
        return False
    s = lines[j].strip()
    s = re.sub(r"^(?:>\s*)+", "", s)
    s = re.sub(r"^[-*+•]\s*", "", s)
    return any(s.startswith(p) for p in mig.NOTE_PREFIXES) or s.startswith("**参考")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = Path(args.source)
    raw = path.read_bytes().decode("utf-8")
    lines = raw.splitlines(keepends=True)

    # 1. exact fixes
    changed = []
    for i, line in enumerate(lines):
        ending = ""
        body = line
        if body.endswith("\r\n"):
            body, ending = body[:-2], "\r\n"
        elif body.endswith("\n"):
            body, ending = body[:-1], "\n"
        key = norm_space(body)
        new = FIXES.get(key)
        if new is not None:
            lines[i] = new + ending
            changed.append((i + 1, key, new))
    print(f"typo fixes: {len(changed)}")
    for n, old, new in changed[:20]:
        print(f"  L{n}: {old[:70]} -> {new[:70]}")

    # 2. duplicate headwords: keep the first occurrence, but use the richest
    # definition from the group and merge any tags.
    groups = {}
    for i, line in enumerate(lines):
        m = is_entry_line(line)
        if not m:
            continue
        h = norm_head(m.group("word"))
        if not h:
            continue
        groups.setdefault(h, []).append(i)
    duplicates = {h: idxs for h, idxs in groups.items() if len(idxs) > 1}
    print(f"duplicate headwords: {len(duplicates)}")
    remove = set()
    ambiguous = []
    for h, idxs in duplicates.items():
        keep = idxs[0]
        keep_m = is_entry_line(lines[keep])
        if not keep_m:
            continue
        if any(detect_note_after(lines, i) for i in idxs[1:]):
            ambiguous.append((h, idxs[0] + 1))
            continue
        rich = max(idxs, key=lambda i: richness(lines[i]))
        rich_m = is_entry_line(lines[rich])
        if not rich_m:
            continue
        rest = line_rest(lines[rich])
        rich_cjk = set(CJK.findall(rest))
        for i in idxs:
            if i == rich:
                continue
            other = line_rest(lines[i])
            if not other:
                continue
            other_cjk = set(CJK.findall(other))
            if other_cjk - rich_cjk:
                rest += "；" + other
                rich_cjk |= other_cjk
        tags = []
        for i in idxs:
            for tag in extract_tags(lines[i]):
                if tag not in tags:
                    tags.append(tag)
        rest = ensure_tags(rest, tags)
        head = norm_head(rich_m.group("word"))
        if head == "x-ray":
            head = "X-ray"
        ending = "\r\n" if lines[keep].endswith("\r\n") else ("\n" if lines[keep].endswith("\n") else "")
        lines[keep] = keep_m.group("prefix") + head + " " + rest + ending
        for i in idxs[1:]:
            remove.add(i)
    if ambiguous:
        print("ambiguous duplicates left for manual review:")
        for h, n in ambiguous:
            print(f"  {h} (L{n})")
    if remove:
        out = [line for i, line in enumerate(lines) if i not in remove]
        lines = out
    print(f"removed duplicate lines: {len(remove)}")

    if args.dry_run:
        print("dry run: no write")
        return
    path.write_bytes("".join(lines).encode("utf-8"))
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
