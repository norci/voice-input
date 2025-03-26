#!/bin/bash
# 保存为 ~/scripts/audio_recorder.sh

# 配置参数
SERVER_URL="http://localhost:8000/transcribe"  # 服务端地址
TMP_DIR="$HOME/.cache/audio_recorder"          # 临时文件目录
PID_FILE="$TMP_DIR/recording.pid"              # 进程锁文件
AUDIO_FILE="$TMP_DIR/last_recording.mp3"       # 录音文件路径

# 创建缓存目录
mkdir -p "$TMP_DIR"

# 检查是否正在录音
if [ -f "$PID_FILE" ]; then
    # 停止录音
    kill -SIGTERM $(cat "$PID_FILE") && rm -f "$PID_FILE"
    # 发送录音文件
    if [ -f "$AUDIO_FILE" ]; then
        response=$(curl -s -F "file=@$AUDIO_FILE" "$SERVER_URL")
        rm "$AUDIO_FILE"
        wtype $response
    fi
else
    # 开始录音（PulseAudio 版本）
    echo "开始录音..."
    parec -d @DEFAULT_SOURCE@ --format=s16le --rate=16000 --channels=1 | lame --quiet -r --little-endian -s 16000 -m m --bitwidth 16 - "$AUDIO_FILE" &

    # 记录进程ID
    echo $! > "$PID_FILE"
fi
