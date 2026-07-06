# tender-document-parser 回归样例

本目录用于保存解析器常见坑的最小样例，避免后续改脚本时出现行为回退。

建议命令：

```bash
python3 scripts/parse_tender.py tests/fixtures/known-pitfalls.md --out-dir /tmp/tender-parser-regression
python3 scripts/validate_parse.py --out-dir /tmp/tender-parser-regression --source tests/fixtures/known-pitfalls.md
```

说明：`known-pitfalls.md` 是脱敏后的坑点最小样例，不是完整招标文件。它用于观察关键口径是否被正确拆分；由于缺少完整报价/货物清单、评分表和正式固定格式上下文，完整契约校验可能返回 `quality_gate.status=blocked`，这是负例样例的预期现象，不代表真实招标文件解析失败。

重点观察：

- `timeline_matrix.json` 中 1 个月建设周期、5 天交货/安装调试节点、1 个月稳定试运行是否被拆开。
- `fixed_formats.json` 中“格式自拟”是否标为 `self_defined_format`。
- `material_checklist.json` 是否抽出授权书、售后承诺函、业绩合同扫描件、人员证书、产品证明截图等资料项。
