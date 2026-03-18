"""VoiceRecorder 和 ConnectionManager 单元测试。

测试重构后的预初始化模式：
- ConnectionManager 同步连接
- VoiceRecorder 资源复用（start/stop_recording_only）
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestConnectionManager:
    """ConnectionManager 类测试。"""

    def test_init_creates_uri(self) -> None:
        """测试初始化时创建正确的 URI。"""
        from voice_input.asr_config import AsrClientConfig

        config = AsrClientConfig(host="192.168.1.100", port=8080)
        from voice_input.connection_manager import ConnectionManager

        cm = ConnectionManager(config)

        assert cm._uri == "wss://192.168.1.100:8080"

    def test_init_default_values(self) -> None:
        """测试默认初始化值。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.connection_manager import ConnectionManager, ConnectionState

        config = AsrClientConfig()
        cm = ConnectionManager(config)

        assert cm._state == ConnectionState.DISCONNECTED
        assert cm._ws is None

    @pytest.mark.asyncio()
    async def test_connect_sets_connected_state(self) -> None:
        """测试连接成功后状态为 CONNECTED。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.connection_manager import ConnectionManager, ConnectionState

        config = AsrClientConfig()
        cm = ConnectionManager(config)

        mock_ws = MagicMock()
        mock_ws.send = AsyncMock()

        with patch("websockets.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_ws
            await cm.connect()

            assert cm._state == ConnectionState.CONNECTED
            assert cm._ws is not None


class TestVoiceRecorder:
    """VoiceRecorder 类测试。"""

    def test_init_creates_queue(self) -> None:
        """测试初始化时创建音频队列。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.voice_gui import VoiceRecorder

        config = AsrClientConfig()

        vr = VoiceRecorder(
            asr_config=config,
            on_result_callback=lambda text, result_type: None,
        )

        assert vr._audio_queue is not None
        assert vr._audio_queue.empty()

    def test_init_sets_config(self) -> None:
        """测试初始化时保存配置。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.voice_gui import VoiceRecorder

        config = AsrClientConfig(
            host="192.168.1.100",
            port=8080,
            sample_rate=16000,
        )

        vr = VoiceRecorder(
            asr_config=config,
            on_result_callback=lambda text, result_type: None,
        )

        assert vr._config.host == "192.168.1.100"
        assert vr._config.port == 8080
        assert vr._config.sample_rate == 16000

    def test_init_default_values(self) -> None:
        """测试默认初始化值。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.voice_gui import VoiceRecorder

        config = AsrClientConfig()
        vr = VoiceRecorder(
            asr_config=config,
            on_result_callback=lambda text, result_type: None,
        )

        assert vr._is_recording is False
        assert vr._force_stop is False
        assert vr._audio_recorder is None
        assert vr._conn_manager is None

    def test_start_recording_only_creates_recorder(self) -> None:
        """测试 start_recording_only 创建 AudioRecorder。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.voice_gui import VoiceRecorder

        config = AsrClientConfig()
        vr = VoiceRecorder(
            asr_config=config,
            on_result_callback=lambda text, result_type: None,
        )

        with patch("voice_input.voice_gui.AudioRecorder") as mock_recorder_class:
            with patch("voice_input.voice_gui.asyncio.create_task") as mock_create_task:
                mock_task = MagicMock()
                mock_create_task.return_value = mock_task

                mock_recorder = MagicMock()
                mock_recorder_class.return_value = mock_recorder

                vr.start_recording_only()

                mock_recorder_class.assert_called_once()
                mock_recorder.start.assert_called_once()
                mock_create_task.assert_called_once()
                assert vr._is_recording is True

    def test_start_recording_only_reuses_existing_recorder(self) -> None:
        """测试 start_recording_only 复用已有 AudioRecorder。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.voice_gui import VoiceRecorder

        config = AsrClientConfig()
        vr = VoiceRecorder(
            asr_config=config,
            on_result_callback=lambda text, result_type: None,
        )

        mock_existing_recorder = MagicMock()
        vr._audio_recorder = mock_existing_recorder

        with patch("voice_input.voice_gui.AudioRecorder") as mock_recorder_class:
            with patch("voice_input.voice_gui.asyncio.create_task") as mock_create_task:
                vr.start_recording_only()

                mock_recorder_class.assert_not_called()
                mock_existing_recorder.start.assert_called_once()

    def test_stop_recording_only_stops_recorder(self) -> None:
        """测试 stop_recording_only 停止 AudioRecorder。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.voice_gui import VoiceRecorder

        config = AsrClientConfig()
        vr = VoiceRecorder(
            asr_config=config,
            on_result_callback=lambda text, result_type: None,
        )

        mock_recorder = MagicMock()
        vr._audio_recorder = mock_recorder
        vr._is_recording = True

        vr.stop_recording_only()

        mock_recorder.stop.assert_called_once()
        assert vr._is_recording is False

    def test_stop_recording_only_handles_none_recorder(self) -> None:
        """测试 stop_recording_only 处理无 AudioRecorder 的情况。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.voice_gui import VoiceRecorder

        config = AsrClientConfig()
        vr = VoiceRecorder(
            asr_config=config,
            on_result_callback=lambda text, result_type: None,
        )

        vr._audio_recorder = None
        vr._is_recording = True

        vr.stop_recording_only()

        assert vr._is_recording is False


class TestVoiceRecorderCallbacks:
    """VoiceRecorder 回调测试。"""

    def test_result_callback_called(self) -> None:
        """测试结果回调被正确调用。"""
        from voice_input.asr_config import AsrClientConfig, ResultType
        from voice_input.voice_gui import VoiceRecorder

        result_received = {}

        def on_result(text: str, result_type: ResultType) -> None:
            result_received["text"] = text
            result_received["type"] = result_type

        config = AsrClientConfig()
        vr = VoiceRecorder(
            asr_config=config,
            on_result_callback=on_result,
        )

        vr._on_result_callback("测试文本", ResultType.FINAL)

        assert result_received["text"] == "测试文本"
        assert result_received["type"] == ResultType.FINAL

    def test_error_callback_called(self) -> None:
        """测试错误回调被正确调用。"""
        from voice_input.asr_config import AsrClientConfig
        from voice_input.voice_gui import VoiceRecorder

        error_received = {}

        def on_error(error_type: str, message: str) -> None:
            error_received["type"] = error_type
            error_received["message"] = message

        config = AsrClientConfig()
        vr = VoiceRecorder(
            asr_config=config,
            on_result_callback=lambda text, rt: None,
            on_error_callback=on_error,
        )

        vr._on_error_callback("CONNECTION_FAILED", "连接超时")

        assert error_received["type"] == "CONNECTION_FAILED"
        assert error_received["message"] == "连接超时"
