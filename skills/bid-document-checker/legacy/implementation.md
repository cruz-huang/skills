# 技术实现指南（v2.0，legacy）

> 本文件为 v2.x 历史实现说明归档，只作追溯参考，不作为 `bid-document-checker v3.0.0` 当前执行依据。

## 三层检查架构实现

### 第一层：招标文件解析
### 第二层：投标文件响应检查
### 第三层：逻辑格式规范检查

---

# 第一层：招标文件解析实现

## 1.1 基础PDF解析

```python
import pdfplumber

def extract_pdf_content(pdf_path, max_pages=None):
    """提取PDF文本内容"""
    content = {}
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages

        for i, page in enumerate(pages):
            text = page.extract_text()
            if text:
                content[i + 1] = text

    return content, total

def extract_tables_from_pdf(pdf_path):
    """提取PDF表格"""
    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if table:
                    all_tables.append({
                        'page': i + 1,
                        'table': table
                    })
    return all_tables
```

## 1.2 招标项目信息提取

```python
import re

def extract_project_info(tender_text):
    """提取项目基本信息"""
    info = {}

    # 项目名称
    match = re.search(r'项目名称[：:]\s*(.+)', tender_text)
    if match:
        info['name'] = match.group(1).strip()

    # 采购单位
    match = re.search(r'(采购|招标|询价)单位[：:]\s*(.+)', tender_text)
    if match:
        info['purchaser'] = match.group(2).strip()

    # 预算/上限价
    match = re.search(r'上限价[：:]\s*¥?\s*([\d,\.]+)', tender_text)
    if match:
        info['budget'] = float(match.group(1).replace(',', ''))

    # 截止时间
    match = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', tender_text[:500])
    if match:
        info['deadline'] = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    return info
```

## 1.3 资质要求结构化提取

```python
def extract_qualification_requirements(tender_text):
    """提取资质要求（结构化）"""
    requirements = []

    # 匹配资质要求段落
    # 格式：（一）...（提供...）

    patterns = [
        (r'（一）\s*(.+?)(?=（二）|$)', '法人资格'),
        (r'（二）\s*(.+?)(?=（三）|$)', '授权关系'),
        (r'（三）\s*(.+?)(?=（四）|$)', '独立性'),
        (r'（四）\s*(.+?)(?=（五）|$)', '信用记录'),
        (r'（五）\s*(.+?)(?=$)', '联合体'),
    ]

    for pattern, req_type in patterns:
        match = re.search(pattern, tender_text, re.DOTALL)
        if match:
            text = match.group(1).strip()

            # 提取证明材料要求
            proof_match = re.search(r'（提供(.+?)）', text)
            proof = proof_match.group(1) if proof_match else ''

            # 判断是否需要公章
            needs_seal = '加盖公章' in text

            requirements.append({
                'type': req_type,
                'description': re.sub(r'\s+', ' ', text),
                'proof_required': proof,
                'needs_seal': needs_seal
            })

    return requirements
```

## 1.4 技术要求提取

```python
def extract_technical_requirements(tender_text):
    """提取技术要求（功能模块清单）"""
    requirements = []

    # 查找建设需求章节
    section_match = re.search(
        r'建设需求(.+?)(?=（[一二三四]）|$)',
        tender_text,
        re.DOTALL
    )

    if not section_match:
        return requirements

    section = section_match.group(1)

    # 提取功能模块
    # 通常格式：序号 一级功能 二级功能 需求描述

    # 使用表格解析（如果表格可用）
    # 简化版：使用正则匹配

    lines = section.split('\n')
    current_module = None

    for line in lines:
        # 一级模块匹配
       一级_match = re.match(r'^\s*数字水管家\s+(\S+)\s+(\S+)\s*$', line)
        if 一级_match:
            current_module = 一级_match.group(1)
            continue

        # 二级模块+需求描述
        二级_match = re.match(r'^\s*(\S+)\s*：(.*)$', line)
        if 二级_match and current_module:
            requirements.append({
                'module': current_module,
                'feature': 二级_match.group(1),
                'description': 二级_match.group(2).strip()[:200]
            })

    return requirements
```

## 1.5 实施要求提取

