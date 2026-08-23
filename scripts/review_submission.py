# -*- coding: utf-8 -*-
"""把投稿 PR 的改动翻译成人类可读的体检报告。

社员经 Decap 后台提交上来的是 YAML frontmatter，社长审核时不该去读 diff 里的
裸字段。本脚本把本次改动的社员作品与档案整理成速览表 + 逐篇详情，附完整性
检查与风险提示，由 CI 贴到 PR 评论区。

设计约定：
  - 只输出报告，永远以 0 退出。硬错误由 build_curated.py 与 verify_all.py 拦截，
    本脚本即使在构建失败后运行也要能给出可读结论（workflow 用 if: always()）。
  - 「提示」不等于「不合格」。缺题解、缺赏析属于可以先上站再补的情形，
    交给社长判断，不由脚本代为否决。

运行：
  python scripts/review_submission.py --base origin/main
  python scripts/review_submission.py --files docs/curated/poems/hu-pan.md
  python scripts/review_submission.py --all
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

CURATED_REL = "docs/curated"
POEMS_REL = f"{CURATED_REL}/poems"
MEMBERS_REL = f"{CURATED_REL}/members"

STATUS_LABEL = {"A": "新增", "M": "修改", "D": "删除", "R": "改名"}

# 近体诗形制：体裁 -> (句数, 每句字数)。旧体诗排版惯例是「一联一行」，
# 故句数须按标点切分统计，不能按换行数——四行的五律实为八句。
FORM_SPEC = {
    "五绝": (4, 5),
    "七绝": (4, 7),
    "五律": (8, 5),
    "七律": (8, 7),
    "六绝": (4, 6),
}
SENTENCE_SPLIT = re.compile(r"[，。；？！,.;?!…]+")


def split_sentences(verse) -> list[str]:
    """把诗句拆成「句」：先并段，再按句读标点切分。"""
    text = "".join(str(seg) for seg in verse)
    text = re.sub(r"\s+", "", text)
    return [s for s in SENTENCE_SPLIT.split(text) if s]


def check_form(genre: str, verse) -> list[str]:
    """核对声明体裁与实际形制是否相符。只对近体诗生效。"""
    spec = FORM_SPEC.get(str(genre).strip())
    if not spec:
        return []
    want_count, want_chars = spec
    sentences = split_sentences(verse)
    issues: list[str] = []
    if len(sentences) != want_count:
        issues.append(f"体裁标作「{genre}」应为 {want_count} 句，实际 {len(sentences)} 句")
    odd = [f"第 {i + 1} 句 {len(s)} 字" for i, s in enumerate(sentences) if len(s) != want_chars]
    if odd:
        issues.append(f"体裁标作「{genre}」应每句 {want_chars} 字，例外：{'、'.join(odd[:4])}")
    return issues


def _run_git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def changed_files(base: str) -> list[tuple[str, str]]:
    """返回 [(状态, 相对路径)]，覆盖 docs/curated 下的改动。"""
    raw = _run_git(["diff", "--name-status", f"{base}...HEAD", "--", CURATED_REL])
    if not raw.strip():
        # 退化：base 不可达（浅克隆等）时改用两点比较
        raw = _run_git(["diff", "--name-status", base, "--", CURATED_REL])
    entries: list[tuple[str, str]] = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        code = parts[0][:1]
        path = parts[-1]  # 改名取新路径
        entries.append((code, path))
    return entries


def _load_registry() -> dict:
    path = ROOT / CURATED_REL / "poem-ids.json"
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _member_names() -> set[str]:
    """在册社员姓名（归一化），用于核对投稿作者。"""
    try:
        from lib import common

        names = set()
        for md in sorted((ROOT / MEMBERS_REL).glob("*.md")):
            import build_curated as bc

            _slug, meta = bc.parse_member(md)
            if meta.get("name"):
                names.add(common.normalized_name(meta["name"]))
        return names
    except Exception:
        return set()


def describe_poem(path: Path, registry: dict, roster: set[str]) -> tuple[list[str], list[str]]:
    """解析单篇作品，返回 (详情行, 提示行)。"""
    detail: list[str] = []
    warn: list[str] = []
    try:
        import build_curated as bc
        from lib import common
    except Exception as exc:  # pragma: no cover
        return [f"- 解析器不可用：{exc}"], []

    try:
        meta, record = bc.parse_poem(path)
    except SystemExit as exc:
        return [], [f"**{path.name}** 无法解析：{exc}"]
    except Exception as exc:
        return [], [f"**{path.name}** 无法解析：{exc}"]

    title, author, genre, year, source, verse, context, notes, appr, famous, srcs = record

    lines = sum(len(str(seg).splitlines()) for seg in verse)
    stanzas = len(verse)
    sentences = split_sentences(verse)
    form_issues = check_form(genre, verse)
    detail.append(f"- **作者**：{author or '（缺）'}" + ("　✅ 在册" if common.normalized_name(author) in roster else "　⚠️ 不在社员名录"))
    detail.append(
        f"- **体裁 · 年代**：{genre or '（缺）'} · {year or '（缺）'}"
        + ("　⚠️ 形制不符" if form_issues else ("　✅ 形制相符" if str(genre).strip() in FORM_SPEC else ""))
    )
    if str(genre).strip() in FORM_SPEC:
        detail.append(f"- **诗句**：{len(sentences)} 句 / {lines} 行" + ("" if verse else "　⚠️ 正文为空"))
    else:
        detail.append(f"- **诗句**：{lines} 行 / {stanzas} 段" + ("" if verse else "　⚠️ 正文为空"))
    detail.append(f"- **题解**：{'有（' + str(len(context)) + ' 字）' if context else '无'}")
    detail.append(f"- **注释**：{len(notes) or '无'}" + (" 条" if notes else ""))
    appr_body = appr.get("body") or []
    appr_src = appr.get("source") or ""
    detail.append(
        f"- **赏析**：{'有（' + str(len(appr_body)) + ' 段' + ('，署「' + appr_src + '」' if appr_src else '') + '）' if appr_body else '无'}"
    )
    detail.append(f"- **名句**：{len(famous) or '无'}" + (" 条" if famous else ""))
    detail.append(f"- **出处溯源**：{'、'.join(str(s) for s in srcs) if srcs else '无'}")

    key = path.stem
    if key in registry:
        pid = f"member_{registry[key]}"
        detail.append(f"- **上站地址**：`poem.html?id={pid}`")
    else:
        detail.append("- **上站地址**：待构建分配")

    if not title:
        warn.append(f"**{path.name}** 缺少 title")
    if not verse:
        warn.append(f"**{path.name}** 诗句正文为空")
    if author and common.normalized_name(author) not in roster:
        warn.append(f"**{path.name}** 的作者「{author}」不在社员名录，需先补 `{MEMBERS_REL}/` 下的档案，否则构建会中止")
    if not context and not appr_body:
        warn.append(f"**{path.name}** 既无题解也无赏析（可先上站后补）")
    if not source:
        warn.append(f"**{path.name}** 缺少 source（出处）")
    for issue in form_issues:
        warn.append(f"**{path.name}** {issue}")

    return detail, warn


def describe_member(path: Path) -> tuple[list[str], list[str]]:
    detail: list[str] = []
    warn: list[str] = []
    try:
        import build_curated as bc

        slug, meta = bc.parse_member(path)
    except Exception as exc:
        return [], [f"**{path.name}** 无法解析：{exc}"]

    detail.append(f"- **姓名**：{meta.get('name') or '（缺）'}")
    detail.append(f"- **身份**：{meta.get('summary') or '（缺）'}")
    detail.append(f"- **时代**：{meta.get('dynasty') or '今'}")
    if meta.get("sub"):
        detail.append(f"- **别号 / 补充**：{meta['sub']}")
    life = meta.get("life") or []
    detail.append(f"- **小传**：{str(len(life)) + ' 条' if life else '无'}")
    detail.append(f"- **名录 slug**：`{slug}`")

    if not meta.get("name"):
        warn.append(f"**{path.name}** 缺少 name，构建会中止")
    return detail, warn


def build_report(entries: list[tuple[str, str]]) -> str:
    registry = _load_registry()
    roster = _member_names()

    poems = [(c, p) for c, p in entries if p.startswith(POEMS_REL)]
    members = [(c, p) for c, p in entries if p.startswith(MEMBERS_REL)]
    others = [(c, p) for c, p in entries if not p.startswith(POEMS_REL) and not p.startswith(MEMBERS_REL)]

    out: list[str] = ["## 投稿体检报告", ""]

    if not entries:
        out.append("本次改动未触及 `docs/curated/`，社库内容无变化。")
        return "\n".join(out)

    # ---- 速览表 ----
    out.append("| 状态 | 类型 | 文件 | 篇名 / 姓名 |")
    out.append("| --- | --- | --- | --- |")
    all_warn: list[str] = []
    poem_details: list[tuple[str, str, list[str]]] = []
    member_details: list[tuple[str, str, list[str]]] = []

    for code, rel in poems:
        path = ROOT / rel
        label = STATUS_LABEL.get(code, code)
        if code == "D" or not path.is_file():
            out.append(f"| {label} | 作品 | `{Path(rel).name}` | — |")
            continue
        detail, warn = describe_poem(path, registry, roster)
        all_warn.extend(warn)
        try:
            import build_curated as bc

            meta, _ = bc.parse_poem(path)
            name = meta.get("title", "")
        except Exception:
            name = "（解析失败）"
        out.append(f"| {label} | 作品 | `{Path(rel).name}` | {name} |")
        poem_details.append((label, name or Path(rel).name, detail))

    for code, rel in members:
        path = ROOT / rel
        label = STATUS_LABEL.get(code, code)
        if code == "D" or not path.is_file():
            out.append(f"| {label} | 社员 | `{Path(rel).name}` | — |")
            continue
        detail, warn = describe_member(path)
        all_warn.extend(warn)
        try:
            import build_curated as bc

            _slug, meta = bc.parse_member(path)
            name = meta.get("name", "")
        except Exception:
            name = "（解析失败）"
        out.append(f"| {label} | 社员 | `{Path(rel).name}` | {name} |")
        member_details.append((label, name or Path(rel).name, detail))

    for code, rel in others:
        out.append(f"| {STATUS_LABEL.get(code, code)} | 其他 | `{rel}` | — |")

    out.append("")

    # ---- 逐篇详情 ----
    if poem_details:
        out.append("### 作品详情")
        out.append("")
        for label, name, detail in poem_details:
            out.append(f"#### {name}（{label}）")
            out.extend(detail)
            out.append("")

    if member_details:
        out.append("### 社员档案")
        out.append("")
        for label, name, detail in member_details:
            out.append(f"#### {name}（{label}）")
            out.extend(detail)
            out.append("")

    # ---- 检查结论 ----
    out.append("### 检查结论")
    out.append("")
    if all_warn:
        out.append(f"⚠️ {len(all_warn)} 项待确认：")
        out.append("")
        for w in all_warn:
            out.append(f"- {w}")
    else:
        out.append("✅ 字段完整性检查未发现问题。")
    out.append("")
    out.append("> 「待确认」不等于不合格：缺题解、缺赏析可以先上站后补，由社务判断。")
    out.append("> 构建与数据校验的硬性结论以本次 workflow 的其余步骤为准。")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="生成投稿体检报告")
    parser.add_argument("--base", help="对比基线（如 origin/main）")
    parser.add_argument("--files", nargs="*", help="直接指定要体检的文件")
    parser.add_argument("--all", action="store_true", help="体检全部社库内容")
    parser.add_argument("--output", help="写入文件（默认输出到 stdout）")
    args = parser.parse_args()

    if args.all:
        entries = [("M", f"{MEMBERS_REL}/{p.name}") for p in sorted((ROOT / MEMBERS_REL).glob("*.md"))]
        entries += [("M", f"{POEMS_REL}/{p.name}") for p in sorted((ROOT / POEMS_REL).glob("*.md"))]
    elif args.files:
        entries = [("M", str(Path(f).as_posix())) for f in args.files]
    elif args.base:
        entries = changed_files(args.base)
    else:
        parser.error("需指定 --base / --files / --all 之一")
        return 2

    report = build_report(entries)

    if args.output:
        Path(args.output).write_text(report + "\n", encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
