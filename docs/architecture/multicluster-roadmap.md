# MiniX Lab에서 ScaleX-POD 멀티클러스터까지의 검증 로드맵

이 문서는 **ScaleX-POD 멀티클러스터**를 만들기 전에, 작은 실험 환경인 **MiniX**에서 ArgoCD, Karmada, Kueue, GitOps 흐름을 먼저 검증하는 계획을 정리한다.

> 용어 정리: 여기서 `ScaleX-POD`는 Kubernetes의 Pod 리소스가 아니라, `Tower / TwinX / EdgeX / DataX / Resource Pool`이 합쳐진 **하나의 멀티클러스터 운영 단위**를 뜻한다.

---

## 1. 핵심 용어

| 용어 | 의미 |
| --- | --- |
| **MiniX** | ScaleX-POD를 만들기 전에 실험하는 작은 단일 클러스터/Lab 환경 |
| **ScaleX-POD** | 실제 목표 멀티클러스터 단위. Tower, TwinX, EdgeX, DataX, Resource Pool이 함께 구성된다. |
| **Tower Cluster** | ScaleX-POD의 관리/제어 클러스터. ArgoCD, Karmada, ESO, Observability 등을 담당한다. |
| **TwinX Cluster** | GPU 렌더링/미디어 처리/렌더링 Job을 담당하는 클러스터 |
| **EdgeX Cluster** | Edge GPU/AI inference/현장 장비 연동을 담당하는 클러스터 |
| **DataX Cluster** | Data Lake/Lakehouse, Object Storage, Spark, Trino, Iceberg 등을 담당하는 데이터 클러스터 |
| **Resource Pool** | GPU/CPU 자원을 논리적으로 묶은 풀. 필요하면 별도 클러스터가 될 수 있고, 초기에는 label/taint/Kueue ResourceFlavor로 표현할 수 있다. |

정리하면 다음과 같다.

```text
MiniX
  = 사전 검증용 작은 Lab

ScaleX-POD
  = 실제 멀티클러스터
  = Tower + TwinX + EdgeX + DataX + Resource Pool
```

---

## 2. 전체 방향

최종 목표는 목적별 Kubernetes 클러스터를 하나의 **ScaleX-POD 멀티클러스터**로 묶는 것이다.

핵심 구성 요소:

- **Kubernetes**: 각 클러스터의 실행 기반
- **ArgoCD**: GitOps 기반 배포/동기화
- **Karmada**: 멀티클러스터 배포, 정책, 장애조치
- **Kueue**: GPU/CPU Job, Spark, AI/Batch 워크로드 큐잉
- **External Secrets Operator(ESO)**: 외부 Secret 저장소 연동
- **Observability Stack**: Prometheus, Grafana, Loki 등

큰 그림:

```text
GitHub MiniX / ScaleX Infra Repository
        |
        v
+---------------------------------------------------+
| ScaleX-POD                                        |
|                                                   |
|  +---------------------------------------------+  |
|  | Tower Cluster                               |  |
|  | - ArgoCD                                    |  |
|  | - Karmada Control Plane                     |  |
|  | - ESO                                       |  |
|  | - Observability                             |  |
|  | - Kueue Manager, optional                   |  |
|  +---------------------------------------------+  |
|          |                                        |
|          | 멀티클러스터 제어 / GitOps / 정책 배포 |
|          v                                        |
|  +-------------+   +-------------+   +---------+  |
|  | TwinX       |   | EdgeX       |   | DataX   |  |
|  | GPU Render  |   | Edge/GPU    |   | Data    |  |
|  +-------------+   +-------------+   +---------+  |
|          |                                        |
|          v                                        |
|  +---------------------------------------------+  |
|  | Resource Pool                               |  |
|  | - GPU Pool                                  |  |
|  | - CPU Pool                                  |  |
|  | - Batch / AI / Spark Jobs                   |  |
|  +---------------------------------------------+  |
+---------------------------------------------------+
```

---

## 3. ScaleX-POD 구성요소별 역할

### 3.1 Tower Cluster

ScaleX-POD의 관리 전용 클러스터다.

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
- ScaleX-POD 내부 여러 클러스터에 공통 정책 배포
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

### 3.2 TwinX Cluster

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

### 3.3 EdgeX Cluster

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

### 3.4 DataX Cluster

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

### 3.5 Resource Pool

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

## 4. MiniX에서 먼저 검증할 이유

ScaleX-POD는 실제 멀티클러스터 구조이기 때문에 바로 적용하면 문제 원인 파악이 어렵다.
따라서 먼저 작은 실험 환경인 MiniX에서 GitOps, Karmada, Kueue 흐름을 축소 검증한다.

MiniX에서 검증할 것:

- ArgoCD app-of-apps 구조 개선
- Karmada host/member 구조 이해
- Karmada PropagationPolicy / OverridePolicy 실습
- Kueue 단일 클러스터 큐잉 실습
- Kueue + SparkApplication 실습
- ArgoCD가 Karmada API Server로 배포하는 구조 검증
- 관리 클러스터와 워커 클러스터 역할 분리

MiniX/Karmada 실험 구조:

