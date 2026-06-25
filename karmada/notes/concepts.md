# Karmada 개념 정리

> 정리 기준: Karmada 공식 문서 v1.18 기준.
> 목적: MiniX에서 먼저 Karmada를 실험하고, 이후 ScaleX-POD 멀티클러스터(Tower / TwinX / EdgeX / DataX / Resource Pool)로 확장하기 위한 개념 정리.

---

## 0. 한 줄 요약

Karmada는 **여러 Kubernetes 클러스터를 하나의 Kubernetes API처럼 다루게 해주는 멀티클러스터 오케스트레이션 시스템**이다.

기존 Kubernetes YAML은 최대한 그대로 두고,

```text
무엇을 배포할지      = Resource Template
어디에 배포할지      = PropagationPolicy
클러스터별로 뭘 바꿀지 = OverridePolicy
```

를 정책으로 분리한다.

즉, ArgoCD가 Git의 YAML을 Karmada API Server에 넣으면, Karmada가 정책에 따라 실제 member cluster로 리소스를 전파한다.

```text
GitHub MiniX / ScaleX Infra repo
  -> ArgoCD on Tower
    -> Karmada API Server on Tower
      -> ScaleX-POD member clusters
         - TwinX
         - EdgeX
         - DataX
         - Resource Pool
```

---

## 1. Karmada란?

Karmada는 `Kubernetes Armada`의 줄임말로, 여러 Kubernetes 클러스터와 여러 클라우드 환경에서 애플리케이션을 실행하고 관리하기 위한 시스템이다.

핵심은 다음과 같다.

- 애플리케이션 YAML을 크게 바꾸지 않는다.
- Kubernetes Native API를 사용한다.
- 여러 클러스터 중 어느 곳에 배포할지 스케줄링한다.
- 클러스터 장애 시 다른 클러스터로 failover 할 수 있다.
- 멀티 클라우드 / 하이브리드 클라우드 / 온프레미스 / 엣지 클러스터를 함께 관리할 수 있다.

쉽게 말하면, 단일 Kubernetes 클러스터에서 하던 운영 방식을 멀티클러스터로 확장해주는 컨트롤 플레인이다.

---

## 2. 왜 Karmada를 쓰는가?

### 2.1 Kubernetes Native API 호환성

Karmada는 Kubernetes API와 잘 맞게 설계되어 있다.
그래서 `kubectl`, Helm, Kustomize, ArgoCD, Flux 같은 기존 도구와 연결하기 쉽다.

→ 기존 YAML과 GitOps 방식을 최대한 유지하면서 멀티클러스터로 넘어갈 수 있다.

### 2.2 Out of the Box 멀티클러스터 기능

직접 구현하려면 복잡한 기능을 정책으로 제공한다.

- Active-active
- Remote DR
- Geo redundant 배포
- cross-cluster failover
- cross-cluster load balancing
- autoscaling 연동

→ 여러 클러스터를 단순히 묶는 수준이 아니라, 운영 시나리오를 정책으로 만들 수 있다.

### 2.3 Vendor Lock-in 회피

Karmada는 특정 클라우드 전용 오케스트레이션이 아니다.
Kubernetes 표준을 따르는 클러스터라면 AWS, Azure, GCP, 온프레미스, 엣지 클러스터를 함께 관리할 수 있다.

→ ScaleX-POD 안의 TwinX, EdgeX, DataX처럼 목적이 다른 자체 클러스터를 묶는 데도 적합하다.

### 2.4 중앙 집중식 관리

클러스터가 어디 있든 Karmada control plane에서 관리한다.

- 퍼블릭 클라우드 클러스터
- 사내 온프레미스 클러스터
- GPU 렌더링 클러스터
- 엣지 GPU 컴퓨팅 클러스터
- 데이터/스토리지 전용 클러스터

→ 물리적으로 흩어진 클러스터를 하나의 운영 관점으로 묶을 수 있다.

### 2.5 풍부한 멀티클러스터 스케줄링

Karmada는 Kubernetes 내부의 노드 스케줄링이 아니라 **클러스터 단위 스케줄링**을 한다.

예:

- GPU 클러스터에만 배포
- 특정 region/zone/provider에 우선 배포
- 클러스터별 replica를 나눠서 배포
- 장애가 난 클러스터를 제외하고 다른 곳으로 이동
- 리소스가 부족하면 overflow 클러스터로 확장

---

## 3. Karmada / ArgoCD / Kueue 역할 분리

현재 목표 조합:

```text
Kubernetes + ArgoCD + Karmada + Kueue
```

이 조합은 괜찮다. 다만 역할을 확실히 나눠야 한다.

| 구성 요소 | 역할 | 쉽게 말하면 |
|---|---|---|
| Kubernetes | 실제 Pod 실행 | 일을 하는 현장 |
| ArgoCD | GitOps 배포 | Git을 보고 YAML을 적용하는 배포봇 |
| Karmada | 멀티클러스터 배치/전파/failover | 어느 클러스터에 보낼지 결정하는 본부 |
| Kueue | batch/GPU job queue/admission/quota | GPU/CPU 작업 대기열 관리자 |