```python
def extract_implementation_requirements(tender_text):
    """提取实施要求（团队、现场等）"""
    requirements = {}

    # 团队组织要求
    match = re.search(
        r'团队组织要求[：:](.+?)(?=[\n\n四、|五、|六、|$])',
        tender_text,
        re.DOTALL
    )
    if match:
        text = match.group(1).strip()
        requirements['team'] = {
            'description': text,
            'has_org_structure': '组织机构' in text,
            'has_personnel': '人员' in text,
            'has_on_site': '现场' in text or '驻场' in text
        }

    # 现场对接要求
    match = re.search(r'现场对接[：:]?\s*(\d+)\s*名', tender_text)
    if match:
        requirements['on_site_count'] = int(match.group(1))

    # 培训要求
    match = re.search(r'培训要求[：:](.+?)(?=[\n\n五、|六、|$])', tender_text, re.DOTALL)
    if match:
        requirements['training'] = match.group(1).strip()[:200]

    # 交付文档要求
    match = re.search(r'交付文档要求[：:](.+?)(?=[\n\n六、|$])', tender_text, re.DOTALL)
    if match:
        requirements['documentation'] = match.group(1).strip()[:200]

    return requirements
```

## 1.6 废标条款提取

```python
def extract_rejection_clauses(tender_text):
    """提取废标条款"""
    clauses = []

    # 定义废标关键词模式
    patterns = [
        (r'废标', '法定废标/招标文件明确'),
        (r'不予接收', '招标文件明确'),
        (r'不予退还.*保证金', '招标文件明确'),
        (r'取消.*中标资格', '招标文件明确'),
        (r'列入.*黑名单', '招标文件明确'),
        (r'联合体.*不接受', '招标文件明确'),
    ]

    for pattern, clause_type in patterns:
        matches = re.finditer(pattern, tender_text)
        for match in matches:
            # 获取上下文
            start = max(0, match.start() - 50)
            end = min(len(tender_text), match.end() + 50)
            context = tender_text[start:end]

            clauses.append({
                'keyword': match.group(0),
                'type': clause_type,
                'context': context
            })

    return clauses
```

## 1.7 第一层输出：结构化要求清单

```python
def parse_tender_document(tender_text):
    """解析招标文件，生成结构化要求清单"""

    return {
        'project_info': extract_project_info(tender_text),
        'qualification_requirements': extract_qualification_requirements(tender_text),
        'technical_requirements': extract_technical_requirements(tender_text),
        'commercial_requirements': {
            'budget': extract_budget(tender_text),
            'period': extract_period(tender_text),
            'warranty': extract_warranty(tender_text),
        },
        'implementation_requirements': extract_implementation_requirements(tender_text),
        'rejection_clauses': extract_rejection_clauses(tender_text),
        'document_structure_required': extract_document_structure(tender_text),
    }
```

---

# 第二层：投标文件响应检查实现

## 2.1 资质要求响应检查

```python
def check_qualification_response(bid_text, tender_requirements):
    """检查资质要求响应"""
    results = []

    for req in tender_requirements:
        req_type = req['type']

        # 检查响应声明
        has_response = False
        response_patterns = [
            f"{req_type}.*完全满足",
            f"我司.*满足.*{req_type}",
            f"{req_type}.*满足",
        ]

        for pattern in response_patterns:
            if re.search(pattern, bid_text):
                has_response = True
                break

        # 检查证明材料
        has_proof = req['proof_required'] in bid_text

        # 检查公章要求
        needs_seal = req.get('needs_seal', False)
        has_seal = '加盖公章' in bid_text or '（盖单位章）' in bid_text

        results.append({
            'type': req_type,
            'has_response': has_response,
            'has_proof': has_proof,
            'needs_seal': needs_seal,
            'has_seal': has_seal,
            'status': 'ok' if has_response and has_proof else 'missing'
        })

    return results
```

## 2.2 技术要求响应检查

```python
def check_technical_response(bid_text, tender_requirements):
    """检查技术要求响应"""
    results = []

    for req in tender_requirements:
        feature = req['feature']

        # 在技术方案中查找对应响应
        found = False
        location = None

        # 精确匹配
        if feature in bid_text:
            found = True
            location = '全文'

        # 模糊匹配
        if not found:
            for keyword in feature.split():
                if len(keyword) > 2 and keyword in bid_text:
                    found = True
                    location = f'关键词"{keyword}"'
                    break

        results.append({
            'feature': feature,
            'module': req['module'],
            'found': found,
            'location': location,
            'status': 'ok' if found else 'missing'
        })

    return results
```

