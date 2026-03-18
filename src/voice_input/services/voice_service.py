"""IVoiceService implementation (Facade)."""

import logging
import threading

from voice_input.asr_config import AsrClientConfig, ResultType
from voice_input.interfaces import (
    ErrorCallback,
    IAudioEngine,
    IServiceFactory,
    IVoiceService,
    ResultCallback,
    StateCallback,
    VoiceState,
)
from voice_input.services.service_factory import ServiceFactory

logger = logging.getLogger(__name__)


class VoiceService(IVoiceService):
    """Facade implementation for voice service."""

    def __init__(self, config: AsrClientConfig, factory: IServiceFactory | None = None) -> None:
        """Initialize voice service.

        Args:
            config: ASR client configuration
            factory: Optional service factory (defaults to ServiceFactory)
        """
        self._config = config
        self._factory = factory or ServiceFactory()

        # Create sub-services using factory
        self._audio_engine: IAudioEngine = self._factory.create_audio_engine(config)
        # ConnectionManager is managed by AudioEngine, but we might want to expose it if needed
        # For now, VoiceService delegates to AudioEngine as per original VoiceManager logic

        # State management
        self._state = VoiceState.IDLE
        self._error_message = ""

        # Callbacks
        self._result_callback: ResultCallback | None = None
        self._error_callback: ErrorCallback | None = None
        self._state_callback: StateCallback | None = None

        # Wire up audio engine callbacks
        self._audio_engine.set_result_callback(self._on_engine_result)
        self._audio_engine.set_error_callback(self._on_engine_error)
        self._audio_engine.set_reconnecting_callback(self._on_reconnecting)

    @property
    def state(self) -> VoiceState:
        """Get current state."""
        return self._state

    @property
    def error_message(self) -> str:
        """Get error message."""
        return self._error_message

    def set_result_callback(self, cb: ResultCallback) -> None:
        """Set result callback."""
        self._result_callback = cb

    def set_error_callback(self, cb: ErrorCallback) -> None:
        """Set error callback."""
        self._error_callback = cb

    def set_state_callback(self, cb: StateCallback) -> None:
        """Set state change callback."""
        self._state_callback = cb

    def start(self) -> bool:
        """Start voice recognition."""
        if self._state not in (VoiceState.IDLE, VoiceState.ERROR):
            logger.warning(f"[状态转换] 当前状态 {self._state}，无法开始")
            return False

        self._error_message = ""
        self._state = VoiceState.IDLE
        logger.info("[状态转换] VoiceService.start() - 正在启动...")

        ok: bool = self._audio_engine.start()
        if ok:
            self._state = VoiceState.RECORDING
            logger.info("[状态转换] IDLE -> RECORDING")
            self._notify_state_change()
        else:
            logger.error("[状态转换] VoiceService.start() - 启动音频引擎失败")

        return ok

    def stop(self) -> None:
        """Stop voice recognition."""
        if self._state != VoiceState.RECORDING:
            logger.warning(f"[状态转换] 当前状态 {self._state}，无法停止")
            return

        logger.info("[状态转换] VoiceService.stop() - 正在停止录音发送...")
        self._audio_engine.stop_sending()
        self._state = VoiceState.POST_PROCESSING
        logger.info("[状态转换] RECORDING -> POST_PROCESSING")
        self._notify_state_change()

        # Note: Timeout logic from original VoiceManager is omitted here as it's a business logic
        # specific to the application flow, but VoiceService could handle it or delegate to a timer.
        # For now, keeping it simple as per typical Facade pattern (exposing subsystem behavior).
        # The original VoiceManager had a 3s timeout to return to IDLE.
        # We will rely on the application layer (GUI) or a dedicated timer if needed,
        # or implement it here if it's core to the service.
        # Let's implement the timeout here to match original behavior.

        def timeout_callback() -> None:
            if self._state == VoiceState.POST_PROCESSING:
                logger.info("[状态转换] POST_PROCESSING 超时，自动返回 IDLE")
                self._state = VoiceState.IDLE
                self._audio_engine.stop()
                self._notify_state_change()

        timer = threading.Timer(3.0, timeout_callback)
        timer.daemon = True
        timer.start()
        logger.info("[状态转换] 已启动 3 秒超时定时器")

    def reset(self) -> None:
        """Reset service state."""
        logger.info("[状态转换] VoiceService.reset() - 正在重置...")

        if self._audio_engine:
            self._audio_engine.stop()

        self._state = VoiceState.IDLE
        self._error_message = ""
        logger.info("[状态转换] -> IDLE (通过 reset)")
        self._notify_state_change()

    def _notify_state_change(self) -> None:
        """Notify state change."""
        if self._state_callback:
            self._state_callback(self._state, self._error_message)

    def _on_engine_result(self, text: str, result_type: ResultType) -> None:
        """Audio engine result callback."""
        logger.debug(f"[结果] {result_type.value}: {text}")

        if self._state == VoiceState.RECONNECTING:
            logger.info("[状态转换] 收到识别结果，连接已恢复 -> RECORDING")
            self._state = VoiceState.RECORDING
            self._notify_state_change()

        if result_type == ResultType.FINAL and self._state == VoiceState.POST_PROCESSING:
            logger.info("[状态转换] 收到最终结果 -> IDLE")
            self._state = VoiceState.IDLE
            self._audio_engine.stop()
            self._notify_state_change()

        if self._result_callback:
            self._result_callback(text, result_type)

    def _on_engine_error(self, error_type: str, message: str) -> None:
        """Audio engine error callback."""
        logger.error(f"[错误] {error_type}: {message}")
        self._state = VoiceState.ERROR
        self._error_message = message

        if self._error_callback:
            self._error_callback(error_type, message)

    def _on_reconnecting(self, attempt: int) -> None:
        """Reconnecting callback."""
        logger.info(f"[重连] 尝试连接 (尝试 {attempt})...")
        if self._state in (VoiceState.RECORDING, VoiceState.POST_PROCESSING):
            logger.info("[状态转换] -> RECONNECTING")
            self._state = VoiceState.RECONNECTING
