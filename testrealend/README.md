# 空间数据追踪系统 - 后端

> **当前稳定版本：v2.4.0** — 修复 Windows + Python 3.12 启动兼容性问题。

---

## 快速启动（三选一）

全部方式都能正常启动，终端会卡住不动即表示服务在运行：

```powershell
# 方式一（推荐）：先 cd 进目录
cd D:\Desktop\MyProjects\Spatial_Data_Tracking_System_lastvension\testrealend
python app.py

# 方式二：从项目根目录用完整路径
cd D:\Desktop\MyProjects\Spatial_Data_Tracking_System_lastvension
python testrealend/app.py

# 方式三：VS Code 打开 app.py → 右上角 ▶ Run
```

**启动成功的标志：** 看到以下输出后终端**卡住不动**（没有回到 `PS D:\...>` 提示符）：

```
 * Serving Flask app 'app'
 * Debug mode: off
```

**停止服务：** 按 `Ctrl + C`。

---

## 为什么 v2.4.0 之前 PowerShell 能打开、VS Code 打不开？

这是 Python 3.12.8 在 Windows 上的两个独立问题叠加导致的：

### 问题一：假 KeyboardInterrupt

网络连接失败（如 Redis 没启动）后清理 socket 时，`sock.close()` 会抛出一个**假的 `KeyboardInterrupt`**。`except Exception` 抓不住它（它是 `BaseException`），进程直接静默崩溃。

### 问题二：`app.run()` 在某些环境下静默返回

Flask 的 `app.run()` 在某些终端环境下（VS Code 终端、从项目根目录调用）会在打印完 `* Debug mode: off` 后**立即返回**，而不是阻塞等待请求。PowerShell 独立窗口不受影响，VS Code 的集成终端受影响。

### 为什么有这种差异？

VS Code 的 Python 插件在运行文件时会设置一些环境变量（如 `PYTHONUNBUFFERED=1`）和使用 `-u` 参数，并且默认工作目录是项目根目录。这些因素组合在一起触发了 Werkzeug 服务器在 Windows + Python 3.12 上的一个底层行为差异，导致 `app.run()` 启动后立即退出。

PowerShell 独立窗口从 `testrealend` 目录运行时没有这些额外环境变量，避开了这个问题。

### v2.4.0 的修复方案

| 问题 | 修复 |
|---|---|
| 假 KeyboardInterrupt | `except Exception` → `except BaseException`（3 处） |
| `app.run()` 静默返回 | 替换为 `werkzeug.serving.make_server()` + 子线程 + 主线程永久阻塞 |
| CWD 差异 | 启动时自动 `os.chdir()` 到脚本目录 |
| SocketIO 干扰 | Windows 上跳过 `flask-socketio` 初始化 |

现在三种启动方式（PowerShell 独立窗口、PowerShell 从根目录、VS Code）表现完全一致，都能稳定运行。

---

## 已知的 Windows 兼容性问题

### 1. `app.run()` 在 Windows + Python 3.12 上静默返回

**症状：** 终端打印完 `* Debug mode: off` 立即回到提示符。

**修复方法（v2.4.0）：**
- `app.run()` → `werkzeug.serving.make_server()` + 子线程
- `create_app()` 外层 `try/except KeyboardInterrupt` 重试 3 次

**涉及文件：** [app.py](app.py)（启动逻辑）、[utils/cache.py](utils/cache.py)（`except BaseException`）

### 2. SocketIO 初始化导致服务不阻塞

**症状：** `SocketIO(app, async_mode="threading")` 初始化后 `app.run()` 立即返回。

**修复方法：** Windows 上跳过 `flask-socketio`，通知降级为 HTTP 轮询。

**涉及文件：** [utils/websocket.py](utils/websocket.py)

### 3. 端口被占用

启动时自动清理端口 5003 上的旧进程，日志显示 `Killed stale process (PID xxxx)`。

---

## 验证服务是否运行

```powershell
curl http://127.0.0.1:5003/api/health
# 返回: {"status": "healthy", ...}
```

---

## 版本历史

| 版本 | 说明 |
|---|---|
| v2.4.0 | 修复 Windows 启动兼容性（`make_server` + `except BaseException` + SocketIO 跳过） |
| v2.3.2 | Socket.IO 稳定性改进，启动重试循环 |
| v2.3.1 | 修复 ruff 检查问题 |
| v2.3.0 | CI/CD 集成 |
