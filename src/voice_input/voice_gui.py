#!/usr/bin/env python3
"""全功能紧凑 GUI 应用 - 重构版本。

重构后的代码结构：
1. 分离职责：UI、录音、ASR 通信、文本注入
2. 简化回调结构
3. 清晰的状态管理
"""

import asyncio
import atexit
import logging
import os
import queue
import socket
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

import contextlib

from gi.repository import GLib, Gtk

from voice_input.asr_client import AsrClient, AsrClientConfig, ResultType
from voice_input.config_loader import Config, load_config

logger = logging.getLogger(__name__)


# ============================================================================
# 文本注入器
# ============================================================================
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


# ============================================================================
# 语音识别管理器
# ============================================================================
class RecognitionManager:
    """语音识别管理器 - 负责管理语音识别流程。"""

    def __init__(
        self,
        asr_client: AsrClient,
        on_result_callback: Callable[[str, ResultType], None],
        on_error_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        """初始化语音识别管理器。

        Args:
            asr_client: ASR 客户端
            on_result_callback: 结果回调函数
            on_error_callback: 错误回调函数
        """
        self._asr_client = asr_client
        self._on_result_callback = on_result_callback
        self._on_error_callback = on_error_callback
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[str] | None = None

    async def start_recognition(self) -> str:
        """开始语音识别。"""
        self._stop_event.clear()

        async def on_result(text: str, result_type: ResultType) -> None:
            if not text or not isinstance(text, str):
                return
            self._on_result_callback(text, result_type)

        try:
            final_text: str = await self._asr_client.recognize_with_stop(
                stop_event=self._stop_event,
                on_result=on_result,
            )
        except Exception as e:
            if self._on_error_callback:
                self._on_error_callback("RECORDING_START_FAILED", str(e))
            return ""
        else:
            return final_text

    def stop_recognition(self) -> None:
        """停止语音识别。"""
        self._stop_event.set()


# ============================================================================
# UI 管理器
# ============================================================================
class UIManager:
    """UI 管理器 - 负责管理 GUI 界面。"""

    def __init__(self, window: "VoiceGUIWindow") -> None:
        """初始化 UI 管理器。

        Args:
            window: GUI 窗口
        """
        self._window = window
        self._result_label = window._result_label
        self._status_indicator = window._status_indicator
        self._toggle_button = window._toggle_button

    def update_status(self, is_recording: bool) -> None:
        """更新录音状态。

        Args:
            is_recording: 是否正在录音
        """
        color = "#00FF00" if is_recording else "#808080"
        label = "停止识别" if is_recording else "开始识别"

        GLib.idle_add(self._update_status_color, color)
        GLib.idle_add(self._toggle_button.set_label, label)

    def update_result_display(self, text: str) -> None:
        """更新结果显示。

        Args:
            text: 要显示的文本
        """
        self._result_label.set_label(text)

    def clear_result_display(self) -> None:
        """清空结果显示。"""
        GLib.idle_add(self._result_label.set_label, "")

    def _update_status_color(self, color: str) -> bool:
        """更新状态指示器颜色。

        Args:
            color: 十六进制颜色值

        Returns:
            False 表示单次执行
        """
        css_provider = Gtk.CssProvider()
        css = f"box {{ background-color: {color}; }}"
        css_provider.load_from_string(css)
        self._status_indicator.get_style_context().add_provider(
            css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        return False


# ============================================================================
# GUI 窗口
# ============================================================================
class VoiceGUIWindow(Gtk.ApplicationWindow):
    """全功能紧凑 GUI 窗口。"""

    def __init__(self, app: Gtk.Application, config: Config) -> None:
        """初始化 GUI 窗口。"""
        super().__init__(application=app, title="Voice Input")

        self._config = config
        self._asr_client: AsrClient | None = None
        self._recognition_manager: RecognitionManager | None = None
        self._ui_manager: UIManager
        self._is_recording = False
        self._text_injector: TextInjector = TextInjector()

        # 窗口配置
        self.set_default_size(200, 100)
        self.set_decorated(False)  # 无边框

        # 创建 UI
        self._setup_ui()

        # 连接关闭事件
        self.connect("close-request", self._on_close)

        # 初始化 ASR 客户端
        self._init_asr_client()

        logger.info("GUI 窗口已初始化")

    def _setup_ui(self) -> None:
        """设置窗口 UI 组件。"""
        # 主容器
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(10)
        main_box.set_margin_bottom(10)
        self.set_child(main_box)

        # 状态指示器 + 按钮（同一行）
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_row.set_valign(Gtk.Align.START)
        top_row.set_halign(Gtk.Align.FILL)
        main_box.append(top_row)

        # 状态指示器（左上角小颜色块）
        self._status_indicator = Gtk.Box()
        self._status_indicator.set_size_request(20, 20)
        top_row.append(self._status_indicator)

        # 开始/停止按钮（左对齐）
        self._toggle_button = Gtk.Button(label="开始识别")
        self._toggle_button.connect("clicked", self._on_toggle_clicked)
        top_row.append(self._toggle_button)

        # 退出按钮（右侧）
        quit_button = Gtk.Button(label="退出")
        quit_button.connect("clicked", self._on_quit_clicked)
        quit_button.set_halign(Gtk.Align.END)
        top_row.append(quit_button)

        # 结果显示区域
        self._result_label = Gtk.Label(label="")
        self._result_label.set_halign(Gtk.Align.CENTER)
        self._result_label.set_wrap(True)
        self._result_label.set_max_width_chars(40)
        main_box.append(self._result_label)

        # 初始化 UI 管理器
        self._ui_manager = UIManager(self)

    def _init_asr_client(self) -> None:
        """初始化 ASR 客户端。"""
        try:
            asr_config = AsrClientConfig.from_config(self._config)
            self._asr_client = AsrClient(asr_config)
            logger.info("ASR 客户端已初始化")
        except Exception as e:
            logger.error(f"初始化 ASR 客户端失败: {e}")

    def _on_toggle_clicked(self, button: Gtk.Button) -> None:
        """切换按钮点击事件。"""
        if self._is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def _on_quit_clicked(self, button: Gtk.Button) -> None:
        """退出按钮点击事件。"""
        self.quit_app()

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    def start_recording(self) -> None:
        """开始录音。"""
        if self._asr_client is None:
            return

        self._is_recording = True
        self._ui_manager.update_status(True)

        self._recognition_manager = RecognitionManager(
            asr_client=self._asr_client,
            on_result_callback=self._on_recognition_result,
            on_error_callback=self._on_recognition_error,
        )

        thread = threading.Thread(target=self._run_async_recognition, daemon=True)
        thread.start()

    def _run_async_recognition(self) -> None:
        """在线程中运行异步识别任务。"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if self._recognition_manager:
                loop.run_until_complete(self._recognition_manager.start_recognition())
        except Exception:
            pass
        finally:
            loop.close()
            GLib.idle_add(self._on_recognition_complete)

    def _on_recognition_result(self, text: str, result_type: ResultType) -> None:
        """处理识别结果。

        Args:
            text: 识别文本
            result_type: 结果类型
        """
        # 显示所有结果
        self._ui_manager.update_result_display(text)

        # 如果是最终结果，注入文本
        if result_type == ResultType.FINAL:
            GLib.idle_add(self._text_injector.inject, text)

    def _on_recognition_error(self, error_type: str, message: str) -> None:
        """处理识别错误。"""
        GLib.idle_add(self._ui_manager.update_result_display, f"错误: {message}")

    def _on_recognition_complete(self) -> bool:
        """识别完成回调。"""
        self._is_recording = False
        self._ui_manager.update_status(False)
        self._ui_manager.clear_result_display()
        return False

    def stop_recording(self) -> None:
        """停止录音。"""
        if self._recognition_manager:
            self._recognition_manager.stop_recognition()

        self._is_recording = False
        self._ui_manager.update_status(False)

    def _on_close(self, _widget: Gtk.Window) -> None:
        """处理窗口关闭事件。"""
        self.quit()

    def quit_app(self) -> None:
        """退出应用。"""
        if self._is_recording:
            self.stop_recording()

        if self.get_application():
            self.get_application().quit()


# ============================================================================
# 应用程序
# ============================================================================
class VoiceGUIApplication(Gtk.Application):
    """全功能紧凑 GUI 应用程序。"""

    def __init__(self, config: Config) -> None:
        """初始化应用程序。"""
        super().__init__(application_id="com.voiceinput.gui", flags=0)
        self._config = config
        self._window: VoiceGUIWindow | None = None

        # 使用 XDG_RUNTIME_DIR（必须存在）
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
        if not runtime_dir or not Path(runtime_dir).is_dir():
            err_msg = "XDG_RUNTIME_DIR is not set or invalid"
            raise RuntimeError(err_msg)
        self._socket_path = f"{runtime_dir}/voice-input.sock"
        self._socket_server_running = threading.Event()
        self._socket_thread: threading.Thread | None = None
        self._action_queue: queue.Queue[str] = queue.Queue()

    def do_activate(self) -> None:
        """应用激活时的回调。"""
        if not self._window:
            self._window = VoiceGUIWindow(self, self._config)
            self._window.show()

            # 启动 Socket 服务
            self._start_socket_server()
            # 启动 GTK 主线程中的 action 处理
            GLib.timeout_add(100, self._process_actions)
        else:
            self._window.present()

    def _process_actions(self) -> bool:
        """处理回调队列（在 GTK 主线程中）。"""
        try:
            while True:
                action = self._action_queue.get_nowait()
                logger.info(f"处理 action: {action}")
                if action == "toggle":
                    if self._window:
                        is_rec = self._window.is_recording()
                        logger.info(f"当前录音状态: {is_rec}")
                        if is_rec:
                            logger.info("调用 stop_recording")
                            self._window.stop_recording()
                        else:
                            logger.info("调用 start_recording")
                            self._window.start_recording()
                elif action == "quit" and self._window:
                    self._window.quit_app()
        except queue.Empty:
            pass
        return True  # 继续定时器

    def _start_socket_server(self) -> None:
        """启动 Unix Socket 服务器。"""
        socket_path = Path(self._socket_path)
        if socket_path.exists():
            with contextlib.suppress(OSError):
                socket_path.unlink()

        self._socket_server_running.set()
        self._socket_thread = threading.Thread(target=self._socket_server_loop, daemon=True)
        self._socket_thread.start()

        # 注册退出时清理
        atexit.register(self._cleanup_socket)

        logger.info(f"Socket 服务已启动: {self._socket_path}")

    def _cleanup_socket(self) -> None:
        """退出时清理 socket 文件。"""
        # 先停止线程
        self._stop_socket_server()
        # 然后清理文件
        socket_path = Path(self._socket_path)
        if socket_path.exists():
            try:
                socket_path.unlink()
                logger.info(f"已清理 socket 文件: {self._socket_path}")
            except OSError:
                pass

    def _socket_server_loop(self) -> None:
        """Socket 服务器监听循环。"""
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(self._socket_path)

        # 设置 socket 文件权限 (所有者读写)
        Path(self._socket_path).chmod(0o600)

        server_sock.listen(1)

        while self._socket_server_running.is_set():
            try:
                server_sock.settimeout(1.0)
                try:
                    conn, _ = server_sock.accept()
                except TimeoutError:
                    continue

                try:
                    data = conn.recv(1024)
                    if not data:
                        conn.close()
                        continue

                    cmd = data.decode().strip()
                    # 命令白名单验证
                    if len(cmd) > 64:
                        logger.warning(f"Socket: 命令过长: {len(cmd)} bytes")
                        continue
                    if cmd == "toggle":
                        self._action_queue.put("toggle")
                        logger.info("Socket: 收到 toggle 命令")
                    elif cmd == "quit":
                        self._action_queue.put("quit")
                        logger.info("Socket: 收到 quit 命令")
                    else:
                        logger.warning(f"Socket: 收到未知命令: {cmd}")
                finally:
                    conn.close()
            except Exception as e:
                if self._socket_server_running.is_set():
                    logger.error(f"Socket 服务器错误: {e}")

        # 先关闭 socket，再删除文件
        with contextlib.suppress(OSError):
            server_sock.close()

        socket_path = Path(self._socket_path)
        if socket_path.exists():
            with contextlib.suppress(OSError):
                socket_path.unlink()
        logger.info("Socket 服务已停止")

    def _stop_socket_server(self) -> None:
        """停止 Socket 服务器。"""
        self._socket_server_running.clear()
        if self._socket_thread:
            self._socket_thread.join(timeout=2)
            self._socket_thread = None
        logger.info("Socket 服务已停止")


def main() -> None:
    """主函数。"""
    # 配置日志输出到文件
    log_file = "/tmp/voice_gui.log"
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # 配置根logger
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.DEBUG)

    # 加载配置
    config = load_config()

    # 创建并运行应用程序
    app = VoiceGUIApplication(config)
    app.run()


if __name__ == "__main__":
    main()
