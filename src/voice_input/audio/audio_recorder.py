"""音频采集器模块.

独立线程持续录音,通过队列输出音频数据.
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
    """音频数据块."""

    data: bytes  # PCM 16-bit 格式
    timestamp: float  # 采集时间戳


class AudioRecorderConfig:
    """Audio recorder configuration."""

    def __init__(
        self,
        sample_rate: int = 16000,
        blocksize: int = 1024,
        channels: int = 1,
        gain: float = 0.5,
        threshold: float = 0.01,
    ) -> None:
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.channels = channels
        self.gain = gain
        self.threshold = threshold


class AudioRecorder:
    """Record audio in a separate thread."""

    def __init__(
        self,
        output_queue: queue.Queue[AudioChunk],
        config: AudioRecorderConfig | None = None,
    ) -> None:
        """Initialize audio recorder.

        Args:
            output_queue: Output queue
            config: Audio configuration
        """
        self._queue = output_queue
        self._config = config or AudioRecorderConfig()
        self._running = threading.Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        """Start recording."""
        if self._running.is_set():
            logger.warning("AudioRecorder already running")
            return

        self._running.set()
        self._thread = Thread(target=self._record_loop, daemon=True, name="AudioRecorder")
        self._thread.start()
        logger.debug("AudioRecorder started")

    def stop(self) -> None:
        """Stop recording."""
        if not self._running.is_set():
            return

        self._running.clear()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

        # 清空队列,避免残留旧数据
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        logger.debug("AudioRecorder stopped")

    def is_running(self) -> bool:
        """Check if recording."""
        return self._running.is_set()

    def _record_loop(self) -> None:
        """Record loop."""
        cfg = self._config
        try:
            with sd.InputStream(
                channels=cfg.channels,
                samplerate=cfg.sample_rate,
                blocksize=cfg.blocksize,
                dtype=np.float32,
            ) as stream:
                while self._running.is_set():
                    try:
                        indata, _ = stream.read(cfg.blocksize)
                    except OSError:
                        # 设备断开等 OS 错误,记录日志
                        logger.warning("Recording device error, will retry")
                        break

                    if not self._running.is_set():
                        break

                    audio_data = indata[:, 0] * cfg.gain

                    max_amplitude = np.max(np.abs(audio_data))
                    if max_amplitude < cfg.threshold:
                        audio_data = np.zeros_like(audio_data)

                    audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
                    chunk = AudioChunk(data=audio_bytes, timestamp=time.time())

                    try:
                        self._queue.put(chunk, timeout=0.1)
                    except queue.Full:
                        logger.warning("Audio queue full, dropping data")

        except Exception:
            logger.exception("AudioRecorder error")
        finally:
            logger.debug("AudioRecorder 循环退出")
