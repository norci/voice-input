"""音频采集器模块。

独立线程持续录音，通过队列输出音频数据。
"""

import logging
import queue
import threading
import time
from dataclasses import dataclass
from threading import Thread

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """音频数据块。"""

    data: bytes  # PCM 16-bit 格式
    timestamp: float  # 采集时间戳


class AudioRecorder:
    """独立线程持续录音，通过队列输出。"""

    def __init__(
        self,
        output_queue: queue.Queue[AudioChunk],
        sample_rate: int = 16000,
        blocksize: int = 1024,
        channels: int = 1,
        gain: float = 0.5,
        threshold: float = 0.01,
    ) -> None:
        """初始化音频采集器。

        Args:
            output_queue: 输出队列
            sample_rate: 采样率
            blocksize: 块大小
            channels: 声道数
            gain: 增益因子 (0.0 - 1.0)
            threshold: 阈值 (0.0 - 1.0)
        """
        self._queue = output_queue
        self._sample_rate = sample_rate
        self._blocksize = blocksize
        self._channels = channels
        self._gain = gain
        self._threshold = threshold

        self._running = threading.Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """启动录音（立即开始，不等待连接）。"""
        if self._running.is_set():
            logger.warning("AudioRecorder 已在运行")
            return

        self._running.set()
        self._thread = Thread(target=self._record_loop, daemon=True, name="AudioRecorder")
        self._thread.start()
        logger.debug("AudioRecorder 已启动")

    def stop(self) -> None:
        """停止录音。"""
        if not self._running.is_set():
            return

        self._running.clear()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        logger.debug("AudioRecorder 已停止")

    def is_running(self) -> bool:
        """检查是否正在录音。"""
        return self._running.is_set()

    def _record_loop(self) -> None:
        """录音循环。"""
        try:
            with sd.InputStream(
                channels=self._channels,
                samplerate=self._sample_rate,
                blocksize=self._blocksize,
                dtype=np.float32,
            ) as stream:
                while self._running.is_set():
                    try:
                        indata, _ = stream.read(self._blocksize)
                    except OSError as e:
                        if self._running.is_set():
                            logger.error(f"录音错误: {e}")
                        break

                    if not self._running.is_set():
                        break

                    audio_data = indata[:, 0] * self._gain

                    max_amplitude = np.max(np.abs(audio_data))
                    if max_amplitude < self._threshold:
                        audio_data = np.zeros_like(audio_data)

                    audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
                    chunk = AudioChunk(data=audio_bytes, timestamp=time.time())

                    try:
                        self._queue.put(chunk, timeout=0.1)
                    except queue.Full:
                        logger.warning("音频队列已满，丢弃数据")

        except Exception as e:
            logger.error(f"AudioRecorder 异常: {e}")
        finally:
            logger.debug("AudioRecorder 循环退出")
