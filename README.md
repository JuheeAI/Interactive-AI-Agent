## **Interactive Multimodal AI Agent API Server**

### ✨ Project Status

- Backend API: ✅ (Implemented)
- Frontend Demo: ✅ (Implemented)
- Core Agent Logic (LLM Orchestrator): ✅ (Implemented)
- Tool Integration:
    - VQA (LLaVA): ✅ (Implemented)
    - Object Detection (Owl-ViT v2): ✅ (Implemented)
    - Segmentation (SAM): ✅ (Implemented)
    - Editing (Stable Diffusion 3): ✅ (Upgraded to SOTA Model)
- Asynchronous System (Celery/WebSocket): ✅ (Implemented)

### **🎬 Demo**


## **1️⃣ Project Overview**

단순한 질의응답을 넘어, 사용자와의 자연어 대화를 통해 이미지에 대한 Q&A, 객체 분할, 이미지 편집 등 복합적인 작업을 자율적으로 수행하는 멀티모달 AI 에이전트 API 및 데모 서비스입니다.

이 에이전트는 LLM을 핵심 두뇌로 사용하여 사용자의 복합적인 의도를 파악하고, 각 작업에 최적화된 여러 AI 모델(LLaVA, SAM, Stable Diffusion 등)들을 Tool처럼 유기적으로 호출하여 문제를 해결합니다.

특히, 에이전트의 핵심 '눈' 역할을 하는 VQA(Visual Question Answering) 모듈에는 최신 대형 멀티모달 모델(LMM)인 **LLaVA-OneVision-1.5**를 채택했습니다. 이를 통해 이미지에 대한 깊이 있는 이해와 복잡한 문맥적 질문에도 높은 정확도의 답변을 제공합니다.

개발된 에이전트는 **FastAPI**와 **Celery**를 이용한 **비동기 태스크 큐** 아키텍처를 기반으로 구축되었으며, 모든 서비스는 **Docker Compose**를 통해 컨테이너 환경에서 안정적으로 운영됩니다.

## 2️⃣ Key Features

- **🤖 대화형 작업 오케스트레이션:** "이 사진 속 강아지를 고양이로 바꿔줘"와 같은 복잡한 자연어 명령을 단계별로 분석하고 실행합니다.
- **⚡️ 실시간 비동기 처리 및 피드백:** **WebSocket**을 통해 AI의 작업 진행 상황("객체 찾는 중...", "이미지 편집 중...")을 사용자에게 실시간으로 피드백하여 우수한 사용자 경험을 제공합니다.
- **🖼️ 고성능 Visual Question Answering:** 이미지에 대한 사용자의 질문에 정확하게 답변합니다.
- **🎯 정교한 객체 분할 (Segmentation):** 대화로 지목된 객체를 이미지 내에서 정확하게 분리합니다.
- **🎨 컨텍스트 기반 이미지 편집 (Editing):** 분리된 객체를 사용자의 지시에 따라 자연스럽게 수정하거나 제거합니다.
- **🐳 통합 컨테이너 환경:** **Docker Compose**를 통해 프론트엔드, 백엔드 API, AI 워커, 메시지 큐를 한 번에 관리하고 실행합니다.

## 3️⃣ System Architecture

본 서비스는 사용자의 요청을 즉시 처리하고 무거운 AI 작업은 백그라운드에서 수행하는 **비동기/분산 태스크 아키텍처**를 채택했습니다. 이를 통해 사용자는 긴 작업 시간 동안 기다릴 필요 없이 실시간으로 진행 상황을 확인할 수 있습니다.

```
+----------+    +---------------------------------------------------------------------------------+
|   User   |    |                      FastAPI Server (AI Agent Orchestrator)                     |
+----------+    | +-----------------------------------------------------------------------------+ |
     ^          | | 1. (POST /agent/invoke) - 작업 요청  -> Job Queue (Celery + Redis)            | |
     |          | |    - 즉시 'job_id' 반환                                                       | |
     |          | |                                                                             | |
     |(WebSocket| | 2. (WebSocket /ws/{job_id}) - 실시간 진행 상황 구독                              | |
     | Real-time| |    - "Finding cat...", "Masking...", "Editing image..."                     | |
     | Update)  | |                                                                             | |
     |          | | 3. (Worker) - Celery 워커가 Job을 가져와 AI 모델 추론 수행                         | |
     |          | +-----------------------------------------------------------------------------+ |
     +----------+---------------------------------------------------------------------------------+
```

## 4️⃣ Teck Stack

