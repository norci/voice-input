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

## 项目结构

```
voice-input/
├── src/voice_input/
│   ├── voice_gui.py      # 主 GUI 应用
│   ├── asr_client.py     # ASR WebSocket 客户端
│   ├── config_loader.py # 配置加载
│   └── toggle.py         # 切换命令
├── config/
│   └── config.toml       # 配置文件
├── tests/
└── pyproject.toml
```

## 许可证

MIT
