## 问题

仓库 CI（`.github/workflows/ci.yml`）自 2026-06-01 起的全部运行均为失败：backend 作业挂在 `ruff check`，frontend 作业挂在 `eslint`，docker 作业因依赖失败被跳过。

## 根因

- backend：`testrealend` 下 `ruff check` 有 6 处违规（I001×3 导入排序、B007×2 未使用循环变量、SIM117 嵌套 with），另有 13 个文件不符合 `ruff format`——多来自 6 月未经过 CI 的提交。
- frontend：`eslint` 有 11 个 error，其中 `utils/socket.js` 4 处未定义变量属于**真实缺陷**（此前重构把形参改名为 `_token`/`_opts` 时漏改了引用）；其余为常量条件、i18n 重复键、多余分号。另有 3718 个 warning（不阻塞 CI，暂不处理）。

## 修复

见对应 PR：后端 `ruff check`/`ruff format --check` 全绿；前端 `eslint` 0 error、`npm run build` 通过。

## 备注

`pytest` 步骤当前写死 `|| true`（测试失败不阻塞）。全量基线下存在 2 个既有失败用例（另行跟踪）；按计划先修用例、之后再移除 `|| true`，让测试成为硬门禁。
