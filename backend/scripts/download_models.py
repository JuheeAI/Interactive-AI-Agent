import torch
import os
from transformers import pipeline
from diffusers import Flux2Pipeline
from huggingface_hub import login

os.environ["HF_HOME"] = "/workspace/hf_cache"
os.environ["HTTP_TIMEOUT"] = "600" 

MY_HF_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")
if MY_HF_TOKEN:
    login(token=MY_HF_TOKEN)

def download_vqa():
    print("\n--- 1. VQA 모델 다운로드 중 (ViLT) ---")
    model_name = "dandelin/vilt-b32-finetuned-vqa"
    try:
        pipeline("visual-question-answering", model=model_name, model_kwargs={"weights_only": False})
        print("✅ VQA 모델 로드 완료.")
    except Exception as e:
        print(f"❌ VQA 다운로드 중 오류: {e}")

def download_flux():
    print("\n--- 2. FLUX.2 이미지 생성 모델 다운로드 중 (4-bit) ---")
    model_id = "diffusers/FLUX.2-dev-bnb-4bit"
    try:
        Flux2Pipeline.from_pretrained(
            model_id, 
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True
        )
        print("FLUX.2 모델 로드 완료.")
    except Exception as e:
        print(f"FLUX.2 다운로드 중 오류: {e}")

if __name__ == "__main__":
    print("AI 에이전트 필수 모델 사전 다운로드를 시작합니다.")
    download_vqa()
    download_flux()
    print("\n✨ 모든 모델이 /workspace/hf_cache 에 성공적으로 저장되었습니다.")