## 2.3 团队配置响应检查（重点）

```python
def check_team_response(bid_text, tender_requirements):
    """检查团队配置响应"""
    issues = []

    # 团队关键词统计
    team_keywords = {
        '团队': '团队介绍',
        '项目经理': '项目经理/负责人',
        '项目负责人': '项目负责人',
        '技术负责人': '技术负责人',
        '项目成员': '项目成员',
        '组织机构': '组织机构设置',
        '人员配置': '人员配置方案',
        '现场对接': '现场对接安排',
        '驻场': '驻场安排',
    }

    found_keywords = {}
    missing_keywords = []

    for keyword, desc in team_keywords.items():
        if keyword in bid_text:
            found_keywords[keyword] = bid_text.count(keyword)
        else:
            missing_keywords.append(desc)

    # 判断是否满足招标要求
    impl_req = tender_requirements.get('implementation_requirements', {})
    team_req = impl_req.get('team', {})

    if team_req.get('has_org_structure') and '组织机构' not in bid_text:
        issues.append("缺少：项目管理组织机构设置方案")

    if team_req.get('has_on_site') and '现场' not in bid_text and '驻场' not in bid_text:
        issues.append("缺少：现场对接人员安排")

    # 关键人员检查
    if '项目经理' not in bid_text and '项目负责人' not in bid_text:
        issues.append("缺少：项目经理/项目负责人介绍")

    if '技术负责人' not in bid_text:
        issues.append("缺少：技术负责人介绍")

    # 简历检查
    resume_keywords = ['简历', '履历', '专业背景', '资质证书']
    has_resume = any(kw in bid_text for kw in resume_keywords)
    if not has_resume:
        issues.append("缺少：团队成员简历或资质证明")

    return {
        'found_keywords': found_keywords,
        'missing_keywords': missing_keywords,
        'issues': issues,
        'status': 'missing' if issues else 'ok'
    }
```

## 2.4 商务要求响应检查

```python
def check_commercial_response(bid_text, tender_requirements):
    """检查商务要求响应"""
    results = []
    issues = []

    comm_req = tender_requirements.get('commercial_requirements', {})

    # 报价检查
    budget = comm_req.get('budget', 0)
    if budget > 0:
        price_match = re.search(r'合计.*?(\d{3,7})', bid_text)
        if price_match:
            bid_price = float(price_match.group(1))
            if bid_price > budget:
                issues.append(f"报价{bid_price}超过上限{budget}")
            else:
                results.append({
                    'item': '报价',
                    'bid_value': bid_price,
                    'limit': budget,
                    'status': 'ok'
                })
        else:
            issues.append("未找到明确的报价")

    # 工期检查
    period = comm_req.get('period', 0)
    if period > 0:
        period_match = re.search(r'工期[：:]\s*(\d+)\s*天', bid_text)
        if period_match:
            bid_period = int(period_match.group(1))
            if bid_period > period:
                issues.append(f"工期{bid_period}天超过要求{period}天")
            else:
                results.append({
                    'item': '工期',
                    'bid_value': bid_period,
                    'limit': period,
                    'status': 'ok'
                })

    return {
        'results': results,
        'issues': issues,
        'status': 'missing' if issues else 'ok'
    }
```

## 2.5 废标条款规避检查

```python
def check_rejection_risks(bid_text, tender_requirements):
    """检查废标风险"""
    risks = []

    # 1. 法定代表人签字
    if '法定代表人或其委托代理人： （签字或盖章）' in bid_text:
        risks.append({
            'type': '形式要件',
            'item': '法定代表人签字',
            'severity': 'high',
            'description': '法定代表人签字处空白'
        })

    # 2. 投标有效期
    if '投标有效期' not in bid_text:
        risks.append({
            'type': '形式要件',
            'item': '投标有效期',
            'severity': 'medium',
            'description': '未明确投标有效期'
        })

    # 3. 投标保证金
    tender_rejection = tender_requirements.get('rejection_clauses', [])
    requires_bond = any('保证金' in c.get('context', '') for c in tender_rejection)
    if requires_bond and '保证金' not in bid_text:
        risks.append({
            'type': '形式要件',
            'item': '投标保证金',
            'severity': 'high',
            'description': '招标文件要求保证金但未提及'
        })

    # 4. 联合体
    if tender_requirements.get('no_consortium', False):
        if '联合体' in bid_text:
            risks.append({
                'type': '禁止项',
                'item': '联合体',
                'severity': 'high',
                'description': '招标文件不接受联合体'
            })

    return {
        'risks': risks,
        'has_high_risk': any(r['severity'] == 'high' for r in risks),
        'status': 'danger' if any(r['severity'] == 'high' for r in risks) else 'warning'
    }
```

