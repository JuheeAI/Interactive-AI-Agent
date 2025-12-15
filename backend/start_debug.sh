#!/bin/bash

# 기존 Celery 프로세스 종료 (혹시 모를 충돌 방지)
echo "기존 Celery 프로세스 종료 중..."
pkill -f 'celery -A app.tasks' 2>/dev/null

# 환경 변수 설정 (필요하다면 여기에 추가)

# Celery Worker를 포그라운드(Foreground)에서 실행
# 이렇게 해야 오류 메시지가 터미널에 바로 출력됩니다.
echo "Celery Worker (prefork, concurrency=4) 디버그 모드 시작..."
exec celery -A app.tasks worker --loglevel=DEBUG --pool=prefork --concurrency=4