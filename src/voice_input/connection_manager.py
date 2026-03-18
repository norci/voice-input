"""连接管理器模块。

管理 WebSocket 连接生命周期，提供简洁的发送/接收接口。
"""

import asyncio
import json
import logging
import ssl
import threading
from collections.abc import Callable
from contextlib import suppress
from enum import Enum
from typing import TYPE_CHECKING, cast

import websockets

from voice_input.asr_config import AsrResultDict
from voice_input.audio_recorder import AudioChunk

if TYPE_CHECKING:
    from voice_input.asr_config import AsrClientConfig

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """连接状态。"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"


RECONNECT_DELAY = 3


class ConnectionManager:
    """管理 WebSocket 连接生命周期，线程安全。"""

    def __init__(self, config: "AsrClientConfig") -> None:
        """初始化连接管理器。

        Args:
            config: ASR 客户端配置
        """
        self._config = config
        self._state: ConnectionState = ConnectionState.DISCONNECTED
        self._lock = threading.Lock()
        self._ws: websockets.ClientConnection | None = None

        self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

        self._uri = f"wss://{self._config.host}:{self._config.port}"

    def connect_sync(self) -> None:
        """同步连接（在事件循环中执行）。"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.connect())
        finally:
            loop.close()

    async def connect_with_retry(
        self, on_reconnecting: "Callable[[int], None] | None" = None
    ) -> websockets.ClientConnection:
        """建立连接，无限重连。

        Args:
            on_reconnecting: 重连时的回调，参数为重连尝试次数

        Returns:
            WebSocket 连接对象
        """
        attempt = 0
        while True:
            try:
                return await self.connect()
            except ConnectionError as e:
                attempt += 1
                logger.warning(f"连接失败 ({attempt})，{RECONNECT_DELAY}秒后重试: {e}")
                if on_reconnecting:
                    on_reconnecting(attempt)
                await asyncio.sleep(RECONNECT_DELAY)

    @property
    def state(self) -> ConnectionState:
        """获取连接状态。"""
        with self._lock:
            return self._state

    def is_connected(self) -> bool:
        """检查是否已连接。"""
        return self.state == ConnectionState.CONNECTED

    async def connect(self) -> websockets.ClientConnection:
        """建立 WebSocket 连接。

        Returns:
            WebSocket 连接对象

        Raises:
            ConnectionError: 连接失败
        """
        with self._lock:
            if self._state == ConnectionState.CONNECTED and self._ws:
                return self._ws

            if self._state == ConnectionState.CONNECTING:
                raise ConnectionError("连接正在建立中")

            self._state = ConnectionState.CONNECTING

        try:
            logger.debug(f"正在连接: {self._uri}")
            ws = await websockets.connect(
                self._uri,
                subprotocols=[websockets.Subprotocol("binary")],
                ping_interval=None,
                ssl=self._ssl_context,
            )

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

            logger.info("WebSocket 连接已建立")
            return ws  # noqa: TRY300
        except Exception as e:
            with self._lock:
                self._state = ConnectionState.DISCONNECTED
            logger.error("连接失败: %s", e)
            msg = f"连接失败: {e}"
            raise ConnectionError(msg) from e

    async def disconnect(self) -> None:
        """断开 WebSocket 连接。"""
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
            logger.info("WebSocket 连接已断开")

    async def send_audio(self, chunk: AudioChunk) -> None:
        """发送音频数据。

        Args:
            chunk: 音频数据块
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED or not self._ws:
                raise ConnectionError("未连接")
            ws = self._ws

        await ws.send(chunk.data)

    async def receive_result(self) -> AsrResultDict | None:
        """接收识别结果。

        Returns:
            识别结果字典，无结果时返回 None
        """
        with self._lock:
            if self._state != ConnectionState.CONNECTED or not self._ws:
                raise ConnectionError("未连接")
            ws = self._ws

        try:
            message = await ws.recv()
            result = json.loads(message)
            if not isinstance(result, dict):
                return None
            return cast(
                AsrResultDict,
                {
                    "text": result.get("text", ""),
                    "mode": result.get("mode", ""),
                    "is_final": result.get("is_final", False),
                },
            )
        except websockets.exceptions.ConnectionClosed:
            return None
        except Exception as e:
            logger.error(f"接收结果出错: {e}")
            return None


def create_connection_manager(config: "AsrClientConfig") -> ConnectionManager:
    """创建连接管理器。"""
    return ConnectionManager(config)
