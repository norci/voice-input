# 重构计划 V2 - voice-input 项目

## 概述

消除循环依赖并修复 ruff 规则禁用问题。

**当前状态**:
- 分支: main
- 测试: 53/53 通过
- 提交: 领先 origin/main 17 个提交

**目标**:
1. 清理死代码
2. 将中文标点换成半角符号
3. 消除循环依赖 (PLW0603, PLC0415, N806)
4. 移除不必要的 ruff 规则禁用
5. 整理代码结构

---

## 任务 1: 清理死代码

**目标**: 移除所有未使用的函数、类、变量

**分析**:
- `connection_manager.py` 存在两份 (root vs network/)
- `voice_manager.py` 与 `voice_service.py` 功能重复
- 需使用 `ruff check --select=UNUSED` 和 AST 分析

**验收标准**:
- `ruff check src/voice_input --select=F401,F811` 无未使用导入
- 无未定义的变量引用

**文件变更**:
- `src/voice_input/connection_manager.py` → 删除 (保留 network/ 版本)
- `src/voice_input/voice_manager.py` → 删除 (已被 voice_service.py 替代)
- 检查其他潜在死代码

---

## 任务 2: 中文标点 → 半角符号

**目标**: 修复 RUF001, RUF002, RUF003 规则

**变更规则**:
| 中文标点 | 半角符号 |
|---------|---------|
| `，` | `,` |
| `。` | `.` |
| `！` | `!` |
| `？` | `?` |
| `；` | `;` |
| `：` | `:` |
| `""` | `""` |
| `''` | `''` |
| `（` | `(` |
| `）` | `)` |
| `【` | `[` |
| `】` | `]` |

**涉及文件** (根据 grep 结果):
- `src/voice_input/voice_service.py`
- `src/voice_input/voice_manager.py`
- `src/voice_input/state_manager.py`
- `src/voice_input/voice_gui.py`
- `src/voice_input/gui/*.py`
- `src/voice_input/interfaces.py`

**验收标准**:
- `ruff check src/ --select=RUF001,RUF002,RUF003` 无警告
- 移除 ruff.toml 中 RUF001, RUF002, RUF003 禁用

---

## 任务 3: 消除循环依赖

**问题根源**:
```python
# service_factory.py
from voice_input.services.voice_service import VoiceService  # 导入

class ServiceFactory:
    def create_voice_service(self, config):
        return VoiceService(config)  # 使用

# voice_service.py
from voice_input.services.service_factory import ServiceFactory  # 导入

class VoiceService:
    def __init__(self, config, factory=None):
        if factory is None:
            from voice_input.services.service_factory import ServiceFactory  # 延迟导入
            self._factory = ServiceFactory()
```

**当前解决方案** (反模式):
- 使用全局变量 `_VoiceService` 缓存
- 使用延迟导入
- 禁用 PLW0603 (全局变量更新)
- 禁用 PLC0415 (函数内导入)
- 禁用 N806 (函数内变量大写)

**推荐方案**: 依赖注入 + 接口解耦

```python
# interfaces.py - 添加新接口
class IAudioEngineFactory(Protocol):
    """音频引擎工厂接口"""
    def create(self, config: Any) -> IAudioEngine: ...

class IServiceContainer(Protocol):
    """服务容器接口"""
    def get_audio_engine(self) -> IAudioEngine: ...
```

**重构步骤**:

### 步骤 3.1: 提取 IAudioEngineFactory 接口
- 在 `interfaces.py` 添加 `IAudioEngineFactory` 接口
- 将 `AudioEngine.__init__` 的逻辑提取为工厂方法

### 步骤 3.2: 重构 service_factory.py
```python
# 移除全局变量和延迟导入
# 依赖注入而不是内部创建

class ServiceFactory:
    def __init__(self, audio_engine_factory: IAudioEngineFactory | None = None):
        self._audio_engine_factory = audio_engine_factory or DefaultAudioEngineFactory()

    def create_audio_engine(self, config) -> IAudioEngine:
        return self._audio_engine_factory.create(config)

    def create_connection_manager(self, config) -> IConnectionManager:
        return ConnectionManager(config)

    def create_voice_service(self, config) -> VoiceService:
        return VoiceService(config, self)
```

### 步骤 3.3: 重构 voice_service.py
```python
# 移除函数内导入
# 使用构造函数注入

class VoiceService(IVoiceService):
    def __init__(
        self,
        config: AsrClientConfig,
        audio_engine: IAudioEngine | None = None,
    ) -> None:
        self._config = config
        self._audio_engine = audio_engine or AudioEngine(config)
        # ...
```

**验收标准**:
- `ruff check src/ --select=PLW0603,PLC0415,N806` 无警告
- `ruff.toml` 移除 PLW0603, PLC0415, N806 禁用
- 无全局变量用于延迟导入

---

## 任务 4: 整理代码结构

**问题**:
- `audio_engine.py`, `socket_manager.py` 仍在 root 级别
- 应移动到 `audio/` 和 `network/` 子包

**目标结构**:
```
src/voice_input/
├── __init__.py
├── interfaces.py          # 接口定义 (保持)
├── asr_config.py          # 配置 (保持)
├── config_loader.py       # 配置 (保持)
├── audio/
│   ├── __init__.py
│   ├── audio_engine.py    # ← 从 root 移入
│   └── audio_recorder.py
├── network/
│   ├── __init__.py
│   ├── socket_manager.py   # ← 从 root 移入
│   └── connection_manager.py
├── services/
│   ├── __init__.py
│   ├── voice_service.py
│   ├── event_bus.py
│   └── service_factory.py
└── gui/
    ├── __init__.py
    ├── voice_app.py
    ├── voice_window.py
    ├── ui_manager.py
    └── text_injector.py
```

**注意事项**:
- 更新所有导入路径
- 更新 `__init__.py` 导出
- 更新 `pyproject.toml` 的 package 配置 (如需要)

---

## 并行执行策略

使用 4 个 git worktree 并行开发:

```bash
# 创建 worktree
git worktree add ../wt-dead-code feature/cleanup
git worktree add ../wt-punctuation feature/punctuation
git worktree add ../wt-circular-dep feature/circular-dep
git worktree add ../wt-structure feature/structure
```

| Worktree | 任务 | 依赖 |
|---------|------|------|
| wt-dead-code | 任务 1: 清理死代码 | 无 |
| wt-punctuation | 任务 2: 中文标点 | 无 |
| wt-circular-dep | 任务 3: 循环依赖 | 无 |
| wt-structure | 任务 4: 代码结构 | 任务 3 完成 |

**合并顺序**:
1. wt-dead-code → main
2. wt-punctuation → main
3. wt-circular-dep → main
4. wt-structure → main (最后，因为可能影响其他任务)

---

## 验收测试

每个任务完成后必须通过:

```bash
# 运行所有测试
pytest -q

# ruff 检查
ruff check src/voice_input/

# 类型检查 (如有)
mypy src/voice_input/
```

**最终目标**:
- `ruff.toml` 禁用规则 ≤ 15 条 (当前 22 条)
- 无循环依赖相关规则禁用
- 无中文标点相关规则禁用
- 测试 53/53 通过
