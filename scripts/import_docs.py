# -*- coding: utf-8 -*-
"""把 docs 中的开放《全唐诗》、诗人生平与公版注评整合进静态网站。"""

from __future__ import annotations

import ctypes
import json
import os
import re
from collections import Counter, defaultdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path

from lib import common

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = ROOT / "website" / "assets" / "js"
BUILD_WORK = ROOT / "scripts" / "_work"  # 完整诗库为构建中间产物，不随站点托管

OPEN_CORPUS = DOCS / "quan_tang_shi_open.json"
BIOGRAPHIES = DOCS / "quan_tang_shi_poets_biographies.json"
COMMENTARY_DIRS = [
    DOCS / "tang_commentaries_public_domain",
    DOCS / "tang_commentaries_public_domain_2",
    DOCS / "tang_commentaries_public_domain_3",
    DOCS / "tang_commentaries_public_domain_4",
    DOCS / "tang_commentaries_public_domain_5",
    DOCS / "tang_commentaries_public_domain_6",
]

OPEN_SOURCE_LABEL = "《全唐诗》开放数据合并版（chinese-poetry，MIT）"
OPEN_SOURCE_URL = "https://github.com/chinese-poetry/chinese-poetry"
BIO_SOURCE_LABEL = "chinese-poetry《全唐诗》作者小传（MIT）"
CBDB_SOURCE_LABEL = "中国历代人物传记资料库 CBDB（CC BY-NC-SA 4.0）"

# 这些典籍的尖括号内容以逐句古注、校语或篇后评点为主，版式相对稳定，
# 可以用注释断点两侧的诗句做唯一匹配。其余诗话、纪事和传记以散文为主，
# 自动把整段挂到某一首诗上容易误配，仍只在“典籍资料”中提供全文检索。
COMMENTARY_ANNOTATION_BOOKS = {
    "yu_xuan_tang_shi": "古注·《御选唐诗》",
    "tang_shi_jing": "古评·《唐诗镜》",
    "tang_shi_pin_hui": "古评·《唐诗品汇》",
    "ying_kui_lv_sui": "校注·《瀛奎律髓》",
    "tang_xian_san_mei_ji": "校注·《唐贤三昧集》",
    "tang_shi_gu_chui": "古注·《唐诗鼓吹》",
    "san_ti_tang_shi": "古注·《三體唐詩》",
    "cai_diao_ji": "古注·《才調集》",
    "du_shi_xiang_zhu": "古注·《杜詩詳註》",
    "li_taibai_ji_fenlei_buzhu": "古注·《李太白集分類補註》",
}

# 诗话类典籍以「引号内原句」的方式引录唐诗，可对其做十字片段投票匹配。
# 与上面逐句古注/校语不同，这里匹配的是被完整引用的诗行，故单独成类。
QUOTED_VERSE_BOOKS = {
    "shi_ren_yu_xie": "古评·《诗人玉屑》",
    "ren_jian_ci_hua": "古评·《人间词话》",
    "yin_bing_shi_shi_hua": "古评·《饮冰室诗话》",
}
COMMENTARY_SOURCE_PREFIX = "古籍注评："
COMMENTARY_NOTE_PREFIXES = ("古注·《", "古评·《", "校注·《")
COMMENTARY_NGRAM = 10
ANGLE_COMMENT = re.compile(r"〈([^〈〉]{2,1000})〉")
ANGLE_BLOCK = re.compile(r"〈[^〉]*〉")
STRUCTURAL_COMMENT = re.compile(
    r"^(?:其[一二三四五六七八九十百〇\d]{1,3}|"
    r"[一二三四五六七八九十百〇\d]{1,8}首|"
    r"[\u4e00-\u9fff]{1,4}[云曰]|"
    r"(?:以上|以下|右列|右录|上同|下同).{0,10})$"
)


def build_simplifier():
    try:
        from opencc import OpenCC  # type: ignore

        converter = OpenCC("t2s")
        return converter.convert
    except ImportError:
        pass

    if os.name == "nt":
        mapper = ctypes.windll.kernel32.LCMapStringEx
        flag = 0x02000000  # LCMAP_SIMPLIFIED_CHINESE

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

    raise RuntimeError(
        "非 Windows 系统请先安装 opencc-python-reimplemented，再运行本脚本。"
    )


_raw_simplify = build_simplifier()


def simplify(value):
    """繁转简，并把来源中的孤立代理字符替换为 U+FFFD。"""
    converted = _raw_simplify(str(value or ""))
    return converted.encode("utf-8", errors="replace").decode("utf-8")

BRACKETS = re.compile(r"[（(][^）)]*[）)]")
PUNCT = re.compile(r"[\s，。、；：？！·・【】「」『』—…（）()《》〈〉\-]")


def normalize(value):
    value = BRACKETS.sub("", simplify(value))
    return PUNCT.sub("", value)


