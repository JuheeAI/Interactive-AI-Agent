import time
import csv
import psutil
import torch
import matplotlib.pyplot as plt
import pynvml
import argparse
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "data", "profiling_logs")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)
    print(f"폴더 생성 완료: {LOG_DIR}")

def get_gpu_stats():
    """NVIDIA GPU 상태 조회 (메모리, 사용률, 전력, 온도)"""
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # mW -> W
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        
        used_mem = mem_info.used / 1024**2
        gpu_util = util.gpu
        return used_mem, gpu_util, power, temp
    except Exception:
        return 0, 0, 0, 0

def plot_results(csv_path, img_path):
    """CSV 데이터를 읽어서 3단 그래프로 저장"""
    times, gpu_mems, gpu_utils, cpu_utils, ram_utils, gpu_powers, gpu_temps = [], [], [], [], [], [], []
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                times.append(float(row['Time(s)']))
                gpu_mems.append(float(row['GPU_Mem(MB)']))
                gpu_utils.append(float(row['GPU_Util(%)']))
                cpu_utils.append(float(row['CPU_Util(%)']))
                ram_utils.append(float(row['RAM_Util(%)']))
                gpu_powers.append(float(row['GPU_Power(W)']))
                gpu_temps.append(float(row['GPU_Temp(C)']))
    except Exception as e:
        print(f"데이터 읽기 오류: {e}")
        return

    if not times:
        print("데이터가 부족하여 그래프를 그릴 수 없습니다.")
        return

    # 그래프 스타일 설정
    plt.figure(figsize=(12, 12))
    
    # 1. GPU 메모리 & RAM 사용률
    plt.subplot(3, 1, 1)
    plt.plot(times, gpu_mems, label='VRAM Used (MB)', color='blue', linewidth=2)
    plt.title("AI Agent System Resource Profiling", fontsize=15)
    plt.ylabel("VRAM (MB)")
    plt.grid(True, linestyle='--')
    plt.legend(loc='upper left')
    
    # 2. GPU & CPU 사용률 (%)
    plt.subplot(3, 1, 2)
    plt.plot(times, gpu_utils, label='GPU Util (%)', color='green')
    plt.plot(times, cpu_utils, label='CPU Util (%)', color='orange', alpha=0.7)
    plt.ylabel("Utilization (%)")
    plt.ylim(0, 105)
    plt.grid(True, linestyle='--')
    plt.legend(loc='upper left')
    
    # 3. GPU 전력(W) & 온도(C)
    ax3 = plt.subplot(3, 1, 3)
    ax3.plot(times, gpu_powers, label='GPU Power (W)', color='red')
    ax3.set_ylabel("Power (Watts)")
    ax3.set_xlabel("Time (seconds)")
    
    ax3_temp = ax3.twinx() # 온도를 위한 Y축 추가
    ax3_temp.plot(times, gpu_temps, label='GPU Temp (C)', color='purple', linestyle=':')
    ax3_temp.set_ylabel("Temperature (Celsius)")
    
    ax3.grid(True, linestyle='--')
    ax3.legend(loc='upper left')
    ax3_temp.legend(loc='upper right')
    
    plt.tight_layout()
    plt.savefig(img_path)
    print(f"분석 리포트 그래프 저장 완료: {img_path}")

def run_monitor(duration=60):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(LOG_DIR, f"profile_{timestamp}.csv")
    img_path = os.path.join(LOG_DIR, f"profile_{timestamp}.png")
    
    print(f"프로파일링 시작... (최대 {duration}초)")
    print(f"로그 저장 경로: {csv_path}")
    
    start_time = time.time()
    
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Time(s)', 'GPU_Mem(MB)', 'GPU_Util(%)', 'CPU_Util(%)', 'RAM_Util(%)', 'GPU_Power(W)', 'GPU_Temp(C)'])
        
        try:
            while True:
                current_time = time.time() - start_time
                if current_time > duration:
                    break
                
                gpu_mem, gpu_util, gpu_power, gpu_temp = get_gpu_stats()
                cpu_util = psutil.cpu_percent()
                ram_util = psutil.virtual_memory().percent
                
                writer.writerow([
                    f"{current_time:.2f}", 
                    f"{gpu_mem:.2f}", 
                    f"{gpu_util}", 
                    f"{cpu_util}", 
                    f"{ram_util}", 
                    f"{gpu_power:.2f}", 
                    f"{gpu_temp}"
                ])
                f.flush()
                
                time.sleep(0.5) 
                
        except KeyboardInterrupt:
            print("\n프로파일링 중단 (사용자 요청)")
            
    plot_results(csv_path, img_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=300, help="Monitoring duration in seconds")
    args = parser.parse_args()
        
    run_monitor(args.duration)