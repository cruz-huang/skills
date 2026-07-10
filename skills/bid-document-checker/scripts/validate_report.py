#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate bid-document-checker Markdown/HTML reports.

This script is intentionally conservative. It checks structure and consistency;
it does not re-run bid compliance review.
"""

from __future__ import annotations

import argparse
import re
import sys
from html import unescape
from pathlib import Path


REQUIRED_GROUPS = [
    "PRE",
    "G01",
    "G02",
    "G03",
    "G04",
    "G05",
    "G06",
    "D00",
    "D01",
    "D02",
    "D03",
    "D04",
    "D05",
    "D06",
    "D07",
    "D08",
    "D09",
    "D10",
    "D11",
]

REQUIRED_SECTIONS = [
    "报告信息",
    "总论",
    "当前问题",
    "下一步",
]

FULL_STAGES = {
    "full",
    "draft",
    "final",
    "sealed",
    "draft_review",
    "final_content_review",
    "sealed_final_review",
}

REQUIRED_DETAIL_FIELDS = [
    "状态",
    "实际检查内容",
    "结论（位置/结果/风险/问题/建议）",
]

FORBIDDEN_PATTERNS = [
    (re.compile(r"综合评分\s*[:：]?\s*\d+"), "不得输出模拟综合评分"),
    (re.compile(r"预计得分\s*[:：]?\s*\d+"), "不得输出预计得分"),
    (re.compile(r"可得\s*\d+\s*分"), "不得输出无依据可得分"),
]

CHECK_ID_RE = re.compile(r"\b(?:PRE|G\d{2}|D\d{2}|TENDER|PX)-\d{2,4}\b")
ISSUE_ID_RE = re.compile(r"\bP[012]-\d{2,4}\b")
ISSUE_LEVELS = ("P0", "P1", "P2")


def read_text(path: str | None) -> str:
    if not path:
        return ""
    return Path(path).read_text(encoding="utf-8")


def html_to_text(html: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    return re.sub(r"\s+", " ", text)


def issue_ids(text: str) -> set[str]:
    return set(ISSUE_ID_RE.findall(text))


def check_ids(text: str) -> set[str]:
    return set(CHECK_ID_RE.findall(text))


def section_after_heading(text: str, heading: str) -> str:
    match = re.search(rf"(?m)^##\s*{re.escape(heading)}\b.*$", text)
    if not match:
        return ""
    next_heading = re.search(r"(?m)^##\s+", text[match.end() :])
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.start() : end]


def current_issue_section(md: str) -> str:
    return section_after_heading(md, "当前问题")


def issue_ids_by_level(text: str) -> dict[str, set[str]]:
    return {level: set(re.findall(rf"\b{level}-\d{{2,4}}\b", text)) for level in ISSUE_LEVELS}


def mentioned_issue_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for amount, level in re.findall(r"存在\s*(\d+)\s*项\s*(P[012])\b", text):
        counts[level] = int(amount)
    return counts


def remove_current_issue_section(md: str) -> str:
    section = current_issue_section(md)
    return md.replace(section, "", 1) if section else md


def markdown_detail_rows(md: str) -> list[str]:
    without_issues = remove_current_issue_section(md)
    return [
        line.strip()
        for line in without_issues.splitlines()
        if line.lstrip().startswith("|") and CHECK_ID_RE.search(line)
    ]


def html_table_rows(html: str) -> list[str]:
    return re.findall(r"(?is)<tr\b[^>]*>.*?</tr>", html)


def html_metric_count(html: str, level: str) -> int | None:
    css = level.lower()
    match = re.search(
        rf'(?is)<div\s+class="metric\s+{css}"[^>]*>\s*<b>\s*(\d+)\s*</b>',
        html,
    )
    return int(match.group(1)) if match else None


def has_issue_heading(text: str, level: str) -> bool:
    return bool(re.search(rf"(?m)^#{{2,4}}\s*(?:当前问题[：:]\s*)?{level}\b", text))


def mentions_positive_issue_count(text: str, level: str) -> bool:
    return bool(re.search(rf"存在\s*[1-9]\d*\s*项\s*{level}\b", text))


def built_in_check_ids() -> list[str]:
    card_path = Path(__file__).resolve().parents[1] / "references" / "acceptance-card.md"
    if not card_path.exists():
        return []
    card = card_path.read_text(encoding="utf-8")
    return sorted(set(re.findall(r"\b(?:PRE|G\d{2}|D\d{2})-\d{2}\b", card)))


def add_error(errors: list[str], message: str) -> None:
    errors.append(f"ERROR: {message}")


def add_warn(warnings: list[str], message: str) -> None:
    warnings.append(f"WARN: {message}")


def is_full_stage(stage: str) -> bool:
    return stage in FULL_STAGES


def has_detail_rows(md: str) -> bool:
    return bool(CHECK_ID_RE.search(md))


def validate_markdown(md: str, stage: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    issue_section = current_issue_section(md)
    ledger_ids = issue_ids(issue_section)
    all_ids = issue_ids(md)

    for section in REQUIRED_SECTIONS:
        if section not in md:
            add_error(errors, f"Markdown 缺少必要章节或关键词：{section}")

    if all_ids and not ledger_ids:
        add_error(errors, "Markdown 存在 P0/P1/P2 编号，但当前问题区没有唯一问题台账")
    for issue_id in sorted(all_ids - ledger_ids):
        add_error(errors, f"Markdown 问题编号未进入当前问题清单：{issue_id}")

    if is_full_stage(stage):
        for group in REQUIRED_GROUPS:
            if group not in md:
                add_error(errors, f"Markdown 缺少验收卡检查组：{group}")

        for check_id in built_in_check_ids():
            if check_id not in md:
                add_error(errors, f"Markdown 缺少内置验收卡检查项：{check_id}")
    elif not any(group in md for group in REQUIRED_GROUPS):
        add_warn(warnings, "局部/章节检查未出现 PRE/G/D 检查组；请确认报告范围是否写清")

    if is_full_stage(stage) or has_detail_rows(md):
        for field in REQUIRED_DETAIL_FIELDS:
            if field not in md:
                add_error(errors, f"验收卡明细缺少字段：{field}")

    if is_full_stage(stage) and "验收卡覆盖率摘要" not in md:
        add_warn(warnings, "完整检查建议包含验收卡覆盖率摘要")

    if is_full_stage(stage):
        required_card_summary = [
            ("本轮验收卡", r"本轮验收卡"),
            ("验收卡覆盖率摘要", r"验收卡覆盖率摘要"),
            ("项目增量项", r"项目增量项"),
            ("TENDER项", r"TENDER\s*项"),
            ("未映射要求", r"未映射要求"),
        ]
        for label, pattern in required_card_summary:
            if not re.search(pattern, md):
                add_error(errors, f"报告信息中的验收卡摘要缺少字段：{label}")

    if re.search(r"(?m)^##\s*本轮验收卡信息\b", md):
        add_error(errors, "不要输出独立的“本轮验收卡信息”章节；验收卡路径和覆盖率摘要应写入报告信息")

    for pattern, message in FORBIDDEN_PATTERNS:
        if pattern.search(md):
            add_error(errors, message)

    # Empty issue sections are discouraged. It is acceptable to mention "未发现明确 P0"
    # in summary, but not to render an empty P0 issue heading.
    if re.search(r"(?m)^#{2,4}\s*P0.*\n\s*(未发现|无)\b", md):
        add_warn(warnings, "Markdown 可能存在空 P0 问题标题；无 P0 时建议只在总论说明")

    if (re.search(r"\bP0-\d{2,4}\b", md) or mentions_positive_issue_count(md, "P0")) and not has_issue_heading(md, "P0"):
        add_error(errors, "Markdown 存在 P0 问题或 P0 数量，但未在当前问题区列出 P0 小节")

    if "首页摘要" in md and md.count("首页摘要") > 1:
        add_warn(warnings, "Markdown 出现多处“首页摘要”，可能有重复摘要")

    ledger_by_level = issue_ids_by_level(issue_section)
    for level, expected in mentioned_issue_counts(md).items():
        actual = len(ledger_by_level[level])
        if expected != actual:
            add_error(errors, f"Markdown {level} 数量应按当前问题清单统计：摘要写 {expected}，清单为 {actual}")

    for row in markdown_detail_rows(md):
        row_issue_ids = issue_ids(row)
        if not row_issue_ids:
            continue
        if "关联 P" not in row or "详见当前问题清单" not in row:
            add_error(errors, "Markdown 明细行引用问题编号时必须写“关联 Pxx-xx；详见当前问题清单”： " + row[:120])
        if "建议：" in row:
            add_error(errors, "Markdown 明细行不得重复写整改建议，应只引用当前问题清单： " + row[:120])

    return errors, warnings


def validate_html(md: str, html: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    html_text = html_to_text(html)
    ledger_by_level = issue_ids_by_level(current_issue_section(md))
    md_ids = issue_ids(md)
    html_ids = issue_ids(html_text)

    for group in REQUIRED_GROUPS:
        if group in md and group not in html_text:
            add_error(errors, f"HTML 缺少 Markdown 中的检查组：{group}")

    for check_id in sorted(check_ids(md)):
        if check_id not in html_text:
            add_error(errors, f"HTML 缺少 Markdown 中的检查项：{check_id}")

    for section in REQUIRED_SECTIONS:
        if section in md and section not in html_text:
            add_error(errors, f"HTML 缺少 Markdown 中的主要章节：{section}")

    missing = sorted(md_ids - html_ids)
    if missing:
        add_error(errors, "HTML 缺少问题编号：" + ", ".join(missing))
    extra = sorted(html_ids - md_ids)
    if extra:
        add_error(errors, "HTML 出现 Markdown 没有的问题编号：" + ", ".join(extra))

    for level in ISSUE_LEVELS:
        metric = html_metric_count(html, level)
        if metric is not None and metric != len(ledger_by_level[level]):
            add_error(errors, f"HTML {level} 指标卡数量应按当前问题清单统计：指标为 {metric}，清单为 {len(ledger_by_level[level])}")

    for pattern, message in FORBIDDEN_PATTERNS:
        if pattern.search(html_text):
            add_error(errors, f"HTML {message}")

    if html_text.count("首页摘要") > 1:
        add_warn(warnings, "HTML 出现多处“首页摘要”，可能重复")

    if 'id="p0-section"' in html and not re.search(r"\bP0-\d{2,4}\b", html_text):
        add_error(errors, "HTML 存在空 P0 区块；无 P0 时不要列空问题区")

    if re.search(r"\b本轮验收卡信息\b", html_text) or 'id="card-section"' in html or 'data-target="card-section"' in html:
        add_error(errors, "HTML 不要输出独立的“本轮验收卡信息”章节或验收卡导航；相关信息应放在报告信息中")

    if "table-status pass" in html and "pass-row" not in html:
        add_error(errors, "HTML 通过行必须支持整行绿色文字样式：缺少 pass-row 样式或脚本标记")

    for row_html in html_table_rows(html):
        row_text = html_to_text(row_html)
        if not CHECK_ID_RE.search(row_text) or not issue_ids(row_text):
            continue
        if "关联 P" not in row_text or "详见当前问题清单" not in row_text:
            add_error(errors, "HTML 明细表引用问题编号时必须写“关联 Pxx-xx；详见当前问题清单”： " + row_text[:120])
        if "建议：" in row_text:
            add_error(errors, "HTML 明细表不得重复写整改建议，应只引用当前问题清单： " + row_text[:120])

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--md", required=True, help="Markdown report path")
    parser.add_argument("--html", help="HTML report path")
    parser.add_argument(
        "--stage",
        default="full",
        choices=[
            "full",
            "chapter",
            "draft",
            "final",
            "sealed",
            "spot",
            "chapter_review",
            "draft_review",
            "final_content_review",
            "sealed_final_review",
        ],
        help="Report stage. Full/draft/final/sealed require all built-in checks; chapter/spot allow scoped reports.",
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = parser.parse_args()

    md = read_text(args.md)
    errors, warnings = validate_markdown(md, args.stage)

    if args.html:
        html = read_text(args.html)
        html_errors, html_warnings = validate_html(md, html)
        errors.extend(html_errors)
        warnings.extend(html_warnings)

    for warning in warnings:
        print(warning)
    for error in errors:
        print(error)

    if errors or (args.strict and warnings):
        return 1

    print("OK: report structure passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
