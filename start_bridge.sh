#!/bin/bash
# 启动 TV-Schwab 下单桥 (Mac / Linux)
cd "$(dirname "$0")"
if [ ! -f .env ]; then
    echo "找不到 .env, 先复制 .env.example 为 .env 并填好"
    exit 1
fi
set -a
source .env
set +a
echo "DRY_RUN=$DRY_RUN"
./.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
