"""Voice GUI Window."""

from __future__ import annotations

import logging
import time

from voice_input.asr_config import ResultType
from voice_input.config_loader import Config
from voice_input.gui._gtk_init import GLib, Gtk
from voice_input.gui.text_injector import TextInjector
from voice_input.gui.ui_manager import UIManager
from voice_input.interfaces import IVoiceService, VoiceState

logger = logging.getLogger(__name__)

CLICK_DEBOUNCE_MS = 500


class VoiceGUIWindow(Gtk.ApplicationWindow):
    """Full-featured compact GUI window."""

    def __init__(
        self: VoiceGUIWindow,
        app: Gtk.Application,
        config: Config,
        voice_service: IVoiceService,
    ) -> None:
        """Initialize GUI window."""
        super().__init__(application=app, title="Voice Input")

        self._config = config
        self._voice_service = voice_service
        self._ui_manager: UIManager
        self._is_exiting = False
        self._text_injector: TextInjector = TextInjector()

        self._last_click_time = 0
        self.CLICK_DEBOUNCE_MS = CLICK_DEBOUNCE_MS  # 引用模块级常量

        self.set_default_size(200, 100)
        self.set_decorated(False)

        self._setup_ui()
        self.connect("close-request", self._on_close)

        # Wire up service callbacks
        self._voice_service.set_result_callback(self._on_result)
        self._voice_service.set_error_callback(self._on_error)
        self._voice_service.set_state_callback(self._on_state_changed)

        self._ui_manager.update_state(VoiceState.IDLE)
        logger.info("GUI 窗口已初始化")

    def _setup_ui(self: VoiceGUIWindow) -> None:
        """Setup window UI components."""
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        self.set_child(main_box)

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_row.set_valign(Gtk.Align.START)
        top_row.set_halign(Gtk.Align.FILL)
        main_box.append(top_row)

        self._status_indicator = Gtk.Box()
        self._status_indicator.set_size_request(20, 20)
        top_row.append(self._status_indicator)

        self._toggle_button = Gtk.Button(label="开始识别")
        self._toggle_button.connect("clicked", self._on_toggle_clicked)
        top_row.append(self._toggle_button)

        quit_button = Gtk.Button(label="退出")
        quit_button.connect("clicked", self._on_quit_clicked)
        quit_button.set_halign(Gtk.Align.END)
        top_row.append(quit_button)

        self._result_label = Gtk.Label(label="")
        self._result_label.set_halign(Gtk.Align.CENTER)
        self._result_label.set_wrap(True)
        self._result_label.set_max_width_chars(40)
        main_box.append(self._result_label)

    def _on_toggle_clicked(self: VoiceGUIWindow, _button: Gtk.Button | None) -> None:
        """Toggle button click event (with debounce)."""
        logger.info("Toggle clicked")
        now = int(time.time() * 1000)
        if now - self._last_click_time < self.CLICK_DEBOUNCE_MS:
            logger.debug("点击过于频繁,忽略")
            return
        self._last_click_time = now

        state = self._voice_service.state
        logger.info(f"当前状态: {state}")

        if state == VoiceState.IDLE:
            logger.info("调用 start()")
            result = self._voice_service.start()
            logger.info(f"start() 返回: {result}")
        elif state == VoiceState.RECORDING:
            logger.info("调用 stop()")
            self._voice_service.stop()
        elif state == VoiceState.POST_PROCESSING:
            logger.info("调用 reset()")
            self._voice_service.reset()
        elif state == VoiceState.RECONNECTING:
            logger.info("重连中,不处理")
        elif state == VoiceState.ERROR:
            logger.info("调用 reset()")
            self._voice_service.reset()

    def _on_quit_clicked(self: VoiceGUIWindow, _button: Gtk.Button) -> None:
        """Quit button click event."""
        self.quit_app()

    def _on_result(self: VoiceGUIWindow, text: str, result_type: ResultType) -> None:
        """Recognition result callback."""
        if not text:
            return

        state = self._voice_service.state

        if result_type == ResultType.FINAL:
            GLib.idle_add(self._text_injector.inject, text)
            GLib.idle_add(self._ui_manager.update_result_display, text)
            return

        # For intermediate results
        if state == VoiceState.IDLE:
            return

        GLib.idle_add(self._ui_manager.update_result_display, text)

    def _on_error(self: VoiceGUIWindow, error_type: str, message: str) -> None:
        """Error callback."""
        logger.error(f"识别错误: {error_type} - {message}")
        GLib.idle_add(self._ui_manager.update_result_display, f"错误: {message}")

        GLib.idle_add(
            self._ui_manager.update_state,
            VoiceState.ERROR,
            self._voice_service.error_message,
        )

    def _on_state_changed(self: VoiceGUIWindow, state: VoiceState, error_message: str) -> None:
        """State change callback."""
        logger.info(f"_on_state_changed: {state.value}")
        GLib.idle_add(self._ui_manager.update_state, state, error_message)

    def _on_close(self: VoiceGUIWindow, _widget: Gtk.Window) -> None:
        """Handle window close event."""
        self.quit()

    def quit_app(self: VoiceGUIWindow) -> None:
        """Quit application."""
        self._is_exiting = True
        self._voice_service.stop()
        GLib.idle_add(self._do_quit)

    def _do_quit(self: VoiceGUIWindow) -> bool:
        """Actual quit execution."""
        try:
            app = self.get_application()
            if app:
                app.quit()
        except Exception:
            logger.exception("退出时出错")
        return False
