# Bid Tender Skills

面向中文招投标场景的两个 Codex skills：

- `tender-document-parser`：把招标文件解析成可追溯的结构化台账。
- `bid-document-checker`：按招标文件、项目口径和验收卡检查投标文件。

这两个 skill 适合用于投标文件编制前后的辅助工作：先解析招标文件，形成要求、废标红线、评分项、资料清单、固定格式和周期矩阵；再用这些产物检查投标文件的一致性、完整性、签章页码、报价、偏离表、资质业绩、授权售后和技术证明。

## Repository Layout

```text
skills/
  tender-document-parser/
  bid-document-checker/
```

## Install

Copy the two skill directories into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R skills/tender-document-parser ~/.codex/skills/
cp -R skills/bid-document-checker ~/.codex/skills/
```

Then restart Codex so it can discover the new skills.

## Skill: tender-document-parser

Use this skill when you need to turn a tender document into a structured, traceable set of artifacts.

Supported input formats:

- `.docx`
- `.pdf`
- `.txt`
- `.md`

Typical command from the skill directory:

```bash
python3 scripts/parse_tender.py 招标文件.docx
python3 scripts/validate_parse.py --out-dir 招标文件解析 --source 招标文件.docx
```

Main outputs:

- `parse_manifest.json`
- `raw_blocks.json`
- `requirements.json`
- `fatal_checklist.json`
- `scoring_matrix.json`
- `manual_review_queue.md`
- `material_checklist.json`
- `material_checklist.md`
- `material_checklist.xlsx`
- `fixed_formats.json`
- `fixed_formats.md`
- `timeline_matrix.json`
- `parse_result.json`
- `parse_report.md`
- `parse_report.html`

## Skill: bid-document-checker

Use this skill when you need to check a bid document, proposal draft, final draft, signed PDF, or submission-ready package.

It supports two output modes:

- `lightweight_check`：for process checks, chapter checks, internal review, and quick go/no-go summaries.
- `formal_report`：for full bid document review, final review, signed PDF review, or reports that need to be shared.

Main checking areas:

- tender requirement coverage
- fatal and disqualification risks
- quotation consistency
- qualification and performance evidence
- authorization and after-sales documents
- technical proof materials
- deviation tables
- commitments
- payment, delivery, acceptance, warranty, and service terms
- fixed formats
- signature, seal, date, pagination, scans, and visual readability

## Recommended Workflow

1. Run `tender-document-parser` on the latest tender document, amendment, or clarification file.
2. Review `parse_manifest.json`, `manual_review_queue.md`, `material_checklist.*`, `fixed_formats.*`, and `timeline_matrix.json`.
3. Use the parser artifacts as the source of truth for writing, material matching, and checking.
4. Run `bid-document-checker` against the bid document.
5. For final or signed versions, generate a formal Markdown and HTML report.

## Boundaries

These skills are assistants, not legal, procurement, or compliance authorities.

They do not:

- decide whether you should bid;
- guarantee compliance with a tender;
- replace manual review of hard gates, signatures, seals, prices, dates, or legal commitments;
- verify external certificate authenticity;
- validate platform upload, encryption, or submission status;
- make commercial commitments on behalf of a bidder.

Always review generated artifacts against the original tender document before submission.

## Privacy And Security

Do not publish private tender documents, bid documents, certificates, contracts, customer names, prices, signatures, seals, or personal data.

If you use the optional HTML preview helper in `bid-document-checker`, it exposes a copied single-file preview through a temporary tunnel. Anyone with the link may access that HTML while the tunnel is running.

## License

MIT. See [LICENSE](LICENSE).
