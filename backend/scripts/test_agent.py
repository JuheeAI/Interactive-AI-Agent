import requests
import time
import os
import base64
import json

# --- 설정 ---
API_URL = "http://localhost:8000/agent/invoke"
IMAGE_PATH = "test_cat.jpg"  # 테스트할 이미지
OUTPUT_DIR = "test_results"  # 결과 이미지 저장할 폴더

# --- 🚀 핵심: 모든 도구를 다 쓰게 만드는 시나리오 ---
prompts = [
    # 1. [VQA] 단순 시각 지능 테스트 (몸풀기)
    {
        "text": "Describe this image in detail.",
        "expected_tool": "run_vqa",
        "desc": "🔍 1단계: 이미지 설명 (VQA 점검)"
    },

    # 2. [OD + SAM + Inpainting] 전체 파이프라인 풀가동 (GPU 부하 🔥)
    {
        "text": "Change the cat to a robotic dog.",
        "expected_tool": "run_inpainting",
        "desc": "🛠️ 2단계: 고양이를 로봇 개로 변환 (OD -> SAM -> SD3)"
    },

    # 3. [OD + SAM + Inpainting] 연속 부하 테스트 (다른 객체로 변환)
    {
        "text": "Change the cat to a tiger.",
        "expected_tool": "run_inpainting",
        "desc": "🔥 3단계: 고양이를 호랑이로 변환 (연속 생성 테스트)"
    },
    
    # 4. [VQA] 변환된 이미지가 아니라 원본에 대한 속성 질문
    {
        "text": "What is the background color?",
        "expected_tool": "run_vqa",
        "desc": "🎨 4단계: 배경 색상 확인 (VQA 재점검)"
    }
]

# --- 초기화 ---
if not os.path.exists(IMAGE_PATH):
    print(f"❌ Error: {IMAGE_PATH} 파일이 없습니다.")
    exit()

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"🚀 AI Agent Full-Stack Test 시작 ({len(prompts)} steps)\n")
print(f"📂 결과 이미지는 '{OUTPUT_DIR}' 폴더에 저장됩니다.\n")

# --- 테스트 루프 ---
for i, item in enumerate(prompts):
    prompt = item["text"]
    desc = item["desc"]
    
    print(f"▶️ [Test {i+1}/{len(prompts)}] {desc}")
    print(f"   🗣️  프롬프트: \"{prompt}\"")
    
    try:
        with open(IMAGE_PATH, "rb") as img_file:
            files = {"image": img_file}
            data = {"prompt": prompt}
            
            start_time = time.time()
            # 요청 전송
            response = requests.post(API_URL, files=files, data=data)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('status')
                res_type = result.get('type')
                
                print(f"   ⏱️  소요 시간: {duration:.2f}초")
                
                if status == 'success':
                    # 1. 텍스트 결과인 경우 (VQA)
                    if res_type == 'text':
                        print(f"   📝 답변: {result.get('data')}")
                    
                    # 2. 이미지 결과인 경우 (Inpainting)
                    elif res_type == 'image':
                        save_name = f"{OUTPUT_DIR}/step_{i+1}_result.jpg"
                        img_data = base64.b64decode(result.get('data'))
                        with open(save_name, "wb") as f:
                            f.write(img_data)
                        print(f"   🖼️  이미지 생성 완료! 저장됨 -> {save_name}")
                        
                else:
                    print(f"   ⚠️  에이전트 에러: {result.get('error')}")
            else:
                print(f"   ❌ 서버 에러: {response.status_code}")
                
    except Exception as e:
        print(f"   ❌ 연결 실패: {e}")

    print("-" * 60)
    # GPU 열기를 식히지 않고 바로 다음 요청을 보내서 그래프를 유지합니다.

print("\n🎉 모든 테스트 완료! W&B에서 그래프를 확인하세요.")