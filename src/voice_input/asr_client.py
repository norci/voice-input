"""ASR 客户端模块 - 简化实现。

每次语音识别创建一个新连接，识别完成后关闭连接。
参考 FunASR 官方示例实现。
"""

import asyncio
import json
import logging
import ssl
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd
import websockets

if TYPE_CHECKING:
    from voice_input.config_loader import Config
else:
    Config = "Config"

logger = logging.getLogger(__name__)


class ResultType(Enum):
    """识别结果类型。"""

    INTERIM = "interim"  # 中间结果（实时）
    FINAL = "final"  # 最终结果


@dataclass
class AsrResult:
    """识别结果数据类。"""

    text: str
    result_type: ResultType


@dataclass
class AsrClientConfig:
    """ASR 客户端配置。"""

    host: str = "127.0.0.1"
    port: int = 10095
    # 识别模式: offline, online, 2pass
    mode: str = "2pass"
    chunk_size: str = "5,10,5"
    chunk_interval: int = 10
    sample_rate: int = 16000
    # 音频灵敏度控制
    gain: float = 0.5  # 增益因子 (0.0 - 1.0)
    threshold: float = 0.01  # 阈值 (0.0 - 1.0)

    @classmethod
    def from_config(cls, config: "Config") -> "AsrClientConfig":
        """从配置创建 AsrClientConfig。"""
        return cls(
            host=config.asr.server_host,
            port=config.asr.server_port,
            mode=config.asr.server_mode,
            chunk_size=config.asr.chunk_size,
            chunk_interval=config.asr.chunk_interval,
            gain=config.audio.gain,
            threshold=config.audio.threshold,
        )


# 结果回调类型
ResultCallback = Callable[[str, ResultType], Awaitable[None]]


class AsrClient:
    """FunASR WebSocket 客户端 - 简化实现。"""

    def __init__(
        self,
        config: AsrClientConfig | None = None,
    ) -> None:
        """初始化 ASR 客户端。

        Args:
            config: ASR 客户端配置
        """
        if config is None:
            config = AsrClientConfig()

        self._config = config
        self._ws: websockets.ClientConnection | None = None
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        logger.info(f"ASR 客户端已初始化 (服务: {config.host}:{config.port})")

    async def recognize_with_stop(
        self,
        stop_event: asyncio.Event | None = None,
        on_result: ResultCallback | None = None,
    ) -> str:
        """执行一次完整的语音识别，支持停止。

        stop_event 由 AsrClient 内部管理，调用 stop() 即可停止。
        也可外部传入自定义 stop_event（用于测试）。

        Args:
            stop_event: 可选的外部停止事件（测试用），默认内部创建
            on_result: 结果回调函数

        Returns:
            最终识别结果文本
        """
        # 内部管理 stop_event，供 stop() 方法跨线程使用
        if stop_event is None:
            stop_event = asyncio.Event()
        self._stop_event = stop_event

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        uri = f"wss://{self._config.host}:{self._config.port}"
        final_text = ""

        blocksize = 1024
        channels = 1
        sample_rate = self._config.sample_rate

        async def send_audio(ws: websockets.ClientConnection) -> None:
            """发送音频数据。"""
            try:
                with sd.InputStream(
                    channels=channels,
                    samplerate=sample_rate,
                    blocksize=blocksize,
                    dtype=np.float32,
                ) as stream:
                    while not stop_event.is_set():
                        indata, _ = stream.read(blocksize)
                        if stop_event.is_set():
                            break

                        audio_data = indata[:, 0] * self._config.gain

                        max_amplitude = np.max(np.abs(audio_data))
                        if max_amplitude < self._config.threshold:
                            audio_data = np.zeros_like(audio_data)

                        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
                        await ws.send(audio_bytes)
                        await asyncio.sleep(0)
            except (OSError, websockets.exceptions.ConnectionClosed):
                pass

        async def receive_results(ws: websockets.ClientConnection) -> None:
            """接收识别结果。"""
            nonlocal final_text
            last_final_text = ""
            try:
                while not stop_event.is_set():
                    # 阻塞接收，连接关闭时立即抛出 ConnectionClosed
                    meg = await ws.recv()

                    meg = json.loads(meg)
                    text = meg.get("text", "")
                    mode = meg.get("mode", "")
                    is_final = meg.get("is_final", False)

                    if not text:
                        continue

                    if mode in ("offline", "2pass-offline") or is_final:
                        if text == last_final_text:
                            continue
                        last_final_text = text
                        result_type = ResultType.FINAL
                        final_text = text
                        logger.info(f"最终结果: {text}")
                    else:
                        result_type = ResultType.INTERIM
                        logger.debug(f"中间结果: {text}")

                    if on_result:
                        await on_result(text, result_type)

            except websockets.exceptions.ConnectionClosed:
                pass

        logger.info(f"准备连接到 ASR 服务器: {uri}")
        try:
            logger.info(f"正在连接到 ASR 服务器: {uri}")
            ws = await websockets.connect(
                uri,
                subprotocols=[websockets.Subprotocol("binary")],
                ping_interval=None,
                ssl=ssl_context,
            )
            logger.info("WebSocket 连接已建立")

            try:
                # 保存引用，供主线程跨线程关闭连接
                self._ws = ws
                self._event_loop = asyncio.get_running_loop()

                # 发送初始化消息
                init_msg = {
                    "mode": self._config.mode,
                    "chunk_size": [int(x) for x in self._config.chunk_size.split(",")],
                    "chunk_interval": self._config.chunk_interval,
                    "is_speaking": True,
                }
                await ws.send(json.dumps(init_msg))
                logger.info("已建立连接，开始识别...")

                # 并发执行发送和接收
                # 连接关闭时两个子任务都捕获 ConnectionClosed 并正常返回
                await asyncio.gather(
                    send_audio(ws),
                    receive_results(ws),
                )
                return final_text
            finally:
                # 确保 WebSocket 连接被关闭
                if ws is not None:
                    with suppress(Exception):
                        await ws.close()
        except (OSError, ConnectionRefusedError) as e:
            logger.error(f"ASR 服务器连接失败 (OSError): {e}", exc_info=True)
            raise

        except websockets.exceptions.ConnectionClosed:
            # 连接被关闭（停止时触发），正常退出
            logger.info("WebSocket 连接已关闭")
            return final_text

        except Exception as e:
            logger.error(f"识别异常: {e}", exc_info=True)
            # 重新抛出异常，让调用者能够处理错误
            raise

    def stop(self) -> None:
        """停止语音识别（线程安全）。

        可从任何线程调用。内部通过 call_soon_threadsafe
        在事件循环中设置 stop_event 并关闭 WebSocket 连接。
        """
        if self._event_loop is None or not self._event_loop.is_running():
            return

        # 设置停止事件
        if self._stop_event is not None:
            self._event_loop.call_soon_threadsafe(self._stop_event.set)

        # 关闭 WebSocket 连接，中断阻塞的 ws.recv()
        if self._ws is not None:
            asyncio.run_coroutine_threadsafe(self._close_ws(), self._event_loop)

    async def _close_ws(self) -> None:
        """关闭 WebSocket 连接（在事件循环中执行）。"""
        if self._ws is not None:
            with suppress(Exception):
                await self._ws.close()
            self._ws = None


def create_asr_client(
    host: str = "127.0.0.1",
    port: int = 10095,
    mode: str = "2pass",
    config: AsrClientConfig | None = None,
) -> AsrClient:
    """创建 ASR 客户端。"""
    if config is None:
        config = AsrClientConfig(host=host, port=port, mode=mode)
    return AsrClient(config)
