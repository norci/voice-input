"""voice_input - Linux 桌面中文语音输入法

此模块提供完整的语音输入功能，包括：
- AsrClient: FunASR WebSocket 客户端
- VoiceGUIWindow: GTK4 GUI 窗口
- Config: 配置加载和管理

使用示例:
    from voice_input import load_config, VoiceGUIWindow

    config = load_config()
"""

__version__ = "0.1.0"

# AsrClient 模块
from voice_input.asr_client import AsrClient, AsrClientConfig, AsrResult, ResultType

# 配置加载模块
from voice_input.config_loader import Config, load_config

# GUI 模块
from voice_input.voice_gui import VoiceGUIApplication, VoiceGUIWindow

__all__ = [
    "AsrClient",
    "AsrClientConfig",
    "AsrResult",
    "Config",
    "ResultType",
    "VoiceGUIApplication",
    "VoiceGUIWindow",
    "__version__",
    "load_config",
]
