# tender-document-parser 招标解析验收卡

版本：v1.2

用途：用于招标文件解析前后自检，确保解析产物可追溯、质量门清楚、人工复核队列不被绕过。它只负责解析和产物验收，不写投标正文，不判断最终投标策略，不替代规则审查、资料匹配或整本投标文件检查。

## 1. 使用规则

- 每次解析招标文件、重跑解析脚本、补充固定格式摘录或证明材料清单后，必须按本卡自检。
- 解析产物必须能追溯到源文件、source hash 和原文块；PDF 使用页码追溯，DOCX 使用 body_index、paragraph_index、table_index 和 block_id 追溯。
- `quality_gate` 和 `manual_review_queue` 是基础解析硬门禁；`artifact_gates` 用于区分资料清单、固定格式和周期矩阵是否可交接，不得为了推进写作而绕过。
- 解析产物字段应符合 `references/parse-contract.md`；解析完成后建议执行 `scripts/validate_parse.py` 做结构校验。
- 脚本失败、覆盖率异常、关键表格未分类、固定格式或证明材料清单缺失时，只能写“需人工复核”，不得写成“招标文件无要求”。
- 自检结论只用：`通过`、`软提醒通过`、`需人工复核`、`阻断`。

## 2. 职责边界

招标解析主责：

- 抽取 raw blocks、requirements、fatal checklist、scoring matrix、manual review queue、parse manifest 和摘要报告。
- 确认解析源文件、hash、输出路径和产物指纹。
- 标出资格、废标、评分、技术、商务、报价、签章、递交、固定格式、证明材料等要求。
- 为规则审查、资料匹配、写作和整本检查提供可追溯依据。

招标解析不负责：

- 编写投标正文、承诺函、偏离表或报价。
- 修改招标原件、补遗答疑原件、商务资料或厂商资料。
- 代替主控锁定投标主体、报价版本、授权策略或最终投标口径。
- 凭印象补造未解析出的招标要求。

## 3. 招标解析验收卡

| 检查ID | 检查域 | 必查项 | 通过标准 | 风险处理 |
|---|---|---|---|---|
| TP-01 | 源文件门禁 | 是否确认本次解析源文件、修订版、补遗答疑、图纸或清单 | manifest 指向当前源文件，source hash 已记录 | 修订版/补遗缺失或版本不明，阻断 |
| TP-02 | 命令记录 | 是否记录实际解析命令和输出目录 | 命令、源文件、out-dir 可复现 | 命令不明时不得声称已重跑 |
| TP-03 | manifest | `parse_manifest.json` 是否存在且 source_file、source_sha256、输出文件 hash 完整 | manifest 可读，路径和 hash 对应本次文件 | manifest 缺失或指向旧文件，阻断 |
| TP-04 | raw blocks | `raw_blocks.json` 是否包含段落、表格、单元格、块号和位置 | 原文块能支持回查标题、正文、表格和固定格式 | raw blocks 缺失或表格为空，需人工复核 |
| TP-05 | requirements | `requirements.json` 是否覆盖资格、商务、技术、实施、签章、报价、递交等要求 | 每条 requirement 有类别、风险、来源和响应提示 | 核心类别缺失，阻断或人工复核 |
| TP-06 | fatal checklist | `fatal_checklist.json` 是否抽出废标、否决、资格、报价、签章、格式、递交红线 | 生死线有原文来源和风险等级 | 废标/资格/签章全为 0，需人工查原文 |
| TP-07 | scoring matrix | `scoring_matrix.json` 是否抽出评分项、分值、得分条件和证明材料 | 分值、条件、证明材料和来源可追溯 | 评分为 0 或分值缺失，阻断写作放行 |
| TP-08 | material checklist | 是否生成 `material_checklist.json/md/xlsx` | 资料名称、来源ID、用途分类、资料分类、责任方、盖章/扫描、原文来源齐全；能区分内部可编辑材料、固定证明材料、厂商外部材料、技术/产品证明、人员/业绩证明 | 清单缺失或分类不全，交规则审查/资料匹配补出 |
| TP-09 | fixed formats | 是否生成 `fixed_formats.md/json` 并抽取投标文件格式、固定表格、签章日期位置和表格结构 | 排除目录页同名条目，保留标题、说明、列名、字段顺序、签章位置；`format_type` 能区分 fixed_template/self_defined_format/table_template/signature_block | 固定格式未抽取，不放行对应写作和 DOCX 排版 |
| TP-10 | manual queue | `manual_review_queue.md` 是否只放必须确认的硬门禁和关键缺口 | 每项有原因、来源、建议动作和门禁等级 | 队列未清或未说明，不得跳过 |
| TP-11 | quality gate | `quality_gate.status` 与 `artifact_gates` 是否读取并回报 | 基础解析门、资料清单门、固定格式门、周期矩阵门状态分开说明 | 基础 blocked 不得写作；资料/格式/周期门未过不得关闭对应质量门 |
| TP-12 | 表格分类 | 评分表、技术参数表、报价表、资格表、格式表、递交/签章表是否分类 | 关键表格均有类别和原文块号 | `unparsed_tables` 含关键表格，需人工复核 |
| TP-13 | 目录页排除 | 固定格式和章节定位是否排除目录页、页眉页脚和重复标题 | 使用上下文、样式或正文位置判断 | 只按首次标题命中，列 P1 |
| TP-14 | 原文保真 | 表格、固定格式、偏离表、报价表是否保留原文标题、说明、列名、空格和结构线索 | 不精简、不合并、不改写固定格式 | 改写格式会误导写作，阻断相关章节 |
| TP-15 | 证明材料字段 | 评分项/资格项/技术项中的 proof_materials 是否抽取或标待复核 | 证明材料能交给资料匹配逐项核对 | 证明材料不明，不能关闭资料门 |
| TP-16 | 周期矩阵 | 是否生成 `timeline_matrix.json` 并拆分服务期/建设周期、交货期、安装调试、稳定试运行、验收、付款、质保起算 | 周期条目有类型、数值、触发事件、来源和风险提示；交货期不得误作总工期 | 周期矩阵缺失或混淆，需规则审查/主控确认 |
| TP-17 | DOC/DOCX/PDF 风险 | 多格式招标文件是否存在版本差异或解析限制 | 主解析源明确，参考源差异有说明 | 可能影响响应的差异，停止回报主控 |
| TP-18 | 输出完整性 | parse_report.md/html、parse_result.json、requirements/fatal/scoring/manual/material/fixed/timeline 等是否全部生成 | 输出路径齐全，可供下游读取，manifest 记录输出指纹；`validate_parse.py` 无 error | 关键产物缺失，视为解析失败或需人工复核 |
| TP-19 | 下游交接 | 是否说明给 bid-reviewer、bid-materials、bid-writer、bid-document-checker 的使用边界 | 回报含产物路径、质量门、人工缺口、不可用项 | 只说“解析完成”不算交接完成 |

## 4. 停止并回报条件

- 找到补遗、答疑、修订版、图纸或清单缺失。
- 解析脚本失败、输出为空、manifest 指向旧文件或 source hash 不匹配。
- `quality_gate.status=blocked`，或 `manual_review_queue.md` 存在硬门禁未处理。
- 评分项、资格项、废标项、签章/格式、技术/报价清单任一核心类别覆盖异常。
- 固定格式模板、证明材料清单、周期矩阵或关键表格未能追溯原文，或 `artifact_gates` 显示资料清单/固定格式/周期矩阵需人工复核。
- DOC、DOCX、PDF 或多个版本之间存在可能影响响应的差异。

## 5. 回报模板

```markdown
【招标解析回报】
- 状态：通过 / 软提醒通过 / 需人工复核 / 阻断
- 解析命令：
- 源文件：
- source hash：
- 输出目录：
- 关键产物：
- quality_gate：
- artifact_gates：
- manual_review_queue：
- 固定格式摘录：
- 证明材料清单：
- 周期矩阵：
- validate_parse：
- 需规则审查/主控确认：
- 下游使用提醒：
```