### 추천 흐름

초기에는 이렇게 가져가는 게 좋다.

```text
GitHub MiniX / ScaleX Infra repo
  -> ArgoCD on Tower
    -> Karmada API Server on Tower
      -> ScaleX-POD member cluster
        -> Kueue가 Job/Ray/Spark/ML workload 입장 제어
```

즉,

- ArgoCD는 Karmada API Server에 YAML을 넣는다.
- Karmada는 어떤 클러스터로 보낼지 결정한다.
- Kueue는 각 클러스터 안에서 GPU/CPU batch job을 언제 실행할지 제어한다.

처음부터 Karmada와 Kueue를 깊게 섞기보다는,

1. Karmada로 멀티클러스터 전파 먼저 실험
2. Kueue는 member cluster 내부에서 GPU batch queue로 실험
3. 이후 MultiKueue 또는 Karmada + Kueue 고급 패턴 검토

순서가 안전하다.

### 3.1 ArgoCD와 Karmada를 같이 쓰는 이유

겉으로 보면 ArgoCD와 Karmada가 둘 다 YAML을 클러스터에 적용하는 것처럼 보인다.
하지만 둘의 핵심 역할은 다르다.

```text
ArgoCD  = Git을 source of truth로 보고 원하는 YAML을 sync/diff/rollback하는 GitOps 배포기
Karmada = 여러 클러스터 중 어디에, 어떻게, 몇 개를 보낼지 결정하는 멀티클러스터 오케스트레이터
```

비교하면 다음과 같다.

| 구분 | ArgoCD | Karmada |
|---|---|---|
| 핵심 역할 | GitOps 배포/동기화 | 멀티클러스터 배치/전파/failover |
| Source of truth | Git repository | Karmada API Server에 들어온 리소스와 정책 |
| 잘하는 것 | sync, diff, prune, rollback, app-of-apps, UI | cluster placement, replica 분산, override, failover, Push/Pull member 관리 |
| 단일 클러스터 운영 | 매우 적합 | 보통 과함 |
| 멀티클러스터 정책 | ApplicationSet/values로 가능하지만 복잡해질 수 있음 | 전문 영역 |
| Git 변경 자동 반영 | 담당 | 직접 담당하지 않음 |

둘을 같이 쓰면 역할이 이렇게 나뉜다.

```text
GitHub MiniX / ScaleX Infra repo
  -> ArgoCD
     - Git 변경 감지
     - diff/sync/rollback 관리
     - Karmada API Server에 YAML 적용
  -> Karmada
     - TwinX / EdgeX / DataX / Resource Pool 중 배치 결정
     - replica 분산
     - cluster별 override 적용
     - 장애/taint/failover 처리
```

ScaleX-POD 기준 권장 흐름:

```text
GitHub
  -> ArgoCD on Tower
    -> Karmada API Server on Tower
      -> TwinX / EdgeX / DataX / Resource Pool
        -> Kueue가 각 클러스터 내부에서 Job admission/quota 제어
```

즉, ArgoCD는 **무엇을 배포할지와 Git 상태 동기화**를 담당하고,
Karmada는 **그 리소스를 ScaleX-POD 안의 어느 클러스터에 어떻게 배치할지**를 담당한다.

### 3.2 ArgoCD만 쓸 때의 한계

ArgoCD만으로도 여러 클러스터에 배포할 수 있다.
예를 들면 ApplicationSet으로 TwinX, EdgeX, DataX에 각각 Application을 만들 수 있다.

하지만 ScaleX-POD처럼 클러스터 역할이 나뉘고, 장애조치와 replica 분산까지 필요하면 다음이 복잡해진다.

- 클러스터 배치 정책이 ApplicationSet, Helm values, Kustomize patch에 흩어질 수 있다.
- `TwinX 장애 시 Resource Pool로 이동` 같은 런타임 failover 표현이 어렵다.
- 전체 replica 10개를 TwinX 8개, EdgeX 2개처럼 나누는 정책 관리가 복잡하다.
- 클러스터별 image registry, storageClass, nodeSelector 차이를 values/patch로 계속 관리해야 한다.

이 영역은 Karmada의 PropagationPolicy, OverridePolicy, replicaScheduling이 더 자연스럽다.

### 3.3 Karmada만 쓸 때의 한계

Karmada만 써도 `kubectl apply -f`로 Karmada API Server에 리소스를 넣을 수 있다.
하지만 그렇게 하면 GitOps 운영 장점이 약해진다.

Karmada만 사용할 때 부족한 부분:

- Git repository 자동 감시
- UI 기반 diff/sync
- Application 단위 배포 상태 관리
- sync history
- rollback
- app-of-apps
- Git 기준 drift 감지

따라서 ScaleX-POD에서는 다음처럼 역할을 분리하는 것이 좋다.

