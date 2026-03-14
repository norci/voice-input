#!/usr/bin/env python3
"""
CLI tool to toggle voice-input via Unix Socket.

Usage:
    voice-input-toggle
"""

import os
import socket
import sys
from pathlib import Path

# 使用 XDG_RUNTIME_DIR
RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR")
if not RUNTIME_DIR or not Path(RUNTIME_DIR).is_dir():
    sys.exit(1)
SOCKET_PATH = f"{RUNTIME_DIR}/voice-input.sock"


def send_command(cmd: str) -> int:
    """Send command via Unix Socket."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(3.0)
        sock.connect(SOCKET_PATH)
        sock.send(cmd.encode())
        sock.close()
    except FileNotFoundError:
        return 1
    except ConnectionRefusedError:
        return 1
    except TimeoutError:
        return 1
    except Exception:
        return 1
    else:
        return 0


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
