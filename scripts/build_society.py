# -*- coding: utf-8 -*-
"""构建「社务」前端静态索引（P4 · 社务内容）。

与 build_curated.py 解耦：本脚本只读取 docs/ 下的社务源数据，
输出 website/assets/js 下的轻量索引 JS，绝不触碰核心诗库 poems-data.js，
因此不会影响 57k 诗作的全量重建与校验。

数据源：
  docs/lessons.json              社课题目 + 关联 member_ 作品（按 id 关联，不改 11 字段契约）
  docs/news/*.md                 公告 / 活动（frontmatter + 极简 Markdown 正文）
  docs/periodicals/*.json        社刊（复用 source-book 式结构，关联 member_ 作品）

输出：
  website/assets/js/lessons-index.js      window.LESSONS_INDEX
  website/assets/js/news-index.js         window.NEWS_INDEX
  website/assets/js/periodicals-index.js  window.PERIODICALS_INDEX

运行：python scripts/build_society.py
依赖：pyyaml（仅 news 解析需要）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
NEWS_DIR = DOCS / "news"
PERIODICALS_DIR = DOCS / "periodicals"
LESSONS_JSON = DOCS / "lessons.json"
ASSETS = ROOT / "website" / "assets" / "js"
BUILD_WORK = ROOT / "scripts" / "_work"

sys.path.insert(0, str(ROOT / "scripts"))
from lib import common  # noqa: E402


# ---------- 极简 Markdown → HTML（仅供 news 正文） ----------
def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _sanitize_url(url: str) -> str | None:
    url = url.strip()
    if url.startswith(("http://", "https://", "./", "../", "#", "/")):
        return url
    if re.fullmatch(r"[A-Za-z0-9._/-]+", url):  # 站内相对路径
        return url
    return None


def _render_inline(text: str) -> str:
    text = _escape(text)
    # 链接 [文本](url)
    def link_sub(m):
        label, url = m.group(1), m.group(2)
        safe = _sanitize_url(url)
        if safe is None:
            return m.group(0)
        return f'<a href="{safe}">{label}</a>'

    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_sub, text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def render_markdown(md: str) -> str:
    lines = md.splitlines()
    out: list[str] = []
    para: list[str] = []
    in_list = False
    list_kind = ""  # "ul" 或 "ol"

    def flush_para():
        if para:
            out.append("<p>" + " ".join(para) + "</p>")
            para.clear()

    def close_list():
        nonlocal in_list, list_kind
        if in_list:
            out.append(f"</{list_kind}>")
            in_list = False
            list_kind = ""

    def open_list(kind: str):
        nonlocal in_list, list_kind
        if not in_list:
            out.append(f"<{kind}>")
            in_list = True
            list_kind = kind

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            close_list()
            continue
        if line.strip() == "---":
            flush_para()
            close_list()
            out.append("<hr>")
            continue
        if line.startswith("### "):
            flush_para()
            close_list()
            out.append("<h3>" + _render_inline(line[4:].strip()) + "</h3>")
            continue
        if line.startswith("## "):
            flush_para()
            close_list()
            out.append("<h2>" + _render_inline(line[3:].strip()) + "</h2>")
            continue
        m_ul = re.match(r"^[-*]\s+", line)
        m_ol = re.match(r"^\d+\.\s+", line)
        if m_ul or m_ol:
            flush_para()
            kind = "ol" if m_ol else "ul"
            if in_list and list_kind != kind:
                close_list()
            open_list(kind)
            item = re.sub(r"^(?:[-*]|\d+\.)\s+", "", line)
            out.append("<li>" + _render_inline(item) + "</li>")
            continue
        para.append(_render_inline(line.strip()))
    flush_para()
    close_list()
    return "\n".join(out)


# ---------- 解析各数据源 ----------
def parse_lessons() -> dict:
    if not LESSONS_JSON.is_file():
        raise SystemExit(f"缺少社课数据：{LESSONS_JSON}")
    data = json.loads(LESSONS_JSON.read_text(encoding="utf-8"))
    lessons = data.get("lessons") or []
    for lesson in lessons:
        lesson["works"] = [str(w) for w in lesson.get("works", [])]
    return {
        "title": data.get("title", "石湖诗社 · 社课"),
        "intro": data.get("intro", ""),
        "lessons": lessons,
    }


def parse_news() -> list:
    if not NEWS_DIR.is_dir():
        return []
    items = []
    for path in sorted(NEWS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if not text.lstrip().startswith("---"):
            raise SystemExit(f"{path.name} 缺少 YAML frontmatter")
        _, fm, body = text.split("---", 2)
        meta = yaml.safe_load(fm) or {}
        items.append(
            {
                "id": str(meta.get("id") or path.stem),
                "title": str(meta.get("title", "")),
                "date": str(meta.get("date", "")),
                "author": str(meta.get("author", "")),
                "tag": str(meta.get("tag", "")),
                "html": render_markdown(body.strip()),
            }
        )
    items.sort(key=lambda it: it.get("date", ""), reverse=True)
    return items


def parse_periodicals() -> list:
    if not PERIODICALS_DIR.is_dir():
        return []
    items = []
    for path in sorted(PERIODICALS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        works = []
        for w in data.get("works", []):
            if isinstance(w, str):
                works.append({"id": w, "note": ""})
            else:
                works.append({"id": str(w.get("id", "")), "note": str(w.get("note", ""))})
        items.append(
            {
                "id": str(data.get("id", path.stem)),
                "title": str(data.get("title", "")),
                "issue": str(data.get("issue", "")),
                "date": str(data.get("date", "")),
                "editor": str(data.get("editor", "")),
                "description": str(data.get("description", "")),
                "works": works,
            }
        )
    items.sort(key=lambda it: it.get("date", ""), reverse=True)
    return items


def validate_works(lessons: dict, periodicals: list) -> None:
    """软校验：引用的 member_ 作品 id 是否在诗库中存在（缺失仅告警，不致命）。"""
    poems_path = BUILD_WORK / "poems-data.js"
    if not poems_path.is_file():
        print("[warn] 未找到 poems-data.js，跳过作品 id 校验")
        return
    poems = common.load_js_assignment(poems_path, "POEMS_DATA")
    known = set(poems)
    referenced = set()
    for lesson in lessons.get("lessons", []):
        referenced.update(lesson.get("works", []))
    for periodical in periodicals:
        for w in periodical.get("works", []):
            referenced.add(w.get("id", ""))
    missing = sorted(i for i in referenced if i and i not in known)
    if missing:
        print(f"[warn] 以下作品 id 在诗库中未找到（请核对 member_ 编号）：{', '.join(missing)}")
    else:
        print(f"[ok] 社务引用的 {len(referenced)} 个作品 id 全部命中诗库")


def main() -> None:
    lessons = parse_lessons()
    news = parse_news()
    periodicals = parse_periodicals()
    validate_works(lessons, periodicals)

    common.write_js(ASSETS / "lessons-index.js", "LESSONS_INDEX", lessons)
    common.write_js(ASSETS / "news-index.js", "NEWS_INDEX", news)
    common.write_js(ASSETS / "periodicals-index.js", "PERIODICALS_INDEX", periodicals)

    print(
        f"[society] 社课 {len(lessons['lessons'])} 题 · 公告 {len(news)} 则 · "
        f"社刊 {len(periodicals)} 辑"
    )


if __name__ == "__main__":
    main()
