# -*- coding: utf-8 -*-
"""一次性抓取公版诗话（诗人玉屑、人间词话、饮冰室诗话）为站点可托管的来源 JSON。

输出：docs/tang_commentaries_public_domain_6/*.json
与既有 tang_commentaries_public_domain* 结构一致（metadata + chapters），
由 import_docs.build_sources 在构建期读取，离线、可复现。

用法：
  python scripts/fetch_shiphua.py            # 跳过已存在的文件
  python scripts/fetch_shiphua.py --force    # 覆盖重抓
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import time
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "tang_commentaries_public_domain_6"
API_URL = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "TangPoetrySite/1.0 (public-domain source integration)"
RATE_LIMIT = 1.0
TIMEOUT = 45

# ---- 繁简转换（与 import_docs 一致：优先 opencc，回退 Windows API） ----
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
    raise RuntimeError("非 Windows 系统请先安装 opencc")


_simplify = build_simplifier()


def simplify(value):
    return _simplify(str(value or "")).encode("utf-8", errors="replace").decode("utf-8")


# ---- Wikisource 抓取（带重试/退避） ----
def api_parse(page: str, attempts: int = 4):
    query = urlencode(
        {
            "action": "parse",
            "page": page,
            "prop": "wikitext",
            "format": "json",
            "formatversion": 2,
        }
    )
    request = Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=TIMEOUT) as response:
                payload = json.load(response)
            if "error" in payload:
                raise RuntimeError(payload["error"].get("code", "error"))
            return payload["parse"]
        except (HTTPError, URLError, TimeoutError, IncompleteRead) as error:
            if attempt == attempts:
                raise
            retry_after = 0
            if isinstance(error, HTTPError) and error.code == 429:
                retry_after = int(error.headers.get("Retry-After", "0") or 0)
            time.sleep(max(retry_after, 2 * attempt))
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
        if stripped.startswith("{{") and stripped.endswith("}}"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def extract_text_from_wikitext(wikitext: str) -> str:
    """清洗 wiki 标记，保留 === 章节层级（供 parse_sections 还原作者上下文）。"""
    text = clean_wikitext(wikitext)
    text = re.sub(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]", r"\1", text)
    text = re.sub(r"'''?|''", "", text)
    text = re.sub(r"<sub>.*?</sub>", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.S)
    text = re.sub(r"-\{([^}]*)\}-", r"\1", text)
    out = []
    for line in text.splitlines():
        line = re.sub(r"[ \t\u3000]+", " ", line).strip()
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


# ---- 书名配置 ----
BOOKS = [
    {
        "id": "shi_ren_yu_xie",
        "title": "詩人玉屑",
        "author": "宋·魏慶之",
        "edition": "維基文庫《四庫全書本》",
        "description": "南宋詩話，輯錄唐、宋詩人評論與本事，引錄大量唐詩原句。",
        "source_url": "https://zh.wikisource.org/wiki/詩人玉屑_(四庫全書本)",
        "volumes": [
            [f"詩人玉屑/卷{i:02d}", f"詩人玉屑 (四庫全書本)/卷{i:02d}"]
            for i in range(1, 22)
        ],
    },
    {
        "id": "ren_jian_ci_hua",
        "title": "人間詞話",
        "author": "清·王國維",
        "edition": "維基文庫通行本",
        "description": "王國維詞學批評，間引唐詩以為評騭。",
        "source_url": "https://zh.wikisource.org/wiki/人間詞話",
        "pages": ["人間詞話", "人間詞話 (1926)"],
    },
    {
        "id": "yin_bing_shi_shi_hua",
        "title": "飲冰室詩話",
        "author": "近代·梁啟超",
        "edition": "維基文庫通行本",
        "description": "梁啟超詩學隨筆，間及唐、宋名篇。",
        "source_url": "https://zh.wikisource.org/wiki/飲冰室詩話",
        "pages": [
            "飲冰室詩話",
            "飲冰室詩話/卷一",
            "飲冰室詩話/卷01",
            "飲冰室詩話/卷1",
        ],
    },
]


def fetch_first(candidates):
    for page in candidates:
        try:
            parsed = api_parse(page)
            return page, parsed["wikitext"]
        except RuntimeError as exc:
            if "missingtitle" in str(exc):
                continue
            raise
    return None, None


def build_book(book: dict):
    chapters = []
    if "volumes" in book:
        for vol_cands in book["volumes"]:
            try:
                page, wt = fetch_first(vol_cands)
            except Exception as exc:  # 网络抖动：跳过该卷，不影响其他卷
                print(f"  [skip] {' / '.join(vol_cands)} 抓取失败：{exc}")
                time.sleep(RATE_LIMIT)
                continue
            if not wt:
                print(f"  [skip] {' / '.join(vol_cands)} 不存在")
                time.sleep(RATE_LIMIT)
                continue
            text = extract_text_from_wikitext(wt)
            vnum = re.search(r"卷(\d+)", vol_cands[0])
            idx = int(vnum.group(1)) if vnum else len(chapters) + 1
            chapters.append({"index": idx, "title": f"卷{idx:02d}", "text": text})
            print(f"  [ok] {page} -> 卷{idx:02d} ({len(text)} 字)")
            time.sleep(RATE_LIMIT)
    else:
        try:
            page, wt = fetch_first(book["pages"])
        except Exception as exc:
            print(f"  [skip] {' / '.join(book['pages'])} 抓取失败：{exc}")
            return None
        if not wt:
            print(f"  [skip] {' / '.join(book['pages'])} 不存在")
            return None
        text = extract_text_from_wikitext(wt)
        chapters.append({"index": 1, "title": book["title"], "text": text})
        print(f"  [ok] {page} ({len(text)} 字)")

    if not chapters:
        return None

    payload = {
        "metadata": {
            "title": book["title"],
            "author": book["author"],
            "edition": book["edition"],
            "description": book["description"],
            "source": "中文維基文庫",
            "source_url": book["source_url"],
            "downloaded_on": time.strftime("%Y-%m-%d"),
            "rights": {
                "ancient_work": "Public domain",
                "wikisource_transcription": "CC BY-SA 4.0",
                "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
                "attribution": f"中文維基文庫編者，《{book['title']}》，{book['source_url']}",
            },
            "limitations": [
                "本文件是古代/近代原著及評語，不含現代白話翻譯。",
                "文字由維基文庫開放錄入轉換而來，可能存在 OCR、標點或異體字訛誤。",
                "轉換時刪除了網頁導航與站點介面，正文內容未作校訂。",
            ],
        },
        "chapters": chapters,
    }
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for book in BOOKS:
        out = OUT_DIR / f"{book['id']}.json"
        if out.exists() and not args.force:
            print(f"== 跳过已存在：{out.name} ==")
            continue
        print(f"== 抓取《{book['title']}》 ==")
        payload = build_book(book)
        if not payload:
            print("  [warn] 未抓到任何章節，跳过写文件")
            continue
        out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"  已写：{out} （{len(payload['chapters'])} 章）")


if __name__ == "__main__":
    main()
