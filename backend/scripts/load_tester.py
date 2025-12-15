import os
import base64
import time
from celery import Celery
import multiprocessing
from tqdm import tqdm
from datetime import datetime
import numpy as np
import csv 

BASE_DIR = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

# 테스트할 이미지와 프롬프트. 쉬운 SD3 작업 1가지를 정하겠습니다.
TEST_PROMPT = "change the cat to a dog"
IMAGE_PATH = os.path.join(BASE_DIR, "data", "test_images", "test_cat.jpg")

# 부하 레벨 설정
NUM_CONCURRENT_USERS = 20    # 동시에 Celery에 요청을 보내는 프로세스 수 (사용자 수)
TASKS_PER_USER = 5           # 각 사용자가 보낼 요청 수 (총 20 * 5 = 100회 요청)

# Celery 설정
broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend_url = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
app = Celery('app.tasks', broker=broker_url, backend=backend_url)

# QPS 계산을 위해 전역 변수로 성공/실패 카운트를 관리
SUCCESS_COUNT = 0
FAILURE_COUNT = 0
TOTAL_TASKS = NUM_CONCURRENT_USERS * TASKS_PER_USER

def append_to_csv(latency, status):
    global SUCCESS_COUNT, FAILURE_COUNT
    csv_path = os.path.join(BASE_DIR, "data", "stress_test_log.csv")
    
    # 카운터 업데이트
    if 'SUCCESS' in status:
        SUCCESS_COUNT += 1
    else:
        FAILURE_COUNT += 1
        
    with open(csv_path, 'a', newline='') as f: # 'a' (append) 모드로 변경
        writer = csv.writer(f)
        writer.writerow([f"{latency:.4f}", status])

def send_task(image_data, prompt): # task_id, queue_manager 인자 제거
    start_time = time.time()
    
    try:
        task = app.send_task('app.tasks.run_agent_task', args=[prompt, image_data])
        # timeout은 30초로 유지
        result = task.get(timeout=30) 
        
        end_time = time.time()
        latency = end_time - start_time
        
        if result and result.get("status") == "success":
            append_to_csv(latency, 'SUCCESS') # 파일에 기록
        else:
            # 실패 시 상세 에러 메시지 기록
            error_msg = result.get('error', 'UNKNOWN FAILURE') if result else 'NO RESPONSE'
            append_to_csv(latency, f'FAILURE: {error_msg[:50]}')

    except Exception as e:
        append_to_csv(time.time() - start_time, f'ERROR: {str(e)[:50]}')

def worker_task_loop(image_data, prompt, tasks_per_user): 
    """
    각 멀티프로세스(사용자)가 반복적으로 Celery 작업을 요청하는 함수
    """
    for j in range(tasks_per_user):
        send_task(image_data, prompt) 

def run_load_test():
    global SUCCESS_COUNT, FAILURE_COUNT
    # 이미지 데이터 로드
    if not os.path.exists(IMAGE_PATH):
        print(f"이미지 파일 없음: {IMAGE_PATH}. 먼저 benchmark.py를 돌려 파일을 생성하세요.")
        return

    with open(IMAGE_PATH, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
        
    csv_path = os.path.join(BASE_DIR, "data", "stress_test_log.csv")

    # 파일 초기화 (실시간 기록 준비)
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Latency', 'Status']) 
        
    print(f"\n⚡ 부하 테스트 시작 (Total Tasks: {TOTAL_TASKS})")
    print(f"   - 동시 사용자: {NUM_CONCURRENT_USERS}명")
    print(f"   - 각 사용자당 작업: {TASKS_PER_USER}회\n")

    processes = []
    
    test_start_time = time.time()

    # 동시 사용자 수만큼 프로세스 생성 및 작업 요청
    for i in range(NUM_CONCURRENT_USERS):
        p = multiprocessing.Process(
            target=worker_task_loop,
            args=(image_data, TEST_PROMPT, TASKS_PER_USER) # log_queue 인자 제거
        )
        processes.append(p)
        p.start()

        time.sleep(0.1)

    # 모든 프로세스가 끝날 때까지 대기
    for p in tqdm(processes, desc="Waiting for Processes"):
        p.join()

    test_end_time = time.time()
    total_time = test_end_time - test_start_time
    
    # 전역 카운터를 사용
    success_count = SUCCESS_COUNT
    error_count = FAILURE_COUNT
    
    # Latency 계산을 위해 파일에서 성공 요청만 읽어옴 (정확도를 위해)
    latencies = []
    try:
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            next(reader) # 헤더 건너뛰기
            for row in reader:
                if row[1] == 'SUCCESS':
                    latencies.append(float(row[0]))
    except FileNotFoundError:
        pass # 파일이 없으면 0으로 처리

    avg_latency = np.mean(latencies) if latencies else 0
    qps = success_count / total_time if total_time > 0 else 0
    
    print("\n\n[Stress Test Final Report]")
    print("=" * 40)
    print(f"총 소요 시간: {total_time:.2f} s")
    print(f"총 요청 수: {TOTAL_TASKS} 건")
    print(f"성공 요청 수: {success_count} 건")
    print(f"실패/에러 수: {error_count} 건")
    print("-" * 40)
    print(f"평균 처리 속도 (Latency): {avg_latency:.2f} s")
    print(f"시스템 처리량 (QPS): {qps:.2f} QPS")
    print("=" * 40)
    

if __name__ == "__main__":
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        pass
    
    run_load_test()