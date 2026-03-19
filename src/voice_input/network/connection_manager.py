"""连接管理器模块.

管理 WebSocket 连接生命周期,提供简洁的发送/接收接口.
"""

import asyncio
import json
import logging
import ssl
import threading
from collections.abc import Callable
from contextlib import suppress
from enum import Enum
from typing import TYPE_CHECKING

import websockets

if TYPE_CHECKING:
    from voice_input.asr_config import AsrClientConfig

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"


RECONNECT_DELAY = 3.0


class ConnectionManager:
    """管理 WebSocket 连接生命周期,线程安全."""

    def __init__(self: "ConnectionManager", config: "AsrClientConfig") -> None:
        """初始化连接管理器.

        Args:
            config: ASR 客户端配置
        """
        self._config = config
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._lock = threading.Lock()
        self._ws: websockets.ClientConnection | None = None
        self._should_reconnect = True

        # SSL 配置: 本地开发环境使用自签名证书,禁用验证
        # 注意: 生产环境应启用证书验证
        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

        self._uri = f"wss://{self._config.host}:{self._config.port}"

    @property
    def is_connected(self: "ConnectionManager") -> bool:
        """检查是否已连接."""
        return self.state == ConnectionState.CONNECTED

    async def connect(self: "ConnectionManager") -> None:
        """建立连接."""
        await self._connect_impl()

    async def connect_with_retry(
        self: "ConnectionManager", on_reconnecting: "Callable[[int], None] | None" = None
    ) -> None:
        """建立连接,带最大重试次数限制.

        Args:
            on_reconnecting: 重连时的回调,参数为重连尝试次数
        """
        max_attempts = 10
        attempt = 0
        delay = RECONNECT_DELAY

        while True:
            if not self._should_reconnect or attempt >= max_attempts:
                if attempt >= max_attempts:
                    logger.warning("Max retry attempts reached (%d), stopping", max_attempts)
                break
            try:
                await self._connect_impl()
            except ConnectionError as e:
                attempt += 1
                logger.warning(
                    "Connection failed (%d/%d), retrying in %ds: %s",
                    attempt,
                    max_attempts,
                    delay,
                    e,
                )
                if on_reconnecting:
                    on_reconnecting(attempt)
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 30)
            else:
                return

    @property
    def state(self: "ConnectionManager") -> ConnectionState:
        """获取连接状态."""
        with self._lock:
            return self._state

    async def _connect_impl(self: "ConnectionManager") -> websockets.ClientConnection:
        """内部连接实现.

        Returns:
            WebSocket 连接对象

        Raises:
            ConnectionError: 连接失败
        """
        with self._lock:
            if self._state == ConnectionState.CONNECTED and self._ws:
                return self._ws

            if self._state == ConnectionState.CONNECTING:
                msg = "Connection is being established"
                raise ConnectionError(msg)

            self._state = ConnectionState.CONNECTING

        try:
            logger.debug("Connecting to: %s", self._uri)
            ws = await websockets.connect(
                self._uri,
                subprotocols=[websockets.Subprotocol("binary")],
                ping_interval=None,
                ssl=self._ssl_context,
            )
        except Exception as e:
            with self._lock:
                self._state = ConnectionState.DISCONNECTED
            logger.exception("Connection failed")
            msg = f"Connection failed: {e}"
            raise ConnectionError(msg) from e
        else:
            init_msg = {
                "mode": self._config.mode,
                "chunk_size": [int(x) for x in self._config.chunk_size.split(",")],
                "chunk_interval": self._config.chunk_interval,
                "is_speaking": True,
            }
            await ws.send(json.dumps(init_msg))

            with self._lock:
                self._ws = ws
                self._state = ConnectionState.CONNECTED

            logger.info("WebSocket connected")
            return ws

    async def disconnect(self: "ConnectionManager") -> None:
        """断开 WebSocket 连接."""
        with self._lock:
            if self._state == ConnectionState.DISCONNECTED:
                return
            self._state = ConnectionState.CLOSING

        ws_to_close = None
        with self._lock:
            ws_to_close = self._ws
            self._ws = None
            self._state = ConnectionState.DISCONNECTED

        if ws_to_close:
            with suppress(Exception):
                await ws_to_close.close()
            logger.info("WebSocket disconnected")

    async def send(self: "ConnectionManager", data: bytes) -> None:
        """Send data.

        Args:
            data: Data to send
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED or not self._ws:
                msg = "Not connected"
                raise ConnectionError(msg)
            ws = self._ws

        await ws.send(data)

    async def receive(self: "ConnectionManager") -> bytes | None:
        """Receive data.

        Returns:
            Received bytes or None
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED or not self._ws:
                msg = "Not connected"
                raise ConnectionError(msg)
            ws = self._ws

        try:
            data: str | bytes = await ws.recv()
            if isinstance(data, str):
                data = data.encode("utf-8")
        except websockets.exceptions.ConnectionClosed:
            return None
        except Exception:
            logger.exception("Receive error")
            return None
        return data


def create_connection_manager(config: "AsrClientConfig") -> ConnectionManager:
    """创建连接管理器."""
    return ConnectionManager(config)