| 구분 | 기술 | 설명 |
| --- | --- | --- |
| Frontend | React, Vite | 현대적이고 빠른 사용자 인터페이스 구축 |
|  | Tailwind CSS | Utility-First 방식의 신속한 UI 스타일링 |
|  | Axios, Socket.IO-Client | 백앤드 API와의 안정적인 비동기 통신 |
| Backend | FastAPI, Uvicorn | 비동기 처리를 통한 고성능 API 서버 구축 |
|  | Celery | 무거운 AI 작업을 처리하는 분산 태스크 큐 |
|  | Redis | Celery의 메시지 브로커 및 결과 백엔드 |
| ML/AI | PyTorch, Hugging Face | 딥러닝 모델의 백엔드 및 추론 프레임워크 |
|  | LLM (GPT/Gemini) | 에이전트의 계획 및 추론을 위한 핵심 두뇌 |
|  | LLaVA / VQA Models | 이미지-텍스트 이해 및 질의응답 도구 |
|  | Segment Anything Model | 정교한 객체 분할(마스킹) 도구 |
|  | Diffusers (Stable Diffusion) | 이미지 생성 및 인페인팅 편집 도구 |
| Infra & DevOps | GCP Compute Engine | GPU 인턴스를 활용한 서비스 호스팅 |
|  | Docker, Docker Compose | 애플리케이션 컨테이너화 및 배포 환경 표준화 |
| MLOps | Weights & Biases | AI 에이전트의 모든 추론 과정, 성능 지표, 결과물을 실시간으로 추적하고 시각화하는 실험 관리 도구 |

## 5️⃣ Installation & Execution

본 프로젝트는 docker-compose를 통해 모든 서비스(프론트엔드, 백엔드, AI 워커 등)를 한 번에 실행하도록 구성되어 있습니다.

**Prerequisites**

- Docker & Docker Compose
- Git
- `.env` 파일 설정 (API 키 등)

**Execution Steps**

1. **GitHub 리포지토리 복제 및 이동**Bash
    
    `git clone https://github.com/your-username/Interactive-AI-Agent.git
    cd Interactive-AI-Agent`
    
2. **환경 변수 설정**
    - `.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 필요한 API 키(OpenAI, Google AI 등)를 입력합니다.
3. **Docker Compose를 이용한 전체 서비스 실행**Bash
    
    `docker-compose up --build -d`
    
4. **데모 접속**
    - 이제 브라우저에서 `http://localhost:3000` (설정한 프론트엔드 포트)으로 접속하여 데모를 확인할 수 있습니다.

## 6️⃣ API Usage

본 에이전트는 비동기 API를 제공하여 긴 작업 시간에 대한 즉각적인 응답을 보장합니다.

**1. 작업 요청(Invoke Task)**

- **Endpoint**: `/agent/invoke`
- **Method**: `POST`
- **Action**: 사용자가 이미지와 프롬프트를 보내면, 서버는 작업을 대기열에 등록하고 `job_id` 를 즉시 반환합니다.
- **Response**
    
    ```json
    { "status": "processing", "job_id": "some-unique-job-id" }
    ```
    

**2. 실시간 상태 및 결과 수신(Real-time Updates)**

- **Endpoint**: `/ws/{job_id}`
- **Protocol**: `WebSocket`
- **Action**: 프론트엔드는 받은 `job_id` 로 WebSocket에 연결하여 AI 에이전트의 현재 작업 상태와 최종 결과물을 실시간으로 스트리밍 받습니다.
- **Message Stream (Example)**
    
    ```json
    {"status": "progress", "message": "Analyzing prompt..."}
    {"status": "progress", "message": "Identifying the cat using VQA..."}
    {"status": "progress", "message": "Creating a precise mask using SAM..."}
    {"status": "success", "output_image_url": "http://.../result.jpg"}
    ```
    

## 7️⃣ Core Components & Technical Philosophy

본 프로젝트는 단일 모델이 아닌, LLM 기반 에이전트가 여러 전문가 모델들을 도구처럼 사용하는 시스템입니다.

- **두뇌 (Brain)**: `GPT-4o`가 사용자의 복합적인 요청을 이해하고, 이를 해결하기 위한 단계적인 계획을 수립합니다.
- **도구상자 (Toolbox)**:
    - **고성능 VQA (LLaVA-OneVision-1.5-4B)**: 에이전트의 핵심 '눈' 역할을 합니다. 최신 대형 멀티모달 모델을 사용하여 이미지에 대한 복합적인 질문을 이해하고 답변합니다.
    - **제로샷 객체 탐지 (Owl-ViT v2)**: "왼쪽에 있는 고양이"와 같은 텍스트 지시만으로 이미지 내 객체의 정확한 위치(Bounding Box)를 찾아내는 '포인터' 역할을 합니다.
    - **정교한 세그멘테이션 (SAM)**: 탐지된 객체의 경계선을 픽셀 단위로 정교하게 분리하는 '손' 역할을 합니다.
    - **고품질 이미지 편집 (Stable Diffusion 3 Medium)**: 분리된 마스크 영역을 사용자의 프롬프트에 따라 창의적으로 수정하는 SOTA '붓' 역할을 합니다.

