# -*- coding: utf-8 -*-
"""验证当前全唐诗静态站的数据、路由和资源是否一致。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from lib import common
from build_frontend_assets import SITE_VERSION

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
ASSETS = WEBSITE / "assets"
BUILD_WORK = ROOT / "scripts" / "_work"  # 完整诗库为构建中间产物，不随站点托管
DOCS = ROOT / "docs"


def load_source_book(path: Path):
    text = path.read_text(encoding="utf-8").strip()
    match = re.search(r"window\.SOURCE_BOOKS\[[^\]]+\]\s*=", text)
    if not match:
        raise ValueError(f"{path.name} 不包含 SOURCE_BOOKS 赋值")
    payload = text[match.end() :].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)


def main() -> int:
    errors: list[str] = []

    def check(condition: bool, message: str) -> None:
        print(f"[{'OK' if condition else 'FAIL'}] {message}")
        if not condition:
            errors.append(message)

    required = [
        WEBSITE / "index.html",
        WEBSITE / "navigation.html",
        WEBSITE / "poem.html",
        WEBSITE / "poet.html",
        WEBSITE / "poets.html",
        WEBSITE / "members.html",
        WEBSITE / "sources.html",
        WEBSITE / "about.html",
        ASSETS / "css" / "poem.css",
        ASSETS / "js" / "poems-index.js",
        BUILD_WORK / "poems-data.js",
        ASSETS / "js" / "poets-data.js",
        ASSETS / "js" / "poets-index.js",
        ASSETS / "js" / "famous-lines.js",
        ASSETS / "js" / "sources-index.js",
        BUILD_WORK / "sources-data.js",
        ASSETS / "js" / "site-meta.js",
        ASSETS / "js" / "page-poem.js",
        ASSETS / "js" / "page-poet.js",
        ASSETS / "js" / "page-poets.js",
        ASSETS / "js" / "page-sources.js",
        ASSETS / "js" / "members-index.js",
        ASSETS / "js" / "page-members.js",
        ASSETS / "js" / "lessons-index.js",
        ASSETS / "js" / "news-index.js",
        ASSETS / "js" / "periodicals-index.js",
        WEBSITE / "society.html",
        WEBSITE / "lessons.html",
        WEBSITE / "news.html",
        WEBSITE / "periodicals.html",
        DOCS / "lessons.json",
    ]
    for path in required:
        check(path.is_file() and path.stat().st_size > 0, f"资源存在：{path.relative_to(ROOT)}")

    if errors:
        return 1

    poems = common.load_js_assignment(BUILD_WORK / "poems-data.js", "POEMS_DATA")
    index = common.load_js_assignment(ASSETS / "js" / "poems-index.js", "POEMS_INDEX")
    poets = common.load_js_assignment(ASSETS / "js" / "poets-data.js", "POETS_DATA")
    poet_index = common.load_js_assignment(ASSETS / "js" / "poets-index.js", "POETS_INDEX")
    famous = common.load_js_assignment(ASSETS / "js" / "famous-lines.js", "FAMOUS_LINES")
    sources = common.load_js_assignment(BUILD_WORK / "sources-data.js", "SOURCES_DATA")
    source_index = common.load_js_assignment(ASSETS / "js" / "sources-index.js", "SOURCES_INDEX")
    meta = common.load_js_assignment(ASSETS / "js" / "site-meta.js", "SITE_META")

    sharded_poems = {}
    for path in sorted((ASSETS / "js" / "poem-shards").glob("*.js")):
        sharded_poems.update(common.load_js_assignment(path, "POEM_SHARD"))
    sharded_works = {}
    for path in sorted((ASSETS / "js" / "poet-work-shards").glob("*.js")):
        sharded_works.update(common.load_js_assignment(path, "POET_WORKS"))
    sharded_sources = {
        book["id"]: book
        for book in (
            load_source_book(path)
            for path in sorted((ASSETS / "js" / "source-books").glob("*.js"))
        )
    }

    poem_ids = set(poems)
    index_ids = [item.get("i") for item in index]
    index_id_set = set(index_ids)
    normalize_name = lambda value: re.sub(r"\s+", "", value or "")
    authors = {normalize_name(item.get("a", "")) for item in index if normalize_name(item.get("a", ""))}
    poet_names = {
        normalize_name(item.get("name", ""))
        for item in poets.values()
        if normalize_name(item.get("name", ""))
    }
    widths = {len(record) for record in poems.values() if isinstance(record, list)}
    annotated_data = sum(common.has_annotation(record) for record in poems.values())
    annotated_index = sum(bool(item.get("n")) for item in index)
    source_chapters = sum(len(book.get("chapters", [])) for book in sources)

    check(len(poems) == meta.get("poems"), f"诗作数据符合站点元信息（{len(poems):,} 首）")
    check(len(index) == meta.get("poems"), f"检索索引符合站点元信息（{len(index):,} 条）")
    check(len(poets) == meta.get("poets"), f"诗人数据符合站点元信息（{len(poets):,} 位）")
    check(poet_index.keys() == poets.keys(), "轻量诗人索引与完整诗人数据一致")
    check(len(index_ids) == len(index_id_set), "检索索引 ID 无重复")
    check(poem_ids == index_id_set, "诗作数据与检索索引 ID 完全一致")
    check(sharded_poems == poems, f"诗作分片完整且内容一致（{len(sharded_poems):,} 首）")
    check(widths == {11}, f"所有诗作符合 11 字段契约（实际宽度 {sorted(widths)}）")
    check(authors == poet_names, "检索索引中的作者均有诗人资料")
    check(annotated_data == annotated_index, f"注解标记一致（{annotated_data:,} 首）")
    check(annotated_data == meta.get("annotated"), "注解数量符合站点元信息")
    check(bool(famous), f"首页名句数据非空（{len(famous):,} 条）")
    check(len(sources) == meta.get("books"), f"典籍数量符合站点元信息（{len(sources)} 部）")
    check(len(source_index) == len(sources), "轻量典籍索引数量一致")
    check(sharded_sources == {book["id"]: book for book in sources}, "逐部典籍分片完整且内容一致")
    check(source_chapters == meta.get("chapters"), f"典籍章节符合站点元信息（{source_chapters} 章）")
    check(
        isinstance(meta.get("source_replacement_chars"), int),
        f"已记录来源中的 Unicode 替代符（{meta.get('source_replacement_chars')} 个）",
    )
    check(
        all(book.get("title") and book.get("license") and book.get("chapters") for book in sources),
        "每部典籍均有书名、许可和正文",
    )
    work_ids = [work[0] for works in sharded_works.values() for work in works]
    check(len(work_ids) == len(set(work_ids)) == len(poems), "诗人作品分片覆盖全部诗作且无重复")
    check(
        all(entry[7] == len(sharded_works.get(slug, [])) for slug, entry in poet_index.items()),
        "诗人索引中的作品数量与作品分片一致",
    )

    navigation = (WEBSITE / "navigation.html").read_text(encoding="utf-8")
    poem_page = (WEBSITE / "poem.html").read_text(encoding="utf-8")
    poet_page = (WEBSITE / "poet.html").read_text(encoding="utf-8")
    poets_page = (WEBSITE / "poets.html").read_text(encoding="utf-8")
    sources_page = (WEBSITE / "sources.html").read_text(encoding="utf-8")
    about_page = (WEBSITE / "about.html").read_text(encoding="utf-8")
    check("poem.html?id=" in navigation, "检索结果使用诗作查询参数路由")
    check("assets/js/page-poem.js" in poem_page and "assets/js/poems-data.js" not in poem_page, "诗作页使用按需数据分片")
    check("assets/js/page-poet.js" in poet_page and "assets/js/poems-data.js" not in poet_page, "诗人页使用作品分片")
    poets_js = (WEBSITE / "assets" / "js" / "page-poets.js").read_text(encoding="utf-8")
    check(
        "poet.html?id=" in poets_page or "poet.html?id=" in poets_js,
        "诗人索引使用诗人查询参数路由",
    )
    check("assets/js/poets-index.js" in poets_page and "assets/js/poems-data.js" not in poets_page, "诗人索引使用轻量数据")
    check("assets/js/sources-index.js" in sources_page and "assets/js/sources-data.js" not in sources_page, "典籍页使用轻量索引与按书分片")
    check("sources.html?book=" in sources_page, "典籍页使用书目与章节查询参数路由")
    check("sources.html" in navigation and "sources.html" in about_page, "主要导航均提供典籍入口")

    # 社员名录（P1.4）：索引一致性 + 全站入口
    members_page = (WEBSITE / "members.html").read_text(encoding="utf-8")
    members_index = common.load_js_assignment(ASSETS / "js" / "members-index.js", "MEMBERS_INDEX")
    member_slugs = {slug for slug, entry in poet_index.items() if entry[9]}
    check(set(members_index) == member_slugs, "社员名录索引与诗人索引 isMember 标记一致")
    check(
        all(entry[6] == sharded_works.get(slug, []) for slug, entry in members_index.items()),
        "社员名录内联作品清单与作品分片一致",
    )
    check(
        all(str(poem_id).startswith("member_") for entry in members_index.values() for poem_id, *_ in entry[6]),
        "社员作品均使用 member_ 命名空间",
    )
    check(
        "assets/js/members-index.js" in members_page and "assets/js/poets-index.js" not in members_page,
        "社员名录只加载轻量社员索引",
    )
    nav_pages = {
        "navigation.html": navigation,
        "about.html": about_page,
        "poets.html": poets_page,
        "sources.html": sources_page,
        "poem.html": poem_page,
        "poet.html": poet_page,
        "society.html": (WEBSITE / "society.html").read_text(encoding="utf-8"),
        "lessons.html": (WEBSITE / "lessons.html").read_text(encoding="utf-8"),
        "news.html": (WEBSITE / "news.html").read_text(encoding="utf-8"),
        "periodicals.html": (WEBSITE / "periodicals.html").read_text(encoding="utf-8"),
    }
    missing_member_nav = [name for name, html in nav_pages.items() if "members.html" not in html]
    check(
        not missing_member_nav,
        f"主要页面均提供社员名录入口{': ' + ', '.join(missing_member_nav) if missing_member_nav else ''}",
    )
    missing_society_nav = [name for name, html in nav_pages.items() if "society.html" not in html]
    check(
        not missing_society_nav,
        f"主要页面均提供社务入口{': ' + ', '.join(missing_society_nav) if missing_society_nav else ''}",
    )

    # 社务内容（P4）：索引完整性与引用一致性
    lessons_index = common.load_js_assignment(ASSETS / "js" / "lessons-index.js", "LESSONS_INDEX")
    news_index = common.load_js_assignment(ASSETS / "js" / "news-index.js", "NEWS_INDEX")
    periodicals_index = common.load_js_assignment(ASSETS / "js" / "periodicals-index.js", "PERIODICALS_INDEX")
    check(isinstance(lessons_index, dict) and bool(lessons_index.get("lessons")), "社课索引包含题目")
    check(isinstance(news_index, list) and bool(news_index), "公告索引非空")
    check(isinstance(periodicals_index, list) and bool(periodicals_index), "社刊索引非空")
    ref_ids = set()
    for lesson in lessons_index.get("lessons", []):
        ref_ids.update(lesson.get("works", []))
    for periodical in periodicals_index:
        for work in periodical.get("works", []):
            ref_ids.add(work.get("id", ""))
    missing_refs = sorted(i for i in ref_ids if i and i not in poems)
    check(
        not missing_refs,
        f"社务引用的作品 id 均在诗库中（{len(ref_ids)} 个）{': ' + ', '.join(missing_refs) if missing_refs else ''}",
    )
    lessons_page = (WEBSITE / "lessons.html").read_text(encoding="utf-8")
    news_page = (WEBSITE / "news.html").read_text(encoding="utf-8")
    periodicals_page = (WEBSITE / "periodicals.html").read_text(encoding="utf-8")
    check(
        "assets/js/lessons-index.js" in lessons_page and "poems-data.js" not in lessons_page,
        "社课题页只加载轻量社课索引",
    )
    check(
        "assets/js/news-index.js" in news_page and "poems-data.js" not in news_page,
        "公告页只加载轻量公告索引",
    )
    check(
        "assets/js/periodicals-index.js" in periodicals_page and "poems-data.js" not in periodicals_page,
        "社刊页只加载轻量社刊索引",
    )

    # SEO 基础件：sitemap / robots / 版本号一致性（P1.1 + P1.3）
    sitemap_index = WEBSITE / "sitemap_index.xml"
    robots_txt = WEBSITE / "robots.txt"
    check(sitemap_index.is_file() and "sitemapindex" in sitemap_index.read_text(encoding="utf-8"), "sitemap 索引存在")
    check(robots_txt.is_file() and "Sitemap:" in robots_txt.read_text(encoding="utf-8"), "robots.txt 存在并声明 sitemap")
    stale_versions = []
    version_token = f"?v={SITE_VERSION}"
    for path in list(WEBSITE.glob("*.html")) + [ASSETS / "js" / name for name in (
        "page-poem.js", "page-poet.js", "page-sources.js",
    )]:
        found = set(re.findall(r"\?v=(\d+)", path.read_text(encoding="utf-8")))
        if found and found != {str(SITE_VERSION)}:
            stale_versions.append(f"{path.name}:{','.join(sorted(found))}")
    check(
        not stale_versions,
        f"全站资源版本号统一为 ?v={SITE_VERSION}{': ' + ', '.join(stale_versions) if stale_versions else ''}",
    )
    sitemap_dir = WEBSITE / "sitemaps"
    sitemap_files = sorted(p.name for p in sitemap_dir.glob("*.xml")) if sitemap_dir.is_dir() else []
    check(bool(sitemap_files), f"sitemap 分片已生成（{len(sitemap_files)} 个文件）")
    if sitemap_index.is_file():
        index_text = sitemap_index.read_text(encoding="utf-8")
        orphan_maps = [
            name for name in sitemap_files
            if f"/sitemaps/{name}" not in index_text
        ]
        check(not orphan_maps, f"sitemap 索引覆盖全部分片{': ' + ', '.join(orphan_maps) if orphan_maps else ''}")

    missing_links = []
    for page in WEBSITE.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        for reference in re.findall(r'(?:href|src)=["\']([^"\']+)', html):
            if reference.startswith(("http://", "https://", "#", "data:", "mailto:")):
                continue
            local = reference.split("#", 1)[0].split("?", 1)[0]
            if not local:
                continue
            target = page.parent / local
            # 目录形式的链接（如 ./admin/）由静态服务器回落到其 index.html
            if target.is_file() or (target.is_dir() and (target / "index.html").is_file()):
                continue
            missing_links.append(f"{page.name} -> {local}")
    check(
        not missing_links,
        f"HTML 本地链接与资源均存在{': ' + ', '.join(missing_links) if missing_links else ''}",
    )

    legacy_paths = []
    pattern = re.compile(r"(?:[Ee]:[/\\]项目[/\\]Tang Poetry|C:[/\\]Users[/\\]Tianbuyu)")
    for path in (ROOT / "scripts").rglob("*.py"):
        if "data" in path.parts or "tang_dict" in path.parts or "_archive" in path.parts:
            continue
        if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
            legacy_paths.append(str(path.relative_to(ROOT)))
    check(not legacy_paths, f"源码不含旧机器绝对路径{': ' + ', '.join(legacy_paths) if legacy_paths else ''}")

    print()
    if errors:
        print(f"验证失败：{len(errors)} 项。")
        return 1
    print(
        f"验证通过：{len(poems):,} 首诗、{len(poets):,} 位诗人、"
        f"{annotated_data:,} 首带注解、{len(famous):,} 条名句、"
        f"{len(sources)} 部典籍 / {source_chapters} 章。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
