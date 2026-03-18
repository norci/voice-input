"""接口契约定义.

此文件定义所有模块间的接口契约.
所有子任务的实现必须遵守这些接口.
修改此文件需要通知所有并行开发的 worktree.

接口变更日志:
    v1.0 (2026-03-18): 初始版本
        - 定义 IVoiceService, IStateManager, IAudioEngine
        - 定义 IConnectionManager, IEventBus, IServiceFactory
        - 定义 VoiceState, EventType, 回调类型
"""

from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol

# ==================== 状态定义 ====================


class VoiceState(Enum):
    """语音识别状态枚举."""

    IDLE = "idle"
    RECORDING = "recording"
    POST_PROCESSING = "post_processing"
    RECONNECTING = "reconnecting"
    ERROR = "error"


# ==================== 结果类型定义 ====================
# ResultType 已移至 asr_config.py,避免循环依赖
# 使用时导入: from voice_input.asr_config import ResultType


# ==================== 回调类型定义 ====================

if TYPE_CHECKING:
    from voice_input.asr_config import ResultType

ResultCallback = Callable[[str, "ResultType"], None]
ErrorCallback = Callable[[str, str], None]  # (error_type, message)
StateCallback = Callable[[VoiceState, str], None]  # (state, error_message)
ReconnectingCallback = Callable[[int], None]  # (attempt)


# ==================== 核心服务接口 ====================


class IVoiceService(Protocol):
    """语音服务接口 - Facade模式的外观接口."""

    def start(self) -> bool:
        """开始语音识别.

        Returns:
            是否成功开始
        """
        ...

    def stop(self) -> None:
        """停止语音识别."""
        ...

    def reset(self) -> None:
        """重置服务状态."""
        ...

    @property
    def state(self) -> VoiceState:
        """获取当前状态."""
        ...

    @property
    def error_message(self) -> str:
        """获取错误信息."""
        ...

    def set_result_callback(self, cb: ResultCallback) -> None:
        """设置结果回调."""
        ...

    def set_error_callback(self, cb: ErrorCallback) -> None:
        """设置错误回调."""
        ...

    def set_state_callback(self, cb: StateCallback) -> None:
        """设置状态变化回调."""
        ...


class IStateManager(Protocol):
    """状态管理器接口 - 状态模式."""

    @property
    def state(self) -> VoiceState:
        """获取当前状态."""
        ...

    @property
    def error_message(self) -> str:
        """获取错误信息."""
        ...

    def transition_to(self, new_state: VoiceState, error: str = "") -> None:
        """状态转换.

        Args:
            new_state: 新状态
            error: 错误信息(仅在 ERROR 状态时使用)
        """
        ...

    def can_start(self) -> bool:
        """检查是否可以开始识别."""
        ...

    def can_stop(self) -> bool:
        """检查是否可以停止识别."""
        ...

    def set_state_callback(self, cb: StateCallback) -> None:
        """设置状态变化回调."""
        ...


class IAudioEngine(Protocol):
    """音频引擎接口."""

    def start(self) -> bool:
        """启动音频引擎.

        Returns:
            是否成功启动
        """
        ...

    def stop_sending(self) -> None:
        """停止发送,保持接收.

        停止录音,但保持 WebSocket 连接继续接收识别结果.
        """
        ...

    def stop(self) -> None:
        """完全停止音频引擎."""
        ...

    def set_result_callback(self, cb: ResultCallback) -> None:
        """设置结果回调."""
        ...

    def set_error_callback(self, cb: ErrorCallback) -> None:
        """设置错误回调."""
        ...

    def set_reconnecting_callback(self, cb: ReconnectingCallback) -> None:
        """设置重连回调."""
        ...


class IConnectionManager(Protocol):
    """连接管理器接口 - 适配器模式."""

    async def connect(self) -> None:
        """建立连接."""
        ...

    async def connect_with_retry(self, on_reconnecting: ReconnectingCallback | None = None) -> None:
        """建立连接,支持重试.

        Args:
            on_reconnecting: 重连时的回调,参数为重连尝试次数
        """
        ...

    async def disconnect(self) -> None:
        """断开连接."""
        ...

    async def send(self, data: bytes) -> None:
        """发送数据.

        Args:
            data: 要发送的字节数据
        """
        ...

    async def receive(self) -> bytes | None:
        """接收数据.

        Returns:
            接收到的字节数据,无数据时返回 None
        """
        ...

    @property
    def is_connected(self) -> bool:
        """检查是否已连接."""
        ...


# ==================== 事件系统接口 ====================


class EventType(Enum):
    """事件类型."""

    RESULT = "result"
    ERROR = "error"
    STATE_CHANGED = "state_changed"
    RECONNECTING = "reconnecting"


class IEventBus(Protocol):
    """事件总线接口 - 观察者模式."""

    def subscribe(self, event_type: EventType, callback: Callable[..., Any]) -> None:
        """订阅事件.

        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        ...

    def unsubscribe(self, event_type: EventType, callback: Callable[..., Any]) -> None:
        """取消订阅.

        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        ...

    def publish(self, event_type: EventType, data: dict[str, Any]) -> None:
        """发布事件.

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        ...


# ==================== 工厂接口 ====================


class IServiceFactory(Protocol):
    """服务工厂接口 - 工厂模式."""

    def create_voice_service(self, config: object) -> IVoiceService:
        """创建语音服务实例.

        Args:
            config: ASR 客户端配置

        Returns:
            语音服务实例
        """
        ...

    def create_audio_engine(self, config: object) -> IAudioEngine:
        """创建音频引擎实例.

        Args:
            config: ASR 客户端配置

        Returns:
            音频引擎实例
        """
        ...

        # def create_connection_manager(self, config: object) -> IConnectionManager:
        """创建连接管理器.

        Args:
            config: ASR 客户端配置

        Returns:
            连接管理器实例
        """
        ...
