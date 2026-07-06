# 招标解析产物契约

版本：v1.0  
适用解析器：tender-document-parser v2.3.1+

本文件定义解析产物的最低结构要求。下游 Agent 不应只看文件名或生成时间，而应以 `parse_manifest.json`、source hash、quality gate、artifact gates 和本契约字段为准。

## 总体规则

- 所有结构化产物必须包含 `schema_version`、`source_file`、`source_sha256`、`parser_version`。
- 所有要求、评分、资料、固定格式、周期条目必须能追溯到原文：至少提供 `source_refs` 或可映射回 `raw_blocks.json` 的 block id。
- `quality_gate.status=blocked` 时不得进入正式写作或成稿。
- `artifact_gates.*.status=needs_manual_review` 时，对应下游工作不得直接放行。
- `manual_review_queue.md` 中的项是必须人工复核的解析缺口，不是最终招标结论。

## 必备产物

| 文件 | 必备性 | 主要用途 |
|---|---|---|
| `parse_manifest.json` | 必备 | 记录源文件、source hash、输出文件 hash |
| `raw_blocks.json` | 必备 | 原文块和表格追溯 |
| `requirements.json` | 必备 | 逐条招标要求台账 |
| `fatal_checklist.json` | 必备 | 废标、资格、签章、报价等红线 |
| `scoring_matrix.json` | 必备 | 评分项、分值、证明材料 |
| `manual_review_queue.md` | 必备 | 人工复核缺口 |
| `material_checklist.json` | 必备 | 资料项结构化清单 |
| `material_checklist.md` | 必备 | 资料项人工查看版 |
| `material_checklist.xlsx` | 必备 | 内部核料和外部收资表 |
| `fixed_formats.json` | 必备 | 固定格式结构化摘录 |
| `fixed_formats.md` | 必备 | 固定格式人工查看版 |
| `timeline_matrix.json` | 必备 | 周期、交付、验收、付款、质保口径矩阵 |
| `parse_result.json` | 必备 | 兼容总结果和 artifact gates |
| `parse_report.md` / `parse_report.html` | 建议 | 人工摘要 |

## requirements.json

每条 `requirements[]` 至少包含：

- `requirement_id`
- `category`
- `risk_level`
- `title`
- `text`
- `confidence`
- `source_refs`
- `requires_response`
- `requires_seal`
- `response_hint`

要求：

- `source_refs` 不得为空。
- `category` 不得只依赖标题，正文条款、表格行、签章块均需保留。
- 对服务期、交货期、验收、付款、质保等条款，不得只归为泛化商务条款；必须同时进入 `timeline_matrix.json`。

## fatal_checklist.json

每条 `items[]` 至少包含：

- `requirement_id`
- `fatal_type` 或可区分红线类型的字段
- `text`
- `source_refs`
- `must_confirm`
- `action`

要求：

- 废标、否决、资格不满足、报价红线、固定格式破坏、签章缺失、递交密封错误必须优先进入红线清单。
- 红线条目不能只给摘要，必须能回查原文。

## scoring_matrix.json

每条 `items[]` 至少包含：

- `scoring_id`
- `requirement_id`
- `score_group`
- `item_name`
- `max_score`
- `criteria`
- `proof_materials`
- `source_refs`

要求：

- 总分能明确计算时应提供 `total_score`；兼容旧字段 `known_total_score`，但新产物应优先读取 `total_score`。
- 分值缺失、评分表无法分类、证明材料字段为空时，必须进入 `manual_review_queue.md` 或 artifact gate warning。

## material_checklist.json / MD / Excel

每条 `items[]` 至少包含：

- `material_id`
- `material_name`
- `requirement`
- `source_requirement_id` 或 `scoring_id`
- `usage_category`
- `material_class`
- `responsible_party`
- `needs_seal`
- `needs_scan`
- `purpose_flags`
- `source_refs`
- `source_text_location`
- `notes`
- `review_status`

`material_class` 取值建议：

- `投标人内部可编辑材料`
- `投标人固定证明材料`
- `厂商外部盖章/授权材料`
- `技术/产品证明材料`
- `人员/业绩证明材料`

要求：

- 不得只靠硬编码材料名；应结合“提供/提交/出具/附/证明/截图/扫描件/证书/合同/授权/售后”等规则抽取。
- 资料名称过泛时标记 `review_status=needs_manual_review`。
- 资料是否真实存在、是否过期、是否盖章，由资料匹配和人工核验完成；解析器只抽取招标要求。

## fixed_formats.json / MD

每条 `items[]` 至少包含：

- `fixed_format_id`
- `kind`
- `format_type`
- `block_id`
- `title`
- `match_reason`
- `source_refs`
- `format_notes`

`format_type` 必须使用以下值之一：

- `fixed_template`：招标提供固定文本模板。
- `self_defined_format`：招标要求提供文件，但格式自拟或自行编制。
- `table_template`：招标提供表格模板。
- `signature_block`：签字、盖章、日期、身份信息等签章块。

要求：

- 目录页同名条目不能当正文模板。
- `格式自拟` 不得误判为必须照抄的固定模板。
- 表格模板必须保留行列、字段顺序、签章日期位置和版式线索。

## timeline_matrix.json

每条 `items[]` 至少包含：

- `timeline_id`
- `timeline_type`
- `name`
- `value`
- `trigger`
- `meaning`
- `source_requirement_id`
- `source_refs`
- `risk_note`
- `confidence`

`timeline_type` 建议取值：

- `service_period`
- `construction_period`
- `delivery_period`
- `installation_commissioning`
- `trial_run`
- `acceptance`
- `payment`
- `warranty_start`
- `warranty_period`
- `bid_validity`
- `deadline`

要求：

- 服务期/建设周期、交货期、安装调试节点、稳定试运行、验收、付款、质保起算必须拆开记录。
- 出现“5 天交付/交货”和“1 个月建设周期”时，必须在 `warnings` 中提醒后续响应矩阵拆口径。
- 稳定试运行不得被误写为建设周期或交货期。

## 校验建议

每次解析完成后执行：

```bash
python3 scripts/validate_parse.py --out-dir 招标文件解析 --source 招标文件.docx
```

校验通过只代表产物结构和门禁字段完整，不代表招标要求已经被人工最终锁定。
