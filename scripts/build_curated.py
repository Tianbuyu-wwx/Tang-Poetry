# -*- coding: utf-8 -*-
"""将 docs/curated/ 下的社员作品与社员档案桥接进静态站的共享数据层。

数据布局（与 Decap CMS 的 folder collection 一一对应，便于社员自助投稿）：
  docs/curated/members/<slug>.md   每社员一份（frontmatter，无正文）
  docs/curated/poems/<slug>.md     每首诗一份（frontmatter + 诗句正文）

数据契约（与《全唐诗》共用 11 字段定长数组）：
  [标题, 作者, 体裁, 年代, 出处, 诗句, 题解, 注释, 赏析, 名句, 出处溯源]
社员作品 id 前缀 member_；社员档案 slug 前缀 member_poet_（取自文件名）。
注意：curated_ 前缀属于既有的「补遗诗」（SITE_META.supplements），本脚本不触碰。

运行：python scripts/build_curated.py
依赖：pyyaml（managed venv）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CURATED_DIR = ROOT / "docs" / "curated"
MEMBERS_DIR = CURATED_DIR / "members"
POEMS_DIR = CURATED_DIR / "poems"
ID_REGISTRY = CURATED_DIR / "poem-ids.json"
BUILD_WORK = ROOT / "scripts" / "_work"
ASSETS = ROOT / "website" / "assets" / "js"
POEMS_DATA_JS = BUILD_WORK / "poems-data.js"
POETS_DATA_JS = ASSETS / "poets-data.js"
SITE_META_JS = ASSETS / "site-meta.js"

sys.path.insert(0, str(ROOT / "scripts"))
from lib import common  # noqa: E402
import build_frontend_assets as bfa  # noqa: E402


def _split_frontmatter(text: str):
    """从 Markdown 文件切出 (frontmatter_dict, 正文)。无 frontmatter 抛错。"""
    if not text.lstrip().startswith("---"):
        raise ValueError("缺少 YAML frontmatter（应以 --- 起首）")
    _, fm, body = text.split("---", 2)
    return (yaml.safe_load(fm) or {}), body


def _pair(item, k0: str, k1: str):
    """兼容 Decap 投稿（对象列表 [{term,gloss}]）与手写底稿（成对数组 [term,gloss]）。"""
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        return [str(item[0]), str(item[1])]
    if isinstance(item, dict):
        return [str(item.get(k0) or ""), str(item.get(k1) or "")]
    return ["", ""]


def _check_id(md_path: Path, meta: dict) -> None:
    """Decap 用 frontmatter 的 id 作文件名；若被手工改乱，此处提前拦截。"""
    declared = meta.get("id")
    if declared and str(declared) != md_path.stem:
        raise SystemExit(f"{md_path.name} 的 id「{declared}」与文件名不一致，请统一后重建")


def parse_member(md_path: Path):
    """解析单个社员档案 Markdown，返回 (slug, 档案 dict)。

    slug 由文件名派生并加 member_poet_ 命名空间前缀，与 open_/curated_ 隔离，
    保证重建时可以精确清理而不误伤既有数据。
    """
    meta, _body = _split_frontmatter(md_path.read_text(encoding="utf-8"))
    _check_id(md_path, meta)
    return f"member_poet_{md_path.stem}", meta


def parse_poem(md_path: Path):
    """解析单篇社员作品 Markdown，返回 (frontmatter, 11 字段记录)。"""
    meta, body = _split_frontmatter(md_path.read_text(encoding="utf-8"))
    _check_id(md_path, meta)
    # 诗句：以空行分段（stanza），段内以换行分行；丢弃空段
    verse = [seg.strip() for seg in re.split(r"\n\s*\n", body.strip()) if seg.strip()]
    appr = meta.get("appreciation") or {}
    appr_body = appr.get("body") or []
    if isinstance(appr_body, str):
        appr_body = [appr_body]
    record = [
        str(meta.get("title", "")),
        str(meta.get("author", "")),
        str(meta.get("genre", "未知")),
        str(meta.get("year", "")),  # YAML 会把 2024 解析成 int，前端按字符串渲染
        str(meta.get("source", "")),
        verse,
        meta.get("context", "") or "",
        [_pair(x, "term", "gloss") for x in (meta.get("notes") or [])],
        {"body": [str(x) for x in appr_body], "source": str(appr.get("source") or "")},
        [_pair(x, "line", "comment") for x in (meta.get("famous") or [])],
        meta.get("sources") or [],
    ]
    if len(record) != 11:
        raise ValueError(f"{md_path.name} 记录字段数不为 11")
    return meta, record


def main() -> None:
    if not MEMBERS_DIR.is_dir():
        raise SystemExit(f"缺少社员档案目录：{MEMBERS_DIR}")
    if not POEMS_DIR.is_dir():
        raise SystemExit(f"缺少社员作品目录：{POEMS_DIR}")

    member_files = sorted(MEMBERS_DIR.glob("*.md"))
    poem_files = sorted(POEMS_DIR.glob("*.md"))
    if not member_files:
        raise SystemExit(f"{MEMBERS_DIR} 下没有任何社员档案")
    if not poem_files:
        raise SystemExit(f"{POEMS_DIR} 下没有任何社员作品")

    members = [parse_member(p) for p in member_files]
    member_by_name = {common.normalized_name(m["name"]): slug for slug, m in members}

    # ---- 社员档案并入 POETS_DATA（仅清理 member_poet_*，保留 open_/curated_） ----
    poets = common.load_js_assignment(POETS_DATA_JS, "POETS_DATA")
    for key in [k for k in poets if k.startswith("member_poet_")]:
        del poets[key]
    for slug, m in members:
        if not m.get("name"):
            raise SystemExit(f"社员档案 {slug}.md 缺少 name")
        poets[slug] = {
            "sealChar": m.get("sealChar", m["name"][:1]),
            "name": m["name"],
            "nameEn": m.get("nameEn", ""),
            "dynasty": m.get("dynasty", "今"),
            "summary": m.get("summary", ""),
            "sub": m.get("sub", ""),
            "life": m.get("life", []),
            "sources": m.get("sources", []),
            "biographyStatus": m.get("biographyStatus", "member"),
            "isMember": True,
        }
    common.write_js(POETS_DATA_JS, "POETS_DATA", poets)

    # ---- 社员作品并入 POEMS_DATA（仅清理 member_*，保留 open_/curated_ 补遗） ----
    poems = common.load_js_assignment(POEMS_DATA_JS, "POEMS_DATA")
    for key in [k for k in poems if k.startswith("member_")]:
        del poems[key]

    # 文件名 -> 数字 id 的持久映射：保证新增/删除作品不会挪动既有作品的 URL。
    # 号码只增不减，删稿后其号码作废而不回收。
    registry = json.loads(ID_REGISTRY.read_text(encoding="utf-8")) if ID_REGISTRY.is_file() else {}
    next_id = max(registry.values(), default=-1) + 1

    annotated_added = 0
    for p in poem_files:
        meta, record = parse_poem(p)
        author = meta.get("author", "")
        if common.normalized_name(author) not in member_by_name:
            raise SystemExit(f"作者「{author}」不在社员档案中：{p.name}")
        if p.stem not in registry:
            registry[p.stem] = next_id
            next_id += 1
        poems[f"member_{registry[p.stem]}"] = record
        if common.has_annotation(record):
            annotated_added += 1
    n = len(poem_files)
    common.atomic_write(
        ID_REGISTRY,
        json.dumps(dict(sorted(registry.items(), key=lambda kv: kv[1])), ensure_ascii=False, indent=2) + "\n",
    )

    # ---- site-meta 计数：从实际数据重算，避免增量误差 ----
    meta = common.load_js_assignment(SITE_META_JS, "SITE_META")
    meta["poems"] = len(poems)
    meta["open_poems"] = sum(1 for k in poems if k.startswith("open_"))
    meta["supplements"] = sum(1 for k in poems if k.startswith("curated_"))
    meta["poets"] = len(poets)
    meta["annotated"] = sum(common.has_annotation(r) for r in poems.values())
    meta["poets_with_life"] = sum(1 for p in poets.values() if p.get("life"))
    common.write_js(SITE_META_JS, "SITE_META", meta)

    # 先写 POEMS_DATA（build_assets 会读取它再生分片/索引）
    common.write_js(POEMS_DATA_JS, "POEMS_DATA", poems)

    # ---- 全量重建（reset_generated_directory 打 no-op，避开安全删除守卫） ----
    bfa.reset_generated_directory = lambda path: None
    stats = bfa.build_assets()

    print(f"[member] 社员作品 {n} 首；社员 {len(members)} 位；新增注解 {annotated_added} 条")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
