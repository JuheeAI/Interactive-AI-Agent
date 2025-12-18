## Experiment & Troubleshooting Report

Interactive Multi-modal AI Agent의 성능 최적화 과정과 리소스 제한 환경에서의 장애 해결 기록을 담고 있습니다.

## 1. 지능형 큐 라우팅을 통한 Latency 최적화

!!
작업들이 어떻게 처리되는지 보여주는 Gantt Chart 형태의 시각화가 가장 좋음. WandB Wall Time 차트 캡처(Heavy 작업드르 사이로 Light 작업들이 비집고 들어가 처리되는 타임라인 이미지를 삽임하기)
Latency 비교 막대 그래프(X축(Task 유형), Y축(응답 시간), 비교(단일 큐(FIFO) vs 멀티 큐(Preemption)))
추가 수치(VQA 응답 속도 85% 개선(17s -> 2s) 문구 차트 상단에 강조.)
!!

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

!!
단순 나열보다 비교 테이블과 Rader Chart를 활용해 FLUX.2의 우위를 시각화하기 
평가 항목(Latency, CLIP Score, VRAM Efficiency, Deployment Complexity)
비교(SD3 Pipeline vs FLUX.2 Single)

지표 (Metrics),SD3 Pipeline (3-Stage),FLUX.2 (Single),개선율 (Gain)
Average Latency,24.5s,18.2s,25% ↓
CLIP Score,28.4,31.2,10% ↑
VRAM Consumption,모델 교체 시 스와핑 발생,34GB 고정,리소스 안정성 확보
!!

**[실험 내용]**
특정 영역 수정을 위해 `Detection + SAM2 + SD3`를 조합한 파이프라인과 단일 `FLUX.2 (Img2Img)` 모델의 성능을 비교 분석함. 

**[비교 데이터]**
(지표 추가하기)

**[인사이트]**
멀티 스테이지 파이프라인은 정교한 제어가 가능하지만 모델 간 데이터 전송(Tensor Transfer) 및 로딩 오버헤드가 발생함. FLUX.2와 같은 최신 파운데이션 모델의 Semantic 이해도가 우수해 단일 모델로의 전환이 서빙 효율과 품질 면에서 유리함을 입증함. 

## 3. 리소스 제한 환경에서의 Fault Tolerance 전략

!!
OOM을 어떻게 극복했는지 보여주는 리소스 모니터링 그래프 필요
VRAM 점유율 시계열 그래프 (X축(시간, 요청 횟수), Y축(VRAM 사용량(GB)), 포인트(OOM 직전 VRAM이 정점에 도달했다가 torch.cuda.empty_cache()와 gc.collect() 호출 시 급격히 떨어지는 톱니바퀴형 패턴 강조))
스트레스 테스트 성공률 파이차트(105회 테스트 중 성공 100% (재시도 성공 포함)를 시각화해 Hugh Availability 증명)
!!

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

## 4. 자가 피드백 루프 (Quality Assurance)

!!
생성된 이미지와 VQA 검수 결과를 나란히 보여주는 샘플 갤러리 추가하기
Before/After 이미지 비교 (이미지 A는 사용자 프롬프트에 충실한 생성물 -> VQA 검수 PASS, 이미지 B는 프롬프트 누락 발생 -> VQA 검수 FAIL -> 자동 재지시 로직 작동)
품질 지표(self_success_rate) 추이 그래프 (실험을 반복할수록 피드백 루프를 통해 품질이 안정화되는 과정을 보여주는 선 그래프 삽입하기.)
