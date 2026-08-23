# -*- coding: utf-8 -*-
"""《人間詞話》试点：提取其中对唐诗/宋词的评论并匹配到全唐诗。"""
from __future__ import annotations

import ctypes
import json
import os
import re
from collections import Counter
from pathlib import Path
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
        return OpenCC("t2s").convert
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
    raise RuntimeError("非 Windows 请安装 opencc")

_raw_simplify = build_simplifier()


def simplify(value):
    converted = _raw_simplify(str(value or ""))
    return converted.encode("utf-8", errors="replace").decode("utf-8")


def normalize(value):
    value = BRACKETS.sub("", simplify(value))
    return PUNCT.sub("", value)


def api_parse(page: str) -> dict:
    query = urlencode({
        "action": "parse",
        "page": page,
        "prop": "text|wikitext",
        "format": "json",
        "formatversion": 2,
    })
    request = Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload["parse"]


def extract_text_from_wikitext(wikitext: str) -> str:
    # 去掉 header/versions 模板
    text = re.sub(r"\{\{[^\}]*\}\}", "", wikitext, flags=re.S)
    text = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"'''?|''", "", text)
    text = re.sub(r"<sup>.*?</sup>", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.S)
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


def parse_sections(text: str):
    sections = []
    current_section = ""
    for line in text.splitlines():
        stripped = line.strip()
        m = re.match(r"^===\s*([^=].*?)\s*===$", stripped)
        if m:
            current_section = m.group(1).strip()
            continue
        if re.match(r"^==\s*([^=].*?)\s*==$", stripped):
            continue
        if not stripped:
            continue
        sections.append({"section": current_section, "text": line})
    return sections


def find_quotes(text: str, min_len=10, max_len=200):
    quotes = []
    for m in re.finditer(r"[「『]([^「』』\n]{%d,%d})[」』]" % (min_len, max_len), text):
        raw = m.group(1)
        norm = normalize(raw)
        if len(norm) >= min_len:
            quotes.append({"raw": raw, "normalized": norm, "start": m.start(), "end": m.end()})
    return quotes


def match_quote(quote: dict, unique_grams: dict):
    text = quote["normalized"]
    if len(text) < COMMENTARY_NGRAM:
        return None, 0
    scores = Counter()
    for i in range(len(text) - COMMENTARY_NGRAM + 1):
        pid = unique_grams.get(text[i:i + COMMENTARY_NGRAM])
        if pid:
            scores[pid] += 1
    if not scores:
        return None, 0
    ranked = scores.most_common()
    top = ranked[0][1]
    second = ranked[1][1] if len(ranked) > 1 else 0
    coverage = top / max(1, len(text) - COMMENTARY_NGRAM + 1)
    if second >= top - 2 or coverage < 0.20:
        return None, top
    return ranked[0][0], top


def extract_commentary(line: str, quote_raw: str) -> str:
    sentences = re.split(r"(?<=[。！？；])", line)
    target = ""
    for sent in sentences:
        if quote_raw in sent:
            target = sent
            break
    if not target:
        target = line
    def replace_other(m):
        return m.group(0) if quote_raw in m.group(0) else "……"
    cleaned = re.sub(r"[「『][^「』』]+[」』]", replace_other, target)
    cleaned = cleaned.replace(quote_raw, "")
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = cleaned.replace("「」", "").replace("『』", "")
    cleaned = cleaned.strip("，。、；：？！·")
    return cleaned[:300]


def main():
    poems = load_poems()
    unique_grams = build_unique_verse_index(poems)
    print(f"poems={len(poems)}, unique grams={len(unique_grams)}")

    parsed = api_parse("人間詞話")
    text = extract_text_from_wikitext(parsed["wikitext"])
    sections = parse_sections(text)

    matched = 0
    unmatched = 0
    all_matches = []
    for sec in sections:
        quotes = find_quotes(sec["text"])
        for quote in quotes:
            pid, score = match_quote(quote, unique_grams)
            if pid:
                matched += 1
                commentary = extract_commentary(sec["text"], quote["raw"])
                all_matches.append({
                    "section": sec["section"],
                    "poem_id": pid,
                    "author": poems[pid]["author"],
                    "title": poems[pid]["title"],
                    "quote": quote["raw"][:80],
                    "commentary": commentary[:150],
                    "score": score,
                })
            else:
                unmatched += 1

    total = matched + unmatched
    print(f"quotes={total}, matched={matched}, unmatched={unmatched}, rate={matched/total:.1%}")
    out = ROOT / "tmp_renjian_cihua_prototype.json"
    out.write_text(json.dumps({
        "summary": {"quotes": total, "matched": matched, "unmatched": unmatched, "rate": matched/total if total else 0},
        "matches": all_matches,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved: {out}")


if __name__ == "__main__":
    main()