def normalize_verse(parts):
    return normalize("".join(parts or []))


def has_enrichment(record: list) -> bool:
    return common.has_annotation(record) or bool(
        (record[2] and record[2] != "未知")
        or record[3]
        or record[9]
    )


def merge_unique(left, right):
    merged = []
    seen = set()
    for value in list(left or []) + list(right or []):
        marker = json.dumps(value, ensure_ascii=False, sort_keys=True)
        if marker not in seen:
            seen.add(marker)
            merged.append(value)
    return merged


def merge_enrichment(target: list, source: list) -> None:
    if source[2] and source[2] != "未知":
        target[2] = source[2]
    if source[3]:
        target[3] = source[3]
    for index in (6, 7, 8, 9):
        if common.value_size(source[index]) > common.value_size(target[index]):
            target[index] = source[index]
    inherited_sources = list(source[10] or [])
    if source[4] and source[4] != target[4]:
        inherited_sources.append(source[4])
    target[10] = merge_unique(target[10], inherited_sources)


def remove_generated_commentary(poems: dict) -> None:
    """移除上一次自动挂接的古注，使重复构建始终可复现。"""
    for record in poems.values():
        record[7] = [
            note
            for note in (record[7] or [])
            if not (
                isinstance(note, list)
                and note
                and str(note[0]).startswith(COMMENTARY_NOTE_PREFIXES)
            )
        ]
        record[10] = [
            source
            for source in (record[10] or [])
            if not str(source).startswith(COMMENTARY_SOURCE_PREFIX)
        ]


def choose_best(candidates, source: list, poems: list):
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    source_verse = normalize_verse(source[5])[:600]
    ranked = []
    for index in candidates:
        target_verse = normalize_verse(poems[index].get("paragraphs"))[:600]
        score = SequenceMatcher(None, source_verse, target_verse).ratio()
        ranked.append((score, index))
    ranked.sort(reverse=True)
    return ranked[0][1]


def build_poems(old_poems: dict, open_data: dict):
    source_poems = open_data["poems"]
    records = {}
    title_index = defaultdict(list)
    author_first_index = defaultdict(list)
    global_first_index = defaultdict(list)

    for index, poem in enumerate(source_poems):
        poem_id = f"open_{index:05d}"
        author = simplify(poem.get("author", "")).strip()
        title = simplify(poem.get("title", "")).strip()
        paragraphs = [simplify(part).strip() for part in poem.get("paragraphs", []) if part.strip()]
        raw_notes = [simplify(note).strip() for note in poem.get("notes", []) if str(note).strip()]
        notes = [["来源短注", note] for note in raw_notes]
        records[poem_id] = [
            title,
            author,
            "未知",
            "",
            OPEN_SOURCE_LABEL,
            paragraphs,
            "",
            notes,
            {},
            [],
            [OPEN_SOURCE_URL],
        ]
        author_key = normalize(author)
        title_key = normalize(title)
        first_key = normalize_verse(paragraphs)[:16]
        title_index[(author_key, title_key)].append(index)
        if first_key:
            author_first_index[(author_key, first_key)].append(index)
            global_first_index[first_key].append(index)

    assigned_annotated = set()
    matched = defaultdict(int)
    supplements = []

    for old_id, old in old_poems.items():
        if not has_enrichment(old):
            continue
        author_key = normalize(old[1])
        title_key = normalize(old[0])
        first_key = normalize_verse(old[5])[:16]
        candidates = title_index.get((author_key, title_key), [])
        method = "author_title"
        if not candidates and first_key:
            by_author_first = author_first_index.get((author_key, first_key), [])
            if len(by_author_first) == 1:
                candidates = by_author_first
                method = "author_first"
        if not candidates and first_key:
            by_global_first = global_first_index.get(first_key, [])
            if len(by_global_first) == 1:
                candidates = by_global_first
                method = "global_first"

        chosen = choose_best(candidates, old, source_poems)
        target_id = f"open_{chosen:05d}" if chosen is not None else None
        old_is_annotated = common.has_annotation(old)
        if target_id and not (old_is_annotated and target_id in assigned_annotated):
            merge_enrichment(records[target_id], old)
            matched[method] += 1
            if old_is_annotated:
                assigned_annotated.add(target_id)
            continue

        if old_is_annotated:
            copied = json.loads(json.dumps(old, ensure_ascii=False))
            copied[4] = "项目既有整理本补录"
            copied[10] = merge_unique(
                copied[10],
                ["与开放语料未能唯一对齐，保留为整理本异文/组诗条目"],
            )
            supplements.append(copied)

    for index, record in enumerate(supplements):
        records[f"curated_{index:05d}"] = record

    return records, matched, len(supplements)


