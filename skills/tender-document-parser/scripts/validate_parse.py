#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate tender-document-parser artifacts against the parse contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import re
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_OUTPUTS = {
    "parse_result": "parse_result.json",
    "raw_blocks": "raw_blocks.json",
    "requirements": "requirements.json",
    "fatal_checklist": "fatal_checklist.json",
    "scoring_matrix": "scoring_matrix.json",
    "manual_review_queue": "manual_review_queue.md",
    "material_checklist_json": "material_checklist.json",
    "material_checklist": "material_checklist.md",
    "material_checklist_xlsx": "material_checklist.xlsx",
    "fixed_formats_json": "fixed_formats.json",
    "fixed_formats_md": "fixed_formats.md",
    "timeline_matrix": "timeline_matrix.json",
    "parse_report": "parse_report.md",
    "html_report": "parse_report.html",
}


REQUIREMENT_FIELDS = {
    "requirement_id",
    "category",
    "risk_level",
    "title",
    "text",
    "confidence",
    "source_refs",
    "requires_response",
    "requires_seal",
    "response_hint",
    "content_trust",
}
MATERIAL_FIELDS = {
    "material_id",
    "material_name",
    "requirement",
    "usage_category",
    "material_class",
    "responsible_party",
    "needs_seal",
    "needs_scan",
    "purpose_flags",
    "source_refs",
    "source_text_location",
    "notes",
    "review_status",
}
FIXED_FORMAT_TYPES = {"fixed_template", "self_defined_format", "table_template", "signature_block"}
TIMELINE_FIELDS = {
    "timeline_id",
    "timeline_type",
    "name",
    "value",
    "trigger",
    "meaning",
    "source_requirement_id",
    "source_refs",
    "risk_note",
    "confidence",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_output(out_dir: Path, manifest: dict[str, Any], key: str) -> Path:
    entry = manifest.get("outputs", {}).get(key, {})
    if entry.get("path"):
        return Path(entry["path"])
    return out_dir / EXPECTED_OUTPUTS[key]


def add_issue(issues: list[str], code: str, message: str) -> None:
    issues.append(f"{code}: {message}")


def compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def warn_material_quality(material_items: list[dict[str, Any]], warnings: list[str]) -> None:
    suspicious_patterns = (
        r"支付含税合同金额",
        r"合同金额的\d+",
        r"中标服务费",
        r"银行转账",
        r"合同乙方",
        r"名称一致",
        r"终止合同",
        r"项目(?:质保)?验收报告",
    )
    for item in material_items:
        material_id = item.get("material_id", "material")
        name = compact(item.get("material_name", ""))
        material_class = item.get("material_class", "")
        if any(re.search(pattern, name) for pattern in suspicious_patterns):
            add_issue(warnings, "MATERIAL_SUSPICIOUS_NAME", f"{material_id} 名称疑似不是投标资料：{item.get('material_name')}")
        if re.search(r"信用中国|营业执照|事业单位法人|AAA|ISO|管理体系|电子与智能化|资质", name) and material_class != "投标人固定证明材料":
            add_issue(warnings, "MATERIAL_CLASS_CONFLICT", f"{material_id} {item.get('material_name')} 不应归为 {material_class}")
        if re.search(r"3C|节能|环境标志|检测报告|彩页|官方网站截图|软件功能截图|产品截图|专利|著作权|软著", name) and material_class != "技术/产品证明材料":
            add_issue(warnings, "MATERIAL_CLASS_CONFLICT", f"{material_id} {item.get('material_name')} 不应归为 {material_class}")
        if re.search(r"授权书|授权函|售后服务承诺函|质保承诺函|原厂.*(?:授权|售后|质保)|厂商.*(?:授权|售后|质保)|制造商.*(?:授权|售后|质保)|开发商.*(?:授权|售后|质保)", name) and material_class != "厂商外部盖章/授权材料":
            add_issue(warnings, "MATERIAL_CLASS_CONFLICT", f"{material_id} {item.get('material_name')} 不应归为 {material_class}")
        if re.search(r"业绩|合同关键页|业绩合同|人员|团队|项目经理|PMP|HCIP|高级工程师|社保|个税|身份证", name) and material_class != "人员/业绩证明材料":
            add_issue(warnings, "MATERIAL_CLASS_CONFLICT", f"{material_id} {item.get('material_name')} 不应归为 {material_class}")


def warn_timeline_quality(timeline_items: list[dict[str, Any]], warnings: list[str]) -> None:
    if not timeline_items:
        return
    type_counts = Counter(item.get("timeline_type") for item in timeline_items)
    empty_value_count = sum(1 for item in timeline_items if not item.get("value"))
    multi_value_items = [
        item for item in timeline_items if len([part for part in str(item.get("value", "")).split("、") if part]) >= 3
    ]
    if len(timeline_items) > 100:
        add_issue(warnings, "TIMELINE_TOO_MANY", f"timeline_matrix 条目过多：{len(timeline_items)}")
    if type_counts.get("acceptance", 0) > 30:
        add_issue(warnings, "TIMELINE_ACCEPTANCE_TOO_MANY", f"验收类周期条目偏多：{type_counts.get('acceptance')}")
    if empty_value_count > 10 and empty_value_count / max(len(timeline_items), 1) > 0.35:
        add_issue(warnings, "TIMELINE_EMPTY_VALUE_RATIO", f"周期条目空 value 偏多：{empty_value_count}/{len(timeline_items)}")
    if len(multi_value_items) > 15:
        add_issue(warnings, "TIMELINE_MULTI_VALUE_TOO_MANY", f"同一条周期混入多个时间值偏多：{len(multi_value_items)}")
    for item in timeline_items:
        meaning = compact(item.get("meaning", ""))
        if item.get("timeline_type") == "delivery_period" and re.search(r"中标服务费|服务费.*交付|银行转账", meaning):
            add_issue(warnings, "TIMELINE_DELIVERY_NOISE", f"{item.get('timeline_id')} 疑似把服务费交付误识别为交货期")


def check_fields(item: dict[str, Any], required_fields: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(field for field in required_fields if field not in item)
    if missing:
        add_issue(errors, "FIELD_MISSING", f"{label} 缺少字段：{', '.join(missing)}")


def validate_content_security(doc: dict[str, Any], label: str, errors: list[str]) -> None:
    security = doc.get("content_security")
    if not isinstance(security, dict):
        add_issue(errors, "CONTENT_SECURITY_MISSING", f"{label} 缺少 content_security")
        return
    if security.get("source_trust") != "untrusted_external":
        add_issue(errors, "CONTENT_TRUST_INVALID", f"{label} source_trust 必须为 untrusted_external")
    if security.get("status") not in {"pass", "needs_manual_review"}:
        add_issue(errors, "CONTENT_SECURITY_STATUS_INVALID", f"{label} content_security.status 无效")
    candidates = security.get("candidates", [])
    if security.get("candidate_count") != len(candidates):
        add_issue(errors, "CONTENT_SECURITY_COUNT_MISMATCH", f"{label} candidate_count 与 candidates 数量不一致")
    policy = security.get("policy", {})
    if policy.get("allow_as_instructions") is not False:
        add_issue(errors, "UNTRUSTED_INSTRUCTIONS_ALLOWED", f"{label} 不得允许外部内容作为指令")
    if policy.get("allow_tool_use_from_content") is not False:
        add_issue(errors, "UNTRUSTED_TOOL_USE_ALLOWED", f"{label} 不得允许外部内容触发工具调用")


def validate_artifacts(out_dir: Path, source: Path | None = None, strict: bool = False) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = out_dir / "parse_manifest.json"
    if not manifest_path.exists():
        add_issue(errors, "MANIFEST_MISSING", f"未找到 {manifest_path}")
        return report(errors, warnings, strict)

    manifest = load_json(manifest_path)
    if manifest.get("source_trust") != "untrusted_external":
        add_issue(errors, "MANIFEST_CONTENT_TRUST_MISSING", "manifest 必须声明 source_trust=untrusted_external")
    manifest_security = manifest.get("content_security", {})
    if manifest_security.get("allow_as_instructions") is not False:
        add_issue(errors, "MANIFEST_SECURITY_POLICY_MISSING", "manifest 必须声明外部内容不得作为指令")
    if source:
        if not source.exists():
            add_issue(errors, "SOURCE_MISSING", f"源文件不存在：{source}")
        else:
            actual_hash = sha256_file(source)
            if manifest.get("source_sha256") != actual_hash:
                add_issue(
                    errors,
                    "SOURCE_HASH_MISMATCH",
                    f"manifest source_sha256 与当前源文件不一致：{manifest.get('source_sha256')} != {actual_hash}",
                )

    for key in EXPECTED_OUTPUTS:
        path = resolve_output(out_dir, manifest, key)
        if not path.exists():
            add_issue(errors, "OUTPUT_MISSING", f"缺少输出 {key}: {path}")
            continue
        manifest_entry = manifest.get("outputs", {}).get(key)
        if manifest_entry and manifest_entry.get("sha256") and path.suffix.lower() != ".xlsx":
            actual = sha256_file(path)
            if manifest_entry["sha256"] != actual:
                add_issue(errors, "OUTPUT_HASH_MISMATCH", f"{key} hash 与 manifest 不一致：{path}")

    required_json_keys = [
        "parse_result",
        "raw_blocks",
        "requirements",
        "fatal_checklist",
        "scoring_matrix",
        "material_checklist_json",
        "fixed_formats_json",
        "timeline_matrix",
    ]
    if any(not resolve_output(out_dir, manifest, key).exists() for key in required_json_keys):
        return report(errors, warnings, strict)

    parse_result = load_json(resolve_output(out_dir, manifest, "parse_result"))
    raw_blocks_doc = load_json(resolve_output(out_dir, manifest, "raw_blocks"))
    requirements_doc = load_json(resolve_output(out_dir, manifest, "requirements"))
    fatal_doc = load_json(resolve_output(out_dir, manifest, "fatal_checklist"))
    scoring_doc = load_json(resolve_output(out_dir, manifest, "scoring_matrix"))
    material_doc = load_json(resolve_output(out_dir, manifest, "material_checklist_json"))
    fixed_doc = load_json(resolve_output(out_dir, manifest, "fixed_formats_json"))
    timeline_doc = load_json(resolve_output(out_dir, manifest, "timeline_matrix"))

    for label, doc in [
        ("parse_result.json", parse_result),
        ("raw_blocks.json", raw_blocks_doc),
        ("requirements.json", requirements_doc),
        ("fatal_checklist.json", fatal_doc),
        ("scoring_matrix.json", scoring_doc),
        ("material_checklist.json", material_doc),
        ("fixed_formats.json", fixed_doc),
        ("timeline_matrix.json", timeline_doc),
    ]:
        validate_content_security(doc, label, errors)

    gate_status = parse_result.get("quality_gate", {}).get("status")
    if gate_status == "blocked":
        add_issue(errors, "QUALITY_GATE_BLOCKED", "quality_gate.status=blocked")
    elif gate_status not in {"pass", "pass_with_soft_review"}:
        add_issue(warnings, "QUALITY_GATE_REVIEW", f"quality_gate.status={gate_status}")

    artifact_gates = parse_result.get("artifact_gates", {})
    if "content_security_gate" not in artifact_gates:
        add_issue(errors, "CONTENT_SECURITY_GATE_MISSING", "artifact_gates 缺少 content_security_gate")
    for gate_name, gate in artifact_gates.items():
        if gate.get("status") == "needs_manual_review":
            add_issue(warnings, "ARTIFACT_GATE_REVIEW", f"{gate_name}=needs_manual_review")

    requirements = requirements_doc.get("requirements", [])
    if not requirements:
        add_issue(errors, "REQUIREMENTS_EMPTY", "requirements.json 没有要求条目")
    for item in requirements:
        check_fields(item, REQUIREMENT_FIELDS, item.get("requirement_id", "requirement"), errors)
        if not item.get("source_refs"):
            add_issue(errors, "SOURCE_REFS_EMPTY", f"{item.get('requirement_id')} 缺少 source_refs")
        if item.get("content_trust") != "untrusted_external":
            add_issue(errors, "REQUIREMENT_CONTENT_TRUST_INVALID", f"{item.get('requirement_id')} 未标记为外部不可信内容")

    security = parse_result.get("content_security", {})
    security_status = security.get("status")
    security_candidates = security.get("candidates", [])
    security_reviews = [
        item
        for item in parse_result.get("manual_review_queue", [])
        if item.get("review_type") == "prompt_injection_candidate"
    ]
    if security_status == "needs_manual_review":
        if gate_status != "blocked":
            add_issue(errors, "CONTENT_SECURITY_NOT_BLOCKING", "疑似提示注入存在时 quality_gate 必须 blocked")
        if len(security_reviews) != len(security_candidates):
            add_issue(errors, "CONTENT_SECURITY_REVIEW_MISMATCH", "疑似提示注入候选必须逐条进入人工复核队列")
    elif security_candidates:
        add_issue(errors, "CONTENT_SECURITY_STATUS_MISMATCH", "存在候选但 content_security.status 未阻断")

    quarantined_blocks = [
        block
        for block in raw_blocks_doc.get("blocks", [])
        if block.get("security_status") == "quarantined_prompt_injection_candidate"
    ]
    if len(quarantined_blocks) != len(security_candidates):
        add_issue(errors, "QUARANTINE_COUNT_MISMATCH", "隔离原文块数量与安全候选数量不一致")

    scoring_items = scoring_doc.get("items", [])
    if not scoring_items:
        add_issue(warnings, "SCORING_EMPTY", "scoring_matrix.items 为空，需人工确认招标是否无评分表")
    if scoring_items and scoring_doc.get("total_score") is None and scoring_doc.get("known_total_score") is None:
        add_issue(warnings, "SCORING_TOTAL_SCORE_MISSING", "评分矩阵缺少 total_score/known_total_score")
    missing_score = [item.get("scoring_id", "") for item in scoring_items if item.get("max_score") in {None, ""}]
    if missing_score:
        add_issue(warnings, "SCORING_SCORE_MISSING", f"评分项分值缺失：{', '.join(missing_score[:10])}")

    material_items = material_doc.get("items", [])
    if not material_items:
        add_issue(warnings, "MATERIAL_EMPTY", "material_checklist.json 没有资料项")
    for item in material_items:
        check_fields(item, MATERIAL_FIELDS, item.get("material_id", "material"), errors)
        if not (item.get("source_requirement_id") or item.get("scoring_id")):
            add_issue(warnings, "MATERIAL_SOURCE_ID_MISSING", f"{item.get('material_id')} 缺少 requirement_id/scoring_id")
    warn_material_quality(material_items, warnings)

    fixed_items = fixed_doc.get("items", [])
    if not fixed_items:
        add_issue(warnings, "FIXED_FORMAT_EMPTY", "fixed_formats.json 没有固定格式摘录")
    for item in fixed_items:
        format_type = item.get("format_type")
        if format_type not in FIXED_FORMAT_TYPES:
            add_issue(errors, "FIXED_FORMAT_TYPE_INVALID", f"{item.get('fixed_format_id')} format_type={format_type}")
        text = f"{item.get('title', '')} {item.get('text', '')} {item.get('header_text', '')}"
        if "格式自拟" in text and format_type == "fixed_template":
            add_issue(errors, "SELF_DEFINED_AS_FIXED", f"{item.get('fixed_format_id')} 将格式自拟误标为 fixed_template")
        if not item.get("source_refs"):
            add_issue(errors, "FIXED_SOURCE_REFS_EMPTY", f"{item.get('fixed_format_id')} 缺少 source_refs")

    timeline_items = timeline_doc.get("items", [])
    if not timeline_items:
        add_issue(warnings, "TIMELINE_EMPTY", "timeline_matrix.json 没有周期条目")
    for item in timeline_items:
        check_fields(item, TIMELINE_FIELDS, item.get("timeline_id", "timeline"), errors)
        if not item.get("source_refs"):
            add_issue(errors, "TIMELINE_SOURCE_REFS_EMPTY", f"{item.get('timeline_id')} 缺少 source_refs")
    warn_timeline_quality(timeline_items, warnings)
    timeline_types = {item.get("timeline_type") for item in timeline_items}
    if {"construction_period", "delivery_period"} <= timeline_types and not timeline_doc.get("warnings"):
        add_issue(warnings, "TIMELINE_WARNING_MISSING", "同时存在建设周期和交货期，但 timeline_matrix.warnings 为空")

    return report(errors, warnings, strict)


def report(errors: list[str], warnings: list[str], strict: bool) -> int:
    if warnings and strict:
        errors.extend(f"STRICT_{warning}" for warning in warnings)
        warnings = []
    print("parse artifact validation")
    print(f"  errors: {len(errors)}")
    print(f"  warnings: {len(warnings)}")
    if errors:
        print("ERRORS:")
        for issue in errors:
            print(f"  - {issue}")
    if warnings:
        print("WARNINGS:")
        for issue in warnings:
            print(f"  - {issue}")
    if errors:
        return 1
    print("  status: pass")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验 tender-document-parser 解析产物是否满足产物契约。")
    parser.add_argument("--out-dir", required=True, type=Path, help="解析产物目录")
    parser.add_argument("--source", type=Path, default=None, help="可选：源招标文件，用于校验 source_sha256")
    parser.add_argument("--strict", action="store_true", help="将 warning 也视为失败")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    return validate_artifacts(args.out_dir.resolve(), args.source.resolve() if args.source else None, args.strict)


if __name__ == "__main__":
    raise SystemExit(main())
