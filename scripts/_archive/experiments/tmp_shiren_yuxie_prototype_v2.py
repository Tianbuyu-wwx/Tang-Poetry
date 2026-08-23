# -*- coding: utf-8 -*-
"""《詩人玉屑》评点接入原型 v2：章节作者上下文 + 更严格的匹配。"""

from __future__ import annotations

import ctypes
import json
import os
import re
import time
from collections import Counter
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
API_URL = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "TangPoetrySite/1.0 (public-domain source integration)"
COMMENTARY_NGRAM = 10

BRACKETS = re.compile(r"[（(][^）)]*[）)]")
PUNCT = re.compile(r"[\s，。、；：？！·・【】「」『』—…（）()《》〈〉\-\[\]]")


def build_simplifier():
    try:
        from opencc import OpenCC
        converter = OpenCC("t2s")
        return converter.convert
    except ImportError:
        pass
    if os.name == "nt":
        mapper = ctypes.windll.kernel32.LCMapStringEx
        flag = 0x02000024

        def windows_simplify(value):
            value = str(value or "")
            if not value:
                return ""
            size = mapper("zh-CN", flag, value, len(value), None, 0, None, None, 0)
            if not size:
                return value
            target = ctypes.create_unicode_buffer(size)
            mapper("zh-CN", flag, value, len(value), target, size, None, None, 0)
            return target.value
        return windows_simplify
    raise RuntimeError("非 Windows 系统请安装 opencc")


_raw_simplify = build_simplifier()


def simplify(value):
    converted = _raw_simplify(str(value or ""))
    return converted.encode("utf-8", errors="replace").decode("utf-8")


def normalize(value):
    value = BRACKETS.sub("", simplify(value))
    return PUNCT.sub("", value)


def api_parse(page: str, attempts: int = 5) -> dict:
    query = urlencode({
        "action": "parse",
        "page": page,
        "prop": "text|wikitext",
        "format": "json",
        "formatversion": 2,
    })
    request = Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.load(response)
            if "error" in payload:
                raise RuntimeError(payload["error"])
            return payload["parse"]
        except (HTTPError, URLError, TimeoutError, IncompleteRead) as error:
            if attempt == attempts:
                raise RuntimeError(f"下载失败：{page}: {error}") from error
            retry_after = 0
            if isinstance(error, HTTPError) and error.code == 429:
                retry_after = int(error.headers.get("Retry-After", "0") or 0)
            time.sleep(max(retry_after, attempt * 4))
    raise AssertionError("unreachable")


def clean_wikitext(wikitext: str) -> str:
    lines = wikitext.splitlines()
    cleaned = []
    in_header = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("{{header") or stripped.startswith("{{header2"):
            in_header = True
            continue
        if in_header and stripped == "}}":
            in_header = False
            continue
        if in_header:
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def extract_text_from_wikitext(wikitext: str) -> str:
    text = clean_wikitext(wikitext)
    text = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"'''?|''", "", text)
    text = re.sub(r"<sub>.*?</sub>", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.S)
    # 去掉繁简转换标记 -{...}-
    text = re.sub(r"-\{([^}]*)\}-", r"\1", text)
    lines = []
    for line in text.splitlines():
        line = re.sub(r"[ \t\u3000]+", " ", line).strip()
        if line or (lines and lines[-1]):
            lines.append(line)
    return "\n".join(lines).strip()


def load_poems():
    path = ROOT / "docs" / "quan_tang_shi_open.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    records = {}
    by_author = {}
    for index, poem in enumerate(data["poems"]):
        poem_id = f"open_{index:05d}"
        author = simplify(poem.get("author", "")).strip()
        title = simplify(poem.get("title", "")).strip()
        paragraphs = [simplify(part).strip() for part in poem.get("paragraphs", []) if part.strip()]
        verse = normalize("".join(paragraphs))
        records[poem_id] = {
            "id": poem_id,
            "author": author,
            "title": title,
            "paragraphs": paragraphs,
            "verse": verse,
        }
        by_author.setdefault(normalize(author), []).append(poem_id)
    return records, by_author


def build_unique_verse_index(poems: dict):
    owners = {}
    for poem_id, record in poems.items():
        verse = record["verse"]
        if len(verse) < COMMENTARY_NGRAM:
            continue
        grams = {verse[i:i + COMMENTARY_NGRAM] for i in range(len(verse) - COMMENTARY_NGRAM + 1)}
        for gram in grams:
            previous = owners.get(gram)
            if previous is None:
                owners[gram] = poem_id
            elif previous != poem_id:
                owners[gram] = ""
    return {gram: owner for gram, owner in owners.items() if owner}


def parse_sections(text: str):
    """解析 ===作者=== 和 ====小标题==== 层级，返回带上下文的行列表。"""
    sections = []
    current_author = ""
    current_section = ""
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^===\s*([^=].*?)\s*===$", stripped):
            current_author = re.sub(r"^===\s*|\s*===$", "", stripped).strip()
            current_section = ""
            continue
        if re.match(r"^====\s*([^=].*?)\s*====$", stripped):
            current_section = re.sub(r"^====\s*|\s*====$", "", stripped).strip()
            continue
        if re.match(r"^==\s*([^=].*?)\s*==$", stripped):
            continue
        if not stripped:
            continue
        sections.append({
            "author": current_author,
            "section": current_section,
            "text": line,
        })
    return sections


