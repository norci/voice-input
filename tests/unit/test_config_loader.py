"""配置模块单元测试。

Tests for Story 1.2: 配置加载器
"""

import tempfile
from pathlib import Path

from src.voice_input.config_loader import (
    AsrConfig,
    AudioConfig,
    Config,
    WindowConfig,
    create_default_config,
    load_config,
    save_config,
)


class TestAsrConfig:
    """AsrConfig 类测试。"""

    def test_default_values(self) -> None:
        """测试默认值。"""
        config = AsrConfig()

        assert config.server_host == "127.0.0.1"
        assert config.server_port == 10095
        assert config.server_mode == "2pass"
        assert config.chunk_size == "5,10,5"
        assert config.chunk_interval == 10

    def test_custom_values(self) -> None:
        """测试自定义值。"""
        config = AsrConfig(
            server_host="192.168.1.100",
            server_port=8080,
            server_mode="offline",
            chunk_size="10,20,10",
            chunk_interval=20,
        )

        assert config.server_host == "192.168.1.100"
        assert config.server_port == 8080
        assert config.server_mode == "offline"
        assert config.chunk_size == "10,20,10"
        assert config.chunk_interval == 20


class TestAudioConfig:
    """AudioConfig 类测试。"""

    def test_default_values(self) -> None:
        """测试默认值。"""
        config = AudioConfig()

        assert config.gain == 0.5
        assert config.threshold == 0.01

    def test_custom_values(self) -> None:
        """测试自定义值。"""
        config = AudioConfig(gain=0.3, threshold=0.05)

        assert config.gain == 0.3
        assert config.threshold == 0.05


class TestWindowConfig:
    """WindowConfig 类测试。"""

    def test_default_values(self) -> None:
        """测试默认值。"""
        config = WindowConfig()

        # WindowConfig 暂无自定义字段
        assert config is not None


class TestConfig:
    """Config 类测试。"""

    def test_default_values(self) -> None:
        """测试默认值。"""
        config = Config()

        assert config.asr.server_host == "127.0.0.1"
        assert config.asr.server_port == 10095
        assert config.audio.gain == 0.5
        assert config.audio.threshold == 0.01

    def test_from_dict_empty(self) -> None:
        """测试从空字典创建。"""
        config = Config.from_dict({})

        assert config.asr.server_host == "127.0.0.1"
        assert config.asr.server_port == 10095
        assert config.audio.gain == 0.5
        assert config.audio.threshold == 0.01

    def test_from_dict_partial(self) -> None:
        """测试从部分字典创建。"""
        data: dict[str, object] = {"window": {}}
        config = Config.from_dict(data)

        # Window config should be empty
        assert config.window is not None
        assert config.asr.server_host == "127.0.0.1"  # 默认值
        assert config.audio.gain == 0.5  # 默认值
        assert config.audio.threshold == 0.01  # 默认值

    def test_from_dict_full(self) -> None:
        """测试从完整字典创建。"""
        data = {
            "asr": {
                "server_host": "192.168.1.100",
                "server_port": 8080,
                "server_mode": "offline",
                "chunk_size": "10,20,10",
                "chunk_interval": 20,
            },
            "audio": {
                "gain": 0.3,
                "threshold": 0.05,
            },
            "window": {},
        }
        config = Config.from_dict(data)

        assert config.asr.server_host == "192.168.1.100"
        assert config.asr.server_port == 8080
        assert config.asr.server_mode == "offline"
        assert config.asr.chunk_size == "10,20,10"
        assert config.asr.chunk_interval == 20
        assert config.audio.gain == 0.3
        assert config.audio.threshold == 0.05

    def test_to_dict(self) -> None:
        """测试转换为字典。"""
        config = Config(
            asr=AsrConfig(
                server_host="192.168.1.100",
                server_port=8080,
                server_mode="offline",
                chunk_size="10,20,10",
                chunk_interval=20,
            ),
            audio=AudioConfig(gain=0.3, threshold=0.05),
            window=WindowConfig(),
        )

        data = config.to_dict()

        assert data["asr"]["server_host"] == "192.168.1.100"
        assert data["asr"]["server_port"] == 8080
        assert data["asr"]["server_mode"] == "offline"
        assert data["asr"]["chunk_size"] == "10,20,10"
        assert data["asr"]["chunk_interval"] == 20
        assert data["audio"]["gain"] == 0.3
        assert data["audio"]["threshold"] == 0.05
        assert data["window"] == {}


class TestLoadConfig:
    """load_config 函数测试。"""

    def test_load_nonexistent_file(self) -> None:
        """测试加载不存在的文件返回默认配置。"""
        config = load_config(Path("/nonexistent/path/config.toml"))

        assert config.asr.server_host == "127.0.0.1"
        assert config.asr.server_port == 10095

    def test_load_valid_file(self) -> None:
        """测试加载有效配置文件。"""
        toml_content = """
[asr]
server_host = "192.168.1.100"
server_port = 8080
server_mode = "offline"
chunk_size = "10,20,10"
chunk_interval = 20

[audio]
gain = 0.3
threshold = 0.05

[window]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)

            assert config.asr.server_host == "192.168.1.100"
            assert config.asr.server_port == 8080
            assert config.asr.server_mode == "offline"
            assert config.asr.chunk_size == "10,20,10"
            assert config.asr.chunk_interval == 20
            assert config.audio.gain == 0.3
            assert config.audio.threshold == 0.05
        finally:
            temp_path.unlink()

    def test_load_partial_file(self) -> None:
        """测试加载部分配置文件。"""
        toml_content = """
[window]
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(toml_content)
            temp_path = Path(f.name)

        try:
            config = load_config(temp_path)

            # Window config should be empty
            assert config.window is not None
            assert config.asr.server_host == "127.0.0.1"  # 默认值
            assert config.asr.server_port == 10095  # 默认值
            assert config.audio.gain == 0.5  # 默认值
            assert config.audio.threshold == 0.01  # 默认值
        finally:
            temp_path.unlink()


class TestSaveConfig:
    """save_config 函数测试。"""

    def test_save_and_load(self) -> None:
        """测试保存和加载配置。"""
        config = Config(
            asr=AsrConfig(
                server_host="192.168.1.100",
                server_port=8080,
            ),
            audio=AudioConfig(gain=0.3, threshold=0.05),
            window=WindowConfig(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "config.toml"

            save_config(config, temp_path)
            loaded_config = load_config(temp_path)

            assert loaded_config.asr.server_host == "192.168.1.100"
            assert loaded_config.asr.server_port == 8080
            assert loaded_config.audio.gain == 0.3
            assert loaded_config.audio.threshold == 0.05

    def test_save_creates_directory(self) -> None:
        """测试保存时创建目录。"""
        config = Config()

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "subdir" / "config.toml"

            save_config(config, temp_path)
            assert temp_path.exists()


class TestCreateDefaultConfig:
    """create_default_config 函数测试。"""

    def test_create_default(self) -> None:
        """测试创建默认配置。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "config.toml"

            config = create_default_config(temp_path)

            assert config.asr.server_host == "127.0.0.1"
            assert config.asr.server_port == 10095
            assert temp_path.exists()
