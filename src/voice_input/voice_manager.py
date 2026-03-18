"""语音识别状态控制器。

管理语音识别的状态机：IDLE -> RECORDING -> POST_PROCESSING -> IDLE
"""

import logging
import threading
from collections.abc import Callable

from voice_input.asr_config import AsrClientConfig, ResultType
from voice_input.audio_engine import AudioEngine
from voice_input.interfaces import VoiceState
from voice_input.state_manager import StateManager

logger = logging.getLogger(__name__)


class VoiceManager:
    """语音识别状态控制器。

    单一职责：管理状态转换，委托音频处理给 AudioEngine。
    """

    def __init__(self, config: AsrClientConfig) -> None:
        """初始化语音管理器。

        Args:
            config: ASR 配置
        """
        self._config = config

        self._audio_engine = AudioEngine(config)
        self._state_manager = StateManager(self._audio_engine)

        # 设置音频引擎回调
        self._audio_engine.set_result_callback(self._on_engine_result)
        self._audio_engine.set_error_callback(self._on_engine_error)
        self._audio_engine.set_reconnecting_callback(self._on_reconnecting)

        # 设置状态管理器回调
        self._state_manager.set_state_callback(self._on_state_changed)

        self._result_callback: Callable[[str, ResultType], None] | None = None
        self._error_callback: Callable[[str, str], None] | None = None
        self._state_callback: Callable[[VoiceState, str], None] | None = None

    @property
    def state(self) -> VoiceState:
        """获取当前状态。"""
        return self._state_manager.state

    @property
    def error_message(self) -> str:
        """获取错误信息。"""
        return self._state_manager.error_message  # type: ignore[no-any-return]

    def set_result_callback(self, cb: Callable[[str, ResultType], None]) -> None:
        """设置结果回调。"""
        self._result_callback = cb

    def set_error_callback(self, cb: Callable[[str, str], None]) -> None:
        """设置错误回调。"""
        self._error_callback = cb

    def set_state_callback(self, cb: Callable[[VoiceState, str], None]) -> None:
        """设置状态变化回调。"""
        self._state_callback = cb

    def start(self) -> bool:
        """开始识别。

        Returns:
            是否成功开始
        """
        if not self._state_manager.can_start():
            logger.warning(f"[状态转换] 当前状态 {self._state_manager.state}，无法开始")
            return False

        logger.info("[状态转换] VoiceManager.start() - 正在启动...")

        ok: bool = self._audio_engine.start()
        if ok:
            self._state_manager.transition_to(VoiceState.RECORDING)
        else:
            logger.error("[状态转换] VoiceManager.start() - 启动音频引擎失败")

        return ok

    def _on_state_changed(self, state: VoiceState, error_message: str) -> None:
        """状态变化回调。"""
        if self._state_callback:
            self._state_callback(state, error_message)

    def stop(self) -> None:
        """停止录音发送，保持连接接收结果。

        RECORDING -> POST_PROCESSING
        超时后自动返回 IDLE（如果没收到 FINAL）
        """
        if not self._state_manager.can_stop():
            logger.warning(f"[状态转换] 当前状态 {self._state_manager.state}，无法停止")
            return

        logger.info("[状态转换] VoiceManager.stop() - 正在停止录音发送...")
        self._audio_engine.stop_sending()
        self._state_manager.transition_to(VoiceState.POST_PROCESSING)

        # 超时后自动返回 IDLE
        def timeout_callback() -> None:
            if self._state_manager.state == VoiceState.POST_PROCESSING:
                logger.info("[状态转换] POST_PROCESSING 超时，自动返回 IDLE")
                self._state_manager.transition_to(VoiceState.IDLE)

        timer = threading.Timer(3.0, timeout_callback)
        timer.daemon = True
        timer.start()
        logger.info("[状态转换] 已启动 3 秒超时定时器")

    def reset(self) -> None:
        """重置到空闲状态，清除错误。

        从 POST_PROCESSING 或 ERROR 状态恢复到 IDLE。
        """
        logger.info("[状态转换] VoiceManager.reset() - 正在重置...")

        if self._audio_engine:
            self._audio_engine.stop()

        self._state_manager.transition_to(VoiceState.IDLE)

    def _on_engine_result(self, text: str, result_type: ResultType) -> None:
        """音频引擎结果回调 - 委托给状态管理器。"""
        self._state_manager.handle_result(text, result_type)

        # 始终通知用户结果回调
        if self._result_callback:
            self._result_callback(text, result_type)

    def _on_engine_error(self, error_type: str, message: str) -> None:
        """音频引擎错误回调 - 委托给状态管理器。"""
        self._state_manager.handle_error(error_type, message)

        # 始终通知用户错误回调
        if self._error_callback:
            self._error_callback(error_type, message)

    def _on_reconnecting(self, attempt: int) -> None:
        """重连回调 - 委托给状态管理器。"""
        self._state_manager.handle_reconnecting(attempt)
