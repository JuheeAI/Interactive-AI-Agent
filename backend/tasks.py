from celery import Celery, states
from celery.app.task import Task
import os
import time
import wandb

celery_app = Celery(
    'tasks',
    broker=os.environ.get("CELERY_BROKER_URL"),
    backend=os.environ.get("CELERY_RESULT_BACKEND")
)

@celery_app.task(bind=True)
def run_fake_ai_task(self: Task):
    """
    10초 동안 진행 상황을 업데이트하는 가짜 AI 작업
    """
    # W&B 초기화
    wandb.init(project="ai_agent_project", name=f"job_{self.request.id}")

    start_time = time.time()
    wandb.log({"status": "STARTED"})

    # 1. 작업 시작 알림
    self.update_state(state='PROGRESS', meta={'status': '1/3 - 작업 시작...'})
    time.sleep(5)

    # 2. 50% 진행 알림
    self.update_state(state='PROGRESS', meta={'status': '2/3 - 50% 진행 중...'})
    wandb.log({"progress": 50})
    time.sleep(5)

    # 작업 완료
    end_time = time.time()
    duration = end_time - start_time
    wandb.log({"status": "COMPLETED", "duration_seconds": duration})
    wandb.finish()

    return {'status': '3/3 - 작업 완료!', 'duration': duration}