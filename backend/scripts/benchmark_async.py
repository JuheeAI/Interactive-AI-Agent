import os, sys, random
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

import base64, time, requests, pandas as pd
from celery import Celery
from tqdm import tqdm 

from benchmark import IMAGE_SOURCES, TEST_CASES, prepare_images, IMAGE_DIR, RESULT_DIR

broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
app = Celery('tasks', broker=broker_url, backend=backend_url)

def run_async_benchmark():
    prepare_images()

    # extended_cases = TEST_CASES * 7
    # random.shuffle(extended_cases) 

    extended_cases = TEST_CASES * 1
    random.shuffle(extended_cases)

    results_summary = []
    print(f"\n비동기 큐 벤치마크 시작. 총 {len(extended_cases)}개 태스크 실행.\n")

    if not os.path.exists(RESULT_DIR): os.makedirs(RESULT_DIR)

    for i, case in enumerate(tqdm(extended_cases, desc="Async Testing")):
        filename, prompt, task_type = case["image"], case["prompt"], case["type"]
        img_path = os.path.join(IMAGE_DIR, filename)

        with open(img_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # 2. 지능형 큐 라우팅 적용
        target_queue = "light_tasks"
        if "SD3" in task_type or any(k in prompt.lower() for k in ["draw", "transform", "make"]):
            target_queue = "heavy_tasks"

        # 3. apply_async를 사용하여 큐 지정 전송
        task = app.send_task(
            'app.tasks.run_agent_task', 
            args=[prompt, image_data],
            queue=target_queue
        )

        try:
            result = task.get(timeout=600) 

            if result["status"] == "success":
                metrics = result.get("metrics", {})
                summary = {
                    "ID": i + 1,
                    "Queue": target_queue, # 어느 큐로 갔는지 기록
                    "Type": task_type,
                    "Time(s)": round(metrics.get("timer/total_latency", 0), 2),
                    "CLIP": round(metrics.get("evaluation/clip_score", 0), 2) if "SD3" in task_type else "-",
                    "Self-Check": "PASS" if metrics.get("evaluation/self_success_rate") == 1 else "FAIL",
                    "Mem(MB)": round(metrics.get("system/peak_gpu_memory_mb", 0), 0)
                }
                results_summary.append(summary)
            else:
                print(f"\n실패 (ID {i+1}): {result.get('error')}")

        except Exception as e:
            print(f"\n에러 (ID {i+1}): {e}")

    if results_summary:
        df = pd.DataFrame(results_summary)
        df.to_csv(os.path.join(RESULT_DIR, "async_report.csv"), index=False)
        print(f"\n비동기 리포트 저장 완료: {RESULT_DIR}/async_report.csv")

if __name__ == "__main__":
    run_async_benchmark()