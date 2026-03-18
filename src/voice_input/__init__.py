"""voice_input - Linux 桌面中文语音输入法

此模块提供完整的语音输入功能,包括:
- VoiceGUIWindow: GTK4 GUI 窗口
- Config: 配置加载和管理

使用示例:
    from voice_input import load_config, VoiceGUIWindow

    config = load_config()
"""

__version__ = "0.1.0"

# ASR 配置模块
from voice_input.asr_config import AsrClientConfig, ResultType

# 配置加载模块
from voice_input.config_loader import Config, load_config
from voice_input.gui import VoiceGUIApplication, VoiceGUIWindow

# 新架构模块
from voice_input.services import EventBus, ServiceFactory, VoiceService

__all__ = [
    "AsrClientConfig",
    "Config",
    "EventBus",
    "ResultType",
    "ServiceFactory",
    "VoiceGUIApplication",
    "VoiceGUIWindow",
    "VoiceService",
    "__version__",
    "load_config",
]
