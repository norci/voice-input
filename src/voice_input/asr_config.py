"""ASR 配置模块.

定义识别结果类型和 ASR 客户端配置.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from voice_input.config_loader import Config
else:
    Config = "Config"

logger = logging.getLogger(__name__)


class ResultType(Enum):
    """识别结果类型."""

    INTERIM = "interim"  # 中间结果(实时)
    FINAL = "final"  # 最终结果


class AsrResultDict(TypedDict):
    """ASR 识别结果字典类型."""

    text: str
    mode: str
    is_final: bool


@dataclass
class AsrClientConfig:
    """ASR 客户端配置."""

    host: str = "127.0.0.1"
    port: int = 10095
    # 识别模式: offline, online, 2pass
    mode: str = "2pass"
    chunk_size: str = "5,10,5"
    chunk_interval: int = 10
    sample_rate: int = 16000
    # 音频灵敏度控制
    gain: float = 0.5  # 增益因子 (0.0 - 1.0)
    threshold: float = 0.01  # 阈值 (0.0 - 1.0)

    # Valid port range constants
    _MAX_PORT: int = 65535
    _VALID_SAMPLE_RATES: tuple[int, int, int] = (16000, 44100, 48000)

    def __post_init__(self: "AsrClientConfig") -> None:
        """Validate configuration after initialization."""
        if not self.host:
            msg = "host cannot be empty"
            raise ValueError(msg)
        if self.port <= 0 or self.port > self._MAX_PORT:
            msg = f"Invalid port: {self.port}"
            raise ValueError(msg)
        if self.sample_rate not in self._VALID_SAMPLE_RATES:
            msg = f"Unsupported sample rate: {self.sample_rate}"
            raise ValueError(msg)

    @classmethod
    def from_config(cls: type["AsrClientConfig"], config: "Config") -> "AsrClientConfig":
        """从配置创建 AsrClientConfig."""
        return cls(
            host=config.asr.server_host,
            port=config.asr.server_port,
            mode=config.asr.server_mode,
            chunk_size=config.asr.chunk_size,
            chunk_interval=config.asr.chunk_interval,
            gain=config.audio.gain,
            threshold=config.audio.threshold,
        )
