"""Voice GUI Application."""

import logging
import os
import queue
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from voice_input.config_loader import Config
from voice_input.gui.voice_window import VoiceGUIWindow
from voice_input.interfaces import IVoiceService
from voice_input.socket_manager import SocketManager

logger = logging.getLogger(__name__)


class VoiceGUIApplication(Gtk.Application):
    """Full-featured compact GUI application."""

    def __init__(self, config: Config, voice_service: IVoiceService) -> None:
        """Initialize application."""
        super().__init__(application_id="com.voiceinput.gui", flags=0)
        self._config = config
        self._voice_service = voice_service
        self._window: VoiceGUIWindow | None = None

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

    def _handle_socket_command(self, cmd: str) -> None:
        """Handle Socket command."""
        if cmd == "toggle":
            self._action_queue.put("toggle")
        elif cmd == "quit":
            self._action_queue.put("quit")
        else:
            logger.warning(f"收到未知命令: {cmd}")

    def _process_actions(self) -> bool:
        """Process callback queue (in GTK main thread)."""
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
        """Callback when application shuts down."""
        self._socket_manager.stop_server()
        super().do_shutdown()
