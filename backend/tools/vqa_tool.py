import multiprocessing

try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM
import os

PROCESSOR = None
MODEL = None
MODEL_ID = "lmms-lab/LLaVA-OneVision-1.5-4B-Instruct" 

def load_vqa_model():
    """VQA 모델(4B)을 Hugging Face Hub에서 직접 로드합니다."""
    global PROCESSOR, MODEL
    if PROCESSOR is None or MODEL is None:
        hf_token = os.environ.get("HUGGING_FACE_TOKEN")
        
        PROCESSOR = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True, token=hf_token)
        MODEL = AutoModelForCausalLM.from_pretrained(
            MODEL_ID, 
            torch_dtype=torch.float16, 
            device_map="auto", 
            trust_remote_code=True,
            token=hf_token
        )

def run_vqa(image: Image.Image, question: str) -> str:
    """
    LLaVA 모델을 사용하여 이미지와 질문에 대한 답변을 생성합니다.
    """
    load_vqa_model()

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": question}
            ]
        }
    ]
    
    prompt = PROCESSOR.apply_chat_template(messages, add_generation_prompt=True)
    inputs = PROCESSOR(text=prompt, images=image, return_tensors="pt").to("cuda", torch.float16)

    output = MODEL.generate(**inputs, max_new_tokens=100)
    decoded_output = PROCESSOR.decode(output[0], skip_special_tokens=True)
    
    try:
        answer = decoded_output.split("ASSISTANT:")[1].strip()
    except IndexError:
        answer = decoded_output

    return answer