"""配置文件加载器。

使用 TOML 格式管理应用配置。
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli
import tomli_w

logger = logging.getLogger(__name__)


@dataclass
class AsrConfig:
    """ASR 语音识别配置。"""

    server_host: str = "127.0.0.1"
    server_port: int = 10095
    server_mode: str = "2pass"
    chunk_size: str = "5,10,5"
    chunk_interval: int = 10
    reconnect_interval: int = 3


@dataclass
class WindowConfig:
    """窗口配置。"""


@dataclass
class Config:
    """应用配置。"""

    asr: AsrConfig = field(default_factory=AsrConfig)
    window: WindowConfig = field(default_factory=WindowConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """从字典创建配置。

        Args:
            data: 配置字典

        Returns:
            Config 实例
        """
        asr_data = data.get("asr", {})

        return cls(
            asr=AsrConfig(
                server_host=asr_data.get("server_host", "127.0.0.1"),
                server_port=asr_data.get("server_port", 10095),
                server_mode=asr_data.get("server_mode", "2pass"),
                chunk_size=asr_data.get("chunk_size", "5,10,5"),
                chunk_interval=asr_data.get("chunk_interval", 10),
                reconnect_interval=asr_data.get("reconnect_interval", 3),
            ),
            window=WindowConfig(),
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。

        Returns:
            配置字典
        """
        return {
            "asr": {
                "server_host": self.asr.server_host,
                "server_port": self.asr.server_port,
                "server_mode": self.asr.server_mode,
                "chunk_size": self.asr.chunk_size,
                "chunk_interval": self.asr.chunk_interval,
                "reconnect_interval": self.asr.reconnect_interval,
            },
            "window": {},
        }


DEFAULT_CONFIG_PATH = Path("config/config.toml")


def load_config(config_path: Path | None = None) -> Config:
    """加载配置文件。

    Args:
        config_path: 配置文件路径，默认使用 config/config.toml

    Returns:
        Config 实例

    Raises:
        FileNotFoundError: 配置文件不存在
        tomli.TOMLDecodeError: TOML 解析失败
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    logger.info(f"加载配置文件：{config_path}")

    if not config_path.exists():
        logger.warning(f"配置文件不存在：{config_path}，使用默认配置")
        return Config()

    try:
        with config_path.open("rb") as f:
            data = tomli.load(f)

        config = Config.from_dict(data)
        logger.info("配置文件加载成功")

    except tomli.TOMLDecodeError as e:
        logger.error(f"TOML 解析失败：{e}")
        raise

    return config


def save_config(config: Config, config_path: Path | None = None) -> None:
    """保存配置到文件。

    Args:
        config: Config 实例
        config_path: 配置文件路径，默认使用 config/config.toml

    Raises:
        tomli_w.TOMLSerializationError: TOML 序列化失败
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    logger.info(f"保存配置文件：{config_path}")

    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with config_path.open("wb") as f:
            tomli_w.dump(config.to_dict(), f)

        logger.info("配置文件保存成功")

    except Exception as e:
        logger.error(f"配置文件保存失败：{e}")
        raise


def create_default_config(config_path: Path | None = None) -> Config:
    """创建默认配置文件。

    Args:
        config_path: 配置文件路径，默认使用 config/config.toml

    Returns:
        创建的 Config 实例
    """
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    config = Config()
    save_config(config, config_path)
    logger.info(f"已创建默认配置文件：{config_path}")
    return config
