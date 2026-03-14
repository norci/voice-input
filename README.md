# voice-input

语音输入工具 - 支持 Hyprland 快捷键激活

## 快速开始

### 安装

#### 系统依赖

本项目需要 GTK4 和 PyGObject。请根据您的发行版安装：

**Arch Linux / Manjaro**
```bash
sudo pacman -S gtk4 python-gobject
```

**Ubuntu / Debian**
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0
```

**Fedora**
```bash
sudo dnf install python3-gobject gtk4
```

> 📖 完整的系统依赖文档请参考：[SYSTEM_DEPENDENCIES.md](SYSTEM_DEPENDENCIES.md)

#### 安装 Python 依赖

```bash
# 使用 uv 安装
uv install
```

### 基本用法

```bash
# 启动语音输入
voice-input

# 切换模式
voice-input --toggle
```

## Hyprland 快捷键配置

### 方法一：使用安装脚本（推荐）

```bash
./scripts/setup-hyprland-hotkey.sh
```

脚本将引导你完成配置：
- 自动检测 Hyprland 配置目录
- 备份现有配置
- 添加快捷键绑定
- 重新加载配置

### 方法二：手动配置

编辑 `~/.config/hypr/hyprland.conf`，添加：

```ini
# voice-input 快捷键绑定
bind = SUPER, V, exec, voice-input --toggle
```

然后重新加载配置：

```bash
hyprctl reload
```

### 自定义快捷键

```ini
# Ctrl + Alt + V
bind = CONTROL ALT, V, exec, voice-input --toggle

# Shift + V
bind = SHIFT, V, exec, voice-input --toggle

# F12
bind = , F12, exec, voice-input --toggle
```

详细配置说明请参考：[docs/story_7_1_hyprland_hotkey.md](docs/story_7_1_hyprland_hotkey.md)

## 文档

- [Story 7-1: Hyprland 快捷键配置](docs/story_7_1_hyprland_hotkey.md)
- [快捷键使用示例](docs/hotkey_usage.md)
- [项目上下文](project-context.md)

## 示例

查看 `examples/` 目录：

- `hyprland.conf.example` - Hyprland 配置文件模板
- `audio_stream_capture_example.py` - 音频流捕获示例
- `chinese_asr_example.py` - 中文识别示例

## 脚本

- `scripts/setup-hyprland-hotkey.sh` - Hyprland 快捷键安装脚本
- `scripts/manage-daemon.sh` - systemd 服务管理脚本

## systemd 服务配置

### 快速安装

```bash
# 安装服务
./scripts/manage-daemon.sh install

# 启用开机自启
./scripts/manage-daemon.sh enable

# 启动服务
./scripts/manage-daemon.sh start
```

### 管理命令

| 命令 | 说明 |
|------|------|
| `./scripts/manage-daemon.sh install` | 安装 systemd 服务 |
| `./scripts/manage-daemon.sh uninstall` | 卸载服务 |
| `./scripts/manage-daemon.sh start` | 启动服务 |
| `./scripts/manage-daemon.sh stop` | 停止服务 |
| `./scripts/manage-daemon.sh restart` | 重启服务 |
| `./scripts/manage-daemon.sh status` | 查看状态 |
| `./scripts/manage-daemon.sh enable` | 启用开机自启 |
| `./scripts/manage-daemon.sh disable` | 禁用开机自启 |
| `./scripts/manage-daemon.sh logs` | 查看日志 |

详细文档：[Story 7-3: systemd Service 配置](docs/story_7_3_systemd_service.md)

## 开发

```bash
# 运行测试
pytest

# 代码格式化
ruff format .

# 代码检查
ruff check .
```

## 许可证

MIT