## 2.6 第二层输出：响应对照表

```python
def check_bid_response(bid_text, tender_requirements):
    """检查投标文件响应完整性"""

    return {
        'qualification': check_qualification_response(bid_text, tender_requirements),
        'technical': check_technical_response(bid_text, tender_requirements),
        'team': check_team_response(bid_text, tender_requirements),
        'commercial': check_commercial_response(bid_text, tender_requirements),
        'rejection_risks': check_rejection_risks(bid_text, tender_requirements),
    }
```

---

# 第三层：逻辑格式规范检查实现

## 3.1 内部一致性检查

```python
def check_internal_consistency(bid_text):
    """检查内部一致性"""
    issues = []

    # 项目名称一致性
    names = re.findall(r'项目名称[：:]\s*(.+)', bid_text)
    if len(set(names)) > 1:
        issues.append(f"项目名称不一致: {set(names)}")

    # 报价数字一致性
    prices = re.findall(r'[¥￥]?\s*([\d,]+)\s*元', bid_text)
    unique_prices = set(p.replace(',', '') for p in prices)
    # 如果有多个不同价格，可能存在问题

    # 章节标题一致性
    # 目录中的章节与正文一致

    return issues
```

## 3.2 计算准确性检查

```python
def check_calculation_accuracy(bid_text):
    """检查计算准确性"""
    issues = []

    # 提取报价表
    price_section = re.search(
        r'项目报价(.+?)(?=（三）|$)',
        bid_text,
        re.DOTALL
    )

    if price_section:
        section = price_section.group(1)

        # 提取所有"数量 单价 小计"行
        lines = re.findall(r'(\d+)\s+(\d+)\s+(\d+)', section)

        for work, unit_price, subtotal in lines:
            work = int(work)
            unit_price = int(unit_price)
            subtotal = int(subtotal)

            expected = work * unit_price
            if expected != subtotal:
                issues.append(
                    f"计算错误: {work} × {unit_price} = {expected}, 但显示{subtotal}"
                )

    return issues
```

## 3.3 格式规范性检查

```python
def check_format_compliance(bid_text):
    """检查格式规范性"""
    issues = []

    # 页码连续性
    page_numbers = re.findall(r'第\s*(\d+)\s*页', bid_text)
    if page_numbers:
        nums = [int(p) for p in page_numbers]
        expected = list(range(1, len(nums) + 1))
        if nums != expected:
            issues.append(f"页码不连续: 期望{expected[:5]}..., 实际{nums[:5]}...")

    # 签字盖章
    if '（签字或盖章）' in bid_text and '（签字或盖章）' in bid_text:
        # 检查是否有实际的签字
        signature_area = re.search(
            r'法定代表人.*?(?=投标人名称|供应商名称|单位名称|\n\n)',
            bid_text,
            re.DOTALL
        )
        if signature_area and len(signature_area.group(0).strip()) < 50:
            issues.append("法定代表人签字处可能为空")

    return issues
```

## 3.4 固定格式一致性检查

```python
def check_fixed_format_compliance(bid_text, tender_templates):
    """检查招标固定格式是否被复刻，而不是被自由改写"""
    issues = []

    if not tender_templates:
        issues.append({
            'type': 'fixed_format',
            'severity': 'review',
            'message': '未见招标固定格式模板，按招标文字要求人工复核'
        })
        return issues

    for tpl in tender_templates:
        title = tpl.get('title')
        required_fields = tpl.get('fields', [])
        required_order = tpl.get('field_order', required_fields)

        section = locate_bid_section_by_title(bid_text, title)
        if not section:
            issues.append({'type': 'fixed_format', 'severity': 'high', 'message': f'缺少固定格式材料：{title}'})
            continue

        missing_fields = [field for field in required_fields if field not in section]
        if missing_fields:
            issues.append({'type': 'fixed_format', 'severity': 'high', 'message': f'{title} 缺少字段：{missing_fields}'})

        if not is_order_preserved(section, required_order):
            issues.append({'type': 'fixed_format', 'severity': 'high', 'message': f'{title} 字段顺序与招标模板不一致'})

        if looks_like_free_text_rewrite(section, required_fields):
            issues.append({'type': 'fixed_format', 'severity': 'high', 'message': f'{title} 疑似被改写为自由文本'})

        if has_unclosed_placeholders(section):
            issues.append({'type': 'fixed_format', 'severity': 'high', 'message': f'{title} 存在待定/占位符/空白未闭环'})

    return issues
```