```text
MiniX Lab

실제 MiniX
  - 작은 단일 클러스터
  - ArgoCD/GitOps/Kueue 등을 먼저 검증하는 장소

Karmada 동작 실험용 kind/k3d lab
  - tower: Karmada control plane / Tower 축소판
  - twinx: TwinX 역할의 member cluster
  - edgex: EdgeX 역할의 member cluster
  - datax: DataX 역할의 member cluster
```

이 kind/k3d lab은 실제 ScaleX-POD가 아니라, ScaleX-POD에 들어갈 Karmada 동작을 미리 확인하는 축소 실험이다.

---

## 5. 단계별 진행 계획

### Phase 0. 문서화 및 현재 구조 정리

목표:

- `MiniX`와 `ScaleX-POD` 용어 분리
- ScaleX-POD가 멀티클러스터 단위임을 명확히 정리
- Karmada 실험 디렉터리 구성
- 실험 기록 방식 통일

상태:

- `karmada/` 디렉터리 생성 완료
- Karmada 기본 개념/실험 계획 문서화 완료
- 이 문서에서 MiniX Lab → ScaleX-POD 멀티클러스터 로드맵 정리

---

### Phase 1. Karmada 기초 실험

목표:

- kind 기반 `tower`, `twinx`, `edgex`, `datax` 생성
- Karmada init
- twinx/edgex/datax member cluster join
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

첫 실행 계획서:

- [`karmada/experiments/2026-06-25-00-kind-lab-plan.md`](../../karmada/experiments/2026-06-25-00-kind-lab-plan.md)

이 문서에는 실행 순서, 명령어, 기대 결과, 실제 결과 기록 위치, 문제/에러 기록 형식, ScaleX-POD에 주는 의미를 함께 기록한다.

---

### Phase 2. ArgoCD + Karmada 연동

목표:

ArgoCD가 직접 member cluster에 배포하는 것이 아니라, Karmada API Server에 배포하도록 구성한다.

MiniX의 단순 흐름:

```text
ArgoCD -> MiniX 단일 클러스터
```

ScaleX-POD 목표 흐름:

```text
ArgoCD on Tower
  -> Karmada API Server on Tower
    -> TwinX / EdgeX / DataX / Resource Pool
```

역할 분리:

```text
ArgoCD  = Git 변경 감지, diff/sync/rollback, app-of-apps 등 GitOps 담당
Karmada = ScaleX-POD 안에서 cluster placement, replica 분산, override, failover 담당
```

따라서 ArgoCD는 Karmada API Server에 리소스와 정책을 sync하고,
Karmada는 그 리소스를 TwinX / EdgeX / DataX / Resource Pool로 전파한다.

검증 항목:

- ArgoCD cluster secret으로 Karmada API Server 등록
- ArgoCD Application destination을 Karmada로 설정
- Karmada policy와 resource template을 GitOps로 관리

---

### Phase 3. Kueue 단일 클러스터 실험

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

### Phase 4. Karmada + Kueue 조합 실험

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

### Phase 5. MiniX 실제 앱 일부 적용

처음부터 전체 MiniX 앱을 Karmada로 옮기지 않는다.

우선순위:

1. nginx 같은 stateless demo
2. 간단한 Job
3. SparkApplication
4. GPU dummy workload
5. 실제 ingestion/batch job
6. Trino/Spark/Data workload 일부

Rook Ceph, Confluent, Milvus 같은 무거운 stateful 시스템은 마지막에 검토한다.

---

### Phase 6. ScaleX-POD 설계 확정

MiniX에서 충분히 검증한 뒤, 실제 ScaleX-POD 멀티클러스터 구성을 확정한다.

결정할 것:

- Tower Cluster를 `k3s`로 갈지 `kubeadm`으로 갈지
- Karmada member 연결은 Push부터 할지 Pull까지 볼지
- Kueue MultiKueue를 사용할지, Karmada 중심으로 갈지
- Secret 관리는 ESO + Vault로 갈지, ESO + GitHub/Cloud Secret으로 갈지
- GPU Pool을 별도 클러스터로 둘지, 각 클러스터 node label로 표현할지
- DataX storage를 Rook Ceph 중심으로 갈지 별도 NAS/Object Storage와 연동할지

---

## 6. 최종 목표 아키텍처

장기 목표는 하나의 ScaleX-POD 안에 다음 멀티클러스터 구성을 갖추는 것이다.

```text
ScaleX-POD

Tower Cluster
  - GitOps / Control Plane / Secrets / Observability
  - ArgoCD
  - Karmada
  - ESO
  - Monitoring

TwinX Cluster
  - GPU Rendering
  - Kueue GPU queues

EdgeX Cluster
  - Edge GPU/AI compute
  - Pull mode candidate

DataX Cluster
  - SSD/HDD PB-scale storage
  - Lakehouse / Spark / Trino / Iceberg

Resource Pool
  - GPU/CPU 자원을 논리적으로 분류
  - Kueue ResourceFlavor/ClusterQueue로 quota 관리
  - Karmada cluster label로 배치 정책 관리
```

현재 추천 순서:

```text
1. MiniX/kind에서 Karmada 단독 검증
2. Kueue 단일 클러스터 검증
3. ArgoCD로 GitOps화
4. Karmada + Kueue 조합 검증
5. ScaleX-POD의 Tower 설계 확정
6. TwinX / EdgeX / DataX / Resource Pool을 ScaleX-POD member로 확장
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
