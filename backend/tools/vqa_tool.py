import multiprocessing

# 이 코드를 파일 최상단에 추가하여 CUDA 충돌을 방지합니다.
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import torch
from PIL import Image
from transformers import BlipProcessor, BlipForQuestionAnswering

# 모델과 프로세서를 한 번만 로드하기 위한 전역 변수
PROCESSOR = None
MODEL = None

def load_vqa_model():
    """VQA 모델과 프로세서를 메모리에 한 번만 로드합니다."""
    global PROCESSOR, MODEL
    if PROCESSOR is None or MODEL is None:
        model_name = "Salesforce/blip-vqa-base"
        PROCESSOR = BlipProcessor.from_pretrained(model_name)
        MODEL = BlipForQuestionAnswering.from_pretrained(model_name).to("cuda")

def run_vqa(image: Image.Image, question: str) -> str:
    """
    이미지와 질문을 받아 답변을 텍스트로 반환합니다.
    """
    load_vqa_model()

    rgb_image = image.convert("RGB")

    inputs = PROCESSOR(rgb_image, question, return_tensors="pt").to("cuda")

    out = MODEL.generate(**inputs, max_new_tokens=50)

    answer = PROCESSOR.decode(out[0], skip_special_tokens=True)

    return answer