def best_source_biography(candidates):
    variants = []
    cbdb = []
    statuses = []
    for item in candidates:
        statuses.append(item.get("biography_status", ""))
        variants.extend(item.get("source_biography_variants") or [])
        cbdb.extend(item.get("cbdb_summaries") or [])
        if item.get("biography"):
            variants.append(item["biography"])
    unique_variants = []
    seen = set()
    for text in variants:
        text = simplify(text).strip()
        marker = normalize(text)
        if text and marker not in seen:
            seen.add(marker)
            unique_variants.append(text)
    unique_variants.sort(key=len, reverse=True)
    unique_cbdb = []
    seen.clear()
    for text in cbdb:
        text = simplify(text).strip()
        marker = normalize(text)
        if text and marker not in seen:
            seen.add(marker)
            unique_cbdb.append(text)
    return (unique_variants[0] if unique_variants else ""), unique_cbdb[:1], statuses


def build_poets(old_poets: dict, biography_data: dict, poem_records: dict):
    old_by_name = {}
    old_slug_by_name = {}
    for slug, profile in old_poets.items():
        key = normalize(profile.get("name", ""))
        if key:
            old_by_name[key] = profile
            old_slug_by_name[key] = slug

    bio_by_name = defaultdict(list)
    for profile in biography_data["poets"]:
        bio_by_name[normalize(profile.get("name", ""))].append(profile)

    author_order = []
    seen_authors = set()
    for record in poem_records.values():
        name = record[1].strip()
        key = normalize(name)
        if key and key not in seen_authors:
            seen_authors.add(key)
            author_order.append((key, name))

    result = {}
    used_slugs = set()
    generated = 0
    with_life = 0

    for key, name in author_order:
        existing = old_by_name.get(key, {})
        existing_slug = old_slug_by_name.get(key, "")
        source_bio, cbdb_summaries, statuses = best_source_biography(bio_by_name.get(key, []))
        existing_life = [str(x).strip() for x in existing.get("life", []) if str(x).strip()]
        life = []
        if sum(map(len, existing_life)) > 80:
            life.extend(existing_life)
        if source_bio and normalize(source_bio) not in {normalize(x) for x in life}:
            life.append(source_bio)
        for summary in cbdb_summaries:
            if normalize(summary) not in {normalize(x) for x in life}:
                life.append(summary)
        if life:
            with_life += 1

        summary = str(existing.get("summary", "")).strip()
        if not summary:
            seed = source_bio or (cbdb_summaries[0] if cbdb_summaries else "")
            summary = seed[:180] + ("……" if len(seed) > 180 else "")

        sources = []
        if source_bio:
            sources.append(BIO_SOURCE_LABEL)
        if cbdb_summaries:
            sources.append(CBDB_SOURCE_LABEL)
        if existing_life and existing_slug and not existing_slug.startswith("open_poet_"):
            sources.append("项目既有整理资料（见 docs）")

        slug = existing_slug
        if not slug or slug in used_slugs:
            generated += 1
            slug = f"open_poet_{generated:04d}"
            while slug in used_slugs:
                generated += 1
                slug = f"open_poet_{generated:04d}"
        used_slugs.add(slug)

        result[slug] = {
            "sealChar": name[0] if name else "唐",
            "name": name,
            "nameEn": existing.get("nameEn", ""),
            "dynasty": existing.get("dynasty", "唐"),
            "summary": summary,
            "life": life,
            "sub": existing.get("sub", ""),
            "sources": sources,
            "biographyStatus": next((x for x in statuses if x), ""),
        }

    return result, with_life


def build_sources():
    books = []
    for directory in COMMENTARY_DIRS:
        for path in sorted(directory.glob("*.json")):
            if path.name == "manifest.json":
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            metadata = payload["metadata"]
            rights = metadata.get("rights", {})
            chapters = []
            for chapter in payload["chapters"]:
                chapters.append(
                    {
                        "title": simplify(chapter.get("title", "")).strip(),
                        "text": simplify(chapter.get("text", "")).strip(),
                    }
                )
            books.append(
                {
                    "id": path.stem,
                    "title": simplify(metadata.get("title", path.stem)),
                    "author": simplify(metadata.get("author", "")),
                    "edition": simplify(metadata.get("edition", "")),
                    "description": simplify(metadata.get("description", "")),
                    "source": simplify(metadata.get("source", "中文维基文库")),
                    "sourceUrl": metadata.get("source_url", ""),
                    "license": rights.get("wikisource_transcription", "CC BY-SA 4.0"),
                    "chapters": chapters,
                }
            )
    return books


