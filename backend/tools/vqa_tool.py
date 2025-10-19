import multiprocessing

# CUDA 충돌 방지
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM

# 모델과 프로세서를 한 번만 로드하기 위한 전역 변수
PROCESSOR = None
MODEL = None
MODEL_PATH = "./tools/vqa_models" 

def load_vqa_model():
    """VQA 모델과 프로세서를 메모리에 한 번만 로드합니다."""
    global PROCESSOR, MODEL
    if PROCESSOR is None or MODEL is None:
        # AutoClass와 trust_remote_code=True를 사용하여 로컬 모델을 로드합니다.
        PROCESSOR = AutoProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
        MODEL = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH, 
            torch_dtype=torch.float16, 
            device_map="auto", 
            trust_remote_code=True
        )


def run_vqa(image: Image.Image, question: str) -> str:
    """
    LLaVA 모델을 사용하여 이미지와 질문에 대한 답변을 생성합니다.
    """
    load_vqa_model()

    # LLaVA 모델이 요구하는 대화 형식(messages)으로 입력을 구성합니다.
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": question}
            ]
        }
    ]
    
    # 모델 입력을 위한 템플릿 적용
    prompt = PROCESSOR.apply_chat_template(messages, add_generation_prompt=True)
    
    # 이미지와 텍스트를 함께 처리
    inputs = PROCESSOR(text=prompt, images=image, return_tensors="pt").to("cuda", torch.float16)
    output = MODEL.generate(**inputs, max_new_tokens=100)
    decoded_output = PROCESSOR.decode(output[0], skip_special_tokens=True)
    
    # 출력에서 프롬프트 부분을 제거하고 순수한 답변만 추출
    try:
        answer = decoded_output.split("ASSISTANT:")[1].strip()
    except IndexError:
        answer = decoded_output

    return answer