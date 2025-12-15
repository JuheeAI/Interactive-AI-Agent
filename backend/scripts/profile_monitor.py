import time
import csv
import psutil
import torch
import matplotlib.pyplot as plt
import pynvml
import argparse
import os
from datetime import datetime

LOG_DIR = "../data/profiling_logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def get_gpu_stats():
    """NVIDIA GPU 상태 조회"""
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        
        used_mem = mem_info.used / 1024**2
        gpu_util = util.gpu
        return used_mem, gpu_util
    except Exception:
        return 0, 0

def plot_results(csv_path, img_path):
    """CSV 데이터를 읽어서 그래프로 저장"""
    times, gpu_mems, gpu_utils, cpu_utils = [], [], [], []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            times.append(float(row['Time(s)']))
            gpu_mems.append(float(row['GPU_Mem(MB)']))
            gpu_utils.append(float(row['GPU_Util(%)']))
            cpu_utils.append(float(row['CPU_Util(%)']))

    if not times:
        print("데이터가 부족하여 그래프를 그릴 수 없습니다.")
        return

    plt.figure(figsize=(12, 6))
    
    # 1. GPU 메모리 그래프
    plt.subplot(2, 1, 1)
    plt.plot(times, gpu_mems, label='VRAM Used (MB)', color='blue')
    plt.title("System Resource Profiling")
    plt.ylabel("VRAM (MB)")
    plt.grid(True)
    plt.legend()
    
    # 2. GPU/CPU 사용률 그래프
    plt.subplot(2, 1, 2)
    plt.plot(times, gpu_utils, label='GPU Util (%)', color='green')
    plt.plot(times, cpu_utils, label='CPU Util (%)', color='orange', linestyle='--')
    plt.xlabel("Time (seconds)")
    plt.ylabel("Utilization (%)")
    plt.ylim(0, 105)
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(img_path)
    print(f"그래프 저장 완료: {img_path}")

def run_monitor(duration=60):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(LOG_DIR, f"profile_{timestamp}.csv")
    img_path = os.path.join(LOG_DIR, f"profile_{timestamp}.png")
    
    print(f" 프로파일링 시작... (최대 {duration}초)")
    print(f"로그 저장 경로: {csv_path}")
    
    start_time = time.time()
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Time(s)', 'GPU_Mem(MB)', 'GPU_Util(%)', 'CPU_Util(%)', 'RAM_Util(%)'])
        
        try:
            while True:
                current_time = time.time() - start_time
                if current_time > duration:
                    break
                
                # 데이터 수집
                gpu_mem, gpu_util = get_gpu_stats()
                cpu_util = psutil.cpu_percent()
                ram_util = psutil.virtual_memory().percent
                
                writer.writerow([f"{current_time:.2f}", gpu_mem, gpu_util, cpu_util, ram_util])
                f.flush() # 실시간 저장
                
                time.sleep(0.1) # 0.1초 간격 (정밀 측정)
                
        except KeyboardInterrupt:
            print("\n프로파일링 중단 (사용자 요청)")
            
    plot_results(csv_path, img_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=120, help="Monitoring duration in seconds")
    args = parser.parse_args()
        
    run_monitor(args.duration)