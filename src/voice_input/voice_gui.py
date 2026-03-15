#!/usr/bin/env python3
"""全功能紧凑 GUI 应用 - 包含录音、ASR 通信、显示、Socket 服务。

这个模块实现了持续运行的单体 GUI 应用，包含所有功能：
- Unix Socket 信号处理（开始/停止识别）
- 录音和 ASR 通信
- 实时显示中间结果和最终结果
- 使用 GTK4 窗口，由 Hyprland 管理窗口位置
"""

import asyncio
import atexit
import logging
import os
import queue
import socket
import subprocess
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")

import contextlib

# 导入现有模块
from dataclasses import dataclass

from gi.repository import GLib, Gtk

from voice_input.asr_client import AsrClient, AsrClientConfig, ResultType
from voice_input.config_loader import Config, load_config

# 当前模块的logger（用于文件中logger.info()等调用）
logger = logging.getLogger(__name__)


# ============================================================================
# 数据类
# ============================================================================
@dataclass
class ErrorEvent:
    """错误事件。"""

    error_type: str
    message: str
    timestamp: float


# ============================================================================
# 应用状态数据类
# ============================================================================
class AppState:
    """应用状态。"""

    is_recording: bool = False
    current_text: str = ""
    interim_text: str = ""
    final_text: str = ""