```text
ArgoCD = GitOps 엔진
Karmada = ScaleX-POD 내부 멀티클러스터 스케줄러/전파기
Kueue = 각 클러스터 내부 GPU/CPU Job admission controller
```

---

## 4. Control Plane과 Member Cluster 개념

### 4.1 Host / Tower Cluster

Karmada control plane이 설치되는 클러스터다.
우리 계획에서는 ScaleX-POD 안의 `Tower Cluster`가 여기에 해당한다.

Tower에는 다음과 같은 중앙 운영 도구를 모을 수 있다.

- ArgoCD
- Karmada control plane
- External Secrets Operator
- 모니터링 / 로깅
- 인증 / 정책 / 관리 도구

주의할 점은, Karmada control plane에 Deployment를 넣는다고 해서 그 Pod가 Tower에서 바로 뜨는 것은 아니다.
Karmada에 제출된 리소스는 먼저 Karmada etcd에 저장되고, 정책에 따라 member cluster로 전파된다.

### 4.2 Member Cluster

실제 워크로드가 실행되는 클러스터다.

ScaleX-POD 기준:

| 구성요소 | 목적 |
|---|---|
| Tower | ArgoCD, Karmada, ESO 등 운영 본부 |
| TwinX | GPU 렌더링 전용 |
| EdgeX | Edge 전용 GPU 컴퓨팅 |
| DataX | SSD/HDD PB급 데이터/스토리지 |
| Resource Pool | GPU/CPU 범용 풀 또는 논리적 자원 풀 |

Tower도 필요하면 member cluster로 join할 수 있다.
하지만 기본 설계에서는 **관리용 control plane**과 **실제 워크로드 실행 cluster**를 분리하는 게 좋다.

---

## 5. Push 모드와 Pull 모드

Karmada는 member cluster를 등록하는 방식으로 Push와 Pull을 지원한다.

### 5.1 Push 모드

Karmada control plane이 member cluster의 Kubernetes API Server에 직접 접근한다.

```text
Karmada control plane -> member cluster API Server
```

장점:

- 구조가 단순하다.
- 실험하기 쉽다.
- MiniX PoC에 적합하다.

주의:

- Tower에서 member cluster API Server로 네트워크 접근이 가능해야 한다.
- kubeconfig/권한 관리가 중요하다.

### 5.2 Pull 모드

member cluster 안에 `karmada-agent`가 설치되고, agent가 Karmada에서 작업을 가져간다.

```text
member cluster karmada-agent -> Karmada control plane
```

장점:

- 엣지/폐쇄망/방화벽 뒤 클러스터에 유리하다.
- 중앙에서 member cluster로 직접 들어가지 않아도 된다.

주의:

- 구조가 Push보다 복잡하다.
- agent 상태도 관리해야 한다.

### MiniX 실험 추천

처음에는 Push 모드로 시작한다.

```text
MiniX/kind host
  -> member1
  -> member2
```

나중에 EdgeX처럼 외부에서 직접 접근하기 어려운 클러스터는 Pull 모드를 검토한다.

---

## 6. Karmada 핵심 리소스

| 리소스 | 역할 | 비유 |
|---|---|---|
| Resource Template | 원본 Kubernetes YAML | 무엇을 배포할지 |
| PropagationPolicy | namespaced 리소스 전파 정책 | 어디로 보낼지 |
| ClusterPropagationPolicy | cluster-scoped 전파 정책 | 클러스터 전체 범위 정책 |
| OverridePolicy | namespaced override 정책 | 클러스터별 차이 적용 |
| ClusterOverridePolicy | cluster-scoped override 정책 | 전역 override |
| ResourceBinding | 스케줄링 결과 | 이 리소스는 어느 클러스터에 묶였는지 |
| ClusterResourceBinding | cluster-scoped ResourceBinding | cluster-scoped 스케줄링 결과 |
| Work | 클러스터별 실행 단위 | member cluster로 배달될 작업 묶음 |
| Cluster | member cluster 정보 | 관리 대상 클러스터 |
| ResourceInterpreter | CRD 해석 로직 | CRD의 replica/status/health 읽는 방법 |
| FederatedResourceQuota | 멀티클러스터 quota | 전체 리소스 사용량 제한 |
| ServiceExport / ServiceImport | 멀티클러스터 서비스 디스커버리 | 다른 클러스터 서비스 찾기 |

---

## 7. Resource Template

Resource Template은 우리가 원래 쓰던 Kubernetes YAML이다.

예:

- Deployment
- Service
- ConfigMap
- Secret
- Ingress
- PVC
- CRD 기반 리소스
  - SparkApplication
  - RayCluster
  - FlinkDeployment
  - Kueue ResourceFlavor / ClusterQueue / LocalQueue

Karmada 전용 YAML로 앱을 다시 작성하는 것이 아니라, 기존 Kubernetes 리소스를 템플릿으로 사용한다.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-nginx
  namespace: demo
  labels:
    app: demo-nginx
spec:
  replicas: 3
  selector:
    matchLabels:
      app: demo-nginx
  template:
    metadata:
      labels:
        app: demo-nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.28.0-alpine
