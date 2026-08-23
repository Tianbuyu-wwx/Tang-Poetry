# -*- coding: utf-8 -*-
"""《詩人玉屑》评点接入原型脚本：抓取、解析、估算匹配率。"""

from __future__ import annotations

import ctypes
import json
import os
import re
import time
from collections import Counter, defaultdict
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


def api_revisions(pages: list[str]) -> dict[str, dict]:
    query = urlencode({
        "action": "query",
        "titles": "|".join(pages),
        "prop": "revisions",
        "rvprop": "ids|timestamp",
        "format": "json",
        "formatversion": 2,
    })
    request = Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    result = {}
    for page in payload.get("query", {}).get("pages", []):
        revisions = page.get("revisions", [])
        if revisions:
            result[page["title"]] = revisions[0]
    return result


def clean_wikitext(wikitext: str) -> str:
    """移除 header 模板，保留章节标题标记以便解析。"""
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
        if stripped.startswith("{{") and stripped.endswith("}}"):
            # 简单模板直接跳过
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def extract_text_from_wikitext(wikitext: str) -> str:
    """把维基文本转成相对干净的正文（保留章节层级）。"""
    text = clean_wikitext(wikitext)
    # 去掉内链、粗体、引用标记等
    text = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"'''?|''", "", text)
    text = re.sub(r"<sub>.*?</sub>", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.S)
    # 合并多余空行
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
    return records


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


def find_quoted_verses(text: str, min_len: int = 10, max_len: int = 200):
    """找出文本中被「」或『』包围的引文。"""
    quotes = []
    for match in re.finditer(r"[「『]([^「』』\n]{%d,%d})[」』]" % (min_len, max_len), text):
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


def match_quote(quote: dict, unique_grams: dict):
    """用十字片段投票匹配引文到诗作。"""
    text = quote["normalized"]
    if len(text) < COMMENTARY_NGRAM:
        return None
    scores = Counter()
    for i in range(len(text) - COMMENTARY_NGRAM + 1):
        poem_id = unique_grams.get(text[i:i + COMMENTARY_NGRAM])
        if poem_id:
            scores[poem_id] += 1
    if not scores:
        return None
    ranked = scores.most_common()
    if len(ranked) > 1 and ranked[1][1] >= ranked[0][1] - 1:
        return None
    return ranked[0][0]


def extract_section_commentary(text: str, quote: dict) -> str:
    """把引文所在段落/章节其余文字作为评点。"""
    # 找到引文所在行/段
    lines = text.splitlines()
    quote_line_idx = None
    for idx, line in enumerate(lines):
        if quote["raw"] in line:
            quote_line_idx = idx
            break
    if quote_line_idx is None:
        return ""
    # 取本行去掉引文后的剩余文字
    line = lines[quote_line_idx]
    commentary = line.replace(quote["raw"], " ").strip()
    # 如果本行只剩很少字，尝试合并下一句
    if len(normalize(commentary)) < 12 and quote_line_idx + 1 < len(lines):
        next_line = lines[quote_line_idx + 1]
        if not next_line.startswith("="):
            commentary = commentary + " " + next_line
    commentary = re.sub(r"\s+", "", commentary)
    return commentary


def main():
    poems = load_poems()
    unique_grams = build_unique_verse_index(poems)
    print(f" poems loaded: {len(poems)}, unique grams: {len(unique_grams)}")

    pages = [f"詩人玉屑/卷{i:02d}" for i in range(1, 22)]
    all_stats = []
    all_matches = []

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
        quotes = find_quoted_verses(text)
        matched = 0
        multi_candidate = 0
        unmatched = 0
        for quote in quotes:
            poem_id = match_quote(quote, unique_grams)
            if poem_id:
                matched += 1
                commentary = extract_section_commentary(text, quote)
                all_matches.append({
                    "page": page,
                    "poem_id": poem_id,
                    "author": poems[poem_id]["author"],
                    "title": poems[poem_id]["title"],
                    "quote": quote["raw"][:60],
                    "commentary": commentary[:120],
                })
            else:
                # 判断是否因多候选失败
                text_norm = quote["normalized"]
                scores = Counter()
                for i in range(len(text_norm) - COMMENTARY_NGRAM + 1):
                    pid = unique_grams.get(text_norm[i:i + COMMENTARY_NGRAM])
                    if pid:
                        scores[pid] += 1
                if len(scores) >= 2:
                    multi_candidate += 1
                else:
                    unmatched += 1
        stats = {
            "page": page,
            "quotes": len(quotes),
            "matched": matched,
            "multi": multi_candidate,
            "unmatched": unmatched,
        }
        all_stats.append(stats)
        print(f" quotes={len(quotes)}, matched={matched}, multi={multi_candidate}, unmatched={unmatched}")
        time.sleep(1.2)

    print("\n=== summary ===")
    total_q = sum(s["quotes"] for s in all_stats)
    total_m = sum(s["matched"] for s in all_stats)
    print(f"total quotes: {total_q}, matched: {total_m}, rate: {total_m/total_q:.1%}")

    out = ROOT / "tmp_shiren_yuxie_prototype.json"
    out.write_text(json.dumps({
        "summary": {"quotes": total_q, "matched": total_m, "rate": total_m / total_q if total_q else 0},
        "stats": all_stats,
        "samples": all_matches[:200],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
