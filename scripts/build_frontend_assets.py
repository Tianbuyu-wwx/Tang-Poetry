# -*- coding: utf-8 -*-
"""为纯静态前端生成按需加载的数据分片与轻量索引。"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path

from lib import common

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "website" / "assets" / "js"
BUILD_WORK = ROOT / "scripts" / "_work"  # 完整诗库为构建中间产物，不随站点托管
POEM_SHARD_SIZE = 500
POET_WORK_SHARDS = 64


def reset_generated_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for old_file in path.glob("*.js"):
        old_file.unlink()


def poet_period(poet: dict) -> str:
    """兼容旧资料中 dynasty 曾用于存放字号的情况。"""
    text = " · ".join(str(poet.get(key, "")) for key in ("dynasty", "sub"))
    for period in ("初唐", "盛唐", "中唐", "晚唐", "五代"):
        if period in text:
            return period
    if "唐" in text:
        return "唐"
    return "不详"


def poem_shard_name(poem_id: str) -> str:
    match = re.fullmatch(r"(open|curated|member)_(\d+)", poem_id)
    if not match:
        return "misc"
    return f"{match.group(1)}-{int(match.group(2)) // POEM_SHARD_SIZE:03d}"


def build_poem_index(poems: dict) -> list:
    index = []
    for poem_id, record in poems.items():
        first = ""
        for segment in record[5] or []:
            segment = str(segment).strip()
            if segment:
                first = re.split(r"[，。、]", segment, maxsplit=1)[0][:40]
                break
        index.append(
            {
                "i": poem_id,
                "t": record[0] or "",
                "a": record[1] or "",
                "f": first,
                "n": 1 if common.has_annotation(record) else 0,
            }
        )
    common.atomic_write(
        ASSETS / "poems-index.js",
        "window.POEMS_INDEX=" + common.compact_json(index) + ";",
    )
    return index


def build_poem_shards(poems: dict) -> dict[str, int]:
    target = ASSETS / "poem-shards"
    reset_generated_directory(target)
    shards: dict[str, dict] = defaultdict(dict)
    for poem_id, record in poems.items():
        shards[poem_shard_name(poem_id)][poem_id] = record
    sizes = {}
    for name, records in sorted(shards.items()):
        path = target / f"{name}.js"
        common.atomic_write(path, "window.POEM_SHARD=" + common.compact_json(records) + ";")
        sizes[name] = path.stat().st_size
    return sizes


def build_poet_assets(poems: dict, poets: dict) -> tuple[dict, dict[str, int]]:
    works_by_author: dict[str, list] = defaultdict(list)
    for poem_id, record in poems.items():
        works_by_author[common.normalized_name(record[1])].append(
            [poem_id, record[0], record[2] or ""]
        )
    for works in works_by_author.values():
        works.sort(key=lambda item: item[0])

    target = ASSETS / "poet-work-shards"
    reset_generated_directory(target)
    shards: dict[str, dict] = defaultdict(dict)
    poet_index = {}
    members_index = {}
    for position, (slug, poet) in enumerate(poets.items()):
        shard = f"{position % POET_WORK_SHARDS:02d}"
        name = poet.get("name", "")
        works = works_by_author.get(common.normalized_name(name), [])
        # 社员（isMember）不套用唐代分期，直接显示其所处时代（如"今"）
        is_member = bool(poet.get("isMember"))
        period = poet.get("dynasty") if is_member else poet_period(poet)
        seal = poet.get("sealChar", "") or (name[:1] if name else "唐")
        shards[shard][slug] = works
        poet_index[slug] = [
            name,
            seal,
            poet.get("nameEn", ""),
            period,
            poet.get("summary", ""),
            poet.get("sub", ""),
            bool(poet.get("life")),
            len(works),
            shard,
            is_member,
        ]
        # 社员名录索引：仅 isMember 诗人，内联作品清单，使 members.html 单文件自足
        if is_member:
            members_index[slug] = [
                name,
                seal,
                poet.get("nameEn", ""),
                period,
                poet.get("summary", ""),
                poet.get("sub", ""),
                works,
            ]

    common.atomic_write(ASSETS / "poets-index.js", "window.POETS_INDEX=" + common.compact_json(poet_index) + ";")
    common.atomic_write(
        ASSETS / "members-index.js",
        "window.MEMBERS_INDEX=" + common.compact_json(members_index) + ";",
    )
    sizes = {}
    for name, records in sorted(shards.items()):
        path = target / f"{name}.js"
        common.atomic_write(path, "window.POET_WORKS=" + common.compact_json(records) + ";")
        sizes[name] = path.stat().st_size
    return poet_index, sizes


def build_source_assets(books: list) -> tuple[list, dict[str, int]]:
    target = ASSETS / "source-books"
    reset_generated_directory(target)
    source_index = []
    sizes = {}
    for book in books:
        book_id = book["id"]
        if not re.fullmatch(r"[a-z0-9_-]+", book_id):
            raise ValueError(f"典籍 ID 不能安全用作文件名：{book_id}")
        source_index.append(
            {
                "id": book_id,
                "title": book.get("title", ""),
                "author": book.get("author", ""),
                "edition": book.get("edition", ""),
                "description": book.get("description", ""),
                "source": book.get("source", ""),
                "sourceUrl": book.get("sourceUrl", ""),
                "license": book.get("license", ""),
                "chapters": [chapter.get("title", "") for chapter in book.get("chapters", [])],
            }
        )
        path = target / f"{book_id}.js"
        payload = (
            "window.SOURCE_BOOKS=window.SOURCE_BOOKS||{};window.SOURCE_BOOKS["
            + common.compact_json(book_id)
            + "]="
            + common.compact_json(book)
            + ";"
        )
        common.atomic_write(path, payload)
        sizes[book_id] = path.stat().st_size
    common.atomic_write(ASSETS / "sources-index.js", "window.SOURCES_INDEX=" + common.compact_json(source_index) + ";")
    return source_index, sizes


def build_assets(assets: Path = ASSETS) -> dict:
    global ASSETS
    ASSETS = assets
    poems = common.load_js_assignment(BUILD_WORK / "poems-data.js", "POEMS_DATA")
    poets = common.load_js_assignment(ASSETS / "poets-data.js", "POETS_DATA")
    sources = common.load_js_assignment(ASSETS / "sources-data.js", "SOURCES_DATA")
    poem_index = build_poem_index(poems)
    poem_sizes = build_poem_shards(poems)
    poet_index, work_sizes = build_poet_assets(poems, poets)
    source_index, source_sizes = build_source_assets(sources)
    stats = {
        "poem_shards": len(poem_sizes),
        "annotated_poems": sum(item["n"] for item in poem_index),
        "largest_poem_shard_kib": round(max(poem_sizes.values()) / 1024, 1),
        "poets": len(poet_index),
        "poet_work_shards": len(work_sizes),
        "largest_poet_work_shard_kib": round(max(work_sizes.values()) / 1024, 1),
        "source_books": len(source_index),
        "largest_source_book_kib": round(max(source_sizes.values()) / 1024, 1),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


if __name__ == "__main__":
    build_assets()
