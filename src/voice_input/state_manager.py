"""State manager implementation - State pattern."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from voice_input.interfaces import IStateManager, StateCallback, VoiceState

if TYPE_CHECKING:
    from voice_input.interfaces import IAudioEngine

logger = logging.getLogger(__name__)


class State:
    """Base state class."""

    def __init__(self, context: StateManager) -> None:
        """Initialize state.

        Args:
            context: State context manager
        """
        self._context = context

    def can_start(self) -> bool:
        """Check if can start."""
        return False

    def can_stop(self) -> bool:
        """Check if can stop."""
        return False

    def on_enter(self, error: str = "") -> None:
        """Callback when entering state."""

    def on_exit(self) -> None:
        """Callback when exiting state."""

    def handle_result(self, text: str, result_type: object) -> None:
        """Handle recognition result."""

    def handle_error(self, error_type: str, message: str) -> None:
        """Handle error."""

    def handle_reconnecting(self, attempt: int) -> None:
        """Handle reconnecting event."""


class IdleState(State):
    """Idle state."""

    def can_start(self) -> bool:
        return True

    def on_enter(self, error: str = "") -> None:
        if error:
            self._context._error_message = error
        else:
            self._context._error_message = ""


class RecordingState(State):
    """Recording state."""

    def can_stop(self) -> bool:
        return True


class PostProcessingState(State):
    """Post-processing state."""

    def handle_result(self, _text: str, result_type: object) -> None:
        """Handle recognition result."""
        if hasattr(result_type, "value") and result_type.value == "final":
            self._context.transition_to(VoiceState.IDLE)

    def on_exit(self) -> None:
        """Stop audio engine when exiting."""
        self._context._audio_engine.stop()


class ReconnectingState(State):
    """Reconnecting state."""

    def handle_result(self, _text: str, _result_type: object) -> None:
        """Handle result - connection restored."""
        self._context.transition_to(VoiceState.RECORDING)


class ErrorState(State):
    """Error state."""

    def on_enter(self, error: str = "") -> None:
        self._context._error_message = error


class StateManager(IStateManager):
    """State manager implementation - State pattern.

    Manages state transitions and delegates to current state.
    """

    def __init__(self, audio_engine: IAudioEngine) -> None:
        """Initialize state manager.

        Args:
            audio_engine: Audio engine instance
        """
        self._audio_engine = audio_engine
        self._error_message: str = ""
        self._state_callback: StateCallback | None = None

        # Initialize state instances
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
        """Get current state."""
        return self._current_state_enum

    @property
    def error_message(self) -> str:
        """Get error message."""
        return self._error_message

    def transition_to(self, new_state: VoiceState, error: str = "") -> None:
        """Transition to new state.

        Args:
            new_state: New state
            error: Error message (only used for ERROR state)
        """
        old_state = self._current_state_enum
        if old_state == new_state:
            return

        logger.info("[state] %s -> %s", old_state.value, new_state.value)

        # Exit old state
        self._current_state.on_exit()

        # Enter new state
        self._current_state_enum = new_state
        self._current_state = self._states[new_state]
        self._current_state.on_enter(error)

        # Notify state callback
        if self._state_callback:
            self._state_callback(self._current_state_enum, self._error_message)

    def can_start(self) -> bool:
        """Check if can start."""
        return self._current_state.can_start()

    def can_stop(self) -> bool:
        """Check if can stop."""
        return self._current_state.can_stop()

    def set_state_callback(self, cb: StateCallback) -> None:
        """Set state callback."""
        self._state_callback = cb

    def handle_result(self, text: str, result_type: object) -> None:
        """Handle result - delegate to current state."""
        self._current_state.handle_result(text, result_type)

    def handle_error(self, error_type: str, message: str) -> None:
        """Handle error - delegate to current state."""
        self._current_state.handle_error(error_type, message)

    def handle_reconnecting(self, attempt: int) -> None:
        """Handle reconnecting - delegate to current state."""
        self._current_state.handle_reconnecting(attempt)
