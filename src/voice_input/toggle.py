#!/usr/bin/env python3
"""
CLI tool to toggle voice-input via Unix Socket.

Usage:
    voice-input-toggle
"""

import logging
import os
import socket
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# 使用 XDG_RUNTIME_DIR
RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR")
if not RUNTIME_DIR or not Path(RUNTIME_DIR).is_dir():
    sys.exit(1)
SOCKET_PATH = f"{RUNTIME_DIR}/voice-input.sock"


def send_command(cmd: str) -> bool:
    """向 Socket 发送命令.

    Args:
        cmd: 命令字符串

    Returns:
        是否发送成功
    """
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.connect(SOCKET_PATH)
        sock.sendall(cmd.encode())
    except ConnectionRefusedError:
        logger.warning("Socket 连接被拒绝: %s", SOCKET_PATH)
        return False
    except OSError:
        logger.exception("Socket 通信错误")
        return False
    finally:
        sock.close()
    return True


def toggle() -> int:
    """Toggle voice recognition."""
    return send_command("toggle")


def cmd_quit() -> int:
    """Quit voice-input."""
    return send_command("quit")


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "quit":
        return cmd_quit()
    return toggle()


if __name__ == "__main__":
    sys.exit(main())
