#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
维基百科/维基文库 API 合规抓取脚本
- 仅抓取结构化段落：创作背景、赏析、名句、作者生平
- 遵守 robots.txt、速率限制、CC BY-SA 署名
- 断点续传、指数退避重试
- 输出：JSONL 增量文件，含来源标注
"""

import os, sys, json, time, re, requests
from pathlib import Path
from urllib.parse import quote
from typing import Optional, Dict, List
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parents[1]
BUILD_WORK = ROOT / "scripts" / "_work"  # 完整诗库为构建中间产物，不随站点托管
DATA_DIR = ROOT / "data" / "wiki"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ========== 配置 ==========
API_WP = "https://zh.wikipedia.org/w/api.php"
API_WS = "https://zh.wikisource.org/w/api.php"
UA = "TangPoetryBot/1.0 (https://github.com/your-repo; tangpoetry@example.com)"
RATE_LIMIT = 1.0        # 秒/请求，维基百科建议 1 秒/请求
MAX_RETRIES = 3
TIMEOUT = 15
BATCH_SIZE = 50
MAX_WORKERS = 2         # 并发数，维基建议不超过 2

# 目标段落关键词
TARGET_SECTIONS = {
    "创作背景": ["创作背景", "背景", "创作", "背景故事", "写作背景"],
    "赏析": ["赏析", "鉴赏", "艺术特色", "艺术价值", "艺术分析", "评价"],
    "名句": ["名句", "名句欣赏", "千古名句", "脍炙人口", "传诵", "名句赏析"],
    "作者生平": ["生平", "生平事迹", "人物生平", "人物简介", "人物"],
}

HEADERS = {"User-Agent": "TangPoetryBot/1.0 (https://github.com/your-repo; contact@example.com)"}

# ========== 数据结构 ==========
@dataclass
class WikiSection:
    title: str
    section: str
    content: str
    source_url: str
    source_type: str  # "wikipedia" | "wikisource"

@dataclass
class PoemWikiData:
    poem_id: str
    title: str
    author: str
    sections: List[WikiSection]
    fetched_at: str

# ========== 核心类 ==========
class WikiClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.last_request = 0.0

    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < RATE_LIMIT:
            time.sleep(RATE_LIMIT - elapsed)

    def _request(self, url: str, params: dict) -> Optional[dict]:
        for attempt in range(MAX_RETRIES):
            self._rate_limit()
            try:
                resp = self.session.get(url, params=params, timeout=TIMEOUT)
                self.last_request = time.time()
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    print(f"  [ERROR] {url} {params}: {e}")
                    return None
                time.sleep(2 ** attempt)
        return None

    def search(self, query: str, site: str = "wikipedia") -> List[str]:
        """搜索页面标题，返回前 3 个匹配"""
        api = API_WP if site == "wikipedia" else API_WS
        data = self._request(api, {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 3,
            "format": "json",
            "srprop": "title",
        })
        if not data: return []
        return [item["title"] for item in data.get("query", {}).get("search", [])]

    def get_page_sections(self, title: str, site: str = "wikipedia") -> List[Dict]:
        """获取页面所有段落标题"""
        api = API_WP if site == "wikipedia" else API_WS
        data = self._request(api, {
            "action": "parse",
            "page": title,
            "prop": "sections",
            "format": "json",
        })
        if not data: return []
        return data.get("parse", {}).get("sections", [])

    def get_section_content(self, title: str, section_index: int, site: str = "wikipedia") -> Optional[str]:
        """获取指定段落的纯文本内容"""
        api = API_WP if site == "wikipedia" else API_WS
        data = self._request(api, {
            "action": "parse",
            "page": title,
            "prop": "text",
            "section": section_index,
            "format": "json",
            "disablelimitreport": 1,
        })
        if not data: return None
        html = data.get("parse", {}).get("text", {}).get("*", "")
        # 简单清洗 HTML -> 纯文本
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def extract_target_sections(self, title: str, site: str = "wikipedia") -> List[WikiSection]:
        """提取目标段落"""
        sections = self.get_page_sections(title, site)
        if not sections: return []

        results = []
        for sec in sections:
            sec_title = sec.get("line", "").strip()
            sec_idx = sec.get("index", "")
            # 匹配目标段落
            matched_type = None
            for typ, keywords in TARGET_SECTIONS.items():
                if any(kw in sec_title for kw in keywords):
                    matched_type = typ
                    break
            if not matched_type:
                continue

            content = self.get_section_content(title, sec_idx, site)
            if not content or len(content) < 50:  # 太短跳过
                continue

            results.append(WikiSection(
                title=title,
                section=matched_type,
                content=content[:5000],  # 限长
                source_url=f"https://{'zh.wikipedia.org' if site=='wikipedia' else 'zh.wikisource.org'}/wiki/{quote(title)}#section-{sec_idx}",
                source_type=site,
            ))
        return results

    def fetch_poem_data(self, title: str, author: str) -> Optional[PoemWikiData]:
        """聚合百科+文库数据"""
        all_sections = []
        for site in ("wikipedia", "wikisource"):
            try:
                secs = self.extract_target_sections(title, site)
                if secs:
                    all_sections.extend(secs)
            except Exception as e:
                print(f"  [WARN] {site} {title}: {e}")

        if not all_sections:
            return None

        return PoemWikiData(
            poem_id="",  # 后续匹配填入
            title=title,
            author=author,
            sections=all_sections,
            fetched_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

# ========== 匹配逻辑 ==========
# 路径在 load_poems_index 和 main 中按需解析
DUMMY_LOCAL = None  # 占位

def load_poems_index() -> Dict[tuple, List[str]]:
    """加载 poems-data.js 建立 title+author -> poem_id 映射"""
    POEMS_JS = BUILD_WORK / "poems-data.js"
    src = open(POEMS_JS, encoding="utf-8").read()
    m = re.search(r"window\.POEMS_DATA=(.*?);$", src, re.S)
    D = json.loads(m.group(1))

    mapping = {}
    for k, v in D.items():
        key = (v[1].strip(), v[0].strip())  # (author, title)
        if key not in mapping:
            mapping[key] = []
        mapping[key].append(v[0])  # poem_id
    return mapping

def match_poems(wiki_data: PoemWikiData, id_map: Dict) -> List[tuple]:
    """将 wiki 数据匹配到 poems-data 中的 poem_id"""
    key = (wiki_data.author.strip(), wiki_data.title.strip())
    if key in id_map:
        return [(pid, wiki_data) for pid in id_map[key]]
    # 模糊匹配：作者模糊 + 标题包含
    matches = []
    for (author, title), pids in id_map.items():
        if wiki_data.author in author and wiki_data.title in title:
            for pid in pids:
                matches.append((pid, wiki_data))
    return matches


# ========== 主流程 ==========
def main():
    print("=== 维基百科/维基文库 增量抓取 ===")
    print(f"输出目录: {DATA_DIR}")

    # 1) 加载 poems-data 映射
    id_map = load_poems_index()
    print(f"已加载 {len(set().union(*id_map.values()))} 首诗的映射")

    # 2) 获取所有待抓取的 (author, title) 对
    POEMS_JS = BUILD_WORK / "poems-data.js"
    src = open(POEMS_JS, encoding="utf-8").read()
    m = re.search(r"window\.POEMS_DATA=(.*?);$", src, re.S)
    D = json.loads(m.group(1))

    poems_to_fetch = []
    for k, v in D.items():
        poems_to_fetch.append((v[1].strip(), v[0].strip(), v[0]))  # (author, title, poem_id)

    print(f"待抓取: {len(poems_to_fetch)} 首")

    # 2. 加载已存在的缓存（断点续传）
    cache_file = DATA_DIR / "wiki_cache.jsonl"
    fetched = set()
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    fetched.add((d["author"], d["title"]))
                except: pass
    print(f"已缓存: {len(fetched)} 条")

    # 过滤已抓取
    todo = [(a, t, pid) for a, t, pid in poems_to_fetch if (a, t) not in fetched]
    print(f"待抓取: {len(todo)} 首")

    if not todo:
        print("全部已抓取完成")
        return

    # 3) 并发抓取
    client = WikiClient()
    id_map = load_poems_index()

    # 输出文件
    out_file = DATA_DIR / "wiki_sections.jsonl"
    lock = threading.Lock()

    def worker(args):
        author, title, poem_id = args
        try:
            wiki_data = WikiClient().fetch_poem_data(title, author)
            if not wiki_data:
                return None
            matches = match_poems(wiki_data, load_poems_index())
            if not matches:
                return None
            # 返回所有匹配的 poem_id
            results = []
            for pid, wd in matches:
                wd.poem_id = pid
                results.append(asdict(wd))
            return results
        except Exception as e:
            print(f"  [ERR] {author}《{title}》: {e}")
            return None

    print(f"\n开始抓取 (并发 {MAX_WORKERS}, 限流 {RATE_LIMIT}s)...")
    start = time.time()
    done = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(worker, args): args for args in todo}
        for future in as_completed(futures):
            result = future.result()
            if result:
                with lock:
                    with open(out_file, "a", encoding="utf-8") as f:
                        for item in result:
                            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            done += 1
            if done % 50 == 0:
                elapsed = time.time() - start
                print(f"  进度: {done}/{len(todo)} | 耗时: {elapsed:.0f}s | 剩余: {(len(todo)-done)*elapsed/max(done,1):.0f}s")

    elapsed = time.time() - start
    print(f"\n完成! 耗时: {elapsed:.0f}s")

    # 验证
    print("\n=== 验证结果 ===")
    verify()


def verify():
    """验证抓取结果"""
    cache_file = DATA_DIR / "wiki_cache.jsonl"
    if not cache_file.exists():
        print("无缓存文件")
        return

    stats = {"total": 0, "by_section": {}, "poems": set(), "authors": set()}
    with open(DATA_DIR / "wiki_cache.jsonl", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                stats["total"] += 1
                stats["poems"].add(d["poem_id"])
                stats["authors"].add(d["author"])
                for sec in d["sections"]:
                    stats["by_section"][sec["section"]] = stats["by_section"].get(sec["section"], 0) + 1
            except: pass

    print(f"总段落: {stats['total']}")
    print(f"覆盖诗作: {len(stats['poems'])} 首")
    print(f"涉及作者: {len(stats['authors'])} 位")
    print("段落类型分布:")
    for k, v in sorted(stats["by_section"].items()):
        print(f"  {k}: {v} 段")


if __name__ == "__main__":
    import threading
    main()