def build_unique_verse_index(poems: dict):
    """为每个只属于一首诗的十字片段建立索引。"""
    owners = {}
    verses = {}
    for poem_id, record in poems.items():
        verse = normalize_verse(record[5])
        verses[poem_id] = verse
        grams = {
            verse[index : index + COMMENTARY_NGRAM]
            for index in range(len(verse) - COMMENTARY_NGRAM + 1)
        }
        for gram in grams:
            previous = owners.get(gram)
            if previous is None and gram not in owners:
                owners[gram] = poem_id
            elif previous != poem_id:
                owners[gram] = ""
    return verses, {gram: owner for gram, owner in owners.items() if owner}


def is_useful_comment(value: str) -> bool:
    compact = normalize(value)
    return bool(
        4 <= len(compact) <= 1000
        and not STRUCTURAL_COMMENT.fullmatch(compact)
    )


def match_comment_break(text: str, match, unique_grams: dict):
    """只接受诗句在注释断点处相接的唯一命中，避开相邻作者小传。"""
    before = normalize(
        ANGLE_BLOCK.sub("", text[max(0, match.start() - 120) : match.start()])
    )[-80:]
    after = normalize(
        ANGLE_BLOCK.sub("", text[match.end() : match.end() + 120])
    )[:80]
    context = before + after
    boundary = len(before)
    scores = Counter()
    touches_break = set()
    for index in range(len(context) - COMMENTARY_NGRAM + 1):
        poem_id = unique_grams.get(context[index : index + COMMENTARY_NGRAM])
        if not poem_id:
            continue
        scores[poem_id] += 1
        end = index + COMMENTARY_NGRAM
        if end == boundary or index == boundary or index < boundary < end:
            touches_break.add(poem_id)

    ranked = sorted(
        (
            (score, poem_id)
            for poem_id, score in scores.items()
            if poem_id in touches_break and score >= 2
        ),
        reverse=True,
    )
    if not ranked:
        return None
    if len(ranked) > 1 and ranked[1][0] >= ranked[0][0] - 1:
        return None
    return ranked[0][1]


def extract_angle_commentary(poems: dict, books: list, unique_grams: dict):
    extracted = []
    audit = {}
    for book in books:
        book_id = book["id"]
        label = COMMENTARY_ANNOTATION_BOOKS.get(book_id)
        if not label:
            continue
        candidates = 0
        matched = []
        seen = set()
        for chapter in book["chapters"]:
            text = chapter["text"]
            for match in ANGLE_COMMENT.finditer(text):
                candidates += 1
                comment = re.sub(r"\s+", "", match.group(1)).strip()
                if not is_useful_comment(comment):
                    continue
                poem_id = match_comment_break(text, match, unique_grams)
                if not poem_id:
                    continue
                marker = (poem_id, normalize(comment))
                if marker in seen:
                    continue
                seen.add(marker)
                row = {
                    "poem_id": poem_id,
                    "book_id": book_id,
                    "book_title": book["title"],
                    "chapter": chapter["title"],
                    "label": label,
                    "text": comment,
                    "method": "注释断点相邻诗句唯一命中",
                }
                matched.append(row)
                extracted.append(row)
        audit[book_id] = {
            "title": book["title"],
            "candidates": candidates,
            "notes": len(matched),
            "poems": len({row["poem_id"] for row in matched}),
        }
    return extracted, audit


def normalized_text_map(value: str):
    """移除尖括号内容，并保留归一化字符到原字符串位置的映射。"""
    normalized = []
    positions = []
    depth = 0
    for index, char in enumerate(value):
        if char == "〈":
            depth += 1
            continue
        if char == "〉":
            depth = max(0, depth - 1)
            continue
        if depth:
            continue
        converted = normalize(char)
        normalized.append(converted)
        positions.extend([index] * len(converted))
    return "".join(normalized), positions


