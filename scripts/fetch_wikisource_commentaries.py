# -*- coding: utf-8 -*-
"""下载并整理中文维基文库中的两部公版唐诗注评典籍。

- 《三體唐詩》（宋·周弼編，清·高士奇輯注）六卷
- 《才調集》（蜀·韋縠編）十卷

两部书均以〈尖括號〉保存逐句校語或典故注釋，版式穩定，可直接使用
import_docs.py 的 angle-comment 管線掛接。
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "docs" / "tang_commentaries_public_domain_4"
API_URL = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "TangPoetrySite/1.0 (public-domain source integration)"


class PoemHtmlExtractor(HTMLParser):
    """只提取 MediaWiki 渲染结果中的 ``div.poem`` 正文。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attr_map = dict(attrs)
        if tag == "div" and self.depth == 0:
            classes = set(attr_map.get("class", "").split())
            if "poem" in classes:
                self.depth = 1
                return
        elif self.depth and tag == "div":
            self.depth += 1

        if self.depth and tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.depth:
            return
        if tag == "p":
            self.parts.append("\n")
        if tag == "div":
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.parts.append(data)

    def text(self) -> str:
        value = "".join(self.parts)
        value = value.replace("\u00a0", " ").replace("\ufeff", "")
        lines = []
        for line in value.splitlines():
            line = re.sub(r"[ \t\u3000]+", " ", line).strip()
            if line or (lines and lines[-1]):
                lines.append(line)
        return "\n".join(lines).strip()


def api_parse(page: str, attempts: int = 7) -> dict:
    query = urlencode(
        {
            "action": "parse",
            "page": page,
            "prop": "text|wikitext",
            "format": "json",
            "formatversion": 2,
        }
    )
    request = Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=45) as response:
                payload = json.load(response)
            if "error" in payload:
                raise RuntimeError(payload["error"])
            return payload["parse"]
        except (HTTPError, URLError, TimeoutError) as error:
            if attempt == attempts:
                raise RuntimeError(f"下载失败：{page}: {error}") from error
            retry_after = 0
            if isinstance(error, HTTPError) and error.code == 429:
                retry_after = int(error.headers.get("Retry-After", "0") or 0)
            time.sleep(max(retry_after, attempt * 4))
    raise AssertionError("unreachable")


