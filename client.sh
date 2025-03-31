#!/bin/bash

# 配置参数
SERVER_URL="http://localhost:8000/transcribe"  # 服务端地址
TMP_DIR="$XDG_RUNTIME_DIR/voice-input"          # 临时文件目录
AUDIO_FILE="$TMP_DIR/last_recording"       # 录音文件路径
PIDFILE="$TMP_DIR/pid"       # 录音文件路径
NTF="$TMP_DIR/ntf"
# whisper: m4a mp3 webm mp4 mpga wav mpeg
# 创建缓存目录
[ -d "$TMP_DIR" ] || mkdir -p "$TMP_DIR"

# 检查是否正在录音
if [ -f $PIDFILE ]; then
    # 停止录音
    sleep 0.1; kill -SIGTERM $(cat $PIDFILE) ; rm $PIDFILE
    # 发送录音文件
    if [ -f "$AUDIO_FILE" ]; then
        duration=$(printf "%.0f" $(ffprobe -i "$AUDIO_FILE" -show_entries format=duration -v quiet -of csv="p=0"))
        if [ $duration -gt 1 ]; then
            notify-send -r $(cat $NTF) "开始识别"
            wtype $(curl -s -F "file=@$AUDIO_FILE" "$SERVER_URL" | jq -r '.text')
            notify-send -r $(cat $NTF) -t 2000 "识别结束"
        else
            notify-send -r $(cat $NTF) -t 2000 "录音时间太短" "$duration"
        fi
        rm "$AUDIO_FILE"
    fi
else
    notify-send -p "语音输入..." > $NTF
    # 开始录音（PulseAudio 版本）
    parecord --latency-msec=10 --format=s16le --rate=16000 --channels=1 --file-format=wav $AUDIO_FILE &
    echo $! > $PIDFILE
fi
