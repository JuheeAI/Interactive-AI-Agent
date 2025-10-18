import torch
from PIL import Image
from transformers import AutoProcessor, AutoModelForCausalLM

MODEL = None
PROCESSOR = None

def load_model():
    """모델과 프로세서를 메모리에 한 번만 로드합니다."""
    global MODEL, PROCESSOR
    if MODEL is None:
        model_path = "./tools/vqa_models"  
        PROCESSOR = AutoProcessor.from_pretrained(model_path, trust_remote_code=True)
        MODEL = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16, 
            device_map="auto",
            trust_remote_code=True
        )

def run_vqa(image: Image.Image, question: str) -> str:
    """
    이미지와 질문을 받아 VQA 모델을 실행하고 답변을 반환합니다.
    """
    load_model() 

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": question},
            ],
        }
    ]

    text = PROCESSOR.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    
    inputs = PROCESSOR(text=[text], images=[image], padding=True, return_tensors="pt").to("cuda")

    generated_ids = MODEL.generate(**inputs, max_new_tokens=1024, use_cache=True)
    
    generated_ids_trimmed = [
        out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    
    output_text = PROCESSOR.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )[0]

    return output_text