def api_revisions(pages: list[str]) -> dict[str, dict]:
    query = urlencode(
        {
            "action": "query",
            "titles": "|".join(pages),
            "prop": "revisions",
            "rvprop": "ids|timestamp",
            "format": "json",
            "formatversion": 2,
        }
    )
    request = Request(f"{API_URL}?{query}", headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        payload = json.load(response)
    result = {}
    for page in payload.get("query", {}).get("pages", []):
        revisions = page.get("revisions", [])
        if revisions:
            result[page["title"]] = revisions[0]
    return result


def extract_text(rendered_html: str, page: str) -> str:
    parser = PoemHtmlExtractor()
    parser.feed(rendered_html)
    text = parser.text()
    if len(text) < 500 or "〈" not in text or "〉" not in text:
        raise ValueError(f"正文提取结果异常：{page}")
    return text


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


WORKS = [
    {
        "id": "san_ti_tang_shi",
        "title": "三體唐詩",
        "author": "宋·周弼編，清·高士奇輯注",
        "edition": "四庫全書本",
        "description": "六卷；選七言絕句、七言律詩、五言律詩三體，附高士奇輯注與周弼選例說明，可補逐句校語與典故箋釋。",
        "source_url": "https://zh.wikisource.org/wiki/三體唐詩_(四庫全書本)",
        "pages": [f"三體唐詩 (四庫全書本)/卷{i}" for i in range(1, 7)],
    },
    {
        "id": "cai_diao_ji",
        "title": "才調集",
        "author": "蜀·韋縠編",
        "edition": "四庫全書本",
        "description": "十卷；選唐詩一千首，雖以選本為主，仍保留少量異文校語與本事注釋。",
        "source_url": "https://zh.wikisource.org/wiki/才調集_(四庫全書本)",
        "pages": [f"才調集 (四庫全書本)/卷{i:02d}" for i in range(1, 11)],
    },
]


def fetch_work(work: dict) -> dict:
    pages = work["pages"]
    revisions = api_revisions(pages)
    chapters = []
    for index, page in enumerate(pages, start=1):
        parsed = api_parse(page)
        wikitext = parsed["wikitext"]
        text = extract_text(parsed["text"], page)
        revision = revisions.get(parsed["title"], {})
        chapters.append(
            {
                "index": index,
                "title": f"卷{index:02d}",
                "source_page": f"https://zh.wikisource.org/wiki/{page.replace(' ', '_')}",
                "source_revision": revision.get("revid"),
                "source_revision_timestamp": revision.get("timestamp"),
                "source_wikitext_sha256": sha256_text(wikitext),
                "text": text,
            }
        )
        print(f"[{work['id']}] [{index:02d}/{len(pages)}] {page}: {len(text):,} 字")
        time.sleep(1.5)
    return {"work": work, "chapters": chapters}


def write_outputs(result: dict) -> None:
    work = result["work"]
    chapters = result["chapters"]
    total_chars = sum(len(chapter["text"]) for chapter in chapters)
    source_sha = hashlib.sha256()
    for chapter in chapters:
        source_sha.update(chapter["source_wikitext_sha256"].encode("ascii"))

    metadata = {
        "title": work["title"],
        "author": work["author"],
        "edition": work["edition"],
        "description": work["description"],
        "source": "中文維基文庫",
        "source_url": work["source_url"],
        "downloaded_on": date.today().isoformat(),
        "source_pages_sha256": source_sha.hexdigest(),
        "chapter_count": len(chapters),
        "extracted_character_count": total_chars,
        "language": "文言文；繁體字",
        "rights": {
            "ancient_work": "Public domain",
            "wikisource_transcription": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": f"中文維基文庫編者，《{work['title']}》，{work['source_url']}",
        },
        "limitations": [
            "本文件是古代原著与古代笺注，不含现代白话翻译或现代学术注释。",
            "文字由维基文库开放录入转换而来，可能存在 OCR、标点、异体字或底本讹误。",
            "转换时仅提取页面正文容器，删除站点导航、样式与页面界面，不改写正文。",
        ],
    }
    public_chapters = [
        {
            "index": chapter["index"],
            "title": chapter["title"],
            "source_page": chapter["source_page"],
            "source_revision": chapter["source_revision"],
            "source_revision_timestamp": chapter["source_revision_timestamp"],
            "source_wikitext_sha256": chapter["source_wikitext_sha256"],
            "text": chapter["text"],
        }
        for chapter in chapters
    ]
    payload = {"metadata": metadata, "chapters": public_chapters}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT_DIR / f"{work['id']}.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    markdown = [
        f"# {work['title']}",
        "",
        f"> {work['author']}；{work['edition']}。",
        f"> 來源：[{work['source_url']}]({work['source_url']})；維基文庫錄入依 CC BY-SA 4.0 使用。",
        "",
    ]
    for chapter in public_chapters:
        markdown.extend([f"## {chapter['title']}", "", chapter["text"], ""])
    md_path = OUTPUT_DIR / f"{work['id']}.md"
    md_path.write_text("\n".join(markdown), encoding="utf-8")

    return {
        "id": work["id"],
        "title": work["title"],
        "chapters": len(chapters),
        "characters": total_chars,
        "json_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
        "markdown_sha256": hashlib.sha256(md_path.read_bytes()).hexdigest(),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest_books = []
    for work in WORKS:
        result = fetch_work(work)
        book_manifest = write_outputs(result)
        manifest_books.append(book_manifest)

    manifest = {
        "generated_on": date.today().isoformat(),
        "books": manifest_books,
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    readme_lines = [
        "# 唐诗公版注评资料包（四）",
        "",
        "本目录收录以下两部四库全书本唐诗典籍的完整转录：",
        "",
    ]
    for book in manifest_books:
        readme_lines.append(
            f"- 《{book['title']}》：{book['chapters']} 卷，约 {book['characters']:,} 字"
        )
    readme_lines.extend(
        [
            "",
            "## 文件",
            "",
        ]
    )
    for book in manifest_books:
        readme_lines.append(f"- `{book['id']}.json` / `{book['id']}.md`：《{book['title']}》")
    readme_lines.extend(
        [
            "- `manifest.json`：章节数、字数与文件校验值",
            "",
            "## 来源与许可",
            "",
        ]
    )
    for work in WORKS:
        readme_lines.append(
            f"- [《{work['title']}》（{work['edition']}）]({work['source_url']})"
        )
    readme_lines.extend(
        [
            "- 古代原著为公版；维基文库录入文字依 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 使用",
            "",
            "## 转换说明",
            "",
            "- 通过 MediaWiki API 读取已经公开转录的页面，没有建立或使用本地 OCR 环境。",
            "- 仅提取 `div.poem` 正文，保留页面显示的 `〈古注/校语〉` 边界，删除导航与样式。",
            "- 每卷记录来源页面、页面修订号和源维基文本 SHA-256，便于复核。",
            "- 开放录入可能有异体字、缺字、标点或底本问题；严肃引用应回查原页面和影印本。",
        ]
    )
    (OUTPUT_DIR / "README.md").write_text(
        "\n".join(readme_lines), encoding="utf-8"
    )
    print(f"完成：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
