## 问题

CI 自 2026-06 起持续失败，其中 backend 作业挂在 `ruff check`（6 处违规 + 13 个文件待格式化），frontend 作业挂在 `eslint`（11 个 error）。

Closes {{CI}}

## 改动

**后端（ruff）**

- `ruff check --fix` 修复 4 处：I001×3（导入排序）、SIM117×1（嵌套 with 合并为多上下文 with，语义等价）
- 手动修复 B007×2：`testrealend/resource/watermark_utils.py` 未使用的循环变量改名 `name` → `_name`（循环体内未使用，语义不变）
- `ruff format`：14 个文件格式化（纯引号/换行/空白调整）

**前端（eslint，11 个 error 逐个修复）**

- `src/utils/socket.js`：修复 4 处未定义变量——补全此前重构漏改的引用（`token`/`opts` → 函数形参 `_token`/`_opts`）。这是**真实缺陷修复**，不是风格调整。
- `src/api/chat.js`：`while (true)` → `for (;;)`（等价写法）
- i18n 重复键 ×5（en-US / zh-CN 各 2.5 处）：逐个比对两次定义的值，保留语义正确的一份；其中 `approval.secondReviewReject` 恢复了被旧值静默遮蔽的新按钮文案。重复键是真实问题——JS 会静默采用后一个定义。
- `WatermarkQualityDashboard.vue`：删除多余分号

## 验证

- `python -m ruff check .` → All checks passed
- `python -m ruff format --check .` → 110 files already formatted
- `npx eslint src --ext .js,.vue --quiet` → exit 0；`npm run lint` → exit 0（0 errors；3718 warnings 分毫未动）
- `npm run build` → 成功（约 22s）
- `pytest` 全量：2 failed / 138 passed / 1 skipped，与修复前基线完全一致（2 个失败为既有问题，见 {{PYTEST}}）

## 说明

范围仅限让 CI 的 lint 门转绿；`pytest` 的 `|| true` 与 3718 个 warning 按计划暂不处理。docker 作业在本 PR 合并且 CI 转绿后将首次跑到（此前一直被跳过）。
