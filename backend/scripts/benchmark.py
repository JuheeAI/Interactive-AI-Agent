import os, sys

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import base64
import time
import requests
import pandas as pd
from celery import Celery
from tqdm import tqdm 

IMAGE_SOURCES = {
    "test_cat.jpg": "http://images.cocodataset.org/val2017/000000039769.jpg", 
    "test_room.jpg": "http://images.cocodataset.org/val2017/000000000632.jpg",
    "test_person.jpg": "http://images.cocodataset.org/train2017/000000296882.jpg",
    "test_food.jpg": "http://images.cocodataset.org/train2017/000000126120.jpg",
    "test_city.jpg": "http://images.cocodataset.org/train2017/000000536595.jpg" 
}

TEST_CASES = [
    # 고양이 
    {"image": "test_cat.jpg", "prompt": "change the cat to a dog", "type": "SD3_Easy"},
    {"image": "test_cat.jpg", "prompt": "make the cat look like a cyborg tiger with neon lights", "type": "SD3_Hard"},
    {"image": "test_cat.jpg", "prompt": "what is the animal doing?", "type": "VQA"},

    # 방 
    {"image": "test_room.jpg", "prompt": "add a red sofa in the center", "type": "SD3_Easy"},
    {"image": "test_room.jpg", "prompt": "transform the room into a futuristic spaceship interior", "type": "SD3_Hard"},
    {"image": "test_room.jpg", "prompt": "what is the color of the wall?", "type": "VQA"},

    # 사람
    {"image": "test_person.jpg", "prompt": "change the person to a robot", "type": "SD3_Easy"},
    {"image": "test_person.jpg", "prompt": "make the person look like a marble statue", "type": "SD3_Hard"},
    {"image": "test_person.jpg", "prompt": "is the person smiling?", "type": "VQA"},

    # 음식 
    {"image": "test_food.jpg", "prompt": "change the pizza to a cake", "type": "SD3_Easy"},
    {"image": "test_food.jpg", "prompt": "make the food look like it is burning with blue fire", "type": "SD3_Hard"},
    {"image": "test_food.jpg", "prompt": "what kind of food is this?", "type": "VQA"},

    # 도시
    {"image": "test_city.jpg", "prompt": "add a flying car in the sky", "type": "SD3_Easy"},
    {"image": "test_city.jpg", "prompt": "make it look like a post-apocalyptic ruin", "type": "SD3_Hard"},
    {"image": "test_city.jpg", "prompt": "is it day or night?", "type": "VQA"},
]

BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
IMAGE_DIR = os.path.join(BASE_DIR, "data", "test_images")    
RESULT_DIR = os.path.join(BASE_DIR, "data", "benchmark_results")

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
app = Celery('tasks', broker=broker_url, backend=backend_url)

def prepare_images():
    """이미지 폴더를 확인하고 없으면 공식 이미지를 다운로드합니다."""
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
        print(f"'{IMAGE_DIR}' 폴더 생성됨.")

    # 봇 차단용
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print("테스트 이미지 확인 및 다운로드 중...")
    for filename, url in IMAGE_SOURCES.items():
        save_path = os.path.join(IMAGE_DIR, filename)
        
        if not os.path.exists(save_path):
            print(f"   Downloading {filename}...", end=" ", flush=True)
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    with open(save_path, "wb") as f:
                        f.write(response.content)
                    print("완료")
                else:
                    print(f"실패 (Status: {response.status_code})")
            except Exception as e:
                print(f"에러: {e}")
        else:
            pass 

def run_benchmark():
    prepare_images()
    
    results_summary = []
    print(f"\n벤치마크 시작. 총 {len(TEST_CASES)}개의 태스크를 실행합니다.\n")

    if not os.path.exists(RESULT_DIR):
        os.makedirs(RESULT_DIR)

    for i, case in enumerate(tqdm(TEST_CASES, desc="Running Benchmark")):
        filename = case["image"]
        prompt = case["prompt"]
        task_type = case["type"]
        img_path = os.path.join(IMAGE_DIR, filename)

        if not os.path.exists(img_path):
            print(f"\n파일 없음: {filename} (Skip)")
            continue

        # 이미지 로딩
        with open(img_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Celery 태스크 전송
        task = app.send_task('app.tasks.run_agent_task', args=[prompt, image_data])

        try:
            result = task.get(timeout=300)

            if result["status"] == "success":
                metrics = result.get("metrics", {})
                
                summary = {
                    "ID": i + 1,
                    "Type": task_type,
                    "Image": filename,
                    "Prompt": prompt[:30] + "..." if len(prompt) > 30 else prompt, 
                    "Time(s)": round(metrics.get("timer/total_latency", 0), 2),
                    "Mem(MB)": round(metrics.get("system/peak_gpu_memory_mb", 0), 0),
                    "CLIP": "-",
                    "Self-Check": "-",
                    "VQA/Feedback": ""
                }

                if result["type"] == "image":
                    summary["CLIP"] = round(metrics.get("evaluation/clip_score", 0), 2)
                    
                    pass_fail = metrics.get("evaluation/self_success_rate")
                    summary["Self-Check"] = "PASS" if pass_fail == 1 else "FAIL"
                    
                    feedback = metrics.get("evaluation/self_feedback_ans", "")
                    summary["VQA/Feedback"] = feedback[:25] + "..." if len(feedback) > 25 else feedback
                    
                    save_name = f"{i+1}_{task_type}_{filename}"
                    save_path = os.path.join(RESULT_DIR, save_name)
                    with open(save_path, "wb") as f:
                        f.write(base64.b64decode(result["data"]))
                        
                elif result["type"] == "text":
                    summary["CLIP"] = "-"
                    summary["VQA/Feedback"] = result["data"]
                
                results_summary.append(summary)

            else:
                print(f"\n실패 (ID {i+1}): {result.get('error')}")

        except Exception as e:
            print(f"\n에러 발생 (ID {i+1}): {e}")

    if results_summary:
        df = pd.DataFrame(results_summary)
        
        cols = ["ID", "Type", "Prompt", "Time(s)", "CLIP", "Self-Check", "VQA/Feedback", "Mem(MB)"]
        df = df[cols]

        print("\n\n📊 [Benchmark Report]")
        print("=" * 120)
        print(df.to_string(index=False))
        print("=" * 120)

        df.to_csv(os.path.join(RESULT_DIR, "final_report.csv"), index=False)
        print(f"\n리포트 저장 완료: {RESULT_DIR}/final_report.csv")
    else:
        print("\n완료된 태스크가 없습니다.")

if __name__ == "__main__":
    run_benchmark()