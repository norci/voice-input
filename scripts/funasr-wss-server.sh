#!/bin/bash
# FunASR WebSocket Server 启动脚本
# 支持 start|stop|restart|status 命令

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="${XDG_RUNTIME_DIR:-/tmp}/funasr-wss-server.pid"
LOG_FILE="${XDG_RUNTIME_DIR:-/tmp}/funasr-wss-server.log"

# 默认参数
HOST="127.0.0.1"
PORT="10095"

# 解析命令行参数
ACTION="$1"
shift || true

while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# 获取 PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    fi
}

# 检查进程是否运行
is_running() {
    local pid
    pid=$(get_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

# 启动服务
do_start() {
    if is_running; then
        echo "FunASR WebSocket Server 已在运行 (PID: $(get_pid))"
        return 0
    fi

    echo "启动 FunASR WebSocket Server..."
    echo "  Host: $HOST"
    echo "  Port: $PORT"

    # 启动服务并记录 PID
    nohup uv --directory "$PROJECT_ROOT/FunASR/runtime/python/websocket" run funasr_wss_server.py \
        --host "$HOST" \
        --port "$PORT" \
        > "$LOG_FILE" 2>&1 &

    echo $! > "$PID_FILE"
    echo "FunASR WebSocket Server 已启动 (PID: $(get_pid))"
    echo "日志文件: $LOG_FILE"
}

# 停止服务
do_stop() {
    if ! is_running; then
        echo "FunASR WebSocket Server 未在运行"
        rm -f "$PID_FILE"
        return 0
    fi

    local pid
    pid=$(get_pid)
    echo "停止 FunASR WebSocket Server (PID: $pid)..."

    # 发送 SIGTERM
    kill -TERM "$pid" 2>/dev/null || true

    # 等待进程结束
    local count=0
    local max_wait=30
    while is_running && [ $count -lt $max_wait ]; do
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    echo

    # 如果还没结束，强制终止
    if is_running; then
        echo "强制终止进程..."
        kill -9 "$pid" 2>/dev/null || true
    fi

    rm -f "$PID_FILE"
    echo "FunASW WebSocket Server 已停止"
}

# 重启服务
do_restart() {
    do_stop
    sleep 2
    do_start
}

# 查看状态
do_status() {
    if is_running; then
        echo "FunASR WebSocket Server 正在运行 (PID: $(get_pid))"
        echo "日志文件: $LOG_FILE"
        return 0
    else
        echo "FunASR WebSocket Server 未在运行"
        return 1
    fi
}

# 执行操作
case "$ACTION" in
    start)
        do_start
        ;;
    stop)
        do_stop
        ;;
    restart)
        do_restart
        ;;
    status)
        do_status
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status} [--host HOST] [--port PORT]"
        echo ""
        echo "参数:"
        echo "  --host HOST   监听地址 (默认: 127.0.0.1)"
        echo "  --port PORT  监听端口 (默认: 10095)"
        exit 1
        ;;
esac