def extract_yingkui_prose(poems: dict, books: list, verses: dict, unique_grams: dict):
    """提取《瀛奎律髓》中紧接诗歌正文的方回评语。"""
    book = next((item for item in books if item["id"] == "ying_kui_lv_sui"), None)
    if not book:
        return [], {"title": "瀛奎律髓", "lines": 0, "notes": 0, "poems": 0}

    extracted = []
    seen = set()
    candidate_lines = 0
    for chapter in book["chapters"]:
        for line in chapter["text"].splitlines():
            raw = line.strip()
            if len(raw) < 20:
                continue
            normalized, positions = normalized_text_map(raw)
            if len(normalized) < COMMENTARY_NGRAM:
                continue
            candidate_lines += 1
            scores = Counter()
            starts_like_poem = set()
            for index in range(len(normalized) - COMMENTARY_NGRAM + 1):
                gram = normalized[index : index + COMMENTARY_NGRAM]
                poem_id = unique_grams.get(gram)
                if not poem_id:
                    continue
                scores[poem_id] += 1
                if index <= 12 and verses[poem_id].find(gram) <= 12:
                    starts_like_poem.add(poem_id)

            ranked = sorted(
                (
                    (score, poem_id)
                    for poem_id, score in scores.items()
                    if poem_id in starts_like_poem and score >= 4
                ),
                reverse=True,
            )
            if not ranked:
                continue
            if len(ranked) > 1 and ranked[1][0] >= ranked[0][0] - 2:
                continue
            _, poem_id = ranked[0]
            verse = verses[poem_id]
            cutoff = None
            for size in range(min(16, len(verse)), 7, -1):
                tail = verse[-size:]
                occurrences = [
                    found.start()
                    for found in re.finditer(re.escape(tail), normalized[: len(verse) + 40])
                ]
                if occurrences:
                    cutoff = occurrences[-1] + size
                    break
            if cutoff is None or cutoff > len(positions):
                continue

            commentary = raw[positions[cutoff - 1] + 1 :].strip()
            commentary = ANGLE_BLOCK.sub("", commentary).strip()
            commentary = re.sub(r"\s+", "", commentary)
            if len(normalize(commentary)) < 12:
                continue
            marker = (poem_id, normalize(commentary))
            if marker in seen:
                continue
            seen.add(marker)
            extracted.append(
                {
                    "poem_id": poem_id,
                    "book_id": book["id"],
                    "book_title": book["title"],
                    "chapter": chapter["title"],
                    "label": "古评·《瀛奎律髓》",
                    "text": commentary,
                    "method": "诗行起点、篇末尾句与行后评语三重对齐",
                }
            )

    return extracted, {
        "title": book["title"],
        "lines": candidate_lines,
        "notes": len(extracted),
        "poems": len({row["poem_id"] for row in extracted}),
    }


QUOTED_BRACKETS = re.compile(r"[「『]([^「』』\n]{10,240})[」』]")


def _parse_shiphua_sections(text: str):
    """还原诗话的 ===作者=== / ====小标题==== 层级，供作者上下文加权。"""
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
        sections.append(
            {"author": current_author, "section": current_section, "text": line}
        )
    return sections


def _find_quoted_verses(text: str, min_len: int = 10, max_len: int = 240):
    quotes = []
    for match in QUOTED_BRACKETS.finditer(text):
        raw = match.group(1)
        norm = normalize(raw)
        if len(norm) >= min_len:
            quotes.append({"raw": raw, "normalized": norm})
    return quotes


def _match_quoted_verse(quote: dict, unique_grams: dict, by_author: dict, section_author: str):
    """十字片段投票；若章节作者已知则对其诗作加权，并要求严格胜出与足够覆盖。"""
    text = quote["normalized"]
    if len(text) < COMMENTARY_NGRAM:
        return None
    scores = Counter()
    for index in range(len(text) - COMMENTARY_NGRAM + 1):
        poem_id = unique_grams.get(text[index : index + COMMENTARY_NGRAM])
        if poem_id:
            scores[poem_id] += 1
    if not scores:
        return None
    section_author_norm = normalize(section_author)
    if section_author_norm and by_author:
        boost = max(scores.values()) * 0.3
        for poem_id in by_author.get(section_author_norm, []):
            if poem_id in scores:
                scores[poem_id] += boost
    ranked = scores.most_common()
    top_score = ranked[0][1]
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    coverage = top_score / max(1, len(text) - COMMENTARY_NGRAM + 1)
    if second_score >= top_score - 2 or coverage < 0.20:
        return None
    return ranked[0][0]


def _extract_quoted_commentary(line: str, quote_raw: str) -> str:
    """提取含该引文的那一句评点，将句中其他引文替换为「…」。"""
    sentences = re.split(r"(?<=[。！？；])", line)
    target = ""
    for sent in sentences:
        if quote_raw in sent:
            target = sent
            break
    if not target:
        target = line

    def replace_other(match):
        return match.group(0) if quote_raw in match.group(0) else "……"

    cleaned = re.sub(r"[「『][^「』』]+[」』]", replace_other, target)
    cleaned = cleaned.replace(quote_raw, "")
    cleaned = re.sub(r"\s+", "", cleaned)
    cleaned = cleaned.replace("「」", "").replace("『』", "")
    cleaned = cleaned.strip("，。、；：？！·")
    return cleaned[:300]


