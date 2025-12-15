import time
import json
import base64
import io
import os
import requests
from PIL import Image
from celery import Celery
import wandb
import torch

try:
    from .tools.agent_prompt import AGENT_PROMPT
except ImportError:
    AGENT_PROMPT = """
    You are an AI task planner. Output strictly JSON.
    """

from .tools.vqa_tool import run_vqa
from .tools.object_detection_tool import run_object_detection

try:
    from .tools.sam_tool import run_sam_box as run_sam
except ImportError:
    from .tools.sam_tool import run_sam

from .tools.sd_tool import run_inpainting  
from .tools.evaluation_tool import calculate_clip_score

# --- 설정 ---
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    'tasks',
    broker=broker_url,
    backend=backend_url
)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

@celery_app.task(bind=True)
def run_agent_task(self, prompt: str, image_data: str):
    task_start_time = time.time()

    # GPU 메모리 측정 초기화 (이전 작업의 기록 삭제)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    wandb.init(project="ai_agent_project", name=f"job_{self.request.id}", reinit=True)
    
    try:
        image_bytes = base64.b64decode(image_data)
        original_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        print(f"🧠 LLM: '{prompt}'에 대한 계획 수립 중...")

        llm_start = time.time()
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": AGENT_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        plan = json.loads(response.json()['choices'][0]['message']['content']).get('plan', [])
        
        llm_duration = time.time() - llm_start
        wandb.log({"timer/llm_planning": llm_duration}) 
        
        print(f"📋 계획: {json.dumps(plan, indent=2)}")

        last_result = None
        final_data = None
        
        # CLIP 평가를 위해 '목표 프롬프트'를 저장할 변수
        target_prompt = "" 
        
        for idx, step in enumerate(plan):
            tool = step['tool_name']
            params = step['parameters']
            print(f"🚀 [Step {idx+1}] {tool} 실행 중...")

            for k, v in params.items():
                if v == "[PREVIOUS_STEP_RESULT]": params[k] = last_result
                elif v == "[ORIGINAL_IMAGE]": params[k] = original_image

            # --- 도구 분기 처리 ---
            start_t = time.time()
            
            if tool == "run_object_detection":
                last_result = run_object_detection(original_image, params['query'])
                if not last_result: raise Exception("객체를 찾지 못했습니다.")
                print(f"좌표: {last_result}")

            elif tool == "run_sam":
                last_result = run_sam(original_image, last_result)
                print("마스크 생성 완료")
                if isinstance(last_result, Image.Image):
                     wandb.log({f"step_{idx}_mask": wandb.Image(last_result)})

            elif tool == "run_inpainting":
                print("SD3 이미지 생성 중...")
                # 생성에 사용된 프롬프트 저장 (평가용)
                target_prompt = params['prompt']
                
                last_result = run_inpainting(params['image'], params['mask_image'], params['prompt'])
                final_data = last_result
                if isinstance(last_result, Image.Image):
                     wandb.log({f"step_{idx}_result": wandb.Image(last_result)})

            elif tool == "run_vqa":
                last_result = run_vqa(original_image, params['question'])
                final_data = last_result
            
            duration = time.time() - start_t
            wandb.log({f"timer/{tool}": duration})
            print(f"[Step {idx+1}] 완료 ({duration:.2f}s)")

        total_latency = time.time() - task_start_time

        # --- 정량적 평가 지표 측정 ---
        metrics = {"timer/total_latency": total_latency}

        # 1. GPU Peak Memory 측정 (MB)
        if torch.cuda.is_available():
            peak_memory = torch.cuda.max_memory_allocated() / (1024 ** 2)
            metrics["system/peak_gpu_memory_mb"] = peak_memory
            print(f"GPU Peak Memory: {peak_memory:.2f} MB")

        # 2. CLIP Score 측정 (이미지 생성 작업이었을 경우)
        if isinstance(final_data, Image.Image) and target_prompt:
            clip_score = calculate_clip_score(final_data, target_prompt)
            metrics["evaluation/clip_score"] = clip_score
            metrics["evaluation/target_prompt"] = target_prompt
            print(f"CLIP Score: {clip_score} (Prompt: {target_prompt})")
        
        # 지표 전송
        wandb.log(metrics)
        wandb.finish()
        
        # 최종 결과 반환
        result_payload = {
            "status": "success",
            "metrics": metrics 
        }

        if isinstance(final_data, Image.Image):
            buf = io.BytesIO()
            final_data.save(buf, format="JPEG")
            result_payload["type"] = "image"
            result_payload["data"] = base64.b64encode(buf.getvalue()).decode()
        else:
            result_payload["type"] = "text"
            result_payload["data"] = str(final_data)
            
        return result_payload

    except Exception as e:
        print(f"에러 발생: {e}")
        wandb.finish()
        return {"status": "error", "error": str(e)}