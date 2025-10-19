from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from tasks import run_agent_task, celery_app
from celery import states
from celery.result import AsyncResult
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
    ext = os.path.splitext(image.filename)[1]
    temp_image_path = f"temp_{uuid.uuid4()}{ext}"

    with open(temp_image_path, "wb") as buffer:
        buffer.write(await image.read())
    
    task = run_agent_task.delay(image_path=temp_image_path, user_prompt=prompt)
    
    return {"status": "processing", "job_id": task.id}

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    await websocket.accept()
    # AsyncResult를 직접 사용하여 task 객체를 가져옵니다.
    task = AsyncResult(job_id, app=celery_app)
    
    last_message = None
    try:
        # 작업이 끝날 때까지(SUCCESS 또는 FAILURE) 상태를 주기적으로 확인합니다.
        while task.state not in [states.SUCCESS, states.FAILURE]:
            if task.state == 'PROGRESS':
                current_message = task.info
                if current_message != last_message:
                    await websocket.send_json(current_message)
                    last_message = current_message
            # 상태 업데이트가 너무 잦지 않도록 잠시 대기합니다.
            await asyncio.sleep(0.5)

        # 루프가 끝난 후, 작업의 최종 상태를 확인합니다.
        if task.state == states.SUCCESS:
            # 작업이 성공한 경우, 정상적인 결과(result)를 전송합니다.
            await websocket.send_json(task.result)
        elif task.state == states.FAILURE:
            # 작업이 실패한 경우, 에러 정보를 담은 별도의 JSON 메시지를 만들어 전송합니다.
            error_info = str(task.info) # 예외 객체를 문자열로 변환
            await websocket.send_json({
                "status": "FAILED",
                "error": error_info
            })

    except WebSocketDisconnect:
        print(f"Client {job_id} disconnected")
    finally:
        await websocket.close()