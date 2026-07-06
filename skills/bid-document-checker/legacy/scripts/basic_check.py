#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投标文件基础检查脚本（legacy）

本脚本为 v2.x 历史脚本归档，只作追溯参考，不作为
bid-document-checker v3.0.0 当前执行入口。
"""

import re
import sys
from datetime import datetime

def check_basic_format(text):
    """检查基本格式"""
    issues = []

    # 检查法定代表人签字
    if not re.search(r'法定代表人[（\(]签字[）\)]|法定代表人.*签章', text):
        issues.append("缺少法定代表人签字或签章")

    # 检查投标函
    if '投标函' not in text:
        issues.append("缺少投标函")

    # 检查报价
    price_matches = re.findall(r'[¥￥]\s*[\d,\.]+|\d+[\d,\.]*\s*元', text)
    if not price_matches:
        issues.append("未找到报价信息")

    # 检查工期
    if not re.search(r'工期\s*[\d一二三四五六七八九十]+', text):
        issues.append("未明确工期")

    return issues

def check_content_completeness(text, required_sections):
    """检查内容完整性"""
    missing = []

    for section in required_sections:
        if section not in text:
            missing.append(section)

    return missing

def extract_key_info(text):
    """提取关键信息"""
    info = {}

    # 提取项目名称
    project_match = re.search(r'项目名称[：:]\s*(.+)', text)
    if project_match:
        info['project_name'] = project_match.group(1).strip()

    # 提取投标总价
    price_match = re.search(r'投标总价[：:]\s*[¥￥]?\s*([\d,\.]+)', text)
    if price_match:
        info['total_price'] = price_match.group(1)

    # 提取工期
    period_match = re.search(r'工期[：:]\s*([\d一二三四五六七八九十]+)\s*[天日历]', text)
    if period_match:
        info['period'] = period_match.group(1)

    # 提取投标有效期
    validity_match = re.search(r'投标有效期[：:]\s*([\d一二三四五六七八九十]+)\s*[天日历]', text)
    if validity_match:
        info['validity'] = validity_match.group(1)

    return info

def generate_report(bid_file, issues, missing_sections, key_info):
    """生成检查报告"""
    report = []
    report.append("# 投标文件基础检查报告")
    report.append(f"## 基本信息")
    report.append(f"- 检查文件：{bid_file}")
    report.append(f"- 检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"- 检查工具：basic_check.py")
    report.append("")

    report.append("## 关键信息提取")
    if key_info:
        for key, value in key_info.items():
            report.append(f"- {key}: {value}")
    else:
        report.append("- 未提取到关键信息")
    report.append("")

    report.append("## 格式检查结果")
    if issues:
        report.append("### 发现问题：")
        for i, issue in enumerate(issues, 1):
            report.append(f"{i}. {issue}")
    else:
        report.append("✅ 未发现格式问题")
    report.append("")

    report.append("## 内容完整性检查")
    if missing_sections:
        report.append("### 缺少的章节：")
        for i, section in enumerate(missing_sections, 1):
            report.append(f"{i}. {section}")
    else:
        report.append("✅ 内容完整")
    report.append("")

    report.append("## 检查结论")
    if not issues and not missing_sections:
        report.append("✅ 通过基础检查")
        report.append("建议：可以进行详细检查")
    else:
        report.append("⚠️ 未通过基础检查")
        report.append("建议：修改发现的问题后再提交")

    return "\n".join(report)

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法：python basic_check.py <投标文件文本>")
        print("示例：python basic_check.py \"投标文件内容...\"")
        sys.exit(1)

    # 读取投标文件内容（实际使用时应从文件读取）
    bid_text = sys.argv[1]

    # 定义必需章节
    required_sections = [
        '投标函',
        '法定代表人身份证明',
        '授权委托书',
        '投标保证金',
        '技术方案',
        '报价表'
    ]

    print("开始检查投标文件...")

    # 执行检查
    issues = check_basic_format(bid_text)
    missing = check_content_completeness(bid_text, required_sections)
    key_info = extract_key_info(bid_text)

    # 生成报告
    report = generate_report("投标文件.txt", issues, missing, key_info)
    print(report)

    # 保存报告到文件
    with open('检查报告.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n报告已保存到：检查报告.md")

if __name__ == '__main__':
    main()
