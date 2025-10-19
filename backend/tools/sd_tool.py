import multiprocessing

try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import torch
from PIL import Image
from diffusers import StableDiffusion3InpaintPipeline
import os

PIPELINE = None

def load_pipeline():
    """SD3 파이프라인을 메모리에 한 번만 로드합니다."""
    global PIPELINE
    if PIPELINE is None:
        hf_token = os.environ.get("HUGGING_FACE_TOKEN")

        PIPELINE = StableDiffusion3InpaintPipeline.from_pretrained(
            "stabilityai/stable-diffusion-3-medium-diffusers", 
            torch_dtype=torch.float16,
            token=hf_token
        )
        PIPELINE.enable_model_cpu_offload()

def run_inpainting(image: Image.Image, mask_image: Image.Image, prompt: str) -> Image.Image:
    """
    원본 이미지, 마스크, 프롬프트를 받아 Inpainting을 수행하고 결과 이미지를 반환합니다.
    """
    load_pipeline()

    result_image = PIPELINE(
        prompt=prompt,
        image=image,
        mask_image=mask_image,
        num_inference_steps=28, 
        guidance_scale=7.0
    ).images[0]

    return result_image