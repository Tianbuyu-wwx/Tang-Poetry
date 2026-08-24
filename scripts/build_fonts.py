# -*- coding: utf-8 -*-
"""生成自托管字体子集（woff2），替代 Google Fonts 外链。

架构（2026-08-24 实测定型）：
  - Noto Serif SC 用 **可变字体**（wght 200-900 单文件覆盖 400/500/700），
    按 **站内字频** 打包成若干片（每片 ~600 字，高频字集中在第 0 片），
    配合 unicode-range 让浏览器只下载当前页面用到的片。
    典型诗页命中前 2~4 片（合计 <400KB），冷门字按需拉取。
  - Ma Shan Zheng / ZCOOL XiaoWei 用于全站印章与标题（印章字来自诗人库，
    覆盖面广），做整集子集单文件。

产物为入库静态资产；只有内容出现大量新用字后才需重跑本脚本刷新。
缺字时回落系统衬线体，不会白块。

用法：python scripts/build_fonts.py
依赖：fonttools + brotli（仅本地生成需要；产物已入库则 CI 无感）
"""
from __future__ import annotations

import json
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path

from fontTools import subset

ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
ASSETS = WEBSITE / "assets"
FONTS_DIR = ASSETS / "fonts"
WORK = ROOT / "scripts" / "_work"

VF_URL = "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Serif/Variable/OTF/Subset/NotoSerifSC-VF.otf"
VF_LOCAL = WORK / "NotoSerifSC-VF.otf"
DISPLAY_FONTS = [
    (
        "ma-shan-zheng",
        "Ma Shan Zheng",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/mashanzheng/MaShanZheng-Regular.ttf",
    ),
    (
        "zcool-xiaowei",
        "ZCOOL XiaoWei",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/zcoolxiaowei/ZCOOLXiaoWei-Regular.ttf",
    ),
]

SLICE_CHARS = 600          # 每片字符数（Google 官方为 ~500，取整 600 减少片数）
BASE_CHUNK = 120           # 第 0 片额外包含的 ASCII/符号数（几乎每个页面都要用）


def collect_texts() -> list[str]:
    """收集站点全部文本载体内容。"""
    texts: list[str] = []

    def feed(path: Path) -> None:
        try:
            texts.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            pass

    candidates = [
        *ASSETS.glob("*.js"),
        *(ASSETS / "poem-shards").glob("*.js"),
        *(ASSETS / "poet-work-shards").glob("*.js"),
        *(ASSETS / "poet-bio-shards").glob("*.js"),
        *(ASSETS / "source-books").glob("*.js"),
        *WEBSITE.glob("*.html"),
        WORK / "sources-data.js",
        ROOT / "docs" / "lessons.json",
        *sorted((ROOT / "docs" / "curated").rglob("*.md")),
        *sorted((ROOT / "docs" / "news").rglob("*.md")),
        *sorted((ROOT / "docs" / "periodicals").rglob("*.md")),
    ]
    for path in candidates:
        feed(path)
    return texts


def build_charset_and_freq(texts: list[str]) -> tuple[str, Counter]:
    """返回 (去重字符集, 字频)。ASCII 与中文标点视为最高频兜底。"""
    counter: Counter = Counter()
    for text in texts:
        counter.update(text)
    charset: set[str] = set(counter)
    charset.update(chr(c) for c in range(0x20, 0x7F))
    charset.update("，。、；：？！「」『』（）《》〈〉【】…—·～“”‘’％℃°×÷±")
    charset.update("０１２３４５６７８９〇一二三四五六七八九十百千万亿")
    charset.difference_update({"\n", "\r", "\t"})
    return "".join(sorted(charset)), counter


def pack_slices(charset: str, counter: Counter) -> list[str]:
    """按字频降序把字符集打包成片；第 0 片强制含全部 ASCII/符号。"""
    base = [ch for ch in sorted(charset) if ord(ch) < 0x2E80]
    cjk = sorted(
        (ch for ch in charset if ord(ch) >= 0x2E80),
        key=lambda ch: (-counter.get(ch, 0), ord(ch)),
    )
    slices = []
    merged_base = "".join(base[: BASE_CHUNK]) + "".join(cjk[: SLICE_CHARS - len(base[:BASE_CHUNK])])
    slices.append(merged_base)
    rest = cjk[SLICE_CHARS - len(base[:BASE_CHUNK]):]
    for i in range(0, len(rest), SLICE_CHARS):
        slices.append(rest[i : i + SLICE_CHARS])
    return slices