```

이 Deployment 자체는 일반 Kubernetes YAML이다.
어디로 보낼지는 PropagationPolicy가 결정한다.

---

## 8. PropagationPolicy

PropagationPolicy는 Resource Template을 어느 cluster로 전파할지 정한다.

```text
Resource Template = 무엇을 배포할 것인가?
PropagationPolicy = 어디에 배포할 것인가?
```

### 8.1 PropagationPolicy와 ClusterPropagationPolicy

| 종류 | 범위 | 사용 예 |
|---|---|---|
| PropagationPolicy | namespace 범위 | Deployment, Service 등 namespaced 리소스 |
| ClusterPropagationPolicy | cluster 범위 | Namespace, CRD, ClusterRole 등 cluster-scoped 리소스 |

### 8.2 resourceSelectors

정책이 어떤 리소스에 적용될지 선택한다.

선택 기준:

- apiVersion
- kind
- name
- namespace
- labelSelector

예:

```yaml
apiVersion: policy.karmada.io/v1alpha1
kind: PropagationPolicy
metadata:
  name: demo-nginx-policy
  namespace: demo
spec:
  resourceSelectors:
    - apiVersion: apps/v1
      kind: Deployment
      name: demo-nginx
  placement:
    clusterAffinity:
      clusterNames:
        - member1
        - member2
```

→ `demo` namespace의 `demo-nginx` Deployment를 `member1`, `member2`로 전파한다.

### 8.3 clusterAffinity

클러스터 이름, 라벨, 필드로 대상 클러스터를 선택한다.

예:

```yaml
placement:
  clusterAffinity:
    labelSelector:
      matchLabels:
        scalex.io/pool: gpu
