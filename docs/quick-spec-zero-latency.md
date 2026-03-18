# Quick Spec: 零延迟语音识别架构

## 目标
解决用户点击"开始识别"后，WebSocket 连接建立期间（1-3秒）音频丢失的问题。

## 架构设计

### 核心组件

#### 1. AudioRecorder（新增）
```python
class AudioRecorder:
    """独立线程持续录音，通过队列输出"""

    # 职责：只负责录音，不关心连接状态
    # - 启动/停止录音
    # - 音频处理（增益、阈值过滤）
    # - 输出到线程安全队列
```

#### 2. ConnectionManager（新增）
```python
class ConnectionManager:
    """管理 WebSocket 连接生命周期，线程安全"""

    # 职责：封装连接复杂性
    # - establish(): 建立连接
    # - close(): 断开连接
    # - send(): 发送音频（内部处理连接状态）
    # - receive(): 接收识别结果
    # - is_connected(): 检查连接状态
```

#### 3. RecognitionManager（重构）
```python
class RecognitionManager:
    """协调音频采集和网络通信"""

    # 职责：编排各组件
    # - start_recording(): 启动录音 + 连接
    # - stop_recording(): 停止录音 + 断开
    # - on_result(): 结果回调
```

### 流程变更

**之前（有问题）：**
```
用户点击 → 建立连接 → 发送初始化 → 开始录音 → 发送音频
                      ↑ 这段时间丢失
```

**之后（修复后）：**
```
用户点击 → 立即开始录音 ─┬─→ 建立连接 → 发送初始化 → 发送队列中的音频
                        └─→ 接收结果 ←─────────────────────────────────────
```

## 实现细节

### 文件变更

1. **新增 `src/voice_input/audio_recorder.py`**
   - AudioRecorder 类
   - AudioChunk 数据类

2. **新增 `src/voice_input/connection_manager.py`**
   - ConnectionManager 类
   - ConnectionState 枚举

3. **修改 `src/voice_input/asr_client.py`**
   - 移除 recognize_with_stop 内部逻辑
   - 保留 AsrClientConfig, AsrResult 等

4. **修改 `src/voice_input/voice_gui.py`**
   - 更新 RecognitionManager 使用新组件

### 线程模型

```
主线程 (GTK)
    │
    ▼
RecognitionManager (在后台线程中运行 asyncio)
    │
    ├─→ AudioRecorder (独立线程) ──Queue──┐
    │                                        │
    └─→ ConnectionManager (asyncio) ───────┘
```

### 状态管理

```
IDLE ──start_recording()──→ RECORDING
  ↑                              │
  └────stop_recording()─────────┘
```

## 验收标准

1. 点击"开始识别"后立即开始录音，无延迟
2. WebSocket 连接建立期间的数据不丢失
3. 连接复用正常工作
4. 停止识别后正确释放资源
5. 现有测试通过

## 预计工作量

- AudioRecorder: 60 行
- ConnectionManager: 100 行
- RecognitionManager 重构: 40 行
- voice_gui.py 更新: 30 行
- 测试: 20 行
