# Karmada 실험실

이 디렉터리는 **ScaleX-POD 멀티클러스터**를 만들기 전에, MiniX Lab에서 **Karmada 멀티클러스터 오케스트레이션**을 연습하고 실험 과정과 결과를 기록하기 위한 공간입니다.

> 목표: 작은 MiniX 실험 환경에서 Karmada를 먼저 이해한 뒤, 실제 ScaleX-POD 안의 Tower / TwinX / EdgeX / DataX / Resource Pool 구조로 확장할 수 있는 GitOps 흐름을 검증한다.

---

## 현재 상태

- 작성일: 2026-06-25
- 상태: 실험 08까지 완료, 수동 NoExecute taint eviction 검증 완료
- 실제 Karmada 설치: `kind-tower`에 설치 완료
- 우선 실험 방식: `kind` 기반 로컬 멀티클러스터 실습
- 최종 적용 대상: ScaleX-POD 멀티클러스터
- 특이사항: Docker/kind 설치, inotify limit, context 전환, Karmada CLI 설치, Namespace binding 상태 이슈, Work 조회 kubeconfig 차이, cluster taint/실제 장애에서 기존 workload eviction 미확인, Failover feature gate 실험, 수동 NoExecute eviction 성공 및 taint 제거 후 자동 재균형 없음, controller-manager anti-affinity rollout 이슈, scheduler-estimator 로그를 실험 문서에 기록

---

## 왜 바로 ScaleX-POD 또는 MiniX 실클러스터에 붙이지 않는가?

ScaleX-POD는 Tower / TwinX / EdgeX / DataX / Resource Pool이 합쳐진 실제 멀티클러스터 단위다.
또한 MiniX에도 ArgoCD, Rook Ceph, Confluent, Trino, Milvus, Ollama 등 무거운 컴포넌트가 많다.
처음부터 실제 클러스터를 Karmada 멤버로 붙이면 원인 파악이 어려워질 수 있으므로, 먼저 가벼운 `kind` 클러스터로 Karmada의 동작 원리를 확인한다.

권장 첫 실험 구조:

```text
tower  : Karmada control plane / Tower 축소판
twinx  : TwinX 역할의 member cluster
edgex  : EdgeX 역할의 member cluster
datax  : DataX 역할의 member cluster
```

---

## 관련 문서

- [MiniX Lab에서 ScaleX-POD 멀티클러스터까지의 검증 로드맵](../docs/architecture/multicluster-roadmap.md)
- [Karmada 실험 진행표](./experiments/README.md)

---

## 학습/실험 로드맵

### 1단계. Karmada 기본 개념 정리

확인할 것:

- Karmada control plane이 무엇인지
- host cluster와 member cluster의 차이
- Push 모드와 Pull 모드의 차이
- ResourceTemplate / PropagationPolicy / OverridePolicy 역할

관련 기록:

- [`notes/concepts.md`](./notes/concepts.md)

---

### 2단계. kind 기반 실습 클러스터 준비

목표:

- `tower`, `twinx`, `edgex`, `datax` 클러스터 생성
- 각 클러스터 kubeconfig/context 확인

예상 명령:

```bash
kind create cluster --name tower
kind create cluster --name twinx
kind create cluster --name edgex
kind create cluster --name datax

kubectl config get-contexts
```

관련 기록:

- [`experiments/2026-06-25-00-kind-lab-plan.md`](./experiments/2026-06-25-00-kind-lab-plan.md)
  - kind cluster 구성
  - 실행 명령
  - 기대 결과
  - 실제 결과 기록 위치
  - 문제/에러 기록 형식
  - ScaleX-POD에 주는 의미
- [`experiments/2026-06-25-01-cluster-affinity-twinx-only.md`](./experiments/2026-06-25-01-cluster-affinity-twinx-only.md)
  - `clusterAffinity.labelSelector`로 twinx-only workload 배치 검증
  - Namespace가 edgex/datax에도 생성되는 관찰 이슈 기록
- [`experiments/2026-06-25-02-namespace-auto-propagation.md`](./experiments/2026-06-25-02-namespace-auto-propagation.md)
  - Namespace 전파 정책 없이 namespaced workload만 전파할 때 namespace 자동 생성 범위 확인
- [`experiments/2026-06-25-03-weighted-replica-scheduling.md`](./experiments/2026-06-25-03-weighted-replica-scheduling.md)
  - `replicaScheduling`의 `Divided + Weighted`로 twinx/edgex/datax replica 가중 분산 검증
- [`experiments/2026-06-25-04-override-policy-env.md`](./experiments/2026-06-25-04-override-policy-env.md)
  - `OverridePolicy`의 `plaintext` overrider로 twinx/edgex/datax별 env 변경 검증
- [`experiments/2026-06-25-05-cluster-taint-failover.md`](./experiments/2026-06-25-05-cluster-taint-failover.md)
  - `Cluster` taint와 `clusterTolerations`로 새 workload 배치 회피/허용 검증
  - 수동 `NoExecute` taint만으로 기존 ResourceBinding 즉시 eviction은 확인되지 않음
- [`experiments/2026-06-25-06-actual-cluster-failover.md`](./experiments/2026-06-25-06-actual-cluster-failover.md)
  - `twinx-control-plane` 중지로 실제 member cluster 장애 감지/복구 확인
  - 현재 controller 옵션에서는 기존 workload 자동 failover가 확인되지 않음
