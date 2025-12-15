import multiprocessing

try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import torch
from PIL import Image
from transformers import Owlv2Processor, Owlv2ForObjectDetection

PROCESSOR = None
MODEL = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def load_model():
    global MODEL, PROCESSOR
    if MODEL is None:
        print(f"OwlV2 모델 로딩 중 (Device: {DEVICE})...")
        model_id = "google/owlv2-base-patch16-ensemble"
        PROCESSOR = Owlv2Processor.from_pretrained(model_id)
        MODEL = Owlv2ForObjectDetection.from_pretrained(model_id).to(DEVICE)
        print("OwlV2 모델 로딩 완료!")

def run_object_detection(image: Image.Image, query: str) -> list | None:
    """
    이미지와 텍스트 쿼리를 받아 객체의 바운딩 박스를 [x1, y1, x2, y2] 형식으로 반환합니다.
    """
    load_model()
    
    texts = [[query]]
    inputs = PROCESSOR(text=texts, images=image, return_tensors="pt").to("cuda")
    
    with torch.no_grad():
        outputs = MODEL(**inputs)
    
    target_sizes = torch.Tensor([image.size[::-1]]).to(DEVICE)

    results = PROCESSOR.post_process_grounded_object_detection(
        outputs=outputs, 
        target_sizes=target_sizes, 
        threshold=0.1)
    
    boxes = results[0]["boxes"]
    scores = results[0]["scores"]

    if len(boxes) == 0:
        return None
        
    max_score_idx = scores.argmax().item()
    best_box = boxes[max_score_idx].cpu().numpy().tolist()

    return [int(coord) for coord in best_box]  # [x1, y1, x2, y2]