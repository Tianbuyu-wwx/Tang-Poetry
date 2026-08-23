# -*- coding: utf-8 -*-
"""探测《詩人玉屑》维基文库页面结构。"""

from __future__ import annotations

import json
import re
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from http.client import IncompleteRead

API_URL = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "TangPoetrySite/1.0 (public-domain source integration)"


class PoemHtmlExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts = []

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


def api_parse(page: str, attempts: int = 5) -> dict:
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
        except (HTTPError, URLError, TimeoutError, IncompleteRead) as error:
            if attempt == attempts:
                raise RuntimeError(f"下载失败：{page}: {error}") from error
            retry_after = 0
            if isinstance(error, HTTPError) and error.code == 429:
                retry_after = int(error.headers.get("Retry-After", "0") or 0)
            time.sleep(max(retry_after, attempt * 4))
    raise AssertionError("unreachable")


def main():
    for vol in [3, 4, 5, 10, 15, 21]:
        page = f"詩人玉屑/卷{vol:02d}"
        print(f"\n{'='*60}\n{page}\n{'='*60}")
        parsed = api_parse(page)
        parser = PoemHtmlExtractor()
        parser.feed(parsed["text"])
        text = parser.text()
        print(f"渲染正文长度: {len(text)} 字")
        print(f"含〈〉: {text.count('〈')} / {text.count('〉')}")
        print("前 2000 字:")
        print(text[:2000])
        print("\n维基文本前 2000 字:")
        print(parsed["wikitext"][:2000])
        time.sleep(1.5)


if __name__ == "__main__":
    main()
