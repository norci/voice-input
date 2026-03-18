# voice-input 项目上下文

## 项目信息
- **项目名称**: voice-input
- **项目类型**: Linux 桌面中文语音输入法 (基于 FunASR)
- **项目路径**: /home/josephx/code/voice-input

## 开发规范

### 包管理规则 - UV

**强制要求**: 使用 `uv` 作为唯一的 Python 包管理工具

| 操作 | 正确命令 |
|------|----------|
| 运行 Python | `uv run <script>` |
| 初始化项目 | `uv sync` |
| 添加依赖 | `uv add <package>` |

---

## GUI 测试规则

测试 GUI 时，禁止命令用户操作，必须用以下方式：

1. 启动 FunASR 服务器：
   ```bash
   cd FunASR/runtime/python/websocket
   uv run funasr_wss_server.py --host 127.0.0.1 --port 10095 &
   ```

2. 启动 GUI：
   ```bash
   cd /home/josephx/code/voice-input
   uv run voice-input > /tmp/voice_gui.log 2>&1 &
   sleep 4
   ```

3. 使用 Socket 操作 GUI：
   ```bash
   echo "toggle" | nc -U /run/user/1000/voice-input.sock
   echo "quit" | nc -U /run/user/1000/voice-input.sock
   ```

4. 查看日志：
   ```bash
   grep "\[状态转换\]" /tmp/voice_gui.log
   ```

## 配置

- 超时时间: 3 秒
- Socket 路径: `/run/user/1000/voice-input.sock`
- 日志文件: `/tmp/voice_gui.log`

## 模块架构

- **socket_manager.py**: Socket 服务器管理（自动清理残留文件）
- **voice_manager.py**: 状态控制器
- **audio_engine.py**: 音频处理器
- **voice_gui.py**: GUI 界面
- **connection_manager.py**: WebSocket 连接管理
- **audio_recorder.py**: 音频录制

### 故障排除

- `ModuleNotFoundError: No module named 'gi'` → `uv add PyGObject`
- `command not found: uv` → `pip install uv`

### 参考

- [uv](https://github.com/astral-sh/uv)
- [PyGObject](https://pygobject.readthedocs.io/)
