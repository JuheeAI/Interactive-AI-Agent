## Experiment & Troubleshooting Report

Interactive Multi-modal AI Agent의 성능 최적화 과정과 리소스 제한 환경에서의 장애 해결 기록을 담고 있습니다.

## 1. 지능형 큐 라우팅을 통한 Latency 최적화

**[배경 맟 가설]**
고부하 작업(FLUX.2 이미지 생성)이 큐를 점유할 경우, 가벼운 작업(VQA)이 불필요하게 대기하며 사용자 경험을 저해함. 

**[실험 설계]**
* **Heavy Queue**
  단일 동시성(-c 1) 설정을 통한 VRAM 보호 및 생성 작업 처리.
* **Light Queue**
  높은 동시성(-c 4) 및 gevent 풀을 통한 빠른 분석 작업 처리.
* **테스트 케이스**
  Heavy 10건, Light 5건 혼합 요청

**[결과 분석]**
* **Before**
  선입선출(FIFO) 방식 적용 시 가벼운 작업이 최대 20초 대기.
* **After**
  비동기 추월 처리(Preeption)로 Light Task Latency 평균 2초 기록 (85% 개선).
* **WandB 증거**
  Wall Time 차트상에서 긴 작업(Heavy) 사이사이에 짧은 작업(Light)이 병렬적으로 완수됨을 확인.

## 2. 모델 아키텍처 트레이드오프: Pipeline vs Single Model

**[실험 내용]**
특정 영역 수정을 위해 `Detection + SAM2 + SD3`를 조합한 파이프라인과 단일 `FLUX.2 (Img2Img)` 모델의 성능을 비교 분석함. 

**[비교 데이터]**
(지표 추가하기)

**[인사이트]**
멀티 스테이지 파이프라인은 정교한 제어가 가능하지만 모델 간 데이터 전송(Tensor Transfer) 및 로딩 오버헤드가 발생함. FLUX.2와 같은 최신 파운데이션 모델의 Semantic 이해도가 우수해 단일 모델로의 전환이 서빙 효율과 품질 면에서 유리함을 입증함. 

## 3. 리소스 제한 환경에서의 Fault Tolerance 전략

**[문제 상황]**
FLUX.2 실행 시 Peak VRAM이 34GB에 도달해 연속 요청 시 이전 작업의 캐시가 정리되지 않아 `RuntimeError: CUDA out of memory` 발생.

**[해결 전략: Self-healing 로직]**
1. **Exponential Backoff**
  OOM 발생 시 20초의 유예 시간을 두고 재시도해서 리소스 회복 시간 확보.
2. **Pre-emptive Memory Flush**
  태스크 진입 전 `torch.cuda.empty_cache()` 및 `gc.collect()` 강제 수행. 
3. **Resource Isolation**
  Docker Deploy 설정을 통한 물리적 GPU 예약 및 워커 동시성 제어.

**[검증]**
* 100회 이상의 연속 스트레스 테스트 결과, 발생한 모든 일시적 메모리 에러를 자가 재시도로 극복해 최종 성공률 100% 달성. 

## 4. 자가 피드백(Self-Reflection) 루프의 신뢰성
**[로직 개요]**
에이전트가 생성한 결과물을 다시 VQA(Vision Question Answering) 모델에 입력해 프롬프트 준수 여부를 검수(`Self-Check`). 

**[성과]**
* 검수 결과가 `FAIL`일 경우 지표(`self_success_rate`)에 즉시 반영하여 모니터링 가시성 확보. 
* 사람이 직접 확인하기 어려운 대량의 실험 데이터 품질을 자동 수치화함. 

