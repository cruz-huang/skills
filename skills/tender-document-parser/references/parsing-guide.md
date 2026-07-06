# 招标文件解析实现指南

## 1. PDF 文本与表格提取

```python
import pdfplumber
import re
import json
from typing import Optional

def extract_pdf_content(pdf_path: str, max_pages: Optional[int] = None) -> tuple[dict, int]:
    """提取PDF文本内容，返回 {页号: 文本} 和总页数"""
    content = {}
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        pages = pdf.pages[:max_pages] if max_pages else pdf.pages
        for i, page in enumerate(pages):
            text = page.extract_text()
            if text:
                content[i + 1] = text
    return content, total


def extract_tables_from_pdf(pdf_path: str) -> list[dict]:
    """提取PDF中的所有表格，返回 [{page, table}, ...]"""
    all_tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            for table in tables:
                if table:
                    all_tables.append({'page': i + 1, 'table': table})
    return all_tables


def merge_pdf_text(content: dict) -> str:
    """合并所有页面文本为单一字符串"""
    return '\n'.join(content.values())
```

## 2. 项目基本信息提取

```python
def extract_project_info(text: str) -> dict:
    """提取项目基本信息"""
    info = {}

    # 项目名称
    m = re.search(r'项目名称[：:]\s*(.+)', text)
    if m:
        info['name'] = m.group(1).strip()

    # 项目编号
    m = re.search(r'(项目编号|招标编号|采购编号)[：:]\s*(.+)', text)
    if m:
        info['project_id'] = m.group(2).strip()

    # 采购/招标单位
    m = re.search(r'(采购单位|招标单位|招标人|询价单位)[：:]\s*(.+)', text)
    if m:
        info['purchaser'] = m.group(2).strip()

    # 采购代理机构
    m = re.search(r'(采购代理机构|招标代理机构)[：:]\s*(.+)', text)
    if m:
        info['agency'] = m.group(2).strip()

    # 预算/上限价/控制价
    for pattern in [r'上限价[：:]\s*¥?\s*([\d,\.]+)',
                    r'预算金额[：:]\s*¥?\s*([\d,\.]+)',
                    r'最高限价[：:]\s*¥?\s*([\d,\.]+)',
                    r'采购预算[：:]\s*¥?\s*([\d,\.]+)']:
        m = re.search(pattern, text)
        if m:
            info['budget'] = float(m.group(1).replace(',', ''))
            break

    # 投标截止时间
    m = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', text[:1000])
    if m:
        info['deadline'] = f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"

    # 开标时间
    m = re.search(r'开标时间[：:]\s*(.+?)(?:\n|$)', text)
    if m:
        info['bid_opening_time'] = m.group(1).strip()

    # 投标有效期
    m = re.search(r'投标有效期[：:]\s*(\d+)\s*(天|日历天|日)', text)
    if m:
        info['validity_days'] = int(m.group(1))

    # 是否接受联合体
    if re.search(r'不接受.*联合体|联合体.*不接受|不允许.*联合体', text):
        info['consortium'] = False
    elif re.search(r'接受.*联合体|联合体.*接受|允许.*联合体', text):
        info['consortium'] = True

    # 投标保证金
    m = re.search(r'投标保证金[：:]\s*¥?\s*([\d,\.]+)', text)
    if m:
        info['bid_bond'] = float(m.group(1).replace(',', ''))

    # 资金来源
    m = re.search(r'资金来源[：:]\s*(.+?)(?:\n|$)', text)
    if m:
        info['funding_source'] = m.group(1).strip()

    return info
```

## 3. 废标条款提取

```python
def extract_rejection_clauses(text: str) -> list[dict]:
    """提取废标/否决条款"""
    clauses = []
    patterns = [
        (r'废标', '废标条款'),
        (r'不予接收', '投标不予接收'),
        (r'取消.*中标资格', '取消中标资格'),
        (r'列入.*黑名单', '列入黑名单'),
        (r'否决.*投标', '否决投标'),
        (r'作.*无效.*处理', '作无效处理'),
        (r'不予退还.*保证金', '保证金不予退还'),
        (r'★', '星号实质性条款'),
        (r'实质性要求', '实质性要求'),
        (r'必须提供', '必须提供'),
        (r'不得偏离', '不得偏离'),
        (r'禁止', '禁止项'),
        (r'不接受', '不接受'),
    ]

    seen = set()
    for pattern, clause_type in patterns:
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - 80)
            end = min(len(text), m.end() + 80)
            context = text[start:end].replace('\n', ' ').strip()
            key = context[:60]
            if key not in seen:
                seen.add(key)
                clauses.append({
                    'keyword': m.group(0),
                    'type': clause_type,
                    'context': context,
                    'position': m.start()
                })

    clauses.sort(key=lambda x: x['position'])
    return clauses
```

## 4. 资质要求提取

