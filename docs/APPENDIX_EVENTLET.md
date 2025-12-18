# Appendix: Attempted eventlet Integration & Retrospective
**Analysis of Resource Isolation in Compute-Bound AI Workloads**


## 1. Background & Hypothesis
기존 `solo` 워커 풀의 작업 처리 효율을 높이고 메시지 브로커(Redis)와의 통신 지연을 최소화하기 위해 비동기 네트워킹 라이브러리인 **eventlet** 도입을 시도했습니다.

* **Hypothesis**
  * 비동기 이벤트 루프를 사용하면 워커가 Task를 수신하고 결과를 반환하는 I/O 대기 시간을 줄여 전체적인 Throughput이 향상될 것이다.

---

## 2. Encountered Issues (The Failure)

실험 결과 AI 모델 추론과 같은 고부하 연산 환경에서는 비동기 루프가 오히려 독이 되는 두 가지 문제를 발견했습니다.

### 2.1 VRAM Anomalies & Over-allocation
* **현상**
  * 정상적인 상황에서 약 34GB를 점유해야 할 VRAM이 40GB 이상으로 급증하며 OOM(Out of Memory)을 유발함.
* **원인**
  * ㄷ비동기 루프 내에서 전역 변수로 선언된 모델 객체의 상태 관리가 경합(Race Condition)을 일으킴. 싱글 프로세스 내에서 여러 그린렛(Greenlet)이 모델 컨텍스트에 접근하려다 모델이 중복 로드되는 현상이 발생함.

### 2.2 Blocking of the Event Loop (Heartbeat Loss)
* **현상**
  * 워커가 작업을 수행하는 동안 메시지 브로커(Redis)와의 연결이 끊어지는 'Lost Connection' 현상 빈발.
* **원인**
  * `eventlet`은 협력적 멀티태스킹(Cooperative Multitasking) 방식입니다. 하지만 GPU 추론(Compute-Bound)은 CPU를 100% 점유하는 작업이므로 이벤트 루프에 제어권을 넘겨주지 못해 브로커와의 하트비트(Heartbeat)를 체크하지 못하는 블로킹이 발생했습니다.

## 3. Technical Comparison

실험 결과를 바탕으로 비동기 풀과 프로세스 격리 풀의 특성을 비교 분석했습니다.

| 특징 | Gevent/Eventlet (비동기) | Multiprocessing (Solo/Prefork) |
| :--- | :---: | :---: |
| **주요 메커니즘** | 단일 프로세스 내 그린렛 | OS 레벨 프로세스 분리 |
| **리소스 공유** | 메모리 및 컨텍스트 공유 | 완전 격리 (Isolated) |
| **적합한 작업** | **I/O-Bound** (API 호출, DB 조회) | **Compute-Bound** (GPU 연산, 이미지 생성) |
| **결과** | **FAIL** (OOM 및 연결 끊김) | **PASS** (안정적인 리소스 관리) |


## 4. Engineering Insight & Lessons Learned

실패 경험을 통해 다음과 같은 기술적 통찰을 얻었습니다.

1.  **도구 선정의 중요성**
    * 모든 비동기가 성능 향상을 보장하지 않음을 확인했습니다. 대규모 행렬 연산이 주가 되는 AI 서빙에는 Process-based Isolation이 리소스 안정성 면에서 필수적입니다.
2.  **리소스 격리(Resource Isolation)**
    * 모델 상태 관리의 무결성을 보장하기 위해서는 메모리 공간을 완전히 분리하는 `spawn` 방식의 워커 전략이 가장 안전함을 실험적으로 체득했습니다.
3.  **현재 아키텍처의 당위성**
    * 최종적으로 Heavy/Light Queue Separation과 Solo Pool을 채택한 근거를 확보했으며 이를 통해 105회 연속 요청에도 죽지 않는 견고한 시스템을 구축할 수 있었습니다.
