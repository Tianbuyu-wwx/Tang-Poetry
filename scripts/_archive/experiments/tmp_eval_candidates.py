# -*- coding: utf-8 -*-
"""评估下一批公版古籍候选：提取样本并统计〈〉注释数量。"""
from __future__ import annotations

import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_URL = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "TangPoetrySite/1.0 (public-domain source integration)"


class PoemHtmlExtractor(HTMLParser):
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
    query = urlencode({
        "action": "parse",
        "page": page,
        "prop": "text|wikitext",
        "format": "json",
        "formatversion": 2,
    })
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


def extract_text(rendered_html: str) -> str:
    parser = PoemHtmlExtractor()
    parser.feed(rendered_html)
    return parser.text()


def evaluate(page: str) -> None:
    parsed = api_parse(page)
    text = extract_text(parsed["text"])
    angle_open = text.count("〈")
    angle_close = text.count("〉")
    variant = len(re.findall(r"一作[「\"']", text))
    print(f"{page}: {len(text):,} 字，〈〉{angle_open}/{angle_close}，一作「…」{variant}")
    out = Path("scripts") / f"tmp_eval_{page.replace('/', '_').replace(' ', '_')}.txt"
    out.write_text(text[:5000], encoding="utf-8")
    print(f"  样本 -> {out}")


if __name__ == "__main__":
    pages = sys.argv[1:]
    if not pages:
        pages = [
            "王右丞集箋註/卷之一",
            "御選唐宋詩醇 (四庫全書本)/卷01",
        ]
    for page in pages:
        try:
            evaluate(page)
        except Exception as e:
            print(f"{page}: ERROR {e}")