```python
def extract_qualification_requirements(text: str) -> list[dict]:
    """提取资质要求"""
    requirements = []

    # 按常见中文序号分段
    section_patterns = [
        (r'（一）\s*(.+?)(?=（二）)', '法人/主体资格'),
        (r'（二）\s*(.+?)(?=（三）)', '授权关系'),
        (r'（三）\s*(.+?)(?=（四）)', '独立性/关联关系'),
        (r'（四）\s*(.+?)(?=（五）)', '信用记录'),
        (r'（五）\s*(.+?)(?=（六）)', '财务状况'),
        (r'（六）\s*(.+?)(?=（七）)', '业绩要求'),
        (r'（七）\s*(.+?)(?=（八）)', '人员要求'),
    ]

    for pattern, req_type in section_patterns:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            content = m.group(1).strip()
            # 提取证明材料
            proof_matches = re.findall(r'[（(]提供(.+?)[）)]', content)
            # 判断是否需要公章
            needs_seal = bool(re.search(r'加盖公章|盖单位章', content))
            requirements.append({
                'type': req_type,
                'description': re.sub(r'\s+', ' ', content),
                'proof_materials': proof_matches,
                'requires_seal': needs_seal,
            })

    # 额外搜索：特定资质证书
    cert_patterns = {
        'ISO9001': r'ISO\s*9001',
        'ISO14001': r'ISO\s*14001',
        'ISO27001': r'ISO\s*27001',
        'CMMI': r'CMMI[-\s]*[345]级',
        '系统集成资质': r'系统集成[^，。\n]*资质',
        '安全生产许可证': r'安全生产许可证',
    }
    for cert_name, cert_pattern in cert_patterns.items():
        m = re.search(cert_pattern, text)
        if m:
            requirements.append({
                'type': '特定资质',
                'cert_name': cert_name,
                'description': m.group(0).strip(),
                'proof_materials': [f'{cert_name}证书'],
                'requires_seal': True,
            })

    return requirements
```

## 5. 评分标准提取

```python
def extract_scoring_criteria(text: str) -> dict:
    """提取评分标准"""
    scoring = {
        'weights': {},
        'technical_items': [],
        'commercial_items': [],
        'price_scoring': {},
        'bonus_items': [],
    }

    # 评分权重
    for scope, label in [('技术', 'technical'), ('商务', 'commercial'), ('价格', 'price')]:
        m = re.search(rf'{scope}[分评].*?(\d+)\s*[分%]', text)
        if m:
            scoring['weights'][label] = int(m.group(1))

    # 评分细则：按表格或段落提取
    # 常见模式：评分项名称 + 分值 + 评分标准
    item_pattern = re.compile(
        r'(\d+)\s*[、．.]\s*(.+?)\s*[（(]\s*(\d+)\s*分[）)]\s*(.+?)(?=\d+\s*[、．.]|\n\n|$)',
        re.DOTALL
    )
    for m in item_pattern.finditer(text):
        item = {
            'name': m.group(2).strip(),
            'max_score': int(m.group(3)),
            'criteria': m.group(4).strip()[:300],
        }
        # 判断属于技术还是商务
        if any(kw in item['name'] + item['criteria']
               for kw in ['技术', '方案', '架构', '实施', '人员', '项目经理']):
            scoring['technical_items'].append(item)
        else:
            scoring['commercial_items'].append(item)

    # 加分项
    bonus_keywords = ['加分', '额外.*分', '奖励.*分', '优先', '优惠']
    for kw in bonus_keywords:
        for m in re.finditer(rf'.{{0,40}}{kw}.{{0,80}}', text):
            scoring['bonus_items'].append(m.group(0).strip())

    return scoring
```

## 6. 技术需求提取

