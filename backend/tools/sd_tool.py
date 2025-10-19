import multiprocessing

try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import torch
from PIL import Image
from diffusers import AutoPipelineForInpainting

PIPELINE = None

def load_pipeline():
    """Inpainting 파이프라인을 메모리에 한 번만 로드합니다."""
    global PIPELINE
    if PIPELINE is None:
        PIPELINE = AutoPipelineForInpainting.from_pretrained(
            "runwayml/stable-diffusion-inpainting",
            torch_dtype=torch.float16,
            variant="fp16"
        ) # .to("cuda")
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
        num_inference_steps=20, 
        guidance_scale=7.5
    ).images[0]

    return result_image