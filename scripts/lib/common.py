# -*- coding: utf-8 -*-
"""全唐诗数据管线公共工具函数。"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


def compact_json(data) -> str:
    """紧凑的 JSON 序列化，用于前端静态数据文件。"""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def load_js_assignment(path: Path, variable: str):
    """从 window.VAR = ... 格式的 JS 文件中读取 Python 对象。"""
    text = path.read_text(encoding="utf-8").strip()
    match = re.search(rf"window\.{re.escape(variable)}\s*=", text)
    if not match:
        raise ValueError(f"{path} 中没有 window.{variable} 赋值")
    payload = text[match.end() :].strip()
    if payload.endswith(";"):
        payload = payload[:-1]
    return json.loads(payload)


def write_js(path: Path, variable: str, data) -> None:
    """原子写入 window.VAR = ... 格式的 JS 文件。"""
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        f"window.{variable}=" + compact_json(data) + ";",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def atomic_write(path: Path, text: str) -> None:
    """原子写入文本文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def value_size(value) -> int:
    """返回字段内容的有效字符长度，用于判断赏析等字段是否为空。"""
    if isinstance(value, dict):
        return len("".join(str(x) for x in value.get("body", [])))
    if isinstance(value, list):
        return len("".join(str(x) for x in value))
    return len(str(value or ""))


def has_annotation(record: list) -> bool:
    """判断诗作记录是否带有题解、注释或赏析。"""
    return bool(
        str(record[6] or "").strip()
        or record[7]
        or value_size(record[8])
    )


def normalized_name(value: str) -> str:
    """去除姓名中的空白字符，用于作者匹配。"""
    return re.sub(r"\s+", "", str(value or ""))
