---
name: tender-document-parser
description: 招标文件解析技能。用于把招标文件 PDF/Word/txt 解析成可追溯结构化台账，输出 parse_manifest、raw_blocks、requirements、fatal_checklist、scoring_matrix、manual_review_queue、material_checklist、fixed_formats、timeline_matrix 和解析报告，供投标主控、规则审查、资料匹配、写作和检查使用。
metadata:
  version: 2.3.1
  updated: 2026-06-29
---

# 招标文件解析

当前版本：v2.3.1  
更新日期：2026-06-29

## 本版变更

- 新增 `references/parse-contract.md`，固化 requirements、fatal_checklist、scoring_matrix、material_checklist、fixed_formats、timeline_matrix 等产物契约。
- 新增 `scripts/validate_parse.py`，用于校验 manifest、source hash、输出完整性、quality_gate、artifact_gates、资料字段、固定格式类型、周期矩阵和人工复核队列。
- 新增 `timeline_matrix.json`，强制拆分服务期/建设周期、交货期、安装调试节点、稳定试运行、验收、付款、质保起算等时间口径。
- 资料清单升级为“规则抽取 + 分类归并 + 人工复核缺口”，并补充 JSON、MD、Excel 三类输出。
- 资料清单增加噪声过滤和名称优先分类，降低付款、合同模板、验收报告模板等误入资料清单的概率。
- 周期矩阵改为分句抽取并增加噪声过滤，降低“交付/验收”宽关键词造成的假口径。
- `validate_parse.py` 增加资料分类冲突、周期数量异常、空 value、混合周期值等质量 warning。
- 固定格式新增 `format_type`：`fixed_template`、`self_defined_format`、`table_template`、`signature_block`。
- 增加回归样例，覆盖工期/交货期误判、业绩时间、签章表、格式自拟、原厂授权/售后函、证明材料扫描件等常见坑。

## 目标

只做一件事：把招标文件拆成“可追溯要求台账”，并把会影响废标、资格、评分完整性、关键表格遗漏、固定格式遗漏和证明材料遗漏的解析缺口列入人工复核或交接说明。不写投标内容，不替用户判断是否参与投标。

解析前后必须读取并执行 `references/acceptance-card.md`。该卡用于确认源文件版本、manifest、source hash、原文块、质量门、人工复核队列、资料清单和固定格式摘录，不替代规则审查、资料匹配或整本投标文件检查。

## 必跑命令

```bash
# 在本 Skill 目录下运行；Codex 使用时应按 Skill 根目录解析 scripts/ 相对路径
python3 scripts/parse_tender.py 招标文件.docx
python3 scripts/validate_parse.py --out-dir 招标文件解析 --source 招标文件.docx
```

默认输出到招标文件所在目录下的 `招标文件解析/` 文件夹。也可以 `--out-dir` 指定其他位置。

支持 `.docx`、`.pdf`、`.txt`、`.md`。旧版 `.doc` 先另存为 `.docx` 或导出为 `.txt` 后再解析。

## 输出文件

| 文件 | 用途 |
|---|---|
| `parse_manifest.json` | 解析结果身份证：源文件路径、文件指纹、输出文件指纹 |
| `raw_blocks.json` | 原文块台账：段落、表格、单元格、位置；DOCX 以 body/段落/表格序号追溯，PDF 才有页码 |
| `requirements.json` | 逐条要求台账：要求、风险、来源、响应提示 |
| `fatal_checklist.json` | 废标/否决/资格/签章/格式/报价等生死线清单 |
| `scoring_matrix.json` | 评分项台账：分值、得分条件、证明材料、来源 |
| `manual_review_queue.md` | 人工复核队列：只放必须人工确认的硬门禁和关键解析缺口 |
| `material_checklist.json` | 资料项结构化清单：用于下游校验和资料匹配 |
| `material_checklist.md` | 资料项清单 Markdown：商务/技术分开列出图片/PDF类不可编辑资料 |
| `material_checklist.xlsx` | 资料项清单 Excel：用于内部核料和外部收资 |
| `fixed_formats.json` | 固定格式结构化摘录：标题、说明、表格、字段、签章日期位置和版式线索 |
| `fixed_formats.md` | 固定格式人工查看版：写作和 DOCX 排版必须回查 |
| `timeline_matrix.json` | 周期矩阵：服务期、建设周期、交货期、安装调试、试运行、验收、付款、质保起算 |
| `parse_result.json` | 兼容下游旧字段，并包含 `artifact_gates` |
| `parse_report.md` | 给人快速查看的摘要报告，只展示可行动关键要求 |
| `parse_report.html` | 给人看的彩色网页报告，优先打开这个 |

