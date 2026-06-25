# MiniX 기반 멀티클러스터 로드맵

이 문서는 최종적으로 구성하려는 `TWINX / EDGEX / DATAX / RESOURCE POOL / TOWER CLUSTER` 구조를 정리하고, 이를 바로 실환경에 적용하기 전에 **MiniX에서 먼저 검증할 실험 계획**을 기록한다.

---

## 1. 전체 방향

최종 목표는 여러 목적별 Kubernetes 클러스터를 하나의 운영 체계로 묶는 것이다.

핵심 구성 요소:

- **Kubernetes**: 각 클러스터의 실행 기반
- **ArgoCD**: GitOps 기반 배포/동기화
- **Karmada**: 멀티클러스터 배포, 정책, 장애조치
- **Kueue**: GPU/CPU Job, Spark, AI/Batch 워크로드 큐잉
- **External Secrets Operator(ESO)**: 외부 Secret 저장소 연동
- **Observability Stack**: Prometheus, Grafana, Loki 등

큰 그림:

```text
GitHub MiniX Repository
        |
        v
+-------------------------------+
| TOWER CLUSTER                 |
| - ArgoCD                      |
| - Karmada Control Plane       |
| - ESO                         |
| - Observability               |
| - Kueue Manager, optional     |
+-------------------------------+
        |
        | 멀티클러스터 제어 / GitOps / 정책 배포
        v
+-------------+   +-------------+   +-------------+
| TWINX       |   | EDGEX       |   | DATAX       |
| GPU Render  |   | Edge/GPU    |   | Data Lake   |
+-------------+   +-------------+   +-------------+
        |
        v
+-------------------------------+
| RESOURCE POOL                 |
| - GPU Pool                    |
| - CPU Pool                    |
| - Batch / AI / Spark Jobs     |
+-------------------------------+
```

---

## 2. 클러스터별 역할

## 2.1 TOWER CLUSTER

관리 전용 클러스터다.

여기에는 실제 서비스 워크로드보다는 운영/제어 컴포넌트를 배치한다.

예상 구성:

- ArgoCD
- Karmada Control Plane
- External Secrets Operator
- cert-manager
- ingress controller
- monitoring stack
- logging stack
- Kueue manager 또는 queue policy 관리 컴포넌트

역할:

- GitHub repo를 source of truth로 사용
- 여러 클러스터에 공통 정책 배포
- Karmada를 통한 멀티클러스터 전파
- Secret, 인증서, 모니터링, 배포 상태 통합 관리

운영 형태:

```text
초기: single-node k3s 또는 kubeadm cluster
향후: 3-node HA management cluster
```

주의점:

- Tower Cluster가 죽어도 기존 member cluster의 Pod는 바로 죽지 않는다.
- 하지만 새 배포, 정책 변경, 장애조치, GitOps 동기화는 영향을 받는다.
- 장기 운영 시 Tower Cluster는 HA 구성이 필요하다.

---

## 2.2 TWINX CLUSTER

GPU 렌더링 전용 클러스터다.

예상 역할:

- Blender/렌더링 Job
- GPU batch rendering
- media processing
- 렌더링 queue 처리

예상 구성:

- NVIDIA GPU Operator
- Kueue worker 또는 local Kueue
- GPU ResourceFlavor
- rendering job templates
- object storage client

주요 검증 항목:

- GPU Job 큐잉
- GPU quota 관리
- Job 우선순위
- 대량 렌더링 작업 분산
- 결과물 저장소 연동

---

## 2.3 EDGEX CLUSTER

Edge 전용 클러스터다.

예상 역할:

- Edge GPU 컴퓨팅
- 저지연 inference
- 현장 장비/센서 연동
- 작은 규모의 AI workload 실행

예상 구성:

- lightweight Kubernetes, 예: k3s
- GPU 또는 NPU runtime
- edge-local storage
- node label / taint 기반 workload 분리

주요 검증 항목:

- 네트워크가 불안정한 환경에서의 배포 방식
- Karmada Pull 모드 필요 여부
- Edge 전용 workload scheduling
- Tower Cluster와의 연결 단절 시 동작

---

## 2.4 DATAX CLUSTER

대용량 데이터 저장/처리 전용 클러스터다.

예상 역할:

- SSD/HDD 기반 대용량 데이터 저장
- Data Lake / Lakehouse
- Object Storage
- Spark/Trino/Iceberg/Nessie 기반 데이터 처리

예상 구성:

- Rook Ceph 또는 별도 Storage System
- HDD pool / SSD pool 분리
- Trino
- Spark Operator
- Iceberg
- Nessie
- PostgreSQL metadata store

주요 검증 항목:

- StorageClass 분리
- SSD/HDD tiering
- ObjectBucketClaim
- Spark job과 object storage 연동
- Trino/Iceberg query path

---

## 2.5 RESOURCE POOL

GPU/CPU 자원을 논리적으로 묶어 사용하는 영역이다.

이것은 반드시 별도 클러스터일 필요는 없다.
처음에는 여러 클러스터의 node label, taint, Kueue ResourceFlavor로 표현할 수 있다.

예상 구분:

```text
GPU Pool
  - rendering-gpu
  - inference-gpu
  - training-gpu

CPU Pool
  - batch-cpu
  - service-cpu
  - data-processing-cpu
```

Kueue 관점:

- ResourceFlavor: 자원 종류 표현
- ClusterQueue: 전체 quota와 정책
- LocalQueue: namespace/team별 큐
- WorkloadPriorityClass: 우선순위

Karmada 관점:

- cluster label로 자원 특성 표현
- PropagationPolicy로 대상 클러스터 선택
- OverridePolicy로 클러스터별 설정 차이 반영

---

## 3. MiniX에서 먼저 검증할 이유

최종 구조는 규모가 크기 때문에 바로 적용하면 문제 원인 파악이 어렵다.
따라서 MiniX에서 축소판을 먼저 만든다.

MiniX에서 검증할 것:

- ArgoCD app-of-apps 구조 개선
- Karmada host/member 구조 이해
- Karmada PropagationPolicy / OverridePolicy 실습
- Kueue 단일 클러스터 큐잉 실습
- Kueue + SparkApplication 실습
- ArgoCD가 Karmada API Server로 배포하는 구조 검증
- 관리 클러스터와 워커 클러스터 역할 분리

MiniX 실험 구조:

```text
MiniX 또는 kind/k3d lab

mgmt 또는 karmada-host
  - ArgoCD
  - Karmada Control Plane
  - Kueue manager, optional

member1
  - 일반 workload 실행
  - Kueue worker/local queue

member2
  - 일반 workload 실행
  - Kueue worker/local queue
```

---

## 4. 단계별 진행 계획

## Phase 0. 문서화 및 현재 구조 정리

목표:

- MiniX repo에 멀티클러스터 구상 정리
- Karmada 실험 디렉터리 구성
- 실험 기록 방식 통일

상태:

- `karmada/` 디렉터리 생성 완료
- Karmada 기본 개념/실험 계획 문서화 완료
- 이 문서에서 전체 X-Cluster 로드맵 정리

---

## Phase 1. Karmada 기초 실험

목표:

- kind 기반 `karmada-host`, `member1`, `member2` 생성
- Karmada init
- member cluster join
- demo-nginx 전파

검증 항목:

- Karmada API Server에 리소스 적용
- member cluster에 Deployment/Service 생성 여부
- PropagationPolicy 동작
- ClusterPropagationPolicy 동작

관련 디렉터리:

```text
karmada/manifests/demo-nginx/
karmada/experiments/
```

---

## Phase 2. ArgoCD + Karmada 연동

목표:

ArgoCD가 직접 member cluster에 배포하는 것이 아니라, Karmada API Server에 배포하도록 구성한다.

기존 흐름:

```text
ArgoCD -> Kubernetes Cluster
```

목표 흐름:

