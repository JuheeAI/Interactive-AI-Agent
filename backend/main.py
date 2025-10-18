from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from tasks import run_vqa_task
import asyncio

app = FastAPI()

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
async def invoke_task():
    task = run_vqa_task.delay()
    return {"status": "processing", "job_id": task.id}

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    task = run_vqa_task.AsyncResult(job_id)
    
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