```python
def extract_technical_requirements(text: str) -> list[dict]:
    """提取技术需求"""
    requirements = []

    # 查找建设需求/技术需求章节
    section = None
    for header in ['建设需求', '技术需求', '采购需求', '项目需求', '功能需求']:
        m = re.search(rf'{header}(.+?)(?=第[三四五六七八九]章|投标文件格式|合同|$)',
                      text, re.DOTALL)
        if m:
            section = m.group(1)
            break

    if not section:
        return requirements

    # 按序号拆分功能项
    items = re.split(r'\n\s*(?=\d+[、．.)])', section)

    for item in items:
        item = item.strip()
        if len(item) < 10:
            continue

        # 识别是否为表格行格式：序号 | 一级模块 | 二级功能 | 描述
        cells = re.findall(r'[\w一-鿿/\-\.\s]+', item)
        if len(cells) >= 3:
            requirements.append({
                'module': cells[0] if len(cells) > 0 else '',
                'feature': cells[1] if len(cells) > 1 else '',
                'description': cells[2] if len(cells) > 2 else '',
            })
        else:
            requirements.append({
                'module': '',
                'feature': '',
                'description': item[:300],
            })

    # 补充：利用表格提取的结果（如果 pdfplumber 已提取表格）
    # tables = extract_tables_from_pdf(pdf_path)
    # 解析表格中的技术需求行

    return requirements


def extract_technical_requirements_from_tables(tables: list[dict]) -> list[dict]:
    """从PDF表格中提取技术需求"""
    requirements = []
    for table_info in tables:
        table = table_info['table']
        page = table_info['page']

        if not table or len(table) < 2:
            continue

        # 识别表头：包含 序号/功能/模块/描述/要求 等关键词
        header = table[0]
        header_text = ' '.join(str(c) for c in header if c)
        if not any(kw in header_text for kw in ['功能', '模块', '需求', '要求', '描述']):
            continue

        # 找到关键列索引
        col_map = {}
        for idx, col in enumerate(header):
            col = str(col).strip() if col else ''
            if '序号' in col:
                col_map['seq'] = idx
            elif '模块' in col or '一级' in col:
                col_map['module'] = idx
            elif '功能' in col or '二级' in col or '子系统' in col:
                col_map['feature'] = idx
            elif '描述' in col or '要求' in col or '功能说明' in col:
                col_map['description'] = idx

        if not col_map:
            continue

        for row in table[1:]:
            if not any(row):
                continue
            req = {'page': page}
            for key, idx in col_map.items():
                if idx < len(row) and row[idx]:
                    req[key] = str(row[idx]).strip()
            if 'description' in req or 'feature' in req:
                requirements.append(req)

    return requirements
```

## 7. 实施要求提取

```python
def extract_implementation_requirements(text: str) -> dict:
    """提取实施要求"""
    reqs = {}

    # 团队组织要求
    m = re.search(r'团队组织要求[：:](.+?)(?=\n\n|\n[四五五六七八九]、|\n第)', text, re.DOTALL)
    if m:
        content = m.group(1).strip()
        reqs['team'] = {
            'description': re.sub(r'\s+', ' ', content),
            'requires_org_chart': '组织机构' in content or '组织架构' in content,
            'requires_personnel': '人员' in content,
            'requires_on_site': '现场' in content or '驻场' in content,
        }

    # 现场对接/驻场要求
    m = re.search(r'现场对接[：:]?\s*(\d+)\s*名', text)
    if m:
        reqs['on_site_headcount'] = int(m.group(1))
    elif re.search(r'驻场', text):
        m = re.search(r'驻场[：:]\s*(.+?)(?:\n|$)', text)
        reqs['on_site_requirement'] = m.group(1).strip() if m else '需驻场'

    # 培训要求
    m = re.search(r'培训要求[：:](.+?)(?=\n\s*\n|\n[五六七八九]、|\n第)', text, re.DOTALL)
    if m:
        reqs['training'] = re.sub(r'\s+', ' ', m.group(1).strip()[:300])

    # 交付文档要求
    m = re.search(r'交付文档要求[：:](.+?)(?=\n\s*\n|\n[六七八九]、|\n第)', text, re.DOTALL)
    if m:
        reqs['documentation'] = re.sub(r'\s+', ' ', m.group(1).strip()[:300])

    # 工期要求
    m = re.search(r'(工期|交付期|服务期)[：:]\s*(\d+)\s*(天|日历天|日|个月|月|年)', text)
    if m:
        reqs['period'] = {'value': int(m.group(2)), 'unit': m.group(3)}

    return reqs
```

## 8. 商务要求提取

```python
def extract_commercial_requirements(text: str) -> dict:
    """提取商务要求"""
    comm = {}

    # 质保期
    m = re.search(r'(质保期|保修期|维保期)[：:]\s*(\d+)\s*(年|月|天)', text)
    if m:
        comm['warranty'] = {'value': int(m.group(2)), 'unit': m.group(3)}

    # 付款方式
    m = re.search(r'付款方式[：:](.+?)(?=\n\s*\n|\n[三四五六七八九]、)', text, re.DOTALL)
    if m:
        comm['payment_terms'] = re.sub(r'\s+', ' ', m.group(1).strip()[:300])

    # 履约保证金
    m = re.search(r'履约(?:担保|保证金|保函)[：:]?\s*(.+?)(?:\n|$)', text)
    if m:
        comm['performance_bond'] = m.group(1).strip()

    # 不允许转包分包
    if re.search(r'不[得以].*转包|不[得以].*分包|禁止.*转包', text):
        comm['no_subcontracting'] = True

    return comm
```

## 9. 投标文件组成要求提取

```python
def extract_document_structure(text: str) -> dict:
    """提取招标文件要求的投标文件组成结构"""
    structure = {
        'required_sections': [],
        'required_forms': [],
        'required_certificates': [],
    }

    # 搜索投标文件组成/格式章节
    section = None
    for header in ['投标文件组成', '投标文件格式', '投标文件内容', '响应文件组成',
                   '投标文件的编制', '投标文件构成']:
        m = re.search(rf'{header}(.+?)(?=第[三四五六七八九]章|评审|评标|开标|\Z)',
                      text, re.DOTALL)
        if m:
            section = m.group(1)
            break

    if not section:
        return structure

    # 提取章节名称
    sections = re.findall(r'[（(]?\d+[）)]?\s*(.+?)(?:（.+?）)?(?:\n|$)', section)
    structure['required_sections'] = [s.strip() for s in sections if len(s.strip()) > 2]

    # 提取必需格式文件/表单
    forms = re.findall(r'(?:格式|模板|范本)[：:]?\s*(.+?)(?:\n|$)', section)
    structure['required_forms'] = [f.strip() for f in forms]

    # 提取必需证照
    certs = re.findall(r'(?:提供|提交|出具)\s*(.+?(?:证书|证明|执照|报告|声明|承诺))', section)
    structure['required_certificates'] = [c.strip() for c in certs]

    return structure
```

## 10. 隐性风险/陷阱识别

```python
def extract_hidden_traps(text: str) -> list[dict]:
    """识别招标文件中的隐性风险和陷阱"""
    traps = []

    # 1. 排他性条款
    exclusive_patterns = [
        (r'指定\s*(?:品牌|型号|厂商)', '指定品牌/型号'),
        (r'唯一\s*(?:来源|授权)', '唯一来源/授权'),
        (r'必须.*原厂', '原厂要求'),
        (r'仅限', '排他性限制'),
    ]
    for pattern, trap_type in exclusive_patterns:
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            traps.append({
                'type': trap_type,
                'severity': 'high',
                'context': text[start:end].replace('\n', ' ').strip(),
                'suggestion': '评估是否满足，如无法满足建议放弃投标或发起质疑',
            })

    # 2. 模糊条款
    vague_patterns = [
        (r'近似品牌', '模糊表述-近似品牌'),
        (r'参考型号', '模糊表述-参考型号'),
        (r'同等档次', '模糊表述-同等档次'),
        (r'国内外一线品牌', '模糊表述-一线品牌'),
        (r'业内知名', '模糊表述-业内知名'),
        (r'等\s*(?:同|类)', '模糊表述-等同/同类'),
        (r'包括但不限于', '开放条款-包括但不限于'),
        (r'招标人.*有权.*解释', '解释权保留'),
        (r'最终.*解释.*权', '解释权保留'),
    ]
    for pattern, trap_type in vague_patterns:
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            traps.append({
                'type': trap_type,
                'severity': 'medium',
                'context': text[start:end].replace('\n', ' ').strip(),
                'suggestion': '建议在答疑期内向招标人书面澄清',
            })

    # 3. 控标倾向识别
    control_patterns = [
        (r'近\s*(\d+)\s*年.*业绩', '业绩时间限制'),
        (r'本地化.*服务', '属地化要求'),
        (r'本地.*注册', '本地注册要求'),
        (r'特定.*行业.*经验', '行业经验限制'),
    ]
    for pattern, trap_type in control_patterns:
        for m in re.finditer(pattern, text):
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            traps.append({
                'type': trap_type,
                'severity': 'medium',
                'context': text[start:end].replace('\n', ' ').strip(),
                'suggestion': '核实自身是否满足，评估竞争格局',
            })

    return traps
```

## 11. 主解析函数

```python
def parse_tender_document(pdf_path: str) -> dict:
    """完整解析招标文件，返回结构化 JSON"""
    # 提取文本
    content, total_pages = extract_pdf_content(pdf_path)
    text = merge_pdf_text(content)

    # 提取表格
    tables = extract_tables_from_pdf(pdf_path)

    result = {
        'project_info': extract_project_info(text),
        'rejection_clauses': extract_rejection_clauses(text),
        'qualification_requirements': extract_qualification_requirements(text),
        'scoring_criteria': extract_scoring_criteria(text),
        'technical_requirements': (
            extract_technical_requirements_from_tables(tables) or
            extract_technical_requirements(text)
        ),
        'implementation_requirements': extract_implementation_requirements(text),
        'commercial_requirements': extract_commercial_requirements(text),
        'document_structure': extract_document_structure(text),
        'hidden_traps': extract_hidden_traps(text),
        'raw_metadata': {
            'total_pages': total_pages,
            'table_count': len(tables),
            'parse_timestamp': __import__('datetime').datetime.now().isoformat(),
        },
    }

    return result


def parse_tender_to_json(pdf_path: str, output_path: str = None) -> str:
    """解析招标文件并输出JSON"""
    result = parse_tender_document(pdf_path)
    json_str = json.dumps(result, ensure_ascii=False, indent=2)
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
    return json_str
```
