from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .tasks import run_agent_task, celery_app
from celery import states
from celery.result import AsyncResult
import asyncio
import base64
import json

app = FastAPI()

# --- 데이터 모델 정의 ---
class TaskRequest(BaseModel):
    prompt: str
    image_data: str # base64 string

# --- CORS 설정 ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 유틸리티: 큐 결정 로직 ---
def get_target_queue(prompt: str) -> str:
    # 생성/변환 등 GPU 부하가 큰 키워드 체크
    heavy_keywords = ["draw", "transform", "make", "generate", "change", "create", "spaceship"]
    if any(k in prompt.lower() for k in heavy_keywords):
        return "heavy_tasks"
    return "light_tasks"

@app.get("/")
def read_root():
    return {"Hello": "Backend"}

# 1. 기존 Form 데이터 전송 방식 (이미지 파일 업로드)
@app.post("/agent/invoke")
async def invoke_task(prompt: str = Form(...), image: UploadFile = File(...)):
    file_content = await image.read()
    image_data = base64.b64encode(file_content).decode("utf-8")

    # 큐 분리 적용
    target_queue = get_target_queue(prompt)
    
    task = run_agent_task.apply_async(
        kwargs={"prompt": prompt, "image_data": image_data},
        queue=target_queue
    )

    return {"status": "processing", "job_id": task.id, "queue": target_queue}

# 2. JSON 데이터 전송 방식 (Base64 이미지 데이터)
@app.post("/run")
async def run_task(request: TaskRequest):
    target_queue = get_target_queue(request.prompt)
    
    task = run_agent_task.apply_async(
        args=[request.prompt, request.image_data],
        queue=target_queue
    )
    return {"task_id": task.id, "queue": target_queue}

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    task = AsyncResult(job_id, app=celery_app)
    
    last_message = None
    try:
        while task.state not in [states.SUCCESS, states.FAILURE]:
            if task.state == 'PROGRESS':
                current_message = task.info
                if current_message != last_message:
                    await websocket.send_json(current_message)
                    last_message = current_message
            await asyncio.sleep(0.5)

        if task.state == states.SUCCESS:
            await websocket.send_json(task.result)
        elif task.state == states.FAILURE:
            await websocket.send_json({
                "status": "FAILED", 
                "error": str(task.info)
            })

    except WebSocketDisconnect:
        print(f"Client {job_id} disconnected")
    finally:
        try:
            await websocket.close()
        except:
            pass