## 执行流程

1. 明确本次招标文件路径；修订版、补遗答疑、图纸或清单优先，不得沿用旧解析。
2. 按 `references/acceptance-card.md` 建立解析验收范围，记录解析命令、主解析源和输出目录。
3. 运行解析脚本，默认输出到招标文件旁边的 `招标文件解析/`。
4. 打开 `parse_manifest.json`，确认 `source_file` 和 `source_sha256` 对应本次招标文件。
5. 打开 `parse_result.json`，分别查看 `quality_gate` 和 `artifact_gates`：`quality_gate` 只代表基础解析门，`material_checklist_gate`、`fixed_formats_gate`、`timeline_matrix_gate` 分别代表资料清单、固定格式和周期矩阵状态。
6. 打开 `manual_review_queue.md`；若有待确认项，必须逐条人工确认，不得凭猜测形成解析结论。
7. 打开 `material_checklist.xlsx` / `material_checklist.md`，确认内部资料和外部厂家资料清单是否可交给资料匹配线程。
8. 打开 `fixed_formats.md` / `fixed_formats.json`，确认投标文件格式、证明书、授权委托书、投标函、承诺函、偏离表、报价表、人员表、业绩表等固定格式是否已摘录；目录页同名标题不能当正文标题。
9. 打开 `timeline_matrix.json`，确认服务期/建设周期、交货期、安装调试、稳定试运行、验收、付款、质保起算等时间口径已拆分。
10. 运行 `scripts/validate_parse.py --out-dir <解析目录> --source <招标文件>`；若失败，必须先修复解析产物或列入人工复核。
11. 按验收卡输出解析回报：解析命令、源文件、source hash、输出目录、quality_gate、artifact_gates、manual_review_queue、资料清单、固定格式摘录、周期矩阵和下游使用限制。
12. 硬门禁清零后，下游技能才允许使用同一 manifest 指向的解析产物；资料清单、固定格式、周期矩阵未过门时，不得直接进入对应写作或排版。

## 下游使用规则

- 做投标文件：优先读取 `requirements.json`，按 `requirement_id` 逐项响应。
- 锁定生死线：读取 `fatal_checklist.json`，先处理废标、资格、报价、签章、格式、递交等红线。
- 冲高分：读取 `scoring_matrix.json`，按评分项、分值、证明材料组织大纲和响应证据。
- 做资料匹配：优先读取 `material_checklist.json` / `material_checklist.xlsx` / `material_checklist.md`；可编辑承诺函和投标表单不作为外部资料缺口。
- 查原文格式或表格：读取 `fixed_formats.md` / `fixed_formats.json`；不足时回到 `raw_blocks.json`，不得凭记忆重写格式。
- 判断周期口径：读取 `timeline_matrix.json`，不要把交货期、安装调试、稳定试运行、验收付款和质保起算混成项目总工期。
- 判断是否跳过解析：只看 `parse_manifest.json` 的 source hash 和输出指纹，不看文件名和生成时间。
- 检查投标文件：用 `requirements.json`、`fatal_checklist.json`、`scoring_matrix.json`、`fixed_formats.json` 作为校验标尺。

## 质量门槛

解析结果不可直接视为“全对”。必须看分级门禁：

- `quality_gate.status=blocked`：基础解析硬门禁未清零，不得进入正式投标文件生成。
- `quality_gate.status=pass_with_soft_review`：可继续准备，但需关注报告中的软提醒；只有进入 `manual_review_queue.md` 的项才要求逐条确认。
- `quality_gate.status=pass`：基础解析质量门槛通过，但仍以原文和 manifest 为准。
- `artifact_gates.material_checklist_gate.status=needs_manual_review`：资料清单未自动形成有效清单，不得关闭资料门。
- `artifact_gates.fixed_formats_gate.status=needs_manual_review`：固定格式未自动摘录，不得放行对应写作和 DOCX 排版。
- `artifact_gates.timeline_matrix_gate.status=needs_manual_review`：周期矩阵未形成，不得锁定服务期、交货期、试运行、验收付款和质保口径。

