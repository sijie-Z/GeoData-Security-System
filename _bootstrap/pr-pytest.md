## 问题

全量测试基线存在 2 个既有失败（`test_watermark.py` 两个用例被 403 拦截），且套件对持久库 `instance/test.db` 非幂等（连续运行会连环失败，从 2 failed 恶化到 5 failed）。同时 CI 的 pytest 步骤写死 `|| true`，测试失败不阻塞流水线。

Closes #4

## 改动（全部在测试层与 CI 配置，业务代码零改动）

- `tests/test_watermark.py`：两处夹具改为与端点角色匹配（`adm2_headers` / `adm3_headers`）；断言未动。
- `tests/conftest.py`：
  - 新增 admin3 账号种子与 `adm3_headers` fixture；
  - 每轮 pytest 开始前清空文件型 SQLite 测试库（连同 `-journal/-wal/-shm` 侧车），且必须在 `import app` **之前**执行——app.py 模块级会创建 app 实例并持有连接，晚删在 Windows 上因文件锁失败（WinError 32，已实证）。
- `.github/workflows/ci.yml`：移除 `pytest ... || true` 的旁路，pytest 成为阻塞门。

## 根因

1. 403：两端点分别 `@admin_role_required("admin2")` / `("admin3")`，原测试使用 admin1 夹具，装饰器在业务逻辑前即拒绝。
2. 非幂等：`instance/test.db` 跨轮持久，残留数据触发 UNIQUE 冲突与聚合查询崩溃。

## 验证

- 连续两次全量：`140 passed, 1 skipped, 0 failed`（两次一致，幂等成立）
- 活体探针（未放宽任何鉴权）：admin1→403（原样）、admin2→200、admin3→400、employee→403、无 token→401
- 修复前对照复现：2 failed → 连跑恶化至 5 failed（污染链已逐一归因）
