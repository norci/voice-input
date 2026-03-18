"""IVoiceService implementation (Facade)."""

import logging
import threading

from voice_input.asr_config import AsrClientConfig, ResultType
from voice_input.audio_engine import AudioEngine
from voice_input.interfaces import (
    ErrorCallback,
    IAudioEngine,
    IVoiceService,
    ResultCallback,
    StateCallback,
    VoiceState,
)

logger = logging.getLogger(__name__)


class VoiceService(IVoiceService):
    """Facade implementation for voice service."""

    def __init__(self, config: AsrClientConfig) -> None:
        """Initialize voice service.

        Args:
            config: ASR client configuration
        """
        self._config = config
        self._audio_engine: IAudioEngine = AudioEngine(config)

        # State management
        self._state = VoiceState.IDLE
        self._error_message = ""

        # Callbacks
        self._result_callback: ResultCallback | None = None
        self._error_callback: ErrorCallback | None = None
        self._state_callback: StateCallback | None = None

        # Timer lock (initialized here to avoid hasattr checks)
        self._timer_lock = threading.Lock()

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
            logger.warning("Cannot start from state: %s", self._state)
            return False

        self._error_message = ""
        self._state = VoiceState.IDLE
        logger.info("VoiceService starting")

        ok: bool = self._audio_engine.start()
        if ok:
            self._state = VoiceState.RECORDING
            logger.info("State: IDLE -> RECORDING")
            self._notify_state_change()
        else:
            logger.error("Failed to start audio engine")

        return ok

    def stop(self) -> None:
        """Stop voice recognition."""
        if self._state != VoiceState.RECORDING:
            logger.warning("Cannot stop from state: %s", self._state)
            return

        logger.info("VoiceService stopping - recording and sending")
        self._audio_engine.stop_sending()
        self._state = VoiceState.POST_PROCESSING
        logger.info("State: RECORDING -> POST_PROCESSING")
        self._notify_state_change()

        def timeout_callback() -> None:
            # 使用锁保护 _audio_engine 访问
            with self._timer_lock:
                if self._state == VoiceState.POST_PROCESSING and self._audio_engine is not None:
                    logger.info("POST_PROCESSING timeout, returning to IDLE")
                    self._state = VoiceState.IDLE
                    self._audio_engine.stop()
                    self._notify_state_change()

        with self._timer_lock:
            self._post_process_timer = threading.Timer(3.0, timeout_callback)
            self._post_process_timer.daemon = True
            self._post_process_timer.start()
        logger.info("Started 3s timeout timer")

    def reset(self) -> None:
        """Reset service state."""
        logger.info("VoiceService resetting")

        with self._timer_lock:
            if self._audio_engine:
                self._audio_engine.stop()
            self._state = VoiceState.IDLE
            self._error_message = ""
        logger.info("State -> IDLE via reset")
        self._notify_state_change()

    def _notify_state_change(self) -> None:
        """Notify state change."""
        if self._state_callback:
            self._state_callback(self._state, self._error_message)

    def _on_engine_result(self, text: str, result_type: ResultType) -> None:
        """Audio engine result callback."""
        logger.debug("Result: %s: %s", result_type.value, text)

        if self._state == VoiceState.RECONNECTING:
            logger.info("Got result while reconnecting -> RECORDING")
            self._state = VoiceState.RECORDING
            self._notify_state_change()

        if result_type == ResultType.FINAL and self._state == VoiceState.POST_PROCESSING:
            logger.info("Got final result -> IDLE")
            self._state = VoiceState.IDLE
            self._audio_engine.stop()
            self._notify_state_change()

        if self._result_callback:
            self._result_callback(text, result_type)

    def _on_engine_error(self, error_type: str, message: str) -> None:
        """Audio engine error callback."""
        logger.error("Engine error: %s: %s", error_type, message)
        self._state = VoiceState.ERROR
        self._error_message = message

        if self._error_callback:
            self._error_callback(error_type, message)

    def _on_reconnecting(self, attempt: int) -> None:
        """Reconnecting callback."""
        logger.info("Reconnecting (attempt %d)", attempt)
        if self._state in (VoiceState.RECORDING, VoiceState.POST_PROCESSING):
            logger.info("State -> RECONNECTING")
            self._state = VoiceState.RECONNECTING
            self._notify_state_change()
