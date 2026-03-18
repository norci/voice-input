"""UI Manager for Voice GUI."""

import logging

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from voice_input.interfaces import VoiceState

logger = logging.getLogger(__name__)

STATE_COLORS = {
    VoiceState.IDLE: "#808080",
    VoiceState.RECORDING: "#00FF00",
    VoiceState.POST_PROCESSING: "#FFD700",
    VoiceState.RECONNECTING: "#FFA500",
    VoiceState.ERROR: "#FF0000",
}

STATE_LABELS = {
    VoiceState.IDLE: "开始识别",
    VoiceState.RECORDING: "停止识别",
    VoiceState.POST_PROCESSING: "处理中...",
    VoiceState.RECONNECTING: "重连中...",
    VoiceState.ERROR: "重置",
}


class UIManager:
    """UI manager - manages GUI interface."""

    def __init__(
        self,
        result_label: Gtk.Label,
        status_indicator: Gtk.Box,
        toggle_button: Gtk.Button,
    ) -> None:
        self._result_label = result_label
        self._status_indicator = status_indicator
        self._toggle_button = toggle_button
        self._css_provider: Gtk.CssProvider | None = None

    def update_state(self, state: VoiceState, error_message: str = "") -> None:
        """Update UI based on state.

        Args:
            state: Current state
            error_message: Error message (only used in ERROR state)
        """
        color = STATE_COLORS.get(state, "#808080")
        label = STATE_LABELS.get(state, "开始识别")

        if state == VoiceState.ERROR and error_message:
            label = f"错误: {error_message[:10]}"

        logger.info(f"UIManager.update_state() - state={state.value}, label={label}")
        GLib.idle_add(self._update_status_color, color)
        GLib.idle_add(self._toggle_button.set_label, label)

    def update_result_display(self, text: str) -> None:
        """Update result display."""
        GLib.idle_add(self._result_label.set_label, text)

    def clear_result_display(self) -> None:
        """Clear result display."""
        GLib.idle_add(self._result_label.set_label, "")

    def _update_status_color(self, color: str) -> bool:
        """Update status indicator color."""
        if self._css_provider is None:
            self._css_provider = Gtk.CssProvider()
        css = f"box {{ background-color: {color}; }}"
        self._css_provider.load_from_string(css)
        self._status_indicator.get_style_context().add_provider(
            self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        return False
