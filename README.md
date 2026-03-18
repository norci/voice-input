# voice-input

Linux 桌面中文语音输入法，基于 FunASR。

## 功能特性

- 实时中文语音识别
- GTK4 图形界面
- WebSocket 与 FunASR 服务通信
- Hyprland 快捷键集成
- 支持本地 FunASR 服务器

## 环境要求

- Python 3.11+
- GTK4
- PyGObject
- sounddevice
- FunASR WebSocket 服务器 (本地或远程)
- 其他 Python 依赖（如 torch、torchaudio 等）将自动安装

## 安装

```bash
# 安装依赖
uv install

# 或使用 pip
pip install -e .
```

## 配置

编辑 `config/config.toml`：

```toml
[asr]
server_host = "127.0.0.1"
server_port = 10095
server_mode = "2pass"
chunk_size = "5,10,5"
chunk_interval = 10

[window]
```

## 使用方法

```bash
# 启动语音输入 GUI
voice-input

# 通过快捷键切换
voice-input-toggle
```

## Systemd 服务管理

项目提供了 systemd user service 管理脚本，可以自动管理 voice-input 和 funasr-wss-server 服务：

```bash
# 安装服务（自动安装 voice-input 和 funasr-wss-server）
./scripts/manage-systemd.sh install

# 卸载服务
./scripts/manage-systemd.sh uninstall
```

安装后，服务会自动启动并随用户会话启动。voice-input 服务依赖于 funasr-wss-server 服务。

手动管理服务：
```bash
# 启动服务
systemctl --user start voice-input
systemctl --user start funasr-wss-server

# 查看状态
systemctl --user status voice-input
systemctl --user status funasr-wss-server

# 停止服务
systemctl --user stop voice-input
systemctl --user stop funasr-wss-server
```

## Hyprland 快捷键配置

编辑 `~/.config/hypr/hyprland.conf`：

```ini
# 快捷键：F4 触发语音输入
bind = , F4, exec, uv --directory ~/code/voice-input run voice-input-toggle

# 窗口规则：浮动、半透明、不获取焦点
windowrule = match:class ^(com\.voiceinput\.gui)$, match:title ^(Voice Input)$, no_initial_focus on, float on, pin on, opacity 0.5
```

重新加载配置：

```bash
hyprctl reload
```

## 重要：Fcitx 输入法设置

**使用语音输入前，必须将 fcitx 切换到英文输入状态。**

原因：`wtype` 直接插入文字（非模拟键盘事件），但如果 fcitx 处于中文输入状态，会拦截并处理 `wtype` 注入的文字，导致注入错误的字符（如 `1234567890-+`）。

另外，fcitx 中文状态下的输入可能会误触发系统快捷键（如 Hyprland 的 F4 绑定），导致语音识别意外停止。

解决方法：
- 使用语音输入前，按 `Shift` 或 `Ctrl+Space` 将 fcitx 切换到英文状态
- 或者在 fcitx 配置中，将语音输入窗口设为始终使用英文输入

需要运行 FunASR WebSocket 服务器。可使用项目提供的脚本：

```bash
./scripts/funasr-wss-server.sh
```

或参考 [FunASR 官方文档](https://github.com/modelscope/FunASR) 配置服务器。

## 开发

```bash
# 运行测试
pytest

# 代码格式化
ruff format src/

# 代码检查
ruff check src/

# 类型检查
mypy src/
```

## GUI 测试

测试 GUI 时，需要启动两个独立的进程：

```bash
# 1. 启动 FunASR 服务器（如果未运行）
cd FunASR/runtime/python/websocket
uv run funasr_wss_server.py --host 127.0.0.1 --port 10095 &

# 2. 后台启动 GUI（不阻塞终端）
uv run voice-input &

# 3. 通过命令触发录音（模拟快捷键）
uv run voice-input-toggle
```

查看日志：
```bash
tail -f /tmp/voice_gui.log
```

## 项目结构

```
voice-input/
├── src/voice_input/
│   ├── __init__.py
│   ├── voice_gui.py      # 主 GUI 应用
│   ├── asr_client.py     # ASR WebSocket 客户端
│   ├── config_loader.py # 配置加载
│   └── toggle.py         # 切换命令
├── config/
│   └── config.toml       # 配置文件
├── tests/
│   ├── unit/
│   └── integration/
└── pyproject.toml
```

## 许可证

MIT
