from celery import Celery, states
from celery.app.task import Task
from PIL import Image
from tools.vqa_tool import run_vqa  
import os
import time
import wandb

celery_app = Celery(
    'tasks',
    broker=os.environ.get("CELERY_BROKER_URL"),
    backend=os.environ.get("CELERY_RESULT_BACKEND")
)

@celery_app.task(bind=True)
def run_vqa_task(self: Task): 
    """
    VQA 모델을 실행하는 실제 AI 작업
    """
    wandb.init(project="ai_agent_project", name=f"job_{self.request.id}")
    start_time = time.time()
    wandb.log({"status": "STARTED", "task_type": "VQA"})

    try:
        self.update_state(state='PROGRESS', meta={'status': 'VQA 모델 실행 시작...'})
        
        image_path = "test_image.jpg" 
        question = "What is in this image?"
        
        image = Image.open(image_path)
        answer = run_vqa(image, question)

        end_time = time.time()
        duration = end_time - start_time
        wandb.log({"status": "COMPLETED", "duration_seconds": duration, "question": question, "answer": answer})
        wandb.finish()
        
        return {'status': 'VQA 작업 완료!', 'answer': answer, 'duration': duration}

    except Exception as e:
        wandb.log({"status": "FAILED", "error": str(e)})
        wandb.finish()
        self.update_state(state=states.FAILURE, meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise e