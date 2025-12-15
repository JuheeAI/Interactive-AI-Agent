import multiprocessing
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
import transformers
from transformers import Sam2Processor, Sam2Model

print(f"현재 Transformers 버전: {transformers.__version__}")

MODEL = None
PROCESSOR = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def load_model():
    """모델과 프로세서를 메모리에 한 번만 로드합니다."""
    global MODEL, PROCESSOR
    if MODEL is None:
        model_id = "facebook/sam2.1-hiera-large"
        print(f"SAM 2.1 모델 로딩 중: {model_id} (Device: {DEVICE})...")
        
        try:
            PROCESSOR = Sam2Processor.from_pretrained(model_id)
            MODEL = Sam2Model.from_pretrained(model_id).to(DEVICE)
            print("SAM 2.1 모델 로딩 완료!")
        except Exception as e:
            print(f"모델 로딩 실패: {e}")
            raise e

def run_sam_box(image: Image.Image, box: list) -> Image.Image:
    """
    이미지와 Bounding Box([x1, y1, x2, y2])를 받아 마스크 이미지를 반환합니다.
    """
    load_model()
    
    # SAM 2 입력 형식 (Batch 1, Object 1)
    input_boxes = [[box]]
    
    # 입력 처리
    inputs = PROCESSOR(
        images=image, 
        input_boxes=input_boxes, 
        return_tensors="pt"
    ).to(DEVICE)

    # 추론
    with torch.no_grad():
        outputs = MODEL(**inputs)

    try:
        masks = outputs.pred_masks[0] # (1, 1, 3, 256, 256) -> (1, 3, 256, 256)

        orig_h, orig_w = inputs["original_sizes"][0].tolist()

        upscaled_masks = F.interpolate(
            masks, 
            size=(orig_h, orig_w), 
            mode="nearest", 
            # align_corners=False
        )

        best_mask = upscaled_masks[0, 0]

        best_mask = (best_mask > 0.0).float()

        mask_numpy = best_mask.cpu().numpy()
        mask_image = Image.fromarray((mask_numpy * 255).astype(np.uint8))

        print(f"[Manual Fix] 마스크 수동 리사이징: {orig_w}x{orig_h}")
        return mask_image
    
    except Exception as e:
        print(f"[Critical] 수동 처리 중 에러: {e}")
        return Image.new('L', image.size, 0)