import multiprocessing
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import torch
from PIL import Image
from transformers import Sam2Processor, Sam2Model

MODEL = None
PROCESSOR = None

def load_model():
    """모델과 프로세서를 메모리에 한 번만 로드합니다."""
    global MODEL, PROCESSOR
    if MODEL is None:
        model_path = "./tools/sam_models"
        PROCESSOR = Sam2Processor.from_pretrained(model_path)
        MODEL = Sam2Model.from_pretrained(model_path).to("cuda")

def run_sam_box(image: Image.Image, box: list) -> Image.Image:
    """
    이미지와 Bounding Box 좌표를 받아 마스크 이미지 객체를 반환합니다.
    """
    load_model()
    input_boxes = [[box]]
    inputs = PROCESSOR(images=image, input_boxes=input_boxes, return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = MODEL(**inputs)

    mask_tensor = PROCESSOR.post_process_masks(
        outputs.pred_masks.cpu(), 
        inputs["original_sizes"].cpu()
    )[0][0, 0] 

    mask_image = Image.fromarray(mask_tensor.numpy().astype('uint8') * 255)
    
    return mask_image 