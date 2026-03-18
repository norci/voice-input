"""音频引擎模块.

管理 WebSocket 连接、录音、发送和接收.
"""

import asyncio
import json
import logging
import queue
import threading
from collections.abc import Callable
from typing import cast

from voice_input.asr_config import AsrClientConfig, AsrResultDict, ResultType
from voice_input.audio.audio_recorder import (
    AudioChunk,
    AudioRecorder,
    AudioRecorderConfig,
)
from voice_input.network.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)


class AudioEngine:
    """音频引擎 - 管理音频采集、发送和接收."""

    def __init__(self, config: AsrClientConfig) -> None:
        """初始化音频引擎.

        Args:
            config: ASR 配置
        """
        self._config = config
        self._conn_manager: ConnectionManager | None = None
        self._audio_recorder: AudioRecorder | None = None
        self._audio_queue: queue.Queue[AudioChunk] = queue.Queue()

        self._is_sending = False
        self._is_running = False
        self._running_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._send_task: asyncio.Task[None] | None = None
        self._receive_task: asyncio.Task[None] | None = None

        self._result_callback: Callable[[str, ResultType], None] | None = None
        self._error_callback: Callable[[str, str], None] | None = None
        self._reconnecting_callback: Callable[[int], None] | None = None

    def set_result_callback(self, cb: Callable[[str, ResultType], None]) -> None:
        """设置结果回调."""
        self._result_callback = cb

    def set_error_callback(self, cb: Callable[[str, str], None]) -> None:
        """设置错误回调."""
        self._error_callback = cb

    def set_reconnecting_callback(self, cb: Callable[[int], None]) -> None:
        """设置重连回调."""
        self._reconnecting_callback = cb

    def start(self) -> bool:
        """启动音频引擎(录音+发送+接收).

        Returns:
            是否成功启动
        """
        if self._is_running:
            logger.warning("AudioEngine 已在运行")
            return False

        logger.info("AudioEngine.start() - 正在启动...")
        self._is_running = True
        self._is_sending = True

        # 1. 清空队列
        self._clear_queue()

        # 2. 创建新的 ConnectionManager(支持重连)
        self._conn_manager = ConnectionManager(self._config)
        logger.info("AudioEngine.start() - ConnectionManager 已创建")

        # 3. 启动录音
        try:
            audio_config = AudioRecorderConfig(
                blocksize=1024,
                channels=1,
                gain=self._config.gain,
                threshold=self._config.threshold,
            )
            self._audio_recorder = AudioRecorder(
                output_queue=self._audio_queue,
                config=audio_config,
            )
            self._audio_recorder.start()
            logger.info("AudioRecorder started")
        except Exception as e:
            logger.exception("Failed to start recording")
            self._is_running = False
            if self._error_callback:
                self._error_callback("RECORDING_FAILED", str(e))
            return False

        # 4. 启动事件循环线程
        logger.info("AudioEngine.start() - 启动事件循环线程...")
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._thread = threading.Thread(
            target=self._run_event_loop, daemon=True, name="AudioEngineLoop"
        )
        self._thread.start()

        logger.info("AudioEngine.start() - 启动完成")
        return True

    def stop_sending(self) -> None:
        """停止发送,保持接收.

        停止录音,但保持 WebSocket 连接继续接收识别结果.
        """
        logger.info("AudioEngine.stop_sending() - 正在停止录音和发送...")
        self._is_sending = False

        if self._audio_recorder:
            self._audio_recorder.stop()
            logger.info("AudioEngine.stop_sending() - AudioRecorder 已停止")

        self._clear_queue()
        logger.info("AudioEngine.stop_sending() - 完成,保持接收")

    def stop(self) -> None:
        """完全停止音频引擎."""
        logger.info("AudioEngine.stop() - 正在完全停止...")
        with self._running_lock:
            logger.info(f"AudioEngine.stop() - 当前 _is_running: {self._is_running}")
            self._is_running = False
            self._is_sending = False
            logger.info(f"AudioEngine.stop() - 设置后 _is_running: {self._is_running}")

        if self._audio_recorder:
            self._audio_recorder.stop()
            self._audio_recorder = None

        self._clear_queue()

        # 不再强制取消任务,让它们自然退出
        # 关闭事件循环(如果还在运行)
        if self._loop and self._loop.is_running():
            logger.info("AudioEngine.stop() - 停止事件循环")
            self._loop.call_soon_threadsafe(self._loop.stop)

        logger.info("AudioEngine.stop() - 信号已发送,等待任务退出")

    def _clear_queue(self) -> None:
        """清空音频队列."""
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break

    def _run_event_loop(self) -> None:
        """事件循环后台线程."""

        async def main() -> None:
            # 启动连接(带重连)
            conn_manager = cast(ConnectionManager, self._conn_manager)
            await conn_manager.connect_with_retry(self._on_reconnecting)

            # 启动发送和接收任务
            self._send_task = asyncio.create_task(self._send_loop())
            self._receive_task = asyncio.create_task(self._receive_loop())

            # 等待任务完成
            try:
                await asyncio.gather(self._send_task, self._receive_task)
            except asyncio.CancelledError:
                logger.debug("任务被取消")

        try:
            loop = cast(asyncio.AbstractEventLoop, self._loop)
            loop.run_until_complete(main())
        except RuntimeError as e:
            if "Event loop stopped" in str(e):
                logger.debug("Event loop stopped")
            else:
                logger.exception("Event loop error")
                if self._error_callback:
                    self._error_callback("LOOP_ERROR", str(e))
        except Exception as e:
            logger.exception("Event loop error")
            if self._error_callback:
                self._error_callback("LOOP_ERROR", str(e))
        finally:
            logger.debug("事件循环结束")
            # 清理
            self._conn_manager = None

    def _on_reconnecting(self, attempt: int) -> None:
        """重连回调."""
        if self._reconnecting_callback:
            self._reconnecting_callback(attempt)

    async def _send_loop(self) -> None:
        """发送循环 - 检查 _is_sending"""
        logger.debug("发送循环启动")
        while self._is_running and self._is_sending:
            try:
                if self._conn_manager is None or not self._conn_manager.is_connected:
                    await asyncio.sleep(0.1)
                    continue

                # 检查队列
                try:
                    chunk = self._audio_queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue

                # 发送音频数据
                # 注意: AudioChunk.data 是 bytes 类型
                audio_bytes = chunk.data
                await self._conn_manager.send(audio_bytes)
                logger.debug(f"Sent {len(audio_bytes)} bytes")

            except Exception as e:
                logger.error(f"音频发送失败: {e}", exc_info=True)
                # 停止发送循环，但不退出，等待 _is_sending 标志被外部设置
                await asyncio.sleep(0.5)
        logger.debug("发送循环结束")

    async def _receive_loop(self) -> None:
        """接收循环 - 始终运行直到完全停止,自动重连"""
        logger.debug("接收循环启动")
        while self._is_running:
            if not self._conn_manager or not self._conn_manager.is_connected:
                # 尝试重连
                try:
                    logger.info("连接已断开,尝试重连...")
                    if self._conn_manager:
                        await self._conn_manager.connect_with_retry(self._on_reconnecting)
                        logger.info("重连成功")
                    else:
                        logger.warning("ConnectionManager is None, stopping reconnection attempts")
                        break
                except Exception as e:
                    if self._is_running:
                        logger.warning(f"重连失败: {e}")
                        await asyncio.sleep(3)
                    continue

            try:
                if self._conn_manager:
                    message = await self._conn_manager.receive()
                    if message:
                        result = json.loads(message)
                        self._process_result(result)
            except Exception:
                if self._is_running:
                    logger.exception("Receive failed")
                await asyncio.sleep(1)  # avoid tight loop
                continue

        logger.debug("接收循环结束")

    def _process_result(self, result: AsrResultDict) -> None:
        """处理识别结果."""
        text = result.get("text", "")
        mode = result.get("mode", "")
        is_final = result.get("is_final", False)

        if not text:
            return

        if mode in ("offline", "2pass-offline") or is_final:
            result_type = ResultType.FINAL
            # 不在日志中记录语音识别结果，以保护隐私
        else:
            result_type = ResultType.INTERIM
            logger.debug(f"AudioEngine._process_result() - INTERIM: {text}")

        if self._result_callback:
            self._result_callback(text, result_type)