def extract_quoted_verse_commentary(poems: dict, books: list, unique_grams: dict, by_author: dict):
    """诗话评点：把引号内完整引用的唐诗原句投票匹配到诗作，取同句评点为注评。"""
    extracted = []
    audit = {}
    for book in books:
        book_id = book["id"]
        label = QUOTED_VERSE_BOOKS.get(book_id)
        if not label:
            continue
        seen = set()
        quotes_total = 0
        for chapter in book["chapters"]:
            for sec in _parse_shiphua_sections(chapter["text"]):
                quotes = _find_quoted_verses(sec["text"])
                quotes_total += len(quotes)
                for quote in quotes:
                    poem_id = _match_quoted_verse(
                        quote, unique_grams, by_author, sec["author"]
                    )
                    if not poem_id:
                        continue
                    commentary = _extract_quoted_commentary(sec["text"], quote["raw"])
                    if not is_useful_comment(commentary):
                        continue
                    marker = (poem_id, normalize(commentary))
                    if marker in seen:
                        continue
                    seen.add(marker)
                    extracted.append(
                        {
                            "poem_id": poem_id,
                            "book_id": book_id,
                            "book_title": book["title"],
                            "chapter": chapter["title"],
                            "label": label,
                            "text": commentary,
                            "method": "引号内原句十字片段投票唯一命中",
                        }
                    )
        audit[book_id] = {
            "title": book["title"],
            "quotes": quotes_total,
            "notes": len(extracted),
            "poems": len({row["poem_id"] for row in extracted}),
        }
    return extracted, audit


def commentary_source_line(book: dict) -> str:
    details = f"{book.get('source', '中文维基文库')}，{book.get('license', 'CC BY-SA 4.0')}"
    if book.get("sourceUrl"):
        details += f"，{book['sourceUrl']}"
    return f"{COMMENTARY_SOURCE_PREFIX}《{book['title']}》（{details}）"


def add_commentary_annotations(poems: dict, books: list):
    before = {poem_id for poem_id, record in poems.items() if common.has_annotation(record)}
    verses, unique_grams = build_unique_verse_index(poems)
    by_author = defaultdict(list)
    for poem_id, record in poems.items():
        by_author[normalize(record[1])].append(poem_id)
    angle_rows, angle_audit = extract_angle_commentary(poems, books, unique_grams)
    prose_rows, prose_audit = extract_yingkui_prose(
        poems, books, verses, unique_grams
    )
    quoted_rows, quoted_audit = extract_quoted_verse_commentary(
        poems, books, unique_grams, by_author
    )
    book_lookup = {book["id"]: book for book in books}
    added_by_source = defaultdict(lambda: {"notes": 0, "poems": set()})
    matched_poems = set()

    for row in angle_rows + prose_rows + quoted_rows:
        record = poems[row["poem_id"]]
        existing = {
            normalize(note[1])
            for note in (record[7] or [])
            if isinstance(note, list) and len(note) > 1
        }
        marker = normalize(row["text"])
        if not marker or marker in existing:
            continue
        record[7].append([row["label"], row["text"]])
        record[10] = merge_unique(
            record[10], [commentary_source_line(book_lookup[row["book_id"]])]
        )
        matched_poems.add(row["poem_id"])
        added_by_source[row["book_id"]]["notes"] += 1
        added_by_source[row["book_id"]]["poems"].add(row["poem_id"])

    after = {poem_id for poem_id, record in poems.items() if common.has_annotation(record)}
    return {
        "notes_added": sum(item["notes"] for item in added_by_source.values()),
        "poems_matched": len(matched_poems),
        "newly_annotated": len(after - before),
        "annotated_before": len(before),
        "annotated_after": len(after),
        "sources": {
            book_id: {
                "title": book_lookup[book_id]["title"],
                "notes": values["notes"],
                "poems": len(values["poems"]),
                "angle_candidates": angle_audit.get(book_id, {}).get("candidates", 0),
            }
            for book_id, values in added_by_source.items()
        },
        "yingkui_prose": prose_audit,
        "quoted_verse": quoted_audit,
        "rows": angle_rows + prose_rows + quoted_rows,
    }