```text
ArgoCD -> Karmada API Server -> member clusters
```

검증 항목:

- ArgoCD cluster secret으로 Karmada API Server 등록
- ArgoCD Application destination을 Karmada로 설정
- Karmada policy와 resource template을 GitOps로 관리

---

## Phase 3. Kueue 단일 클러스터 실험

목표:

Kueue를 먼저 단일 클러스터에서 이해한다.

검증 항목:

- ResourceFlavor
- ClusterQueue
- LocalQueue
- Kubernetes Job 큐잉
- quota 초과 시 Pending 동작
- priority/preemption 동작

예상 workload:

- sleep job
- CPU job
- GPU dummy job
- SparkApplication

---

## Phase 4. Karmada + Kueue 조합 실험

목표:

Karmada와 Kueue의 역할을 분리해서 사용한다.

권장 모델:

```text
ArgoCD
  -> Karmada API Server
    -> 특정 member cluster에 Job/Queue 리소스 전파
      -> 각 member cluster의 Kueue가 실행 허가
```

주의:

- Karmada와 Kueue MultiKueue를 동시에 클러스터 선택자로 사용하면 구조가 꼬일 수 있다.
- 처음에는 Karmada가 클러스터 배치를 담당하고, Kueue는 각 클러스터 내부의 Job admission/quota를 담당하도록 분리한다.

---

## Phase 5. MiniX 실제 앱 일부 적용

처음부터 전체 MiniX 앱을 옮기지 않는다.

우선순위:

1. nginx 같은 stateless demo
2. 간단한 Job
3. SparkApplication
4. GPU dummy workload
5. 실제 ingestion/batch job
6. Trino/Spark/Data workload 일부

Rook Ceph, Confluent, Milvus 같은 무거운 stateful 시스템은 마지막에 검토한다.

---

## 5. 최종 목표 아키텍처

장기 목표:

```text
TOWER CLUSTER
  - GitOps / Control Plane / Secrets / Observability
  - ArgoCD
  - Karmada
  - ESO
  - Monitoring

TWINX CLUSTER
  - GPU Rendering
  - Kueue GPU queues

EDGEX CLUSTER
  - Edge GPU/AI compute
  - Pull mode candidate

DATAX CLUSTER
  - SSD/HDD PB-scale storage
  - Lakehouse / Spark / Trino / Iceberg

RESOURCE POOL
  - GPU/CPU 자원을 논리적으로 분류
  - Kueue ResourceFlavor/ClusterQueue로 quota 관리
  - Karmada cluster label로 배치 정책 관리
```

---

## 6. 우선 결정해야 할 것

아직 결정이 필요한 부분:

- Tower Cluster를 `k3s`로 갈지 `kubeadm`으로 갈지
- Karmada member 연결은 Push부터 할지 Pull까지 볼지
- Kueue MultiKueue를 사용할지, Karmada 중심으로 갈지
- Secret 관리는 ESO + Vault로 갈지, ESO + GitHub/Cloud Secret으로 갈지
- GPU Pool을 별도 클러스터로 둘지, 각 클러스터 node label로 표현할지
- DATAX storage를 Rook Ceph 중심으로 갈지 별도 NAS/Object Storage와 연동할지

현재 추천:

```text
1. MiniX/kind에서 Karmada 단독 검증
2. Kueue 단일 클러스터 검증
3. ArgoCD로 GitOps화
4. Karmada + Kueue 조합 검증
5. Tower Cluster 설계 확정
6. TWINX / EDGEX / DATAX 확장
```

---

## 7. 기록 규칙

실험 결과는 아래 위치에 계속 기록한다.

```text
karmada/experiments/   # Karmada 관련 실험
karmada/notes/         # Karmada 개념 정리
docs/architecture/     # 전체 아키텍처/로드맵
```

각 실험 문서는 다음 형식을 따른다.

```markdown
# 실험명

## 목적
## 환경
## 실행 명령
## 결과
## 문제/에러
## 해결 방법
## 다음 액션
```