def find_quoted_verses(text: str, min_len: int = 10, max_len: int = 240):
    """找出被「」或『』包围的引文，避免跨引号。"""
    quotes = []
    pattern = re.compile(r"[「『]([^「』』\n]{%d,%d})[」』]" % (min_len, max_len))
    for match in pattern.finditer(text):
        raw = match.group(1)
        normalized = normalize(raw)
        if len(normalized) >= min_len:
            quotes.append({
                "raw": raw,
                "normalized": normalized,
                "start": match.start(),
                "end": match.end(),
            })
    return quotes


def match_quote(quote: dict, unique_grams: dict, poems: dict, section_author: str = "", by_author: dict = None):
    """用十字片段投票，并可利用章节作者优先。"""
    text = quote["normalized"]
    if len(text) < COMMENTARY_NGRAM:
        return None, 0
    scores = Counter()
    for i in range(len(text) - COMMENTARY_NGRAM + 1):
        poem_id = unique_grams.get(text[i:i + COMMENTARY_NGRAM])
        if poem_id:
            scores[poem_id] += 1
    if not scores:
        return None, 0

    section_author_norm = normalize(section_author)
    # 如果章节作者已知，提升该作者诗作的分数
    if section_author_norm and by_author:
        boost = max(scores.values()) * 0.3
        for poem_id in by_author.get(section_author_norm, []):
            if poem_id in scores:
                scores[poem_id] += boost

    ranked = scores.most_common()
    top_score = ranked[0][1]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    # 严格：第一名至少比第二名多 2 分，且覆盖度不低于 20%
    coverage = top_score / max(1, len(text) - COMMENTARY_NGRAM + 1)
    if second_score >= top_score - 2 or coverage < 0.20:
        return None, top_score
    return ranked[0][0], top_score


def extract_commentary(line: str, quote_raw: str) -> str:
    """提取包含该引文的那一句评点，将句中其他引文替换为「…」。"""
    # 拆分成句子（保留句末标点）
    sentences = re.split(r"(?<=[。！？；])", line)
    target = ""
    for sent in sentences:
        if quote_raw in sent:
            target = sent
            break
    if not target:
        target = line
    # 把非目标引文替换为「…」
    def replace_other(match):
        if quote_raw in match.group(0):
            return match.group(0)
        return "……"
    cleaned = re.sub(r"[「『][^「』』]+[」』]", replace_other, target)
    # 去掉当前引文本身
    cleaned = cleaned.replace(quote_raw, "")
    cleaned = re.sub(r"\s+", "", cleaned)
    # 清理残留：空引号、转换标记等
    cleaned = re.sub(r"[-\{\}]-", "", cleaned)
    cleaned = cleaned.replace("「」", "").replace("『』", "")
    cleaned = cleaned.strip("，。、；：？！·")
    return cleaned[:300]


def main():
    poems, by_author = load_poems()
    unique_grams = build_unique_verse_index(poems)
    print(f" poems loaded: {len(poems)}, unique grams: {len(unique_grams)}")

    pages = [f"詩人玉屑/卷{i:02d}" for i in range(1, 22)]
    all_stats = []
    all_matches = []
    matched_poems = set()

    for page in pages:
        print(f"\n--- {page} ---")
        try:
            parsed = api_parse(page)
        except RuntimeError as exc:
            if "missingtitle" in str(exc):
                print(" page not found, skip")
                all_stats.append({"page": page, "quotes": 0, "matched": 0, "multi": 0, "unmatched": 0, "missing": True})
                continue
            raise
        wikitext = parsed["wikitext"]
        text = extract_text_from_wikitext(wikitext)
        sections = parse_sections(text)

        matched = 0
        unmatched = 0
        for sec in sections:
            quotes = find_quoted_verses(sec["text"])
            for quote in quotes:
                poem_id, score = match_quote(quote, unique_grams, poems, sec["author"], by_author)
                if poem_id:
                    matched += 1
                    matched_poems.add(poem_id)
                    commentary = extract_commentary(sec["text"], quote["raw"])
                    all_matches.append({
                        "page": page,
                        "poem_id": poem_id,
                        "author": poems[poem_id]["author"],
                        "title": poems[poem_id]["title"],
                        "section_author": sec["author"],
                        "section": sec["section"],
                        "quote": quote["raw"][:80],
                        "commentary": commentary[:150],
                        "score": score,
                    })
                else:
                    unmatched += 1
        stats = {
            "page": page,
            "quotes": matched + unmatched,
            "matched": matched,
            "unmatched": unmatched,
        }
        all_stats.append(stats)
        print(f" quotes={stats['quotes']}, matched={matched}, unmatched={unmatched}")
        time.sleep(1.2)

    print("\n=== summary ===")
    total_q = sum(s["quotes"] for s in all_stats)
    total_m = sum(s["matched"] for s in all_stats)
    print(f"total quotes: {total_q}, matched: {total_m}, rate: {total_m/total_q:.1%}")
    print(f"unique poems matched: {len(matched_poems)}")

    out = ROOT / "tmp_shiren_yuxie_prototype_v2.json"
    out.write_text(json.dumps({
        "summary": {"quotes": total_q, "matched": total_m, "rate": total_m / total_q if total_q else 0, "unique_poems": len(matched_poems)},
        "stats": all_stats,
        "samples": all_matches[:300],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
