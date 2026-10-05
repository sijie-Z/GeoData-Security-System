## 背景

CI 的 `pytest` 步骤当前为 `pytest ... || true`（测试失败不阻塞 CI，属早期过渡设置）。启动"测试转硬门禁"计划前，需要先把既有失败清零、并让套件可重复运行。

## 现状（2026-10-05 全量基线，两次独立运行结果一致）

**2 failed, 138 passed, 1 skipped**。两个既有失败（与近期改动无关）：

- `tests/test_watermark.py::TestWatermarkEmbedding::test_get_embedding_applications`
- `tests/test_watermark.py::TestVectorExtract::test_missing_fields`

另发现套件对持久测试库 `testrealend/instance/test.db` 非幂等：连续运行会因上一轮残留数据产生额外失败（曾观察到 5 failed）；建议夹具改为每轮独立临时库，或运行前强制重建。

## 目标

1. 复现并修复上述 2 个失败用例（先定位根因，再修；修复需带断言证据）；
2. 解决测试库非幂等问题（保证连续两次 `pytest` 结果一致）；
3. 完成后移除 CI 的 `|| true`，让 `pytest` 成为硬门禁（与 lint 门并列全绿）。

## 备注

不阻塞 lint 修复 PR；本 issue 对应"CI 现代化"的下一步。
