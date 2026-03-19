# voice-input

## 项目
- 类型: Linux 桌面中文语音输入法 (FunASR)
- 路径: $PROJECT_ROOT

## 规范

### 包管理
使用 `uv`：
- 运行: `uv run <script>`
- 初始化: `uv sync`
- 添加依赖: `uv add <package>`

### 测试
修改代码后必须测试：

**GUI 测试**（修改 gui/ 时必须执行）：
1. 启动 FunASR: `ss -tlnp | grep 10095 || (cd FunASR/runtime/python/websocket && uv run funasr_wss_server.py --host 127.0.0.1 --port 10095 &)`
2. 启动并验证: `cd $PROJECT_ROOT && rm -f /tmp/voice_gui.log && uv run voice-input > /tmp/voice_gui.log 2>&1 & sleep 4 && cat /tmp/voice_gui.log`
3. 验证无错误
4. 退出: `echo "quit" | nc -U /run/user/1000/voice-input.sock`

**核心逻辑测试**（修改核心逻辑时必须执行）

### 代码检查
修改代码后必须运行：
```bash
ruff check src/ tests/
ruff format --check src/ tests/
mypy src/ tests/
```
禁止随意使用 `# noqa`、`# type: ignore`。误报时用官方方式排除并说明原因。

## 配置
- Socket: `/run/user/1000/voice-input.sock`
- 日志: `/tmp/voice_gui.log`
- 故障排除: `ModuleNotFoundError: No module named 'gi'` → `uv add PyGObject`
