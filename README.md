## **Interactive Multimodal AI Agent API Server**
### Hugh-Performancce AI Serving with Intelligent Task Scheduling & Self-Correction

VRAM 48GB 환경에서 고사양 생성 모델(FLUX.2)의 서빙 최적화를 달성하고, 시스템 안정성(Fault Tolerance)과 품질 보증(Self-Feedback)을 자동화한 자율형 에이전트 시스템입니다.

## 핵심 성과

1. **지능형 작업 스케줄링 및 응답성 개선**
    * **Inteligent Task Routing**
        요청 프롬프트와 작업 부하를 실시간으로 분석하여 Heavy(생성)/Light(VQA) 큐로 자동 분산.
    * **성능 향상**
        큐 분리를 통해 고부하 작업 중에도 경량 작업의 Latency를 약 85% 단축 (17s -> 2s)

2. **가용성 및 리소스 최적화 (Fault Tolerance)**
    * **OOM Self-Healing**
        GPU 메모리 초과 시 Exponential Backoff 재시도 및 VRAM 강제 세정(Torch Cache Flush) 로직을 통해 시스템 중단 방지.
    * **안정성 입증**
        100회 이상의 연속 고부하 스트레스 테스트에서 성공률 100% 달성

3. **모델 파이프라인 최적화 (Model Benchmarking)**
    * **Pipeline vs Single Model**
        기존 Detection + SAM2 + SD3 Inpainting 3단계 파이프라인 대비 단일 FLUX.2 모델의 효율성 검증.
    * **수치적 우위**
        단일 모델 전환으로 Latency 25% 개선 및 CLIP Score 10% 상승 (품질과 속도의 트레이드오프 해결).


## 시스템 아키텍처 (Architecture)

* **API & Core**: FastAPI, GPT-4o (Task Planning & Reasoning)

* **Asynchronous Task**: Celery, Redis(Priority-based Queueing)

* **Vision-Language Models**: FLUX.2(Image Synthesis), VQA Model(Reviewer)

* **Infra & DevOps**: Docker Compose, NVIDIA Container Toolkit(GPU Acceleration), WandB(Monitoring)

## 실험 및 트러블슈팅 (Detailed Reports)

단순한 기능 구현을 넘어서 엔지니어링 관점에서 마주한 병목 지점과 해결 과정을 데이터로 기록했습니다. 

[상세 실험 보고서(EXPERIMENT_REPORT.md)](./docs/EXPERIMENT_REPORT.md)
* **Peak Memory Management**
    FLUX.2 점유 환경에서 동시 요청 처리 시 발생하는 OOM 해결 전략.
* **Preemption Analysis**
    비동기 큐 시스템에서 짧은 작업이 긴 작업을 추월하여 처리되는 과정에 대한 WandB 시각화 분석.
* **Benchmark: Pipeline Redesign**
    3개 모델 연동 방식에서 강력한 단일 파운데이션 모델로 전환한 기술적 근거와 데이터 비교.