def unicode_range_label(text: str) -> str:
    """把一片的码位压成 unicode-range 标签（连续段合并）。"""
    points = sorted(ord(ch) for ch in text)
    spans: list[tuple[int, int]] = []
    for cp in points:
        if spans and cp <= spans[-1][1] + 1:
            spans[-1] = (spans[-1][0], cp)
        else:
            spans.append((cp, cp))
    labels = [
        f"U+{lo:X}" if lo == hi else f"U+{lo:X}-{hi:X}" for lo, hi in spans
    ]
    # CSS unicode-range 无硬性条目上限，但保持可读：超过 60 段时放宽合并间距
    return ",".join(labels)


def subset_woff2(src_path: Path, text: str, out: Path) -> int:
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.ignore_missing_glyphs = True
    font = subset.load_font(str(src_path), options)
    ss = subset.Subsetter(options)
    ss.populate(text=text)
    ss.subset(font)
    subset.save_font(font, str(out), options)
    return out.stat().st_size


def main() -> None:
    texts = collect_texts()
    charset, counter = build_charset_and_freq(texts)
    print(f"charset: {len(charset)} unique chars", flush=True)
    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    css_rules: list[str] = []
    total = 0

    vf = VF_LOCAL
    if not vf.is_file():
        print("download NotoSerifSC VF ...", flush=True)
        urllib.request.urlretrieve(VF_URL, vf)

    slices = pack_slices(charset, counter)
    print(f"noto serif sc: {len(slices)} frequency-packed slices", flush=True)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmpdir = Path(tmp)
        for index, slice_chars in enumerate(slices):
            slice_text = "".join(slice_chars)
            out = FONTS_DIR / f"noto-sc-{index:03d}.woff2"
            size = subset_woff2(vf, slice_text, out)
            total += size
            label = unicode_range_label(slice_text)
            css_rules.append(
                "@font-face {\n"
                '  font-family: "Noto Serif SC";\n'
                "  font-style: normal;\n"
                "  font-weight: 200 900;\n"
                "  font-display: swap;\n"
                f'  src: url("../fonts/{out.name}") format("woff2");\n'
                f"  unicode-range: {label};\n"
                "}\n"
            )
        print(f"  slices done: {total / 1024:.0f} KB cumulative", flush=True)

        for name, family, url in DISPLAY_FONTS:
            raw = tmpdir / f"{name}.ttf"
            print(f"display {name} ...", flush=True)
            urllib.request.urlretrieve(url, raw)
            out = FONTS_DIR / f"{name}.woff2"
            size = subset_woff2(raw, charset, out)
            total += size
            print(f"  -> {out.name}: {size / 1024:.0f} KB")
            css_rules.append(
                "@font-face {\n"
                f'  font-family: "{family}";\n'
                "  font-style: normal;\n"
                "  font-weight: 400;\n"
                "  font-display: swap;\n"
                f'  src: url("../fonts/{name}.woff2") format("woff2");\n'
                "}\n"
            )

    header = (
        "/* 自托管字体子集（由 scripts/build_fonts.py 生成，勿手改）。\n"
        "   替代 Google Fonts 外链：大陆可达、不阻塞渲染、可离线。\n"
        "   Noto Serif SC 为可变字体（wght 200-900），按站内字频分片。 */\n\n"
    )
    css_path = ASSETS / "css" / "fonts.css"
    css_path.write_text(header + "\n".join(css_rules), encoding="utf-8")

    manifest = {
        "slices": len(slices),
        "display_fonts": len(DISPLAY_FONTS),
        "charset_chars": len(charset),
        "total_kb": round(total / 1024),
    }
    (FONTS_DIR / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    print(f"fonts.css written; {json.dumps(manifest)}")


if __name__ == "__main__":
    main()
