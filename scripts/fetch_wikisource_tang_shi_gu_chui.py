# -*- coding: utf-8 -*-
"""下载并整理中文维基文库《唐诗鼓吹》（四库全书本）。

只使用 MediaWiki API 返回的已转录文本，不调用 OCR，也不依赖第三方包。
生成的 JSON/Markdown 可直接由 ``import_docs.py`` 接入网站。
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
OUTPUT_DIR = ROOT / "docs" / "tang_commentaries_public_domain_3"
API_URL = "https://zh.wikisource.org/w/api.php"
WORK_TITLE = "唐詩鼔吹 (四庫全書本)"
SOURCE_URL = "https://zh.wikisource.org/wiki/唐詩鼔吹_(四庫全書本)"
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


def write_outputs(chapters: list[dict]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    total_chars = sum(len(chapter["text"]) for chapter in chapters)
    source_sha = hashlib.sha256()
    for chapter in chapters:
        source_sha.update(chapter["source_wikitext_sha256"].encode("ascii"))

    metadata = {
        "title": "唐詩鼓吹",
        "author": "金·元好問編，元·郝天挺注",
        "edition": "四庫全書本",
        "description": "十卷；以中晚唐七言律詩為主，保存作者小傳、字詞音義、典故出处、异文与郝天挺笺注。",
        "source": "中文維基文庫",
        "source_url": SOURCE_URL,
        "downloaded_on": date.today().isoformat(),
        "source_pages_sha256": source_sha.hexdigest(),
        "chapter_count": len(chapters),
        "extracted_character_count": total_chars,
        "language": "文言文；繁體字",
        "rights": {
            "ancient_work": "Public domain",
            "wikisource_transcription": "CC BY-SA 4.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "attribution": f"中文維基文庫編者，《唐詩鼔吹》，{SOURCE_URL}",
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
    json_path = OUTPUT_DIR / "tang_shi_gu_chui.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    markdown = [
        "# 唐詩鼓吹",
        "",
        "> 金·元好問編，元·郝天挺注；四庫全書本。",
        f"> 來源：[{SOURCE_URL}]({SOURCE_URL})；維基文庫錄入依 CC BY-SA 4.0 使用。",
        "",
    ]
    for chapter in public_chapters:
        markdown.extend([f"## {chapter['title']}", "", chapter["text"], ""])
    md_path = OUTPUT_DIR / "tang_shi_gu_chui.md"
    md_path.write_text("\n".join(markdown), encoding="utf-8")

    manifest = {
        "generated_on": date.today().isoformat(),
        "books": [
            {
                "id": "tang_shi_gu_chui",
                "title": metadata["title"],
                "chapters": len(chapters),
                "characters": total_chars,
                "json_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
                "markdown_sha256": hashlib.sha256(md_path.read_bytes()).hexdigest(),
            }
        ],
    }
    (OUTPUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    readme = f"""# 唐诗公版注评资料包（三）

本目录收录《唐诗鼓吹》十卷完整转录，共提取约 {total_chars:,} 字。它以中晚唐七言律诗为主，郝天挺注涉及作者小传、字词音义、典故出处、异文和诗意说明，可补充逐句古注，也可为古籍评赏提供语境。

## 文件

- `tang_shi_gu_chui.json`：供网站构建程序读取的结构化全文
- `tang_shi_gu_chui.md`：便于人工阅读与检索的完整正文
- `manifest.json`：章节数、字数与文件校验值

## 来源与许可

- [《唐诗鼔吹》（四库全书本）]({SOURCE_URL})
- 古代原著为公版；维基文库录入文字依 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 使用

## 转换说明

- 通过 MediaWiki API 读取已经公开转录的页面，没有建立或使用本地 OCR 环境。
- 仅提取 `div.poem` 正文，保留页面显示的 `〈古注〉` 边界，删除导航与样式。
- 每卷记录来源页面、页面修订号和源维基文本 SHA-256，便于复核。
- 开放录入可能有异体字、缺字、标点或底本问题；严肃引用应回查原页面和影印本。
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    chapters = []
    pages = [f"{WORK_TITLE}/卷{index:02d}" for index in range(1, 11)]
    revisions = api_revisions(pages)
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
        print(f"[{index:02d}/10] {page}: {len(text):,} 字")
        time.sleep(1.5)
    write_outputs(chapters)
    print(f"完成：{OUTPUT_DIR}")


if __name__ == "__main__":
    main()
