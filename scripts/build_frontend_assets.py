# -*- coding: utf-8 -*-
"""为纯静态前端生成按需加载的数据分片与轻量索引。"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote, urlsplit

from lib import common

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "website" / "assets" / "js"
BUILD_WORK = ROOT / "scripts" / "_work"  # 完整诗库为构建中间产物，不随站点托管
POEM_SHARD_SIZE = 500
POET_WORK_SHARDS = 64
WEBSITE = ROOT / "website"

# 资源版本号：唯一来源。改动任何前端文件后只需在这里 +1，
# stamp_asset_versions 会统一写进所有 HTML 与带 ?v= 的脚本，
# 杜绝手工逐页改 v=N 造成漂移（曾出现 v13/v14 并存）。
SITE_VERSION = 20
SITEMAP_MAX_URLS = 40000
STATIC_SITEMAP_PAGES = [
    "",
    "about.html",
    "index.html",
    "lessons.html",
    "members.html",
    "navigation.html",
    "news.html",
    "periodicals.html",
    "poem.html",
    "poet.html",
    "poets.html",
    "society.html",
    "sources.html",
]


def pages_base_url() -> str:
    """站点绝对地址：CI 按仓库名推导，本地回退到当前线上地址。"""
    env_base = os.environ.get("PAGES_BASE_URL")
    if env_base:
        return env_base.rstrip("/")
    repository = os.environ.get("GITHUB_REPOSITORY", "Tianbuyu-wwx/Tang-Poetry")
    owner, _, name = repository.partition("/")
    # 仅主机名规范为全小写；仓库路径段保留原始大小写（Pages 路径区分大小写）
    return f"https://{owner.lower()}.github.io/{name}"


def stamp_asset_versions() -> int:
    """把全站 ?v=N 统一改写为 SITE_VERSION（字节级操作，保持既有换行符）。"""
    token = f"?v={SITE_VERSION}".encode("ascii")
    changed = 0
    for path in sorted(WEBSITE.glob("*.html")) + sorted(ASSETS.glob("*.js")):
        raw = path.read_bytes()
        stamped = re.sub(rb"\?v=\d+", token, raw)
        if stamped != raw:
            path.write_bytes(stamped)
            changed += 1
    return changed


def _sitemap_xml(urls: list) -> str:
    body = "".join(f"    <url><loc>{url}</loc></url>\n" for url in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}</urlset>\n"
    )


def build_sitemap(poems: dict, poets: dict, sources: dict) -> dict:
    """生成 robots.txt 与分片 sitemap。不含 lastmod，保证字节级幂等。"""
    base = pages_base_url()

    def loc(path: str) -> str:
        return f"{base}/{path.replace('&', '&amp;')}"

    groups = {
        "static": [loc(page) for page in STATIC_SITEMAP_PAGES],
        "poets": [loc(f"poet.html?id={quote(str(slug), safe='')}") for slug in poets],
        "chapters": [
            loc(f"sources.html?book={quote(str(book_id), safe='')}&chapter={index}")
            for book_id, book in sorted(sources.items())
            for index in range(len(book.get("chapters") or []))
        ],
    }
    poem_ids = sorted(poems)
    for start in range(0, len(poem_ids), SITEMAP_MAX_URLS):
        part = start // SITEMAP_MAX_URLS
        groups[f"poems-{part:03d}"] = [
            loc(f"poem.html?id={quote(str(pid), safe='')}")
            for pid in poem_ids[start : start + SITEMAP_MAX_URLS]
        ]

    target = WEBSITE / "sitemaps"
    target.mkdir(exist_ok=True)
    for stale in target.glob("*.xml"):
        stale.unlink()
    sizes = {}
    for name, urls in sorted(groups.items()):
        path = target / f"{name}.xml"
        common.atomic_write(path, _sitemap_xml(urls))
        sizes[name] = len(urls)

    index_entries = "".join(
        f"    <sitemap><loc>{base}/sitemaps/{name}.xml</loc></sitemap>\n" for name in sorted(groups)
    )
    common.atomic_write(
        WEBSITE / "sitemap_index.xml",
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{index_entries}</sitemapindex>\n",
    )
    admin_path = urlsplit(base).path.rstrip("/") + "/admin/"
    common.atomic_write(
        WEBSITE / "robots.txt",
        "User-agent: *\n"
        "Allow: /\n"
        f"Disallow: {admin_path}\n"
        "\n"
        f"Sitemap: {base}/sitemap_index.xml\n",
    )
    return sizes


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
    bio_target = ASSETS / "poet-bio-shards"
    reset_generated_directory(bio_target)
    shards: dict[str, dict] = defaultdict(dict)
    bio_shards: dict[str, dict] = defaultdict(dict)
    poet_index = {}
    members_index = {}
    slim_index = {}
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
        # 详情页瘦身索引：仅保留渲染面包屑/侧栏必需的字段，
        # 生平与简介走 poet-bio-shards 异步加载，避免整包 poets-data.js
        # 注意 shard 保持 "07" 式零填充字符串，前端直接拼 URL；
        # period 供诗作页署名栏直接显示朝代（slim 里没有完整数据）
        slim_index[slug] = [
            name,
            seal,
            poet.get("nameEn", ""),
            bool(poet.get("life")),
            shard,
            period,
        ]
        # 生平分片：与作品分片同映射，详情页一次并行拉两小片即可补全诗人资料
        bio_shards[shard][slug] = [
            poet.get("life") or [],
            poet.get("summary", ""),
            poet.get("sources") or [],
            poet.get("dynasty", ""),
            poet.get("sub", ""),
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
    common.atomic_write(ASSETS / "poet-slim.js", "window.POET_SLIM=" + common.compact_json(slim_index) + ";")
    sizes = {}
    for name, records in sorted(shards.items()):
        path = target / f"{name}.js"
        common.atomic_write(path, "window.POET_WORKS=" + common.compact_json(records) + ";")
        sizes[name] = path.stat().st_size
    for name, records in sorted(bio_shards.items()):
        path = bio_target / f"{name}.js"
        common.atomic_write(path, "window.POET_BIO=" + common.compact_json(records) + ";")
        sizes[f"bio-{name}"] = path.stat().st_size
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




def build_famous_lines(poems: dict) -> list:
    """重建首页名句库：为既有 558 条名句反查诗作 id（8/6/4 字窗口匹配）。

    famous-lines.js 历史上是一次性生成的静态文件，只有 line/source 两个字段；
    这里在每次构建时重算 id 链接（91% 命中，异文句自然落空），使首页名句
    可点击直达诗作品页。未命中的条目保持原样展示。
    """
    source_path = ASSETS / "famous-lines.js"
    if not source_path.is_file():
        return []
    famous = common.load_js_assignment(source_path, "FAMOUS_LINES")
    clean_by_id = {
        pid: re.sub(r"[，。、；：！？\s／]", "", "".join(rec[5] or []))
        for pid, rec in poems.items()
    }
    out = []
    linked = 0
    for item in famous:
        clean = re.sub(r"[，。、；：！？\s／]", "", item.get("line", ""))
        pid = None
        for size in (8, 6, 4):
            key = clean[:size]
            if len(key) < 4:
                continue
            for candidate, hay in clean_by_id.items():
                if key in hay:
                    pid = candidate
                    break
            if pid:
                break
        entry = {"line": item.get("line", ""), "source": item.get("source", "")}
        if pid:
            entry["id"] = pid
            linked += 1
        out.append(entry)
    common.atomic_write(
        source_path,
        "window.FAMOUS_LINES=" + common.compact_json(out) + ";",
    )
    print(f"[famous-lines] {linked}/{len(famous)} 条已链接到诗作")
    return out


def infer_genre(record: list) -> str:
    """按诗句形态推断体裁，消掉「未知」。

    规则（保守优先）：题内含乐府/歌/吟/行/曲/引/谣 → 乐府；
    按句长统计：全五言→五古/五律（8句且≥4联→五律），全七言同理；
    混合长短句 → 古风；单句 ≤4 句的短章 → 绝句。
    推断不出 → 保持「未知」。
    """
    title = str(record[0] or "")
    verse = record[5] or []
    lines = []
    for seg in verse:
        for ln in str(seg).replace("。", "，").split("，"):
            ln = ln.strip()
            if ln:
                lines.append(ln)
    if not lines:
        return "未知"
    if len(lines) == 1:
        return "未知"

    yuefu_marks = ("乐府", "歌", "吟", "行", "曲", "引", "谣", "辞", "篇")
    if any(m in title for m in yuefu_marks) and "词" not in title[:2]:
        return "乐府"

    lengths = [len(ln) for ln in lines]
    all5 = all(n == 5 for n in lengths)
    all7 = all(n == 7 for n in lengths)
    if all5:
        return "五言律诗" if len(lines) == 8 else ("五言绝句" if len(lines) == 4 else "五言古诗")
    if all7:
        return "七言律诗" if len(lines) == 8 else ("七言绝句" if len(lines) == 4 else "七言古诗")
    if max(lengths) - min(lengths) <= 2:
        return "杂言古诗"
    return "古风"


def build_assets(assets: Path = ASSETS) -> dict:
    global ASSETS
    ASSETS = assets
    poems = common.load_js_assignment(BUILD_WORK / "poems-data.js", "POEMS_DATA")
    poets = common.load_js_assignment(ASSETS / "poets-data.js", "POETS_DATA")
    sources = common.load_js_assignment(BUILD_WORK / "sources-data.js", "SOURCES_DATA")
    poem_index = build_poem_index(poems)
    poem_sizes = build_poem_shards(poems)
    poet_index, work_sizes = build_poet_assets(poems, poets)
    source_index, source_sizes = build_source_assets(sources)
    famous = build_famous_lines(poems)
    # 体裁推断：仅回填「未知」且已入库主数据（_work），分片/索引随之更新
    inferred = 0
    for pid, record in poems.items():
        if record[2] in ("未知", ""):
            guess = infer_genre(record)
            if guess != "未知":
                record[2] = guess
                inferred += 1
    if inferred:
        common.write_js(BUILD_WORK / "poems-data.js", "POEMS_DATA", poems)
    sitemap_sizes = build_sitemap(poems, poets, {book["id"]: book for book in sources})
    stamped = stamp_asset_versions()
    stats = {
        "poem_shards": len(poem_sizes),
        "annotated_poems": sum(item["n"] for item in poem_index),
        "largest_poem_shard_kib": round(max(poem_sizes.values()) / 1024, 1),
        "poets": len(poet_index),
        "poet_work_shards": sum(1 for key in work_sizes if not key.startswith("bio-")),
        "poet_bio_shards": sum(1 for key in work_sizes if key.startswith("bio-")),
        "largest_poet_work_shard_kib": round(
            max(size for key, size in work_sizes.items() if not key.startswith("bio-")) / 1024, 1
        ),
        "source_books": len(source_index),
        "largest_source_book_kib": round(max(source_sizes.values()) / 1024, 1),
        "sitemap_urls": sum(sitemap_sizes.values()),
        "sitemap_files": len(sitemap_sizes),
        "genre_inferred": inferred,
        "famous_linked": sum(1 for x in famous if x.get("id")),
        "version_stamped_files": stamped,
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return stats


if __name__ == "__main__":
    build_assets()
