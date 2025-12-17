import torch
from transformers import (
    pipeline, 
    AutoModelForVisualQuestionAnswering, 
    AutoTokenizer, 
    AutoImageProcessor
)
from PIL import Image

VQA_PIPELINE = None

def run_vqa(image: Image.Image, question: str) -> str:
    global VQA_PIPELINE
    
    if VQA_PIPELINE is None:
        print("VQA 모델 로딩 중...")
        device = 0 if torch.cuda.is_available() else -1
        
        model_id = "dandelin/vilt-b32-finetuned-vqa"
        
        model = AutoModelForVisualQuestionAnswering.from_pretrained(
            model_id, 
            weights_only=False
        )
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        image_processor = AutoImageProcessor.from_pretrained(model_id)
        
        VQA_PIPELINE = pipeline(
            "visual-question-answering", 
            model=model,
            tokenizer=tokenizer,
            image_processor=image_processor,
            device=device
        )
    
    print(f"VQA 질문 분석: {question}")

    try:
        result = VQA_PIPELINE(image=image, question=question, top_k=1)
        
        answer = result[0]['answer']
        
        print(f"VQA 답변: {answer}")
        return answer

    except Exception as e:
        print(f"VQA 추론 중 에러: {e}")
        return "Error in VQA"