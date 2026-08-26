# -*- coding: utf-8 -*-
"""生成 OG 分享图（1200×630 PNG），替代缺失的社交预览卡。

设计语言与站点一致：宣纸底 + 朱砂印章 + 马善政楷书诗句 + 双语署名。
- 每首带赏析的诗（5,870 首）一张，文件名 = 诗 id，输出 website/og/<id>.png
- 另产默认卡 website/og/default.png（站点级分享兜底）
- 逐张确定性渲染（无时间戳/随机），两次构建字节级一致（幂等）

体积控制：PNG 用调色板量化（宣纸底+墨字+朱印 ≤64 色），单张 ~40-70KB。
字体：Ma Shan Zheng（印章标题）+ Noto Serif SC VF（正文），均自
scripts/_work 读取；缺失时自动从 google/fonts 下载。
"""
from __future__ import annotations

import html
import re
import struct
import subprocess
import sys
import urllib.request
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from lib import common  # noqa: E402
from build_frontend_assets import pages_base_url  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

WORK = ROOT / "scripts" / "_work"
OUT_DIR = ROOT / "website" / "og"
W, H = 1200, 630
PAPER = (250, 246, 237)
PAPER_DEEP = (243, 236, 219)
INK = (26, 26, 26)
INK_LIGHT = (122, 122, 122)
CINNABAR = (168, 50, 50)

MA_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/mashanzheng/MaShanZheng-Regular.ttf"
NOTO_URL = "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Serif/Variable/OTF/Subset/NotoSerifSC-VF.otf"


def ensure_fonts() -> tuple[Path, Path]:
    ma = WORK / "MaShanZheng-Regular.ttf"
    noto = WORK / "NotoSerifSC-VF.otf"
    for path, url in ((ma, MA_URL), (noto, NOTO_URL)):
        if not path.is_file():
            print(f"[fonts] downloading {path.name} ...")
            urllib.request.urlretrieve(url, path)
    return ma, noto


def wrap_by_width(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    buf = ""
    for ch in text:
        if ch == "\n":
            lines.append(buf)
            buf = ""
            continue
        if draw.textlength(buf + ch, font=font) <= max_width:
            buf += ch
        else:
            lines.append(buf)
            buf = ch
    if buf:
        lines.append(buf)
    return lines


def draw_seal(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], char: str, font) -> None:
    """朱砂印章：圆角方框 + 白字。"""
    x0, y0, x1, y1 = box
    radius = 10
    draw.rounded_rectangle(box, radius=radius, fill=CINNABAR)
    bbox = draw.textbbox((0, 0), char, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        ((x0 + x1 - w) / 2 - bbox[0], (y0 + y1 - h) / 2 - bbox[1]),
        char,
        font=font,
        fill=PAPER,
    )


def render_card(title: str, poet: str, verse: str, seal_char: str, out: Path, ma: Path, noto: Path) -> None:
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # 底部纸纹带
    draw.rectangle([0, H - 90, W, H], fill=PAPER_DEEP)
    draw.line([0, H - 90, W, H - 90], fill=(210, 200, 178), width=1)

    f_title = ImageFont.truetype(str(ma), 64)
    f_poet = ImageFont.truetype(str(noto), 30)
    f_verse = ImageFont.truetype(str(noto), 40)
    f_en = ImageFont.truetype(str(noto), 20)
    f_seal = ImageFont.truetype(str(ma), 44)

    margin = 90

    # 顶部：印章 + 站名 + 英文
    draw_seal(draw, (margin, 52, margin + 76, 128), seal_char, f_seal)
    draw.text((margin + 96, 62), "石湖诗社", font=f_poet, fill=INK)
    draw.text((margin + 96, 100), "SHIHU POETRY SOCIETY", font=f_en, fill=INK_LIGHT)

    # 诗题（马善政）
    draw.text((margin, 180), title[:18], font=f_title, fill=INK)

    # 诗句：按句号断行（每行一联），最多三行，超出省略
    verse_lines = []
    for sentence in [s.strip() for s in verse.split("。") if s.strip()]:
        candidate = sentence + "。"
        verse_lines.extend(wrap_by_width(draw, candidate, f_verse, W - margin * 2))
        if len(verse_lines) >= 3:
            break
    verse_lines = verse_lines[:3]
    y = 300
    for line in verse_lines:
        draw.text((margin, y), line, font=f_verse, fill=INK)
        y += 66

    # 底部署名
    draw.text((margin, H - 66), f"—— {poet} ｜ 全唐诗鉴赏", font=f_poet, fill=INK_LIGHT)

    # 右下装饰印章（用站点简体字，马善政字库无繁体「詩」）
    draw_seal(draw, (W - margin - 64, H - 130, W - margin, H - 66), "石", f_seal)

    # PNG 调色板量化（宣纸/墨/朱 ≤64 色）→ 小体积且确定性输出
    quantized = img.convert("P", palette=Image.ADAPTIVE, colors=64)
    quantized.save(out, format="PNG", optimize=True)


def png_bytes(path: Path) -> int:
    return path.stat().st_size


def build_og_images(poems: dict, poets: dict) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ma, noto = ensure_fonts()

    # 默认卡
    default_out = OUT_DIR / "default.png"
    render_card("石湖诗社", "全唐诗鉴赏", "收录《全唐诗》五万七千余首，逐诗笺注、古籍互证。", "石", default_out, ma, noto)

    sizes: dict[str, int] = {"default.png": png_bytes(default_out)}
    generated = 0
    for pid, record in poems.items():
        title = str(record[0] or "")
        poet = str(record[1] or "")
        verse = "".join(record[5] or [])
        appreciation = record[8] or {}
        if not (appreciation.get("text") or appreciation.get("body")):
            continue
        poet_entry = poets.get(pid)
        seal_char = (poet_entry or {}).get("sealChar") or poet[:1] or "詩"
        out = OUT_DIR / f"{pid}.png"
        render_card(title, poet, verse, seal_char, out, ma, noto)
        sizes[f"{pid}.png"] = png_bytes(out)
        generated += 1
    print(f"[og] generated {generated + 1} images, total {sum(sizes.values()) / 1024:.0f} KiB")
    return sizes


if __name__ == "__main__":
    poems = common.load_js_assignment(WORK / "poems-data.js", "POEMS_DATA")
    poets = common.load_js_assignment(WORK / "poets-data.js", "POETS_DATA")
    build_og_images(poems, poets)
