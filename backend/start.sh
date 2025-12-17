#!/bin/bash

echo "기존 Celery 프로세스 종료 중..."
kill -9 $(pgrep -f "celery")
sleep 2

echo "Redis 서버 상태 확인 중..."
if ! pgrep -x "redis-server" > /dev/null
then
    echo "   Redis가 꺼져 있습니다. 지금 시작합니다..."
    redis-server --daemonize yes
    sleep 1
else
    echo "   Redis가 이미 실행 중입니다."
fi

echo "로그 파일 초기화..."
> worker.log

echo "환경 변수 설정 중..."
ENV_FILE="./.env"
if [ -f "$ENV_FILE" ]; then
    echo ".env 파일에서 환경 변수 로드 중..."
    set -a
    source "$ENV_FILE"
    set +a
else
    echo ".env 파일이 없습니다."
    exit 1
fi

export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
export HF_HOME="/workspace/hf_cache"
export HF_HUB_DISABLE_PROGRESS_BARS=1

export IMAGEIO_FFMPEG_EXE=/usr/bin/ffmpeg
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128
export CUDA_MODULE_LOADING=LAZY
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "Celery 서버 시작 (Eventlet Pool, Concurrency=10)..."
# 백그라운드 실행
WANDB_API_KEY=$WANDB_API_KEY WANDB_PROJECT=$WANDB_PROJECT \
nohup celery -A app.tasks worker \
    -Q heavy_tasks \
    --concurrency=1 \
    --pool=solo \
    --hostname=heavy_worker@%h > heavy.log 2>&1 &

nohup celery -A app.tasks worker \
    -Q light_tasks \
    --concurrency=1 \
    --pool=solo \
    --hostname=light1@%h > light1.log 2>&1 &
nohup celery -A app.tasks worker \
    -Q light_tasks \
    --concurrency=1 \
    --pool=solo \
    --hostname=light2@%h > light2.log 2>&1 &

echo "FastAPI Server 시작..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo "서버가 실행되었습니다. 로그를 확인합니다..."
echo "------------------------------------------------"
tail -f worker.log
