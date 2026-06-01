# 空间数据追踪系统 - 后端

## 启动

```powershell
cd testrealend
python app.py
```

## 已知的 Windows 兼容性问题

### 1. `app.run()` 在 Windows + Python 3.12 上静默返回

**症状：** 执行 `python app.py` 后终端打印完 `* Debug mode: off` 立即回到提示符，服务不阻塞。

**根因：** Python 3.12.8 在 Windows 上存在多个问题：

- **假 `KeyboardInterrupt`** — 网络连接失败后清理 socket 时（`sock.close()`）可能抛出一个假的 `KeyboardInterrupt`，`except Exception` 抓不住它（它是 `BaseException`），进程直接崩溃。
- **`app.run()` 静默返回** — 在某些环境下（VS Code 终端、从项目根目录调用），`app.run()` 会在打印完启动信息后立即返回，而不是阻塞等待请求。

**修复方法：**
- `app.run()` 被替换为 `werkzeug.serving.make_server()` + 子线程 + 主线程永久阻塞
- Redis 连接错误用 `except BaseException` 而不是 `except Exception`
- 健康检查中同样使用 `except BaseException`
- `create_app()` 外层有 `try/except KeyboardInterrupt` 重试 3 次的兜底

**涉及的文件：**
- [app.py](app.py) — `make_server()` 启动、`create_app()` 重试
- [utils/cache.py](utils/cache.py) — `init_cache()` 中 `except BaseException`
- [utils/websocket.py](utils/websocket.py) — Windows 上跳过 `SocketIO` 初始化

### 2. SocketIO 初始化导致服务不阻塞

**症状：** 在 Windows 上，`SocketIO(app, async_mode="threading")` 初始化会修改 Flask 的 WSGI 栈，导致 `app.run()` 立即返回。

**修复方法：** 在 Windows 上跳过 `flask-socketio` 初始化，通知功能降级为 HTTP 轮询。

### 3. 端口被占用

启动时会自动清理端口 5003 上的旧进程。如果端口被其他程序占用，日志会显示 `Killed stale process`。

## 快速验证服务是否运行

```powershell
curl http://127.0.0.1:5003/api/health
# 返回: {"status": "healthy", ...}
```
