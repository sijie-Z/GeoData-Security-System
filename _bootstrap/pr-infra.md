## 改动

- 新增 `.github/ISSUE_TEMPLATE/bug_report.md`、`.github/ISSUE_TEMPLATE/feature_request.md`：中文 issue 模板（含 frontmatter 标签）。
- 新增 `.github/PULL_REQUEST_TEMPLATE.md`：PR 四段式（问题 / 改动 / 验证 / 说明）。
- 新增 `.coderabbit.yaml`：CodeRabbit 评审配置（中文、chill 档、自动审 PR）。

## 验证

- `.coderabbit.yaml` 经 yaml.safe_load 解析通过；模板 frontmatter 格式正确。
- 纯新增文件，不影响运行代码。

## 说明

CodeRabbit 需在 GitHub Marketplace 安装应用后生效（仓库侧配置即本文件）。
