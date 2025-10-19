from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from tasks import run_agent_task, celery_app 
import asyncio
import os
import uuid

app = FastAPI()

# --- CORS 설정 ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"Hello": "Backend"}

# --- 메인 에이전트 호출 엔드포인트 ---
@app.post("/agent/invoke")
async def invoke_task(prompt: str = Form(...), image: UploadFile = File(...)):
    # 고유한 파일명 생성 (예: temp_cat.jpg -> temp_a1b2c3d4.jpg)
    ext = os.path.splitext(image.filename)[1]
    temp_image_path = f"temp_{uuid.uuid4()}{ext}"

    with open(temp_image_path, "wb") as buffer:
        buffer.write(await image.read())
    
    task = run_agent_task.delay(image_path=temp_image_path, user_prompt=prompt)
    
    return {"status": "processing", "job_id": task.id}

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    task = celery_app.AsyncResult(job_id)
    
    last_message = None
    try:
        while not task.ready():
            if task.state == 'PROGRESS':
                current_message = task.info
                if current_message != last_message:
                    await websocket.send_json(current_message)
                    last_message = current_message
            await asyncio.sleep(1)
        await websocket.send_json(task.result)
    except WebSocketDisconnect:
        print(f"Client {job_id} disconnected")
    finally:
        await websocket.close()