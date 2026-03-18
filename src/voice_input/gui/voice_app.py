"""Voice GUI Application."""

from __future__ import annotations

import logging
import os
import queue
from pathlib import Path

from voice_input.asr_config import AsrClientConfig
from voice_input.config_loader import Config, load_config
from voice_input.gui._gtk_init import GLib, Gtk
from voice_input.gui.voice_window import VoiceGUIWindow
from voice_input.interfaces import IVoiceService
from voice_input.services.voice_service import VoiceService
from voice_input.socket_manager import SocketManager

logger = logging.getLogger(__name__)


class VoiceGUIApplication(Gtk.Application):
    """Full-featured compact GUI application."""

    def __init__(self: "VoiceGUIApplication", config: Config, voice_service: IVoiceService) -> None:
        """Initialize application."""
        super().__init__(application_id="com.voiceinput.gui", flags=0)
        self._config = config
        self._voice_service = voice_service
        self._window: VoiceGUIWindow | None = None
        self._is_exiting = False  # 公开属性供 VoiceGUIWindow 访问

        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if not runtime_dir or not Path(runtime_dir).is_dir():
            err_msg = "XDG_RUNTIME_DIR is not set or invalid"
            raise RuntimeError(err_msg)
        self._socket_path = f"{runtime_dir}/voice-input.sock"
        self._socket_manager = SocketManager(self._socket_path)
        self._action_queue: queue.Queue[str] = queue.Queue()

    def do_activate(self) -> None:
        """Callback when application is activated."""
        if not self._window:
            self._window = VoiceGUIWindow(self, self._config, self._voice_service)
            self._window.show()

            # Set Socket command handler
            self._socket_manager.set_command_handler(self._handle_socket_command)

            # Start Socket server
            if not self._socket_manager.start_server():
                logger.error("Socket 服务器启动失败")

            GLib.timeout_add(100, self._process_actions)
        else:
            self._window.present()

    def _handle_socket_command(self: "VoiceGUIApplication", cmd: str) -> None:
        """Handle Socket command."""
        if cmd == "toggle":
            self._action_queue.put("toggle")
        elif cmd == "quit":
            self._action_queue.put("quit")
        else:
            logger.warning(f"收到未知命令: {cmd}")

    def _process_actions(self: "VoiceGUIApplication") -> bool:
        """Process callback queue (in GTK main thread)."""
        if self._is_exiting:
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

    def do_shutdown(self: "VoiceGUIApplication") -> None:
        """Callback when application shuts down."""
        self._socket_manager.stop_server()
        super().do_shutdown()


def main() -> None:
    """Main entry point for the GUI application."""

    # Setup logging
    log_file = "/tmp/voice_gui.log"
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.DEBUG)
    logging.getLogger("websockets").setLevel(logging.WARNING)

    # Load config
    try:
        config = load_config()
    except Exception as e:
        logger.error(f"加载配置失败，使用默认配置: {e}", exc_info=True)
        config = Config()

    # Create ASR config and voice service
    try:
        asr_config = AsrClientConfig.from_config(config)
    except Exception:
        logger.exception("Failed to load ASR config")
        asr_config = AsrClientConfig()

    voice_service = VoiceService(asr_config)

    # Create and run application
    app = VoiceGUIApplication(config, voice_service)
    app.run()


if __name__ == "__main__":
    main()
