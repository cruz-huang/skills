# Bid Tender Skills

中文招投标场景的两个 Codex skills。

## Install

```bash
npx skills add https://github.com/cruz-huang/skills --skill tender-document-parser
npx skills add https://github.com/cruz-huang/skills --skill bid-document-checker
```

Restart Codex after installation.

## Skills

- `tender-document-parser`：解析招标文件，输出可追溯的要求、废标红线、评分项、资料清单、固定格式和周期矩阵。
- `bid-document-checker`：检查投标文件，覆盖响应完整性、报价、偏离表、资质业绩、授权售后、技术证明、固定格式、签章页码和图片可读性。

## Notes

- Parser input: `.docx`、`.pdf`、`.txt`、`.md`。
- Checker modes: `lightweight_check`、`formal_report`。
- Always review generated artifacts against the original tender document before submission.
- Do not publish private tender documents, bid documents, certificates, contracts, customer names, prices, signatures, seals, or personal data.

## License

MIT. See [LICENSE](LICENSE).
