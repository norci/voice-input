#!/bin/bash

# 配置参数
TMP_DIR="$XDG_RUNTIME_DIR/voice-input"        # 临时文件目录
AUDIO_FILE="$TMP_DIR/last_recording"          # 录音文件路径
PIDFILE="$TMP_DIR/pid"                        # 录音文件路径
NTF="$TMP_DIR/ntf"
# whisper: m4a mp3 webm mp4 mpga wav mpeg
# 创建缓存目录
[ -d "$TMP_DIR" ] || mkdir -p "$TMP_DIR"

# 检查是否正在录音
if [ -f $PIDFILE ]; then
    # 停止录音
    sleep 0.1
    kill -SIGTERM $(cat $PIDFILE)
    rm $PIDFILE
    read nid <$NTF
    rm $NTF
    notify="notify-send -r $nid -t 2000"
    # 发送录音文件
    if [ -f "$AUDIO_FILE" ]; then
        duration=$(printf "%.0f" $(ffprobe -i "$AUDIO_FILE" -show_entries format=duration -v quiet -of csv="p=0"))
        if [ $duration -lt 1 ]; then
            $notify "录音时间太短" "$duration"
        else
            $notify "开始识别"
            # resp=$(curl https://ai.gitee.com/v1/audio/transcriptions \
            #     -s \
            #     -X POST \
            #     -H "Authorization: Bearer xxx" \
            #     -F "model=SenseVoiceSmall" \
            #     -F "language=auto" \
            #     -F "file=@$AUDIO_FILE")
            resp=$(curl -s -F "file=@$AUDIO_FILE" "http://localhost:8000/transcribe")
            text=$(echo "$resp" | jq -r '.text')
            if [ "$text" != "null" ]; then
                wtype "" "$text"
                $notify "识别结束"
            else
                $notify "识别错误:"$(echo "$resp" | jq -r '.error')
            fi
        fi
        rm "$AUDIO_FILE"
    fi
else
    notify-send -p "语音输入..." >$NTF
    parecord --latency-msec=10 --format=s16le --rate=16000 --channels=1 --file-format=wav $AUDIO_FILE &
    echo $! >$PIDFILE
fi
