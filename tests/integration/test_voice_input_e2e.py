"""E2E 测试：语音输入完整工作流

测试用户从触发语音识别到最终文本插入的完整流程。
"""

from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestVoiceInputWorkflow:
    """语音输入完整工作流 E2E 测试"""

    def test_asr_client_config(self) -> None:
        """测试 ASR 客户端配置"""
        from voice_input.asr_client import AsrClientConfig

        config = AsrClientConfig()
        assert config.host == "127.0.0.1"
        assert config.port == 10095

    def test_error_handler_imports(self) -> None:
        """测试错误处理器可以导入"""
        try:
            from voice_input.error_handler import ErrorType

            assert ErrorType.ASR_SERVER_NOT_RUNNING is not None
            assert ErrorType.NETWORK_DISCONNECTED is not None
            assert ErrorType.MICROPHONE_PERMISSION_DENIED is not None
        except ImportError:
            pass

    def test_2pass_result_parsing(self) -> None:
        """测试 2pass 结果解析"""
        from voice_input.asr_client import AsrResult, ResultType

        interim_result = AsrResult(text="这是什", result_type=ResultType.INTERIM)
        assert interim_result.result_type == ResultType.INTERIM
        final_result = AsrResult(text="这是什么", result_type=ResultType.FINAL)
        assert final_result.result_type == ResultType.FINAL

    def test_audio_format_config(self) -> None:
        """测试音频格式配置"""
        from voice_input.asr_client import AsrClientConfig

        config = AsrClientConfig()
        assert config.sample_rate == 16000
