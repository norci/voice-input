"""Socket manager module.

Manages Unix Socket server for receiving commands.
"""

from __future__ import annotations

import atexit
import contextlib
import logging
import queue
import socket
import threading
from collections.abc import Callable
from pathlib import Path

MAX_COMMAND_LENGTH = 64

logger = logging.getLogger(__name__)


class SocketManager:
    """Socket 管理器."""

    def __init__(self, socket_path: str) -> None:
        """初始化 Socket 管理器.

        Args:
            socket_path: Unix Socket 文件路径
        """
        self._socket_path = socket_path
        self._server_running = threading.Event()
        self._server_thread: threading.Thread | None = None
        self._server_sock: socket.socket | None = None
        self._action_queue: queue.Queue[str] = queue.Queue()
        self._command_handler: Callable[[str], None] | None = None

    def set_command_handler(self, handler: Callable[[str], None]) -> None:
        """设置命令处理回调."""
        self._command_handler = handler

    def start_server(self) -> bool:
        """启动 Socket 服务器.

        Returns:
            是否成功启动
        """
        socket_path = Path(self._socket_path)

        # 检查并清理残留 socket 文件
        if socket_path.exists() and not self._cleanup_stale_socket(socket_path):
            return False

        # 启动服务器
        logger.info("SocketManager: 创建 socket...")
        self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._server_sock.bind(self._socket_path)
            socket_path.chmod(0o600)
            self._server_sock.listen(1)
            logger.info("SocketManager: bind 和 listen 成功")
        except OSError:
            logger.exception("Socket bind failed")
            return False

        self._server_running.set()
        self._server_thread = threading.Thread(target=self._server_loop, daemon=True)
        self._server_thread.start()

        atexit.register(self.stop_server)
        logger.info(f"Socket 服务已启动: {self._socket_path}")
        return True

    def _cleanup_stale_socket(self, socket_path: Path) -> bool:
        """清理残留的 socket 文件.

        如果 socket 文件存在但没有进程监听,删除它.
        如果 socket 文件正在被使用,返回 False.

        Returns:
            是否可以安全启动服务器
        """
        try:
            # 尝试连接,看是否有进程在监听
            test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                test_sock.connect(self._socket_path)
                test_sock.close()
            except (ConnectionRefusedError, FileNotFoundError):
                # 连接被拒绝,说明没有进程在监听
                test_sock.close()
                logger.warning(f"检测到残留 socket 文件,自动清理: {self._socket_path}")
                socket_path.unlink()
                return True
            except Exception as e:
                # 其他错误,尝试删除
                logger.warning(f"检查 socket 时出错 {e},尝试清理: {self._socket_path}")
                socket_path.unlink()
                return True
            else:
                # 能连接,说明有进程在监听
                logger.error(f"Socket 文件已被占用: {self._socket_path}")
                return False
        except Exception:
            logger.exception("Socket cleanup failed")
            return False

    def _server_loop(self) -> None:
        """Socket server loop."""
        logger.info("Server loop started")
        while self._server_running.is_set():
            try:
                self._server_sock.settimeout(1.0)
                try:
                    conn, _ = self._server_sock.accept()
                except TimeoutError:
                    continue

                try:
                    data = conn.recv(1024)
                    if data:
                        cmd = data.decode().strip()
                        if len(cmd) > MAX_COMMAND_LENGTH:
                            msg = f"Command too long: {len(cmd)} bytes"
                            logger.warning("%s", msg)
                            continue
                        if self._command_handler:
                            self._command_handler(cmd)
                        logger.info("Received command: %s", cmd)
                finally:
                    conn.close()
            except Exception:
                if self._server_running.is_set():
                    logger.exception("Socket server error")

        # 清理
        logger.info("SocketManager: 服务器循环结束")

    def stop_server(self) -> None:
        """停止 Socket 服务器."""
        self._server_running.clear()
        if self._server_sock:
            with contextlib.suppress(Exception):
                self._server_sock.close()
            self._server_sock = None
        if self._server_thread:
            self._server_thread.join(timeout=2)
            self._server_thread = None
        logger.info("Socket 服务器已停止")

    def send_command(self, cmd: str) -> bool:
        """向 Socket 发送命令.

        Args:
            cmd: 命令字符串

        Returns:
            是否发送成功
        """
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self._socket_path)
            sock.send(cmd.encode())
        except Exception:
            logger.exception("Send command failed")
            return False
        finally:
            sock.close()
        return True
