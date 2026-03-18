"""Tests for UIManager."""

from unittest.mock import MagicMock

from voice_input.gui.ui_manager import UIManager
from voice_input.interfaces import VoiceState


def test_idle_state_clears_result_display() -> None:
    """Test that entering IDLE state clears the result display."""
    # Arrange
    mock_label = MagicMock()
    mock_status = MagicMock()
    mock_button = MagicMock()

    ui_manager = UIManager(
        result_label=mock_label,
        status_indicator=mock_status,
        toggle_button=mock_button,
    )

    # Set some text first
    ui_manager.update_result_display("测试文本")

    # Act - transition to IDLE state
    ui_manager.update_state(VoiceState.IDLE)

    # Assert - result display should be cleared
    mock_label.set_label.assert_called_with("")


def test_result_display_update() -> None:
    """Test that result display can be updated."""
    # Arrange
    mock_label = MagicMock()
    mock_status = MagicMock()
    mock_button = MagicMock()

    ui_manager = UIManager(
        result_label=mock_label,
        status_indicator=mock_status,
        toggle_button=mock_button,
    )

    # Act
    ui_manager.update_result_display("语音识别结果")

    # Assert
    mock_label.set_label.assert_called_with("语音识别结果")


def test_clear_result_display() -> None:
    """Test that clear_result_display works."""
    # Arrange
    mock_label = MagicMock()
    mock_status = MagicMock()
    mock_button = MagicMock()

    ui_manager = UIManager(
        result_label=mock_label,
        status_indicator=mock_status,
        toggle_button=mock_button,
    )

    # Act
    ui_manager.clear_result_display()

    # Assert
    mock_label.set_label.assert_called_with("")


def test_idle_after_result_clears_display() -> None:
    """Test that entering IDLE clears any existing result."""
    # Arrange
    mock_label = MagicMock()
    mock_status = MagicMock()
    mock_button = MagicMock()

    ui_manager = UIManager(
        result_label=mock_label,
        status_indicator=mock_status,
        toggle_button=mock_button,
    )

    # Simulate recording session
    ui_manager.update_result_display("第一次识别结果")
    ui_manager.update_state(VoiceState.RECORDING)
    ui_manager.update_result_display("中间结果")

    # Act - end of session, go back to IDLE
    ui_manager.update_state(VoiceState.IDLE)

    # Assert - should be cleared
    # Get the last call to set_label
    calls = mock_label.set_label.call_args_list
    assert calls[-1][0][0] == "", f"Expected empty string, got {calls[-1][0][0]}"


def test_non_idle_states_do_not_clear() -> None:
    """Test that non-IDLE states do not clear the display."""
    # Arrange
    mock_label = MagicMock()
    mock_status = MagicMock()
    mock_button = MagicMock()

    ui_manager = UIManager(
        result_label=mock_label,
        status_indicator=mock_status,
        toggle_button=mock_button,
    )

    ui_manager.update_result_display("测试文本")

    # Act - transition to other states
    for state in [VoiceState.RECORDING, VoiceState.POST_PROCESSING, VoiceState.RECONNECTING]:
        ui_manager.update_state(state)

    # Assert - display should NOT be cleared (set_label never called with "")
    for call in mock_label.set_label.call_args_list:
        assert call[0][0] != "", "Display should not be cleared for non-IDLE states"
