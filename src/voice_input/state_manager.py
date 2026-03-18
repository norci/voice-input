"""状态管理器实现 - 状态模式。

实现状态管理器接口 IStateManager 和各个状态类。
"""

import logging
from typing import Any

from voice_input.interfaces import IStateManager, StateCallback, VoiceState

logger = logging.getLogger(__name__)


class State:
    """状态基类 - 抽象基类。"""

    def __init__(self, context: "StateManager") -> None:
        """初始化状态。

        Args:
            context: 状态上下文管理器
        """
        self._context = context

    def can_start(self) -> bool:
        """检查是否可以开始识别。"""
        return False

    def can_stop(self) -> bool:
        """检查是否可以停止识别。"""
        return False

    def on_enter(self, error: str = "") -> None:
        """进入状态时的回调。"""

    def on_exit(self) -> None:
        """退出状态时的回调。"""

    def handle_result(self, text: str, result_type: Any) -> None:
        """处理识别结果。"""

    def handle_error(self, error_type: str, message: str) -> None:
        """处理错误。"""

    def handle_reconnecting(self, attempt: int) -> None:
        """处理重连事件。"""


class IdleState(State):
    """空闲状态。"""

    def can_start(self) -> bool:
        return True

    def on_enter(self, error: str = "") -> None:
        logger.info("[状态] 进入 IDLE 状态")
        if error:
            self._context._error_message = error
        else:
            self._context._error_message = ""


class RecordingState(State):
    """录音状态。"""

    def can_stop(self) -> bool:
        return True

    def on_enter(self, error: str = "") -> None:
        logger.info("[状态] 进入 RECORDING 状态")


class PostProcessingState(State):
    """后处理状态。"""

    def on_enter(self, error: str = "") -> None:
        logger.info("[状态] 进入 POST_PROCESSING 状态")

    def handle_result(self, text: str, result_type: Any) -> None:
        """处理识别结果。"""
        logger.debug(f"[结果] {result_type.value}: {text}")

        if result_type.value == "final":
            logger.info("[状态] 收到最终结果 -> IDLE")
            self._context.transition_to(VoiceState.IDLE)

    def on_exit(self) -> None:
        """退出后处理状态时停止音频引擎。"""
        self._context._audio_engine.stop()


class ReconnectingState(State):
    """重连状态。"""

    def on_enter(self, error: str = "") -> None:
        logger.info("[状态] 进入 RECONNECTING 状态")

    def handle_result(self, text: str, result_type: Any) -> None:
        """处理识别结果 - 连接已恢复。"""
        logger.info("[状态] 收到识别结果，连接已恢复 -> RECORDING")
        self._context.transition_to(VoiceState.RECORDING)


class ErrorState(State):
    """错误状态。"""

    def on_enter(self, error: str = "") -> None:
        logger.error(f"[状态] 进入 ERROR 状态: {error}")
        self._context._error_message = error


class StateManager(IStateManager):
    """状态管理器实现 - 状态模式。

    负责管理状态转换和委托给当前状态处理逻辑。
    """

    def __init__(self, audio_engine: Any) -> None:
        """初始化状态管理器。

        Args:
            audio_engine: 音频引擎实例
        """
        self._audio_engine = audio_engine
        self._error_message: str = ""
        self._state_callback: StateCallback | None = None

        # 初始化状态实例
        self._states: dict[VoiceState, State] = {
            VoiceState.IDLE: IdleState(self),
            VoiceState.RECORDING: RecordingState(self),
            VoiceState.POST_PROCESSING: PostProcessingState(self),
            VoiceState.RECONNECTING: ReconnectingState(self),
            VoiceState.ERROR: ErrorState(self),
        }

        self._current_state_enum = VoiceState.IDLE
        self._current_state: State = self._states[VoiceState.IDLE]

    @property
    def state(self) -> VoiceState:
        """获取当前状态。"""
        return self._current_state_enum

    @property
    def error_message(self) -> str:
        """获取错误信息。"""
        return self._error_message

    def transition_to(self, new_state: VoiceState, error: str = "") -> None:
        """状态转换。

        Args:
            new_state: 新状态
            error: 错误信息（仅在 ERROR 状态时使用）
        """
        old_state = self._current_state_enum
        if old_state == new_state:
            return

        logger.info(f"[状态转换] {old_state.value} -> {new_state.value}")

        # 退出旧状态
        self._current_state.on_exit()

        # 进入新状态
        self._current_state_enum = new_state
        self._current_state = self._states[new_state]
        self._current_state.on_enter(error)

        # 通知状态变化回调
        if self._state_callback:
            self._state_callback(self._current_state_enum, self._error_message)

    def can_start(self) -> bool:
        """检查是否可以开始识别。"""
        return self._current_state.can_start()

    def can_stop(self) -> bool:
        """检查是否可以停止识别。"""
        return self._current_state.can_stop()

    def set_state_callback(self, cb: StateCallback) -> None:
        """设置状态变化回调。"""
        self._state_callback = cb

    def handle_result(self, text: str, result_type: Any) -> None:
        """处理识别结果 - 委托给当前状态。"""
        self._current_state.handle_result(text, result_type)

    def handle_error(self, error_type: str, message: str) -> None:
        """处理错误 - 委托给当前状态。"""
        self._current_state.handle_error(error_type, message)

    def handle_reconnecting(self, attempt: int) -> None:
        """处理重连事件 - 委托给当前状态。"""
        self._current_state.handle_reconnecting(attempt)
