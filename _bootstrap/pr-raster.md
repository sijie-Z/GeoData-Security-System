## 问题

`GET /api/raster_tiles/<data_id>/<z>/<x>/<y>.png` 对认证请求永远返回 404：读取端按平铺文件名 `tiles/<id>/{z}_{x}_{y}.png` 查找，而生成端写的是嵌套目录 `tiles/<id>/<z>/<x>/<y>.png`。

{{CLOSES}}

## 改动

- `testrealend/resource/raster_resource.py`：读取端拼路径改为与生成端一致的嵌套布局（单行改动）。
- 新增 `testrealend/tests/test_raster_tiles.py`：2 个回归用例（命中时返回 200 并校验响应字节；缺失时返回 404）。

## 验证

- `python -m pytest tests/test_raster_tiles.py tests/test_raster.py tests/test_upload.py -q` → 13 passed
- 负控制：把读取端回退到旧实现后运行新测试 → 1 failed, 1 passed（证明该测试确实覆盖此缺陷）
- `ruff check` / `ruff format --check` 对改动文件全部通过

## 说明

本 PR 范围仅限路径对齐；浏览器端瓦片请求的鉴权问题（见 {{ISSUE2}}）另行跟踪，不在本 PR 内。注意：本 PR 的 CI 检查会先显示红色——那是仓库历史遗留的 lint 问题（正在单独修复），不是本次改动引入。
