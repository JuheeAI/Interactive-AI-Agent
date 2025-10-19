import multiprocessing
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

from celery import Celery, states
from celery.app.task import Task
from PIL import Image
import os, time, wandb, json, re, base64
from io import BytesIO
from openai import OpenAI 

from tools.vqa_tool import run_vqa
from tools.sam_tool import run_sam_box
from tools.sd_tool import run_inpainting
from tools.object_detection_tool import run_object_detection 
from tools.agent_prompt import AGENT_PROMPT  

# Celery 설정
celery_app = Celery(
    'tasks',
    broker=os.environ.get("CELERY_BROKER_URL"),
    backend=os.environ.get("CELERY_RESULT_BACKEND")
)

# OpenAI 클라이언트 초기화
try:
    llm_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception as e:
    llm_client = None

# Helper Functions
def image_to_base64(image: Image.Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"

@celery_app.task(bind=True)
def run_agent_task(self: Task, image_path: str, user_prompt: str):
    start_time = time.time()

    if wandb.run is None:
        wandb.init(project="ai_agent_project", name=f"job_{self.request.id}", reinit=True)
    wandb.log({"status": "STARTED", "user_prompt": user_prompt, "image": wandb.Image(image_path)})

    try:
        if not llm_client:
            raise RuntimeError("OpenAI client not configured.")

        self.update_state(state='PROGRESS', meta={'status': 'LLM이 계획 수립 중...'})
        
        response = llm_client.chat.completions.create(
            model=os.getenv("AGENT_LLM_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": AGENT_PROMPT},
                {"role": "user", "content": f"## User Request\n{user_prompt}\nYour JSON Output:"}
            ],
            response_format={"type": "json_object"}
        )
        plan_json = json.loads(response.choices[0].message.content)
        wandb.log({"llm_plan": plan_json})

        original_image = Image.open(image_path).convert("RGB")
        previous_step_result = None

        for i, step in enumerate(plan_json.get("plan", [])):
            tool_name = step.get("tool_name")
            params = step.get("parameters", {})
            self.update_state(state='PROGRESS', meta={'status': f'({i+1}/{len(plan_json["plan"])}) {tool_name} 실행 중...'})
                        
            result = None
            if tool_name == "run_vqa":
                result = run_vqa(original_image, **params)
            
            elif tool_name == "run_object_detection":
                result = run_object_detection(original_image, **params)

            elif tool_name == "run_sam":
                # 이전 단계(run_object_detection)의 결과가 bbox 리스트이면 바로 사용합니다.
                # 더 이상 텍스트에서 bbox를 파싱할 필요가 없습니다.
                if isinstance(previous_step_result, list):
                    params["box"] = previous_step_result
                result = run_sam_box(original_image, **params)

            elif tool_name == "run_inpainting":
                # 필요한 이미지들을 파라미터에 직접 할당합니다.
                params["image"] = original_image
                if isinstance(previous_step_result, Image.Image):
                    params["mask_image"] = previous_step_result
                result = run_inpainting(**params)
            
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            if result is None and tool_name == "run_object_detection":
                 raise ValueError(f"Object Detection 실패: '{params.get('query')}' 객체를 이미지에서 찾을 수 없습니다.")

            previous_step_result = result
            wandb.log({f"step_{i+1}_{tool_name}_result": wandb.Image(result) if isinstance(result, Image.Image) else str(result)})

        duration = time.time() - start_time
        final_payload = {"result_type": "image", "data": image_to_base64(previous_step_result)} if isinstance(previous_step_result, Image.Image) else {"result_type": "text", "data": str(previous_step_result)}
        wandb.log({"final_result": wandb.Image(previous_step_result) if isinstance(previous_step_result, Image.Image) else str(previous_step_result), "status": "COMPLETED", "duration_seconds": duration})
        
        return {"status": "에이전트 작업 완료!", "result": final_payload, "duration": duration}

    except Exception as e:
        wandb.log({"status": "FAILED", "error": str(e)})
        self.update_state(state=states.FAILURE, meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise e
    finally:
        if wandb.run is not None:
            wandb.finish()
        if os.environ.get("KEEP_INPUT_IMAGE") != "1" and os.path.exists(image_path):
            os.remove(image_path)