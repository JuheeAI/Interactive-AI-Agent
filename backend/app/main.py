from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from .tasks import run_agent_task, celery_app
from celery import states
from celery.result import AsyncResult
import asyncio
import base64
import json

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

@app.post("/agent/invoke")
async def invoke_task(prompt: str = Form(...), image: UploadFile = File(...)):
    file_content = await image.read()
    image_data = base64.b64encode(file_content).decode("utf-8")

    task = run_agent_task.delay(prompt=prompt, image_data=image_data)

    return {"status": "processing", "job_id": task.id}

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
            error_info = str(task.info)
            await websocket.send_json({
                "status": "FAILED",
                "error": error_info
            })

    except WebSocketDisconnect:
        print(f"Client {job_id} disconnected")
    finally:
        await websocket.close()