def write_commentary_report(commentary: dict, poems: dict) -> None:
    lines = [
        "# 古籍注释匹配报告",
        "",
        f"> 最近构建：{date.today().isoformat()}",
        "",
        "## 结果",
        "",
        f"- 构建前带注解：**{commentary['annotated_before']} 首**",
        f"- 新挂接古注、校语或评点：**{commentary['notes_added']} 条**",
        f"- 命中诗作：**{commentary['poems_matched']} 首**",
        f"- 新增注解覆盖：**{commentary['newly_annotated']} 首**",
        f"- 构建后带注解：**{commentary['annotated_after']} 首**",
        "",
        "## 来源分布",
        "",
        "| 典籍 | 挂接条数 | 命中诗作 | 扫描尖括注 |",
        "|---|---:|---:|---:|",
    ]
    for source in commentary["sources"].values():
        lines.append(
            f"| 《{source['title']}》 | {source['notes']} | {source['poems']} | {source['angle_candidates']} |"
        )
    prose = commentary["yingkui_prose"]
    lines.extend(
        [
            "",
            f"另从《{prose['title']}》诗行后的散文评点中切分 **{prose['notes']} 条 / {prose['poems']} 首**；这些条目已计入上表《瀛奎律髓》的总数。",
            "",
            "## 诗话引号原句匹配",
            "",
            "| 典籍 | 扫描引文 | 挂接条数 | 命中诗作 |",
            "|---|---:|---:|---:|",
        ]
    )
    for src in commentary.get("quoted_verse", {}).values():
        lines.append(
            f"| 《{src['title']}》 | {src['quotes']} | {src['notes']} | {src['poems']} |"
        )
    lines.extend(
        [
            "",
            "诗话评点匹配规则：引号（「」『』）内完整引用的诗行，经繁简归一后逐十字片段在“只属于一首诗”的索引上投票；要求唯一胜出且覆盖率不低于 20%。若引号所在章节标明了作者（===作者===），则对该作者诗作加权 0.3×。命中的原句同句评点作为注评挂到诗作页。",
            "",
            "## 匹配规则",
            "",
            "1. 原诗繁转简并去除标点，建立只属于一首诗的十字片段索引。",
            "2. 尖括号古注删去后，断点两侧诗句必须连续，且至少两个十字片段唯一指向同一首诗。",
            "3. 若断点处出现两个近似候选即放弃，不用作者名或诗题单独强行匹配。",
            "4. 《瀛奎律髓》行后评点还必须同时对齐诗行起点和全诗末句，才能切分篇后散文。",
            "5. 作者小传、卷目、体裁标签、纯编号以及无法唯一对齐的候选不写入诗作页，仍可在典籍页全文检索。",
            "6. 挂接内容保留古籍原文与书名，不改写成现代白话；学术引用应回查来源页或可靠纸本。",
            "",
            "## 抽样",
            "",
            "| 诗作 ID | 诗人 | 诗题 | 来源 | 注评节选 |",
            "|---|---|---|---|---|",
        ]
    )
    samples = []
    source_seen = Counter()
    for row in commentary["rows"]:
        if source_seen[row["book_id"]] >= 4:
            continue
        source_seen[row["book_id"]] += 1
        samples.append(row)
    for row in samples:
        record = poems[row["poem_id"]]
        excerpt = row["text"][:90].replace("|", "\\|")
        if len(row["text"]) > 90:
            excerpt += "……"
        lines.append(
            f"| `{row['poem_id']}` | {record[1]} | {record[0]} | 《{row['book_title']}》 | {excerpt} |"
        )
    lines.append("")
    (DOCS / "典籍注释匹配报告.md").write_text("\n".join(lines), encoding="utf-8")


def write_report(stats, books):
    lines = [
        "# docs 资料索引与网站整合报告",
        "",
        f"> 最近整合：{date.today().isoformat()}",
        "",
        "## 网站数据",
        "",
        f"- 诗作：**{stats['poems']} 首**（开放语料 {stats['open_poems']} 首，整理本补录 {stats['supplements']} 首）",
        f"- 诗人：**{stats['poets']} 位**（繁简与异体作者名归并后）",
        f"- 带题解、注释、赏析或古籍注评：**{stats['annotated']} 首**",
        f"- 有生平资料：**{stats['poets_with_life']} 位**",
        f"- 公版典籍：**{len(books)} 部 / {stats['chapters']} 章**",
        f"- 来源原文中的 Unicode 替代符：**{stats['source_replacement_chars']} 个**（原样保留，阅读页已提示回查底本）",
        "",
        "## 整合原则",
        "",
        "1. 开放《全唐诗》语料作为正文底库，转为简体展示，原文件保持不变。",
        "2. 既有鉴赏通过繁简归一后的作者、诗题和首句迁移；无法唯一匹配的组诗或异文保留为整理本补录。",
        "3. 诗人生平优先保留现站较完整资料，并补入开放作者小传和 CBDB 事实摘要。",
        "4. 古代注评除在“典籍资料”中全文展示外，还会把能由相邻诗句唯一命中的原文古注挂到诗作页；不自动改写成现代白话。",
        "5. 所有开放资料继续保留来源与许可；学术引用仍应回查原页面或可靠纸本。",
        "",
        "## 数据包",
        "",
        "- `quan_tang_shi_open.json`：chinese-poetry 开放《全唐诗》语料，MIT。",
        "- `quan_tang_shi_poets_biographies.json`：开放小传 + CBDB，合并数据 CC BY-NC-SA 4.0。",
        "- `tang_commentaries_public_domain*/`：中文维基文库公版古籍录入，CC BY-SA 4.0。",
        "",
        "## 已加入网站的典籍",
        "",
    ]
    for book in books:
        lines.append(
            f"- 《{book['title']}》：{len(book['chapters'])} 章；{book['author']}；{book['edition']}；{book['license']}。"
        )
    lines.extend(
        [
            "",
            "## 鉴赏迁移统计",
            "",
            f"- 作者 + 诗题：{stats['matched'].get('author_title', 0)} 条",
            f"- 作者 + 首句：{stats['matched'].get('author_first', 0)} 条",
            f"- 全局唯一首句：{stats['matched'].get('global_first', 0)} 条",
            f"- 作为整理本补录：{stats['supplements']} 条",
            "",
            "## 古籍注评挂接",
            "",
            f"- 新挂接古注、校语或评点：{stats['commentary_notes']} 条",
            f"- 其中诗话引号原句投票匹配：{stats.get('commentary_quoted_notes', 0)} 条",
            f"- 古籍命中诗作：{stats['commentary_poems']} 首",
            f"- 相比既有整理新增注解覆盖：{stats['commentary_new_poems']} 首",
            "- 详细规则、分书统计与抽样见 `典籍注释匹配报告.md`。",
            "",
        ]
    )
    (DOCS / "资料索引.md").write_text("\n".join(lines), encoding="utf-8")


