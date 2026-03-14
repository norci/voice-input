# voice-input 项目上下文

## 项目信息
- **项目名称**: voice-input
- **项目类型**: Linux 桌面中文语音输入法 (基于 FunASR)
- **项目路径**: /home/josephx/code/voice-input

## 开发规范 (所有 Sub Agent 必须遵守)

### 包管理规则 - UV

**强制要求**: 使用 `uv` 作为唯一的 Python 包管理工具

| 操作 | 正确命令 | 禁止命令 |
|------|----------|----------|
| 运行 Python | `uv run <script>` | `python <script>` |
| 初始化项目 | `uv sync` | `pip install` |
| 添加依赖 | `uv add <package>` | `uv pip install <package>` |
| 添加开发依赖 | `uv add --dev <package>` | `uv pip install <package>` |
| 移除依赖 | `uv remove <package>` | `pip uninstall <package>` |
| 更新依赖 | `uv update` | `pip install --upgrade` |

### 代码质量工具

- **ruff**: 代码检查 (`uv add --dev ruff`)
- **mypy**: 类型检查 (`uv add --dev mypy`)
- **pre-commit**: Git hooks (`uv add --dev pre-commit`)
- **pytest**: 测试 (`uv add --dev pytest`)

---

## 系统依赖

### 环境要求

- uv 0.10+

### 安装

```bash
# 安装依赖
uv sync
```

### 故障排除

- `ModuleNotFoundError: No module named 'gi'` → `uv add PyGObject`
- `command not found: uv` → `pip install uv`

### 参考

- [uv](https://github.com/astral-sh/uv)
- [PyGObject](https://pygobject.readthedocs.io/)