## 3.5 高风险字段唯一出处检查

```python
def check_high_risk_field_consistency(bid_text, confirmed_values=None):
    """检查报价、税率、BOM、关键配置、交货期等字段是否全文一致"""
    issues = []
    field_patterns = {
        'total_price': [r'投标总价[：:]\s*[¥￥]?\s*([\d,\.]+)', r'总报价[：:]\s*[¥￥]?\s*([\d,\.]+)'],
        'tax_rate': [r'税率[：:]\s*([\d\.]+%)'],
        'delivery_period': [r'交货期[：:]\s*([^\n，。；;]+)'],
        'warranty': [r'质保期[：:]\s*([^\n，。；;]+)'],
    }

    extracted = extract_field_values(bid_text, field_patterns)
    for field, values in extracted.items():
        if len(set(values)) > 1:
            issues.append({'type': 'unique_source', 'severity': 'high', 'message': f'{field} 多处取值不一致：{values}'})

        if confirmed_values and field in confirmed_values and set(values) - {confirmed_values[field]}:
            issues.append({'type': 'unique_source', 'severity': 'high', 'message': f'{field} 与确认口径不一致'})

    return issues
```

## 3.6 内部块与交付边界检查

```python
def check_internal_block_leakage(bid_text, file_path):
    """检查内部编制信息是否进入正式件"""
    issues = []
    markers = ['资料引用', '检查点', '未闭环事项', '待确认', 'TODO']
    leaked = [m for m in markers if m in bid_text]
    if leaked:
        issues.append({'type': 'internal_marker', 'severity': 'high', 'message': f'正式文件疑似残留内部编制标记：{leaked}'})

    if '/02-工作稿/' in file_path and ('最终' in file_path or '交付' in file_path):
        issues.append({'type': 'artifact_boundary', 'severity': 'high', 'message': '过程稿路径中出现最终/交付命名，需确认是否误作最终版'})

    return issues
```

## 3.7 第三层输出

```python
def check_format_and_logic(bid_text, tender_templates=None, confirmed_values=None, file_path=''):
    """第三层检查：格式和逻辑"""

    return {
        'consistency': check_internal_consistency(bid_text),
        'calculation': check_calculation_accuracy(bid_text),
        'format': check_format_compliance(bid_text),
        'fixed_format': check_fixed_format_compliance(bid_text, tender_templates),
        'unique_source': check_high_risk_field_consistency(bid_text, confirmed_values),
        'internal_boundary': check_internal_block_leakage(bid_text, file_path),
    }
```

---

# 整合：完整检查流程

```python
def full_bid_check(tender_pdf_path, bid_pdf_path):
    """完整投标文件检查流程"""

    # 第一层：解析招标文件
    tender_text = extract_pdf_text(tender_pdf_path)
    tender_requirements = parse_tender_document(tender_text)

    # 第二层：检查投标文件响应
    bid_text = extract_pdf_text(bid_pdf_path)
    bid_response = check_bid_response(bid_text, tender_requirements)

    # 第三层：格式规范检查
    format_check = check_format_and_logic(bid_text)

    # 生成报告
    return {
        'tender_requirements': tender_requirements,
        'bid_response': bid_response,
        'format_check': format_check,
    }
```

---

# 报告生成

```python
def generate_report(check_results):
    """生成检查报告"""

    report = []
    report.append("# 投标文件检查报告")
    report.append("")
    report.append("## 一、招标文件解析结果")
    report.append("...")
    report.append("## 二、投标文件响应检查")
    report.append("...")
    report.append("## 三、问题汇总")
    report.append("...")

    return "\n".join(report)
```