```

→ `scalex.io/pool=gpu` 라벨이 붙은 클러스터로 배포한다.

ScaleX-POD 라벨 예시:

> MiniX 실험에서는 `minix.io/*` 같은 임시 prefix를 써도 되지만, 실제 ScaleX-POD에서는 `scalex.io/*` 같은 prefix를 쓰는 편이 명확하다.

```text
scalex.io/role=tower
scalex.io/role=gpu-render
scalex.io/role=edge-gpu
scalex.io/role=data
scalex.io/pool=gpu
scalex.io/pool=cpu
scalex.io/storage=ssd
scalex.io/storage=hdd
scalex.io/location=homelab
```

### 8.4 clusterAffinities / fallback / overflow

여러 affinity 그룹을 우선순위처럼 사용할 수 있다.

예상 패턴:

```text
1순위: TwinX GPU 클러스터
2순위: Resource GPU Pool
3순위: 클라우드 GPU 클러스터
```

즉, 기본은 TwinX에서 처리하고, GPU 자리가 부족하면 Resource Pool이나 cloud GPU 쪽으로 넘기는 식의 설계가 가능하다.

### 8.5 clusterTolerations

Kubernetes node의 taint/toleration처럼, Karmada도 cluster taint/toleration 개념을 쓴다.

예:

- 특정 클러스터를 점검 중으로 taint
- 정책이 그 taint를 tolerate하지 않으면 다른 클러스터로 이동

```text
TwinX cluster taint: scalex.io/maintenance=true:NoExecute
Policy가 tolerate 안 함
-> 새 workload는 TwinX로 안 감
-> EdgeX/DataX/Resource Pool 후보로 배치

Policy가 clusterTolerations로 tolerate 함
-> 점검 중에도 허용된 workload는 TwinX 배치 가능
```

MiniX kind lab 실험 05에서 확인한 점:

```text
- taint는 새 scheduling에는 반영되어 twinx를 제외했다.
- clusterTolerations가 있으면 taint된 twinx에도 배치되었다.
- 단, 수동 NoExecute taint만으로 이미 배치된 ResourceBinding이 즉시 evict되지는 않았다.
```

### 8.6 spreadConstraints

워크로드를 여러 클러스터에 퍼뜨리는 조건이다.

예:

- region별로 분산
- zone별로 분산
- provider별로 분산
- cluster별로 고르게 분산

Active-active 또는 HA 시나리오에서 중요하다.

```text
같은 region에만 몰지 말고,
region / zone / cluster 기준으로 나눠서 배포
```

### 8.7 replicaScheduling

replica를 클러스터마다 어떻게 배치할지 정한다.

대표 모드:

| 모드 | 의미 | 예시 |
|---|---|---|
| Duplicated | 각 대상 클러스터에 같은 replica 수 배포 | member1에 3개, member2에 3개 |
| Divided | 전체 replica를 여러 클러스터에 나눔 | 전체 10개를 4:3:3으로 분할 |
| Aggregated | 가능한 한 적은 클러스터에 몰아서 배치 | 비용 절감 / locality |
| Weighted | weight 기준으로 나눔 | GPU 많은 클러스터에 더 많이 |
| DynamicWeight | 가용 리소스 기반 동적 분배 | AvailableReplicas 기준 |

예:

```yaml
replicaScheduling:
  replicaSchedulingType: Divided
  replicaDivisionPreference: Weighted
  weightPreference:
    staticWeightList:
      - targetCluster:
          clusterNames:
            - twinx
        weight: 8
      - targetCluster:
          clusterNames:
            - edgex
        weight: 2
```

→ 전체 replica 중 80%는 TwinX, 20%는 EdgeX 쪽으로 보낼 수 있다.

---

## 9. OverridePolicy

OverridePolicy는 클러스터별로 YAML 일부를 바꾸는 정책이다.

```text
OverridePolicy = 같은 앱이지만 클러스터별로 설정을 다르게 바꾸기
```

예:

- 클러스터별 image registry 변경
- StorageClass 변경
- nodeSelector/toleration 변경
- command/args 변경
- env 변경
- label/annotation 추가
- Service type 변경
- PVC 설정 변경

### 9.1 OverridePolicy와 ClusterOverridePolicy

| 종류 | 범위 | 사용 예 |
|---|---|---|
| OverridePolicy | namespace 범위 | 특정 앱/namespace override |
| ClusterOverridePolicy | cluster 범위 | 전역 이미지 registry, 전역 storage 정책 |

namespaced 리소스에는 보통 ClusterOverridePolicy가 먼저 적용되고, 그 다음 OverridePolicy가 적용된다.

### 9.2 Image override 예시

```yaml
apiVersion: policy.karmada.io/v1alpha1
kind: OverridePolicy
metadata:
  name: image-registry-override
  namespace: demo
spec:
  resourceSelectors:
    - apiVersion: apps/v1
      kind: Deployment
      name: demo-nginx
  overrideRules:
    - targetCluster:
        clusterNames:
          - edgex
      overriders:
        imageOverrider:
          - component: Registry
            operator: replace
            value: registry.edge.local
```

→ EdgeX에 배포될 때만 이미지 registry를 바꾼다.

### 9.3 StorageClass override 예시

```text
TwinX  -> fast-nvme
DataX  -> data-ssd
EdgeX  -> edge-local
Cloud  -> gp3 / managed-premium
```

→ 같은 PVC라도 클러스터별 storage class가 다를 수 있으므로 OverridePolicy가 필요하다.

---

## 10. Karmada 내부 동작 흐름

대략적인 흐름은 다음과 같다.

```text
1. 사용자가 Karmada API Server에 Resource Template과 Policy를 적용
2. Policy Controller가 리소스와 정책을 매칭
3. Scheduler가 대상 member cluster를 결정
4. ResourceBinding / ClusterResourceBinding 생성
5. Binding Controller가 cluster별 Work 생성
6. Execution Controller 또는 karmada-agent가 member cluster에 실제 리소스 적용
7. member cluster의 상태가 Karmada control plane으로 다시 집계
```

실무적으로 보면 이 흐름이 중요하다.

```text
Deployment + PropagationPolicy + OverridePolicy
  -> ResourceBinding
    -> Work
      -> karmada-es-<cluster> namespace
        -> member cluster에 실제 Deployment 생성
```

### karmada-es- 네임스페이스

Karmada control plane 내부에는 member cluster별로 `karmada-es-` prefix가 붙은 namespace가 만들어질 수 있다.

예:

```text
karmada-es-twinx
karmada-es-edgex
karmada-es-datax
```

이 공간에 cluster별 Work 등이 분리되어 관리된다.

---

## 11. 주요 컴포넌트

### 11.1 karmada-apiserver

Karmada의 중앙 API Server다.
사용자, kubectl, ArgoCD가 바라보는 입구다.

특징:

- Kubernetes API Server 구현을 사용한다.
- Kubernetes 생태계 도구와 잘 맞는다.
- Karmada API와 Kubernetes 리소스를 함께 받는다.

### 11.2 karmada-aggregated-apiserver

확장 API Server다.
member cluster의 상태 조회, proxy, aggregated API 기능에 관여한다.

예:

- cluster/status
- cluster/proxy
- 여러 cluster 리소스 조회

### 11.3 kube-controller-manager

Kubernetes 기본 컨트롤러 일부를 사용한다.
다만 Karmada control plane에 Deployment를 제출했다고 해서 여기서 Pod를 직접 만들지는 않는다.

중요 포인트:

```text
Karmada control plane = 리소스 저장/전파/스케줄링
Member cluster = 실제 Pod 실행
```

### 11.4 karmada-controller-manager

Karmada 전용 컨트롤러 묶음이다.
Karmada 객체를 감시하고 member cluster에 리소스를 생성/업데이트한다.

### 11.5 karmada-scheduler

어느 member cluster에 배포할지 결정한다.

판단 기준:

- policy 조건
- cluster label/field
- taint/toleration
- spread constraint
- replica scheduling
- cluster resource

### 11.6 karmada-webhook

요청 검증/변경을 담당한다.

- Mutating webhook: 기본값 주입 또는 수정
- Validating webhook: 정책 위반 요청 거부

### 11.7 etcd

Karmada control plane의 저장소다.
Karmada API 객체와 Kubernetes API 객체가 저장된다.

운영 시 반드시 백업 계획이 필요하다.

### 11.8 karmada-agent

Pull 모드 member cluster에 설치된다.
Karmada에서 manifest를 가져와 member cluster에 적용하고, 상태를 다시 Karmada로 보낸다.

---

## 12. Addons

### 12.1 karmada-scheduler-estimator

member cluster 내부의 실제 스케줄링 가능성을 더 정확히 계산한다.

왜 필요한가?

```text
cluster 전체 CPU/GPU 총량은 충분해 보이지만,
실제로는 한 노드에 필요한 만큼의 연속 자원이 없어서 Pod가 Pending 될 수 있음
```

estimator는 이런 문제를 줄이기 위해 member cluster의 노드 단위 상황을 고려한다.

GPU 클러스터에서는 특히 중요하다.

### 12.2 karmada-descheduler

기본적으로 주기적으로 상태를 확인하면서 reschedule을 트리거할 수 있다.
공식 문서 기준으로 dynamic division 전략에서 scheduler-estimator와 함께 효과가 있다.

예:

- 클러스터 자원이 바뀜
- replica 상태가 변함
- 일부 클러스터가 과부하/장애 상태
- 더 적절한 클러스터로 재배치 필요

### 12.3 karmada-search

멀티클러스터 전역 검색과 resource proxy 기능을 제공한다.

예:

```text
내 Pod가 어느 클러스터에 있지?
어느 클러스터에서 nginx Deployment가 Pending이지?
여러 클러스터 이벤트를 한 번에 보고 싶다.
```

이럴 때 전역 검색이 유용하다.

---

## 13. Key Features 자세히

### 13.1 Cross-cloud multi-cluster multi-mode management

Karmada는 public cloud, private cloud, on-prem, edge cluster를 함께 관리할 수 있다.

지원 포인트:

- cluster별 안전한 격리
- Push/Pull 연결 모드
- Kubernetes 사양을 따르는 다양한 클러스터 관리

ScaleX-POD 관점:

```text
Tower에서 TwinX / EdgeX / DataX / Resource Pool을 등록하고
각 클러스터를 역할별 label로 구분한다.
```

### 13.2 Multi-policy multi-cluster scheduling

Karmada의 핵심 기능이다.

사용 가능한 정책:

- ClusterAffinity
- Toleration
- SpreadConstraint
- ReplicasScheduling
- OverridePolicy
- Reschedule

예시 패턴:

```text
GPU rendering app
  -> scalex.io/role=gpu-render 클러스터 우선
  -> 부족하면 scalex.io/pool=gpu 클러스터로 overflow
  -> EdgeX는 latency-sensitive 작업만 허용
```

### 13.3 Cross-cluster failover

클러스터 장애 또는 cluster taint에 따라 replica를 다른 클러스터로 옮기는 시나리오를 만들 수 있다.

예:

```text
TwinX 장애
  -> TwinX에 있던 replica를 Resource GPU Pool로 이동
  -> 서비스 replica가 0으로 떨어지지 않게 유지
```

주의:

- 모든 workload가 자동으로 완벽하게 무중단 이전되는 것은 아니다.
- 수동 cluster taint는 새 scheduling에는 반영되지만, 이미 배치된 workload eviction은 별도 failover/rebalance 조건을 더 확인해야 한다.
- MiniX kind lab 실험 06에서는 실제 `twinx` API 장애가 `READY=False`와 `cluster.karmada.io/not-ready:NoSchedule`로 감지되었지만, 현재 controller 옵션에서는 기존 ResourceBinding 자동 이동이 확인되지 않았다.
- `Failover` feature gate, `NoExecute` taint eviction, WorkloadRebalancer 설정을 추가 검증해야 한다.
- stateful workload는 storage, data locality, network 설계를 같이 봐야 한다.

### 13.4 Global Uniform Resource View

여러 클러스터에 흩어진 리소스를 하나의 관점으로 볼 수 있다.

가능한 것:

- 리소스 상태 수집/집계
- create/update/delete/query 통합
- describe/logs/exec 같은 운영 작업
- global search

ScaleX-POD에서 유용한 점:

```text
TwinX GPU job은 어디서 돌고 있는가?
EdgeX의 특정 Pod가 왜 Pending인가?
DataX 쪽 PVC 상태는 어떤가?
```

### 13.5 Best Production Practices

운영 관점 기능:

- unified authentication
- FederatedResourceQuota
- reusable scheduling strategy

FederatedResourceQuota는 여러 클러스터의 quota를 통합 관점으로 관리할 때 중요하다.

예:

```text
전체 GPU pool에서 특정 팀은 최대 20 GPU까지만 사용
전체 CPU pool에서 dev namespace는 200 core까지만 사용
```

### 13.6 Cross-cluster service governance

Karmada는 MCS API 방식의 `ServiceExport`, `ServiceImport`를 통해 cross-cluster service discovery를 다룰 수 있다.

추가로 실제 Pod-to-Pod 네트워크 연결은 Submariner 같은 멀티클러스터 네트워크 도구가 필요할 수 있다.

중요 구분:

```text
Service discovery = 다른 클러스터 서비스를 이름으로 찾는 것
Network connectivity = 실제 패킷이 클러스터 사이를 오가는 것
```

둘은 다르다.

---

## 14. Resource Interpreter

Karmada가 native Kubernetes 리소스는 어느 정도 이해한다.
예를 들어 Deployment는 replicas, status, health를 어떻게 봐야 하는지 알고 있다.

하지만 CRD는 기본적으로 의미를 모른다.

예:

- SparkApplication
- RayCluster
- FlinkDeployment
- Volcano Job
- Kueue 관련 리소스
- 자체 GPU rendering CRD

이런 리소스는 Karmada가 다음을 알기 어렵다.

```text
replica가 몇 개인가?
CPU/GPU 요청량은 어떻게 계산하는가?
상태가 Healthy인가?
의존 리소스가 있는가?
여러 클러스터 상태를 어떻게 합칠 것인가?
```

그래서 Resource Interpreter가 필요하다.

### 14.1 Interpreter가 하는 일

주요 operation:

| Operation | 역할 |
|---|---|
| InterpretReplica | replica 수와 resource request 해석 |
| InterpretComponent | Ray/Spark/Flink처럼 여러 component가 있는 workload 해석 |
| ReviseReplica | 클러스터별 replica 조정 |
| Retain | member cluster에서 유지해야 할 필드 보존 |
| AggregateStatus | 여러 클러스터 상태를 하나로 집계 |
| InterpretStatus | 상태 필드 추출 |
| InterpretHealth | healthy 여부 판단 |
| InterpretDependency | 의존 리소스 식별 |

### 14.2 MiniX에서 중요한 이유

우리 계획은 단순 웹앱보다 GPU/데이터/배치 워크로드가 많다.

```text
GPU Rendering Job
RayCluster
SparkApplication
Kueue-managed Job
Data processing pipeline
```

이런 것들은 단순 Deployment보다 구조가 복잡하다.
따라서 나중에 Karmada로 CRD workload까지 제대로 스케줄링하려면 Resource Interpreter를 봐야 한다.

초기 실험에서는 Deployment/Service로 시작하고, 그 다음 Spark/Ray/Kueue 관련 CRD로 확장하는 게 좋다.

---

## 15. MiniX 기준 실험 로드맵

### Phase 0. 문서/구조 정리

상태: 진행 중

- [x] Karmada 디렉터리 생성
- [x] roadmap 정리
- [x] concepts 정리 시작
- [ ] 실제 Karmada PoC manifests 추가

### Phase 1. 로컬 멀티클러스터 PoC

목표:

```text
kind 또는 MiniX 내부 테스트 클러스터로
karmada-host + member1 + member2 구성
```

실험:

- Karmada 설치
- member cluster join
- `kubectl get clusters`
- Push 모드 확인

### Phase 2. 기본 전파 실험

목표:

```text
demo-nginx Deployment를 member1/member2에 전파
```

실험:

- Resource Template 작성
- PropagationPolicy 작성
- ResourceBinding / Work 확인
- member cluster에 실제 Deployment 생성 확인

### Phase 3. OverridePolicy 실험

목표:

```text
cluster별 image / env / storageClass / serviceType 변경
```

실험:

- EdgeX는 edge registry 사용
- DataX는 data storageClass 사용
- TwinX는 GPU nodeSelector/toleration 사용

### Phase 4. Failover 실험

목표:

```text
member cluster 하나를 장애/taint 상태로 만들고 replica 이동 확인
```

실험:

- cluster taint 설정
- policy toleration 차이 확인
- replica migration 확인
- 서비스 중단 여부 확인

### Phase 5. Global View / Search 실험

목표:

```text
Karmada에서 전체 member cluster resource 조회
```

실험:

- aggregated API
- karmada-search
- logs/describe/proxy 가능 범위 확인

### Phase 6. ArgoCD 연동

목표:

```text
ArgoCD destination을 Karmada API Server로 설정
```

실험 흐름:

```text
GitHub MiniX / ScaleX Infra repo
  -> ArgoCD Application
    -> Karmada API Server
      -> ScaleX-POD member clusters
```

주의:

- ArgoCD가 member cluster를 직접 배포 대상으로 보지 않게 할지
- Karmada API Server만 destination으로 둘지
- 앱별 sync wave / namespace 생성 순서
- CRD 전파 순서

### Phase 7. Kueue 연동 검토

초기 방향:

```text
Karmada = 어느 클러스터로 보낼지 결정
Kueue = 해당 클러스터 내부에서 batch/GPU job admission 제어
```

실험:

- member cluster에 Kueue 설치
- Karmada로 Job 전파
- Kueue LocalQueue / ClusterQueue 동작 확인
- GPU ResourceFlavor 설계
- 나중에 MultiKueue와 비교

---

## 16. ScaleX-POD 멀티클러스터 아키텍처 초안

```text
+---------------------------------------------------------------+
| ScaleX-POD = 멀티클러스터                                    |
|                                                               |
|  GitHub MiniX / ScaleX Infra Repo                             |
|              |                                                |
|              v                                                |
|         ArgoCD (Tower)                                        |
|              |                                                |
|              v                                                |
|   Karmada API Server (Tower)                                  |
|              |                                                |
|   +----------+------------+------------+----------------+     |
|   |                       |            |                |     |
|   v                       v            v                v     |
| TwinX Cluster        EdgeX Cluster  DataX Cluster  Resource   |
| GPU Rendering        Edge/GPU       Data/Lakehouse Pool       |
+---------------------------------------------------------------+
```

### Tower Cluster

관리용 클러스터다.

들어갈 후보:

- ArgoCD
- Karmada control plane
- External Secrets Operator
- cert-manager
- ingress / gateway
- monitoring / logging
- policy engine
- cluster registry

### TwinX Cluster

GPU rendering 전용.

정책 예:

```text
scalex.io/role=gpu-render
scalex.io/pool=gpu
scalex.io/workload=rendering
```

### EdgeX Cluster

Edge 전용 GPU 컴퓨팅.

정책 예:

```text
scalex.io/role=edge-gpu
scalex.io/location=edge
scalex.io/latency=low
```

### DataX Cluster

대용량 데이터/스토리지.

정책 예:

```text
scalex.io/role=data
scalex.io/storage=ssd
scalex.io/storage-tier=pb
```

### Resource Pool

공용 GPU/CPU 풀.

정책 예:

```text
scalex.io/pool=gpu
scalex.io/pool=cpu
scalex.io/usage=overflow
```

---

## 17. 주의할 점

### 17.1 Karmada는 node scheduler가 아니다

Karmada는 어느 cluster로 보낼지 결정한다.
그 cluster 안에서 어느 node에 Pod를 올릴지는 Kubernetes scheduler가 결정한다.

```text
Karmada scheduler = cluster 선택
Kubernetes scheduler = node 선택
```

### 17.2 Stateful workload는 신중히

DB, object storage, data lake, PVC 많은 workload는 단순 failover가 어렵다.

고려할 것:

- 데이터 복제
- 스토리지 class 차이
- PVC 이동 가능 여부
- 네트워크 latency
- backup/restore

### 17.3 Service discovery와 네트워크 연결은 다르다

ServiceExport/ServiceImport는 서비스를 찾는 방법이고,
실제 클러스터 간 Pod 통신은 Submariner 같은 네트워크 계층이 필요할 수 있다.

### 17.4 CRD workload는 Resource Interpreter가 중요하다

Spark/Ray/Flink/Kueue 같은 CRD workload를 제대로 운영하려면 Karmada가 그 리소스를 어떻게 해석할지 정해야 한다.

### 17.5 정책 selector를 너무 넓게 잡으면 위험하다

예:

```yaml
resourceSelectors:
  - apiVersion: apps/v1
    kind: Deployment
```

이렇게만 쓰면 namespace 안의 Deployment 전체에 정책이 적용될 수 있다.
초기에는 name 또는 label을 명확히 지정하는 게 좋다.

### 17.6 Secret/credential 전파는 나중에 신중히

지금은 실험 단계라 secret은 깊게 신경 쓰지 않더라도, 실제 운영에서는 다음을 고려해야 한다.

- External Secrets Operator와 연계
- cluster별 secret backend
- secret propagation 범위 제한
- Git에 secret 직접 저장 금지

---

## 18. MiniX에서 바로 해볼 첫 실험

첫 실험은 너무 복잡하게 가지 않고 아래 정도가 좋다.

```text
1. karmada-host 구성
2. member1/member2 등록
3. demo namespace 생성
4. nginx Deployment 작성
5. PropagationPolicy로 member1/member2 배포
6. OverridePolicy로 member2의 image tag 또는 env 변경
7. member1 cordon/taint 또는 cluster taint로 failover 확인
8. ArgoCD가 Karmada API Server에 sync하도록 변경
```

실험 결과는 별도 파일에 계속 기록한다.

```text
karmada/notes/lab-log.md
karmada/manifests/
karmada/examples/
```

---

## 19. 참고 링크

- Karmada 공식 문서: https://karmada.io/docs/
- Core Concepts: https://karmada.io/docs/core-concepts/concepts/
- Components: https://karmada.io/docs/core-concepts/components/
- Key Features: https://karmada.io/docs/key-features/features/
- PropagationPolicy: https://karmada.io/docs/userguide/scheduling/propagation-policy/
- OverridePolicy: https://karmada.io/docs/userguide/scheduling/override-policy/
- Resource Interpreter: https://karmada.io/docs/userguide/globalview/customizing-resource-interpreter/
- Multi-cluster Service Discovery: https://karmada.io/docs/userguide/service/multi-cluster-service/