## 8️⃣ Future Improvements

- **성능 최적화**
    
    모델 가중치를 Quantization(양자화)하거나 ONNX/TensorRT로 변환하여 추론 속도 개선
    
- **서비스 확장성**
    
    Kubernetes를 도입하여 트래픽에 따른 자동 확장(Auto-scaling) 기능 구현
    
- **모델 파인튜닝(Fine-tuning)**
    
    특정 도메인(의료, 법률 등)의 데이터셋을 활용하여 기본 모델을 파인튜닝함으로써 특정 분야의 질문에 대한 정확도 향상
    
- **CI/CD 파이프라인 구축**
    
    GitHub Actions를 활용하여 코드 변경 시 자동으로 테스트 및 Docker 이미지 빌드/배포가 이루어지도록 파이프라인 구축
    
- **더 많은 도구 추가(OCR 등)**

## 9️⃣ Acknowledgement

본 프로젝트의 **대화형 에이전트 아키텍처**는 `LLaVA-Interactive` 연구에서, **고품질 이미지 생성**에 대한 접근 방식은 `Diffusion Transformers with Representation Autoencoders (RAE)` 연구에서 큰 영감을 얻었습니다. 훌륭한 연구를 공개해주신 모든 연구자분들께 감사를 표합니다.

### **무엇을 새로 알아봐야 하나요?**

- **RAE 논문을 다시 읽어볼 필요는 없습니다.** 지금은 Lama Cleaner나 Stable Diffusion XL Inpainting 같은 **실용적인 고품질 Inpainting 오픈소스**에 집중하는 것이 좋습니다. RAE는 이들의 "학문적 친척" 정도로만 이해하시면 충분합니다.
- 대신, **Stable Diffusion XL Inpainting** 이나 **PowerPaint** 같은 모델의 사용법, 특히 `diffusers` 라이브러리에서 어떻게 사용하는지를 알아보는 것이 훨씬 더 실용적입니다.

## 🔟 Agent Perfomance & Evaluation

본 에이전트의 성능은 자체적으로 구축할 평가 파이프라인을 통해 정성적 분석과 정량적 지표 모두를 사용하여 종합적으로 측정 및 관리될 예정입니다.

**10.1. 실시간 실험 관리 (Weights & Biases)**
에이전트가 처리하는 모든 요청은 Weights & Biases (W&B) 대시보드에 실시간으로 로깅됩니다. 이를 통해 각 Tool의 개별 성능 뿐만 아니라, LLM이 생성한 실행 계획과 입/출력 결과물까지 모든 과정을 시각적으로 추적하고 정성적으로 분석할 수 있는 환경이 구축되었습니다.

**(W&B 대시보드 스크린샷 또는 링크 삽입)**

**10.2. 향후 측정될 정량적 성능 지표 (Future Quantitative Metrics)**
향후 아래와 같은 표준 평가 케이스 및 지표를 사용하여 에이전트의 성능을 정량적으로 측정하고, 지속적으로 개선해 나갈 계획입니다.

| 분류 | 지표 | 설명 |
| --- | --- | --- |
| **종단간 평가** | 작업 성공률 (Task Success Rate) | 주어진 자연어 명령을 의도대로 완벽하게 수행한 비율을 측정합니다. (가장 중요한 핵심 지표) |
| **이미지-텍스트 연관성** | CLIP Score | (이미지 편집 Task) "강아지를 웃게 만들어줘"라는 프롬프트와 최종 결과물 이미지가 의미적으로 얼마나 일치하는지를 측정합니다. |
| **텍스트 품질 평가** | ROUGE-L | (VQA Task) 에이전트가 생성한 텍스트 답변이 정답(Ground-Truth)과 내용적으로 얼마나 유사한지를 측정합니다. |
| **계획 수립 정확도** | Plan Accuracy | (LLM Brain) 주어진 Task에 대해 LLM이 사전에 정의된 올바른 Tool 순서로 계획을 수립한 비율을 측정합니다. |

**10.3. 실패 케이스 분석 계획**
평가 과정에서 발생하는 실패 케이스에 대해서는 W&B 로그와 각 정량 지표 점수를 통해 근본 원인을 분석할 예정입니다. 예를 들어, Task는 실패했지만 Plan Accuracy가 높았다면 LLM의 계획이 아닌 하위 Tool(SAM, Stable Diffusion 등)의 성능 문제임을 파악하고 개선 방향을 설정할 수 있습니다.
