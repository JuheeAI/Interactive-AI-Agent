import multiprocessing
import os
import torch
import logging
from PIL import Image
from diffusers import Flux2Pipeline, DiffusionPipeline
# from torch.profiler import profile, record_function, ProfilerActivity
import requests
import io
import time


# PROFILE_OUTPUT_DIR = "profiler_output" 
# os.makedirs(PROFILE_OUTPUT_DIR, exist_ok=True)

# 로깅 설정
logger = logging.getLogger(__name__)

# 멀티프로세싱 시작 방식 설정
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

MY_HF_TOKEN = os.environ.get("HUGGING_FACE_TOKEN")

class Flux2ImageGenerator:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Flux2ImageGenerator, cls).__new__(cls)
            cls._instance._is_loaded = False
        return cls._instance

    def __init__(self):
        if self._is_loaded:
            return
        self.pipeline = None
        self._is_loaded = True

    def _remote_text_encoder(self, prompt: str):
        if not prompt: return None
        device = "cuda" if torch.cuda.is_available() else "cpu"
        api_url = "https://remote-text-encoder-flux-2.huggingface.co/predict"

        encoder_start_time = time.time()
        logger.info(f"Sending prompt to Remote API: {api_url}")
        
        try:
            response = requests.post(
                api_url,
                json={"prompt": prompt},
                headers={
                    "Authorization": f"Bearer {MY_HF_TOKEN}",
                    "Content-Type": "application/json"
                },
                timeout=120
            )

            encoder_duration = time.time() - encoder_start_time
            
            if response.status_code != 200:
                logger.error(f"API Error ({response.status_code}): {response.text}")
                return None
                
            data = torch.load(io.BytesIO(response.content))
            
            if isinstance(data, (tuple, list)):
                return data[0].to(device)
            else:
                return data.to(device)

        except Exception as e:
            encoder_duration = time.time() - encoder_start_time
            logger.error(f"Remote Encoder Failed: {e}")
            logger.error(f"❌ Remote Encoder Exception Time: {encoder_duration:.2f}s")
            return None

    def load_pipeline(self):
        """FLUX.2 Img2Img 파이프라인을 로드합니다."""
        if self.pipeline is not None:
            return self.pipeline

        logger.info("⚡ FLUX.2 Img2Img 모델 로드 중 (Text Encoder는 Remote 사용)...")

        # FLUX.2 모델 로드 (Text Encoder는 원격으로 대체하므로 None)
        self.pipeline = Flux2Pipeline.from_pretrained(
            "diffusers/FLUX.2-dev-bnb-4bit",
            # text_encoder=None,
            torch_dtype=torch.bfloat16 
        ).to("cuda")

        logger.info("모델 컴파일 중...")
        try:
            self.pipeline.transformer = torch.compile(
                self.pipeline.transformer, 
                mode="reduce-overhead", 
                fullgraph=True
            )
            logger.info("컴파일 성공.")
        except Exception as e:
            logger.warning(f"모델 컴파일 실패 (속도 저하 가능성): {e}")

        logger.info("FLUX.2 파이프라인 로드 완료.")
        return self.pipeline

    def run_img2img(self, image: Image.Image, prompt: str) -> Image.Image:
        """
        FLUX.2를 사용하여 Image-to-Image 변환을 수행합니다.
        """
        pipe = self.load_pipeline()

        full_inference_start = time.time()

        # 1. 프롬프트 인코딩 (원격 API 사용)
        # prompt_embeds = self._remote_text_encoder(prompt)
        # if prompt_embeds is None:
        #     raise ValueError("Remote Text Encoder failed to generate embeddings.")

        diffusion_start_time = time.time()

        # with profile(
        #     activities=[ProfilerActivity.CPU, ProfilerActivity.CUDA],
        #     record_shapes=True, profile_memory=True, with_stack=False
        # ) as prof:
        #     with record_function("FLUX_INFERENCE"):
        #         result_image = pipe(
        #             prompt=prompt,
        #             image=image, 
        #             guidance_scale=4.0, 
        #             num_inference_steps=20, 
        #         ).images[0]

        result_image = pipe(
                    prompt=prompt,
                    image=image, 
                    guidance_scale=4.0, 
                    num_inference_steps=20, 
                ).images[0]

        # 3. 프로파일링 결과 저장 (Chrome Trace Format)
        # current_time_after_inference = time.time()

        # logger.info("\n\n============ 📊 FLUX.2 GPU Profiling Results (Top 10) ============")
        
        # # 'cuda_time_total' 기준으로 정렬하여 가장 느린 CUDA 연산을 찾습니다.
        # logger.info(prof.key_averages(group_by_input_shape=False).table(
        #     sort_by="cuda_time_total", row_limit=10
        # ))
        # logger.info("==================================================================")

        diffusion_duration = time.time() - diffusion_start_time 
        full_inference_duration = time.time() - full_inference_start

        logger.info(f"⏱️ Diffusion Model (UNet+VAE) Time: {diffusion_duration:.2f}s")
        logger.info(f"⏱️ Full Img2Img Time (Encoder+Diffusion): {full_inference_duration:.2f}s")

        return result_image

# ----------------------------------------------------
# [기존 코드 변경 후 호환성 유지를 위한 래퍼 함수]
# ----------------------------------------------------

def load_pipeline():
    """외부 호환성을 위해 Flux2ImageGenerator 인스턴스를 로드합니다."""
    return Flux2ImageGenerator().load_pipeline()

def run_inpainting(image: Image.Image, mask_image: Image.Image, prompt: str) -> Image.Image:
    """
    외부 호환성 유지를 위해 함수명은 run_inpainting을 사용하지만, 
    내부적으로는 FLUX.2 Img2Img 변환을 수행합니다. (mask_image는 무시)
    """
    generator = Flux2ImageGenerator()
    return generator.run_img2img(image, prompt)