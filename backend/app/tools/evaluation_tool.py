import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image

MODEL = None
PROCESSOR = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

def load_clip_model():
    global MODEL, PROCESSOR
    if MODEL is None:
        model_id = "openai/clip-vit-base-patch32"
        print(f"평가용 CLIP 모델 로딩 중: {model_id}...")
        try:
            PROCESSOR = CLIPProcessor.from_pretrained(model_id)
            MODEL = CLIPModel.from_pretrained(model_id).to(DEVICE)
            print("CLIP 모델 로딩 완료!")
        except Exception as e:
            print(f"CLIP 모델 로딩 실패: {e}")
            return False
    return True

def calculate_clip_score(image: Image.Image, text: str) -> float:
    """
    이미지와 텍스트 사이의 유사도(CLIP Score)를 계산합니다.
    점수가 높을수록 이미지가 텍스트를 잘 묘사한 것입니다.
    """
    if not load_clip_model():
        return 0.0

    # 입력 처리
    inputs = PROCESSOR(
        text=[text], 
        images=image, 
        return_tensors="pt", 
        padding=True
    ).to(DEVICE)

    with torch.no_grad():
        outputs = MODEL(**inputs)
    
    # image-text similarity score (Logits)
    logits_per_image = outputs.logits_per_image 
    score = logits_per_image.item() # 실수값으로 변환
    
    return round(score, 4)