必须人工复核的硬门禁包括：

- `scoring` 为 0：评分标准可能漏掉，必须人工查评审章节。
- `technical` 和 `bill_of_quantities` 都为 0：技术/清单表可能漏掉，必须人工查采购需求。
- `document_structure` 为 0：投标文件组成可能漏掉，必须人工查投标文件格式章节。
- `signature_seal` 为 0：盖章签字要求可能漏掉，必须人工查投标文件格式和递交要求。
- `qualification` 为 0：资格审查要求可能漏掉，必须人工查资格章节。
- 固定格式模板未抽取且招标文件疑似有投标文件格式章节：必须人工查证明书、授权委托书、投标函、承诺函、偏离表、报价表、人员表、业绩表等。
- 证明材料清单缺失或明显不完整：必须人工查资格、评分、签章、产品证明、人员、业绩、授权等要求。
- 废标/否决/强制性条款均为 0：必须人工查评审、无效投标、否决条款章节。
- 关键 `unparsed_tables` 非空：评分表、技术参数表、报价表、资格表、投标文件格式表、签章/密封/递交表必须人工确认。
- `scoring_matrix.items_missing_score` 非空：评分项分值未解析完整，必须人工补齐。

## 降噪规则

- 人看报告只展示“能形成动作”的条目：废标红线、资格门槛、必备格式、扣分风险、报价/清单、签章检查、技术响应、实施交付。
- 章节标题、表头、导航句、空白模板名只保留在 `requirements.json` / `raw_blocks.json` / `fixed_formats.json` 中，供 AI 定位原文和下游脚本追溯。
- 普通评分上下文不进人工复核队列：如综合评估法说明、评标流程、排名规则、评分表标题、表头“评分项目/评分细则”等。
- 合同泛化风险不进人工复核队列：如保密、解释权、合同生效、包括但不限于等；这些保留在 `requirements.json` / `hidden_traps`，供写作和检查参考。
- 只有影响“能否继续写”的缺口才进 `manual_review_queue.md`：关键表格未分类、评分项分值缺失、资格/废标/签章/格式/技术清单等核心类别缺失。
- `manual_review_queue.md` 为空且 `quality_gate.status=pass` 时，不要再追问用户确认普通条款。

## 关键原则

- 结论必须带来源：PDF 用页码，DOCX 用 body_index、paragraph_index、table_index 和 block_id。
- 表格必须保留原文，不精简、不合并、不改写。
- 偏离表和响应表必须保留标题、说明、列名和原文条目号线索，供下游判断响应基准。
- 固定格式摘录应记录空段/隔行、居中、缩进、制表位、下划线对齐、签章留白、表格结构等版式线索。
- 从 Word 抽取章节时，不能只按标题首次命中定位；目录页也会出现同名条目，必须结合段落位置、上下文或样式判断正文标题。
- 固定格式模板只负责摘录原格式，不替写作生成自由文本。
- 解析失败或覆盖率异常时，不得把空结果当作“招标文件没有要求”。
- `manual_review_queue.md` 中的内容都是必须确认的候选疑点，不是最终结论；未进入队列的普通风险只作为写作/检查参考，不要求用户逐条确认。
- 不确定的关键缺口只能写成“待确认/疑似/需人工复核”，不得写成确定事实。
- 补遗、答疑、修订文件出现时，以最新文件重新解析，并重新生成 manifest。

## 资源

| 文件 | 用途 |
|---|---|
| `scripts/parse_tender.py` | 一键解析脚本 |
| `scripts/validate_parse.py` | 解析产物契约校验器 |
| `references/acceptance-card.md` | 招标解析验收卡 |
| `references/parse-contract.md` | 解析产物契约 |
| `references/extraction-patterns.md` | 关键词和正则参考 |
| `references/parsing-guide.md` | 旧版实现参考，仅用于理解，不作为当前执行入口 |
| `tests/fixtures/known-pitfalls.md` | 回归样例：常见解析坑 |