- [`experiments/2026-06-26-07-failover-feature-gate.md`](./experiments/2026-06-26-07-failover-feature-gate.md)
  - `Failover=true`, `enable-no-execute-taint-eviction=true` 옵션 활성화 후 실제 장애 재실험
  - 실제 cluster offline 자동 taint가 `NoSchedule`이라 기존 workload 자동 eviction은 확인되지 않음
- [`experiments/2026-06-26-08-noexecute-eviction.md`](./experiments/2026-06-26-08-noexecute-eviction.md)
  - 수동 `NoExecute` taint와 controller-manager eviction 옵션으로 기존 workload 이동 검증
  - `twinx` workload가 `edgex/datax`로 이동했으며, taint 제거 후 자동 재균형은 확인되지 않음

---

### 3단계. Karmada CLI 설치 및 init

목표:

- `karmadactl` 또는 `kubectl-karmada` 설치
- `tower` 클러스터에 Karmada control plane 설치

예상 명령:

```bash
curl -s https://raw.githubusercontent.com/karmada-io/karmada/master/hack/install-cli.sh \
  | sudo bash -s kubectl-karmada

kubectl config use-context kind-tower
kubectl karmada init
```

설치 후 확인:

```bash
kubectl get pods -n karmada-system
kubectl get deployments -n karmada-system
kubectl get statefulsets -n karmada-system
```

---

### 4단계. member cluster 등록

목표:

- `twinx`, `edgex`, `datax`를 Karmada에 등록
- Push 모드부터 실습

예상 확인:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusters
```

---

### 5단계. demo-nginx 전파 실험

목표:

- Karmada API server에 일반 Kubernetes Deployment/Service를 생성
- PropagationPolicy로 `twinx`, `edgex`, `datax`에 배포
- replica 분산이 어떻게 되는지 확인

예제 매니페스트 위치:

- [`manifests/demo-nginx/`](./manifests/demo-nginx/)

---

### 6단계. ArgoCD와 Karmada 연결

목표:

현재 MiniX의 단순 ArgoCD 흐름:

```text
ArgoCD -> MiniX 단일 클러스터에 직접 배포
```

ScaleX-POD에서 목표로 하는 흐름:

```text
ArgoCD on Tower -> Karmada API server on Tower
                 -> Karmada가 TwinX / EdgeX / DataX / Resource Pool로 전파
```

MiniX/kind 실험에서는 위 구조를 아래처럼 축소해서 검증한다.

```text
ArgoCD 또는 kubectl -> Karmada API server
                    -> twinx / edgex / datax로 전파
```

검증할 것:

- ArgoCD에 Karmada API server를 cluster로 등록할 수 있는지
- ArgoCD Application의 destination을 Karmada API server로 지정했을 때 정상 sync되는지
- Karmada 정책 리소스와 일반 Kubernetes 리소스를 GitOps로 관리할 수 있는지

---

## 실험 기록 방식

각 실험은 `experiments/` 아래에 날짜별 Markdown으로 기록한다.
단순히 성공/실패만 쓰지 않고, 아래를 반드시 남긴다.

- 무엇을 확인하려는 실험인지
- 어떤 명령을 실행했는지
- 성공하면 어떤 결과가 나와야 하는지
- 실제 출력은 어땠는지
- 실패했다면 어디서 막혔고 어떻게 해결했는지
- ScaleX-POD 설계에 어떤 의미가 있는지

권장 형식:

```markdown
# 실험명

## 목적

## 환경

## 실행 명령

## 기대 결과

## 실제 결과

## 성공/실패 판단

## 문제/에러

## 해결 방법

## ScaleX-POD에 주는 의미

## 다음 액션
```

---

## 디렉터리 구조

```text
karmada/
  README.md                         # 전체 계획과 현재 상태
  notes/
    concepts.md                     # 개념 정리
  experiments/
    README.md                                           # 실험 진행표
    2026-06-25-00-kind-lab-plan.md                      # kind/Karmada Lab 구성
    2026-06-25-01-cluster-affinity-twinx-only.md        # twinx-only 배치
    2026-06-25-02-namespace-auto-propagation.md         # namespace 자동 생성 관찰
    2026-06-25-03-weighted-replica-scheduling.md        # weighted replica 분산
    2026-06-25-04-override-policy-env.md                # cluster별 env override
    2026-06-25-05-cluster-taint-failover.md             # cluster taint/toleration/failover 관찰
    2026-06-25-06-actual-cluster-failover.md            # 실제 member cluster 장애 관찰
    2026-06-26-07-failover-feature-gate.md               # Failover feature gate 재실험
  manifests/
    demo-nginx/                     # 기본 전파 실험용 YAML
    demo-twinx-only/                # twinx-only 배치 YAML
    demo-twinx-auto-namespace/      # namespace 자동 생성 확인 YAML
    demo-weighted-replicas/         # weighted replica YAML
    demo-override-env/              # OverridePolicy env YAML
    demo-failover-taint/            # 기존 workload taint 관찰 YAML
    demo-taint-new-scheduling/      # taint 상태 새 workload 배치 YAML
    demo-taint-tolerated/           # clusterTolerations YAML
    demo-cluster-failover/          # 실제 cluster 장애 failover YAML
    demo-failover-enabled/          # Failover 옵션 활성화 재실험 YAML
```