class VoiceGUIWindow(Gtk.ApplicationWindow):
    """全功能紧凑 GUI 窗口。"""

    def __init__(self, app: Gtk.Application, config: Config) -> None:
        """初始化 GUI 窗口。"""
        super().__init__(application=app, title="Voice Input")

        self._config = config
        self._state = AppState()
        self._asr_client: AsrClient | None = None
        self._error_count = 0
        self._recording_task: asyncio.Task[None] | None = None

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
        self._update_status_color("#808080")

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

    def _init_asr_client(self) -> None:
        """初始化 ASR 客户端。"""
        try:
            asr_config = AsrClientConfig.from_config(self._config)
            # 创建 ASR 客户端（新的简化 API 只需要 config）
            self._asr_client = AsrClient(asr_config)

            logger.info("ASR 客户端已初始化")
        except Exception as e:
            logger.error(f"初始化 ASR 客户端失败: {e}")

    def _update_status_color(self, color: str) -> None:
        """更新状态指示器颜色。

        Args:
            color: 十六进制颜色值，如 "#808080" 或 "#00FF00"
        """
        css_provider = Gtk.CssProvider()
        css = f"box {{ background-color: {color}; }}"
        css_provider.load_from_string(css)
        self._status_indicator.get_style_context().add_provider(
            css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _handle_error_event(self, error_event: ErrorEvent) -> None:
        """处理错误事件的共享逻辑.

        Args:
            error_event: 要处理的错误事件
        """
        logger.info(f"发送错误事件: {error_event.error_type} - {error_event.message}")

        # 更新错误计数
        self._error_count += 1

        # 在主线程中更新 UI 显示错误信息
        self._display_error_message(error_event)

    def _send_error_event_async(self, error_type: str, error_message: str) -> None:
        """异步发送错误事件（从非主线程调用）。

        Args:
            error_type: 错误类型
            error_message: 错误消息
        """
        # 创建错误事件
        error_event = ErrorEvent(
            error_type=error_type, message=error_message, timestamp=time.time()
        )

        # 使用 GLib.idle_add 在主线程中处理事件
        GLib.idle_add(self._handle_error_event, error_event)

    def _display_error_message(self, error_event: ErrorEvent) -> None:
        """显示错误信息到 GUI。

        Args:
            error_event: 错误事件
        """
        error_message = f"错误: {error_event.error_type} - {error_event.message}"
        logger.error(error_message)

        # 更新状态指示器颜色（错误用红色）
        self._update_status_color("#FF0000")

        # 显示错误信息到结果标签
        self._result_label.set_label(f"错误: {error_event.message}")

        # 短暂显示后清空
        GLib.timeout_add(3000, self._clear_error_display)

    def _clear_error_display(self) -> bool:
        """清空错误显示（用于短暂显示后）。"""
        self._update_status_color("#808080")  # 恢复灰色
        self._result_label.set_label("")
        return False  # 单次执行

    def _update_interim_text(self, text: str) -> bool:
        """更新中间结果显示（在主线程中调用）。"""
        self._state.interim_text = text
        self._result_label.set_label(text)
        logger.debug(f"更新中间结果: {text}")
        return False  # 单次执行

    def _update_final_text(self, text: str) -> bool:
        """更新最终结果显示（在主线程中调用）。

        显示最终识别结果到 GUI 界面，并注入到光标位置。
        """
        self._state.final_text = text
        self._result_label.set_label(text)
        logger.info(f"最终结果: {text}")

        # 注入文本到光标位置
        self._inject_text(text)

        # 短暂显示后清空
        GLib.timeout_add(2000, self._clear_result_display)

        return False  # 单次执行

    def _inject_text(self, text: str) -> bool:
        """使用 wtype 将文本注入到光标位置。"""
        try:
            result = subprocess.run(
                ["wtype", text], capture_output=True, text=True, timeout=2, check=False
            )
        except FileNotFoundError:
            logger.error("wtype 命令未找到，请安装 wtype")
            return False
        except Exception as e:
            logger.error(f"文本注入错误: {e}")
            return False
        else:
            if result.returncode == 0:
                logger.info(f"文本注入成功: {text}")
                return False  # 返回 False 让 GLib.idle_add 只执行一次
            logger.error(f"文本注入失败: {result.stderr}")
            return False

    def _clear_result_display(self) -> bool:
        """清空结果显示（用于短暂显示后）。"""
        self._result_label.set_label("")
        return False  # 单次执行

    def _on_toggle_clicked(self, button: Gtk.Button) -> None:
        """切换按钮点击事件。"""
        logger.info(f"切换按钮点击，当前录音状态: {self._state.is_recording}")
        if self._state.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def _on_quit_clicked(self, button: Gtk.Button) -> None:
        """退出按钮点击事件。"""
        self.quit_app()

    def is_recording(self) -> bool:
        """Check if currently recording (public method for external access)."""
        return self._state.is_recording

    def start_recording(self) -> None:
        """开始录音。"""
        if self._asr_client is None:
            error_msg = "ASR 客户端未初始化"
            logger.error(error_msg)
            self._send_error_event_async("ASR_CLIENT_NOT_INITIALIZED", error_msg)
            return

        # 在新线程中运行异步任务
        thread = threading.Thread(target=self._run_async_recording, daemon=True)
        thread.start()

        # 更新 UI 状态（在主线程中）
        self._state.is_recording = True
        GLib.idle_add(self._update_status_color, "#00FF00")  # 绿色
        GLib.idle_add(self._toggle_button.set_label, "停止识别")
        logger.info("开始录音")

    def _run_async_recording(self) -> None:
        """在线程中运行异步录音任务。"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            self._recording_task = loop.create_task(self._start_recording_async())
            loop.run_until_complete(self._recording_task)
        except Exception as e:
            logger.error(f"录音任务错误: {e}", exc_info=True)
        finally:
            loop.close()

    async def _start_recording_async(self) -> None:
        """异步开始录音的协程。"""
        if self._asr_client is None:
            error_msg = "ASR 客户端未初始化"
            logger.error(error_msg)
            self._send_error_event_async("ASR_CLIENT_NOT_INITIALIZED", error_msg)
            return

        # 用于跟踪上一次注入的 final 结果，避免重复注入相同内容
        last_injected_text = ""

        async def on_result(text: str, result_type: ResultType) -> None:
            """处理识别结果回调。"""
            nonlocal last_injected_text
            logger.info(f"收到识别结果: {text} ({result_type.value})")
            # 使用 GLib.idle_add 在主线程中更新 UI
            if result_type == ResultType.INTERIM:
                self._state.interim_text = text
                GLib.idle_add(self._result_label.set_label, text)
            elif result_type == ResultType.FINAL:
                self._state.final_text = text
                GLib.idle_add(self._result_label.set_label, text)
                logger.info(f"已更新结果显示为: {text}")
                # 注入文本到光标位置（每个新的 final 结果都注入）
                if text != last_injected_text:
                    last_injected_text = text
                    GLib.idle_add(self._inject_text, text)

        try:
            logger.info("开始语音识别...")
            # stop_event 由 AsrClient 内部管理
            final_text = await self._asr_client.recognize_with_stop(
                on_result=on_result,
            )

            # 保存最终结果
            if final_text:
                self._state.final_text = final_text
                GLib.idle_add(self._result_label.set_label, final_text)
                logger.info(f"识别完成后更新结果显示: {final_text}")

            logger.info(f"识别完成: {final_text}")
        except Exception as e:
            logger.error(f"录音启动失败: {e}")
            self._send_error_event_async("RECORDING_START_FAILED", str(e))
        finally:
            # 更新 UI 状态
            self._state.is_recording = False
            logger.info("finally block: setting is_recording to False")
            GLib.idle_add(self._update_status_color, "#808080")  # 灰色
            GLib.idle_add(self._toggle_button.set_label, "开始识别")

            # 清空识别结果（在识别任务结束后执行）
            logger.info("finally block: clearing result display...")
            GLib.idle_add(self._result_label.set_label, "")
            self._state.interim_text = ""
            self._state.final_text = ""
            logger.info("finally block: result display cleared")

    def stop_recording(self) -> None:
        """停止录音。

        调用 AsrClient.stop() 停止识别，所有异步细节由 AsrClient 内部处理。
        """
        logger.info("stop_recording called, is_recording: %s", self._state.is_recording)

        if self._asr_client:
            self._asr_client.stop()
            logger.info("已通知 AsrClient 停止")

        self._state.is_recording = False
        # 使用 GLib.idle_add 确保在主线程更新 UI
        GLib.idle_add(self._update_status_color, "#808080")  # 灰色
        GLib.idle_add(self._toggle_button.set_label, "开始识别")
        logger.info("停止录音完成（等待识别任务结束以清空结果显示）")

    def _on_close(self, _widget: Gtk.Window) -> None:
        """处理窗口关闭事件。"""
        logger.info("GUI 窗口关闭")
        self.quit()

    def quit_app(self) -> None:
        """退出应用。"""
        logger.info("正在退出应用...")

        # 如果仍在录音，优雅停止
        if self._state.is_recording:
            self.stop_recording()

        # 注意：异步任务会在 WebSocket 关闭后自然退出
        # 录音线程是 daemon 线程，进程退出时自动终止
        logger.info("关闭 GUI 窗口")

        if self.get_application():
            self.get_application().quit()


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
        # Queue for callbacks to communicate with GTK main thread
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

    def _on_socket_toggle(self) -> None:
        """Socket 切换回调（在 GTK 主线程中运行）。"""
        logger.info("Socket Toggle callback triggered")
        # 把操作放入队列，由 GTK 主线程处理
        try:
            self._action_queue.put("toggle")
            logger.info("Action queued successfully")
        except Exception as e:
            logger.error(f"Failed to queue action: {e}")

    def _on_socket_quit(self) -> None:
        """Socket 退出回调。"""
        # 先停止 Socket 服务
        self._stop_socket_server()
        if self._window:
            self._window.quit_app()


def main() -> None:
    """主函数。"""
    # 配置日志输出到文件（配置根logger以捕获所有子模块的日志）
    log_file = "/tmp/voice_gui.log"
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # 配置根logger，通过Python日志传播机制自动捕获所有子模块日志
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().setLevel(logging.DEBUG)

    # 加载配置
    config = load_config()

    # 创建并运行应用程序
    app = VoiceGUIApplication(config)
    app.run()


if __name__ == "__main__":
    main()