def write_overview(stats, poem_records, poet_records):
    counts = Counter(record[1] for record in poem_records.values())
    profiles = {profile["name"]: profile for profile in poet_records.values()}
    lines = [
        "# 唐诗全量总览（开放语料整合版）",
        "",
        "> 正文底库：chinese-poetry 开放《全唐诗》语料，固定提交 `b8594f81a89752241442f2ce267d6f66f96704ee`，源仓库声明 MIT License。",
        "",
        f"> 网站共收录 **{stats['poems']} 首**：开放语料 {stats['open_poems']} 首，另保留 {stats['supplements']} 首无法与开放语料唯一对齐的整理本组诗/异文条目。",
        "",
        f"> 作者名经繁简和异体归并后为 **{stats['poets']} 位**；其中 **{stats['poets_with_life']} 位**有开放小传、CBDB 摘要或项目既有生平资料。",
        "",
        f"> 当前 **{stats['annotated']} 首**带题解、短注、赏析或古籍注评。全量覆盖表示原文已收录，不表示每首都有人工注释。",
        "",
        "> 旧曹寅本文本解析结果（42132 首）已另存为 `唐诗全量总览_曹寅本42132.md`，用于版本比较。",
        "",
        "## 诗人索引（按收录诗数降序）",
        "",
        "| 诗人 | 诗数 | 生平资料 |",
        "|---|---:|---|",
    ]
    for name, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        safe_name = name.replace("|", "\\|")
        profile = profiles.get(name, {})
        life = "有" if profile.get("life") else "待补"
        lines.append(f"| {safe_name} | {count} | {life} |")
    lines.append("")
    (DOCS / "唐诗全量总览.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    open_data = json.loads(OPEN_CORPUS.read_text(encoding="utf-8"))
    biography_data = json.loads(BIOGRAPHIES.read_text(encoding="utf-8"))
    old_poems = common.load_js_assignment(BUILD_WORK / "poems-data.js", "POEMS_DATA")
    old_poets = common.load_js_assignment(ASSETS / "poets-data.js", "POETS_DATA")
    remove_generated_commentary(old_poems)

    poems, matched, supplements = build_poems(old_poems, open_data)
    poets, poets_with_life = build_poets(old_poets, biography_data, poems)
    books = build_sources()
    commentary = add_commentary_annotations(poems, books)

    common.write_js(BUILD_WORK / "poems-data.js", "POEMS_DATA", poems)
    common.write_js(ASSETS / "poets-data.js", "POETS_DATA", poets)
    common.write_js(ASSETS / "sources-data.js", "SOURCES_DATA", books)

    # 页面使用轻量索引和按需分片；保留完整数据包作为生成与校验底库。
    from build_frontend_assets import build_assets

    build_assets(ASSETS)

    annotated = sum(common.has_annotation(record) for record in poems.values())
    chapters = sum(len(book["chapters"]) for book in books)
    source_replacement_chars = sum(
        chapter["title"].count("\ufffd") + chapter["text"].count("\ufffd")
        for book in books
        for chapter in book["chapters"]
    )
    stats = {
        "poems": len(poems),
        "open_poems": len(open_data["poems"]),
        "supplements": supplements,
        "poets": len(poets),
        "poets_with_life": poets_with_life,
        "annotated": annotated,
        "books": len(books),
        "chapters": chapters,
        "source_replacement_chars": source_replacement_chars,
        "matched": dict(matched),
        "commentary_notes": commentary["notes_added"],
        "commentary_poems": commentary["poems_matched"],
        "commentary_new_poems": commentary["newly_annotated"],
        "commentary_quoted_notes": sum(
            src["notes"] for src in commentary["quoted_verse"].values()
        ),
        "commentary_quoted_poems": len(
            {row["poem_id"] for row in commentary["rows"] if row["book_id"] in QUOTED_VERSE_BOOKS}
        ),
    }
    common.write_js(ASSETS / "site-meta.js", "SITE_META", stats)
    write_report(stats, books)
    write_overview(stats, poems, poets)
    write_commentary_report(commentary, poems)

    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
