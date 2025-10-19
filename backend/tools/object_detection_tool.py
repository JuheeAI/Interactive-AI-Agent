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

def load_od_model():
    """Object Detection 모델과 프로세서를 메모리에 한 번만 로드합니다."""
    global PROCESSOR, MODEL
    if PROCESSOR is None or MODEL is None:
        model_name = "google/owlv2-base-patch16-ensemble"
        PROCESSOR = Owlv2Processor.from_pretrained(model_name)
        MODEL = Owlv2ForObjectDetection.from_pretrained(model_name).to("cuda")

def run_object_detection(image: Image.Image, query: str) -> list | None:
    """
    이미지와 텍스트 쿼리를 받아 객체의 바운딩 박스를 [x1, y1, x2, y2] 형식으로 반환합니다.
    """
    load_od_model()
    
    texts = [[query]]
    inputs = PROCESSOR(text=texts, images=image, return_tensors="pt").to("cuda")
    
    with torch.no_grad():
        outputs = MODEL(**inputs)
    
    target_sizes = torch.Tensor([image.size[::-1]])
    results = PROCESSOR.post_process_object_detection(outputs=outputs, target_sizes=target_sizes, threshold=0.1)
    
    boxes = results[0]["boxes"]
    if len(boxes) > 0:
        box = boxes[0].tolist()
        return [int(coord) for coord in box]
        
    return None 