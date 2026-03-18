#!/usr/bin/env python3
"""全功能紧凑 GUI 应用。

使用新架构：
1. VoiceManager - 状态控制器
2. AudioEngine - 音频处理器
3. SocketManager - Socket 管理器
"""

import logging
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from voice_input.asr_config import AsrClientConfig, ResultType
from voice_input.config_loader import Config, load_config
from voice_input.socket_manager import SocketManager
from voice_input.voice_manager import VoiceManager, VoiceState

logger = logging.getLogger(__name__)


CLICK_DEBOUNCE_MS = 500

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


class TextInjector:
    """文本注入器 - 负责将文本插入到光标位置。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_injected_text = ""

    def inject(self, text: str) -> bool:
        if not text or not isinstance(text, str) or not text.strip():
            return False

        if text == self._last_injected_text:
            return False

        with self._lock:
            try:
                result = subprocess.run(
                    ["wtype", f"{text}"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                    check=False,
                )
            except Exception:
                return False
            else:
                if result.returncode == 0:
                    self._last_injected_text = text
                    return True
                return False


class UIManager:
    """UI 管理器 - 负责管理 GUI 界面。"""

    def __init__(self, window: "VoiceGUIWindow") -> None:
        self._window = window
        self._result_label = window._result_label
        self._status_indicator = window._status_indicator
        self._toggle_button = window._toggle_button
        self._css_provider: Gtk.CssProvider | None = None

    def update_state(self, state: VoiceState, error_message: str = "") -> None:
        """根据状态更新 UI。

        Args:
            state: 当前状态
            error_message: 错误信息（仅在 ERROR 状态时使用）
        """
        color = STATE_COLORS.get(state, "#808080")
        label = STATE_LABELS.get(state, "开始识别")

        if state == VoiceState.ERROR and error_message:
            label = f"错误: {error_message[:10]}"

        logger.info(f"UIManager.update_state() - state={state.value}, label={label}")
        GLib.idle_add(self._update_status_color, color)
        GLib.idle_add(self._toggle_button.set_label, label)

    def update_result_display(self, text: str) -> None:
        """更新结果显示。"""
        GLib.idle_add(self._result_label.set_label, text)

    def clear_result_display(self) -> None:
        """清空结果显示。"""
        GLib.idle_add(self._result_label.set_label, "")

    def _update_status_color(self, color: str) -> bool:
        """更新状态指示器颜色。"""
        if self._css_provider is None:
            self._css_provider = Gtk.CssProvider()
        css = f"box {{ background-color: {color}; }}"
        self._css_provider.load_from_string(css)
        self._status_indicator.get_style_context().add_provider(
            self._css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        return False


class VoiceGUIWindow(Gtk.ApplicationWindow):
    """全功能紧凑 GUI 窗口。"""

    def __init__(self, app: Gtk.Application, config: Config) -> None:
        """初始化 GUI 窗口。"""
        super().__init__(application=app, title="Voice Input")

        self._config = config
        self._asr_config: AsrClientConfig | None = None
        self._voice_manager: VoiceManager | None = None
        self._ui_manager: UIManager
        self._is_exiting = False
        self._text_injector: TextInjector = TextInjector()

        self._last_click_time = 0
        self.CLICK_DEBOUNCE_MS = 500

        self.set_default_size(200, 100)
        self.set_decorated(False)

        self._setup_ui()
        self.connect("close-request", self._on_close)

        self._init_asr_config()
        self._init_voice_manager()

        logger.info("GUI 窗口已初始化")

    def _setup_ui(self) -> None:
        """设置窗口 UI 组件。"""
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

        self._ui_manager = UIManager(self)

    def _init_asr_config(self) -> None:
        """初始化 ASR 配置。"""
        try:
            self._asr_config = AsrClientConfig.from_config(self._config)
            logger.info("ASR 配置已加载")
        except Exception as e:
            logger.error(f"加载 ASR 配置失败: {e}")

    def _init_voice_manager(self) -> None:
        """初始化 VoiceManager。"""
        if self._asr_config is None:
            return

        self._voice_manager = VoiceManager(self._asr_config)
        self._voice_manager.set_result_callback(self._on_result)
        self._voice_manager.set_error_callback(self._on_error)
        self._voice_manager.set_state_callback(self._on_state_changed)

        self._ui_manager.update_state(VoiceState.IDLE)
        logger.info("VoiceManager 已初始化")

    def _on_toggle_clicked(self, button: Gtk.Button | None) -> None:
        """切换按钮点击事件（带防抖）。"""
        logger.info("按钮被点击!")
        now = int(time.time() * 1000)
        if now - self._last_click_time < self.CLICK_DEBOUNCE_MS:
            logger.debug("点击过于频繁，忽略")
            return
        self._last_click_time = now

        if self._voice_manager is None:
            logger.warning("_voice_manager is None")
            return

        state = self._voice_manager.state
        logger.info(f"当前状态: {state}")

        if state == VoiceState.IDLE:
            logger.info("调用 start()")
            result = self._voice_manager.start()
            logger.info(f"start() 返回: {result}")
        elif state == VoiceState.RECORDING:
            logger.info("调用 stop()")
            self._voice_manager.stop()
        elif state == VoiceState.POST_PROCESSING:
            logger.info("调用 reset()")
            self._voice_manager.reset()
        elif state == VoiceState.RECONNECTING:
            logger.info("重连中，不处理")
        elif state == VoiceState.ERROR:
            logger.info("调用 reset()")
            self._voice_manager.reset()

    def _on_quit_clicked(self, button: Gtk.Button) -> None:
        """退出按钮点击事件。"""
        self.quit_app()

    def _on_result(self, text: str, result_type: ResultType) -> None:
        """识别结果回调。"""
        GLib.idle_add(self._ui_manager.update_result_display, text)

        if result_type == ResultType.FINAL:
            GLib.idle_add(self._text_injector.inject, text)

        if self._voice_manager:
            state = self._voice_manager.state
            GLib.idle_add(self._ui_manager.update_state, state)

    def _on_error(self, error_type: str, message: str) -> None:
        """错误回调。"""
        logger.error(f"识别错误: {error_type} - {message}")
        GLib.idle_add(self._ui_manager.update_result_display, f"错误: {message}")

        if self._voice_manager:
            GLib.idle_add(
                self._ui_manager.update_state,
                VoiceState.ERROR,
                self._voice_manager.error_message,
            )

    def _on_state_changed(self, state: VoiceState, error_message: str) -> None:
        """状态变化回调。"""
        logger.info(f"_on_state_changed: {state.value}")
        GLib.idle_add(self._ui_manager.update_state, state, error_message)

    def _on_close(self, _widget: Gtk.Window) -> None:
        """处理窗口关闭事件。"""
        self.quit()

    def quit_app(self) -> None:
        """退出应用。"""
        self._is_exiting = True

        if self._voice_manager:
            self._voice_manager.stop()

        GLib.idle_add(self._do_quit)

    def _do_quit(self) -> bool:
        """实际执行退出。"""
        try:
            app = self.get_application()
            if app:
                app.quit()
            os._exit(0)
        except Exception:
            os._exit(1)
        return False


class VoiceGUIApplication(Gtk.Application):
    """全功能紧凑 GUI 应用程序。"""

    def __init__(self, config: Config) -> None:
        """初始化应用程序。"""
        super().__init__(application_id="com.voiceinput.gui", flags=0)
        self._config = config
        self._window: VoiceGUIWindow | None = None

        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if not runtime_dir or not Path(runtime_dir).is_dir():
            err_msg = "XDG_RUNTIME_DIR is not set or invalid"
            raise RuntimeError(err_msg)
        self._socket_path = f"{runtime_dir}/voice-input.sock"
        self._socket_manager = SocketManager(self._socket_path)
        self._action_queue: queue.Queue[str] = queue.Queue()

    def do_activate(self) -> None:
        """应用激活时的回调。"""
        if not self._window:
            self._window = VoiceGUIWindow(self, self._config)
            self._window.show()

            # 设置 Socket 命令处理器
            self._socket_manager.set_command_handler(self._handle_socket_command)

            # 启动 Socket 服务器
            if not self._socket_manager.start_server():
                logger.error("Socket 服务器启动失败")

            GLib.timeout_add(100, self._process_actions)
        else:
            self._window.present()

    def _handle_socket_command(self, cmd: str) -> None:
        """处理 Socket 命令。"""
        if cmd == "toggle":
            self._action_queue.put("toggle")
        elif cmd == "quit":
            self._action_queue.put("quit")
        else:
            logger.warning(f"收到未知命令: {cmd}")

    def _process_actions(self) -> bool:
        """处理回调队列（在 GTK 主线程中）。"""
        if self._window and self._window._is_exiting:
            return False
        try:
            while True:
                action = self._action_queue.get_nowait()
                if action == "toggle":
                    if self._window:
                        self._window._on_toggle_clicked(None)
                elif action == "quit" and self._window:
                    self._window.quit_app()
        except queue.Empty:
            pass
        return True

    def do_shutdown(self) -> None:
        """应用关闭时的回调。"""
        self._socket_manager.stop_server()
        super().do_shutdown()


def main() -> None:
    """主函数。"""
    log_file = "/tmp/voice_gui.log"
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.DEBUG)

    logging.getLogger("websockets").setLevel(logging.WARNING)

    config = load_config()

    app = VoiceGUIApplication(config)
    app.run()


if __name__ == "__main__":
    main()
