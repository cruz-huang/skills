# 中文招投标 Skills

中文招投标场景的两个 Codex Skills。

## 安装

安装招标文件解析：

```bash
npx skills add https://github.com/cruz-huang/skills --skill tender-document-parser
```

安装投标文件检查：

```bash
npx skills add https://github.com/cruz-huang/skills --skill bid-document-checker
```

安装后重启 Codex。

## 技能

- `tender-document-parser`：解析招标文件，输出可追溯的要求、废标红线、评分项、资料清单、固定格式和周期矩阵。
- `bid-document-checker`：检查投标文件，覆盖响应完整性、报价、偏离表、资质业绩、授权售后、技术证明、固定格式、签章页码和图片可读性。

## 说明

- 解析器支持：`.docx`、`.pdf`、`.txt`、`.md`。
- 检查器模式：`lightweight_check`、`formal_report`。
- 提交前请始终对照招标原文复核生成结果。
- 不要公开私有招标文件、投标文件、证书、合同、客户名称、价格、签名、印章或个人信息。

## 许可

MIT，见 [LICENSE](LICENSE)。
