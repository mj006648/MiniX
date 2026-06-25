# 실험 06. 실제 member cluster 장애 failover

## 목적

수동 cluster taint가 아니라 실제 member cluster API 장애 상황에서 Karmada가 cluster 상태를 어떻게 감지하고 기존 workload를 어떻게 처리하는지 확인한다.

ScaleX-POD 기준 의미:

```text
TwinX cluster 자체가 죽거나 API가 끊겼을 때, 기존 workload를 EdgeX/DataX/Resource Pool로 이동할 수 있는지 확인해야 한다.
```

이번 실험에서는 `twinx` kind cluster의 Docker container를 중지해서 API 장애를 시뮬레이션한다.

---

## 가설

```text
초기 상태:
- demo-cluster-failover-nginx replicas=3
- twinx=1, edgex=1, datax=1

장애 시뮬레이션:
- docker stop twinx-control-plane

기대 관찰:
- Karmada Cluster twinx READY가 False 또는 Unknown으로 바뀐다.
- failover.cluster.purgeMode=Directly 정책에 따라 twinx replica가 edgex/datax로 이동할 수 있다.
- 전체 available replica가 가능한 한 유지된다.
```

---

## 매니페스트

```text
karmada/manifests/demo-cluster-failover/
  00-namespace.yaml
  10-deployment.yaml
  20-service.yaml
  30-propagation-policy.yaml
```

핵심 policy:

```yaml
failover:
  cluster:
    purgeMode: Directly
placement:
  clusterAffinity:
    clusterNames:
      - twinx
      - edgex
      - datax
  replicaScheduling:
    replicaSchedulingType: Divided
    replicaDivisionPreference: Weighted
```

---

## 실행 명령

baseline 배포:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-cluster-failover/
```

실제 출력:

```text
namespace/demo-cluster-failover created
deployment.apps/demo-cluster-failover-nginx created
service/demo-cluster-failover-nginx created
propagationpolicy.policy.karmada.io/demo-cluster-failover-nginx-policy created
```

`twinx` cluster 장애 시뮬레이션:

```bash
docker stop twinx-control-plane
```

실제 실행 시각:

```text
2026-06-25T12:07:36Z
twinx-control-plane
```

`twinx` cluster 복구:

```bash
docker start twinx-control-plane
```

실제 실행 시각:

```text
2026-06-25T12:16:37Z
twinx-control-plane
```

---

## 확인 명령

Karmada API Server:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusters -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get cluster twinx -o yaml
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-cluster-failover -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb -n demo-cluster-failover demo-cluster-failover-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}'
```

member cluster:

```bash
for c in twinx edgex datax; do
  echo "--- $c"
  kubectl --context kind-$c get deploy,pods -n demo-cluster-failover
 done
```

Docker/kind:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep -E 'tower|twinx|edgex|datax'
kind get clusters
```

controller 옵션 확인:

```bash
kubectl --context kind-tower -n karmada-system get deploy karmada-controller-manager \
  -o jsonpath='{.spec.template.spec.containers[0].command}'

kubectl --context kind-tower -n karmada-system exec deploy/karmada-controller-manager -- \
  /bin/karmada-controller-manager --help | grep -Ei 'failover|evict|taint|cluster-status'
```

---

## 기대 결과

| 단계 | 기대 결과 |
| --- | --- |
| baseline | twinx=1, edgex=1, datax=1 |
| twinx stop | Karmada Cluster twinx READY False/Unknown |
| failover | twinx replica가 edgex/datax로 이동 가능 |
| 복구 | twinx container 시작, Karmada Cluster READY True 회복 |

---

## 실제 결과

### 1. baseline 배치

```text
ResourceBinding:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1

member cluster:
- twinx: demo-cluster-failover-nginx Deployment 1/1, Pod Running 1개
- edgex: demo-cluster-failover-nginx Deployment 1/1, Pod Running 1개
- datax: demo-cluster-failover-nginx Deployment 1/1, Pod Running 1개
```

### 2. twinx stop 후 Karmada cluster 상태

`twinx-control-plane` 중지 후 Karmada가 장애를 감지했다.

```text
Karmada Cluster twinx:
- READY=False
- Ready condition reason=ClusterNotReachable
- CompleteAPIEnablements=True
```

자동으로 추가된 taint:

```text
[{
  "effect": "NoSchedule",
  "key": "cluster.karmada.io/not-ready",
  "timeAdded": "2026-06-25T12:08:58Z"
}]
```

controller 로그:

```text
Failed to do cluster health check for cluster ... cluster="twinx"
Cluster still offline after ensuring offline is set cluster="twinx" duration="30s"
Taint cluster succeed: cluster now has taints([{Key:cluster.karmada.io/not-ready,Effect:NoSchedule}])
```

### 3. 장애 상태에서 ResourceBinding 관찰

약 7분 동안 관찰했다.

```text
관찰 시간:
- 2026-06-25T12:09:11Z ~ 2026-06-25T12:16:09Z

ResourceBinding은 계속 동일:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1

gracefulEvictionTasks:
- 비어 있음

member ready replicas:
- twinx: unreachable
- edgex: 1
- datax: 1
```

판단:

```text
현재 설치 상태에서는 실제 member cluster 장애가 감지되어도 기존 ResourceBinding이 자동으로 edgex/datax로 이동하지 않았다.
```

### 4. controller-manager 옵션 확인

현재 `karmada-controller-manager` 실행 옵션:

```text
/bin/karmada-controller-manager
--kubeconfig=/etc/karmada/config/karmada.config
--metrics-bind-address=$(POD_IP):8080
--health-probe-bind-address=$(POD_IP):10357
--cluster-status-update-frequency=10s
--leader-elect-resource-namespace=karmada-system
--v=2
```

현재 옵션에는 다음이 없다.

```text
--feature-gates=Failover=true
--enable-no-execute-taint-eviction=true
```

`karmada-controller-manager --help`에서 확인한 관련 설명:

```text
Failover=true|false (BETA - default=false)
--enable-no-execute-taint-eviction
  Enables controller response to NoExecute taints on clusters...
  disabled by default
```

따라서 이번 결과는 다음과 같이 해석한다.

```text
- Karmada는 cluster health check와 offline 감지는 수행했다.
- 자동 taint는 cluster.karmada.io/not-ready:NoSchedule로 들어갔다.
- 기존 workload eviction/failover를 수행하려면 Failover feature gate 또는 NoExecute taint eviction 관련 설정을 별도로 활성화해야 할 가능성이 높다.
```

### 5. twinx 복구

`twinx-control-plane`을 다시 시작했다.

```text
2026-06-25T12:16:37Z
docker start twinx-control-plane
```

복구 후 상태:

```text
twinx node:
- twinx-control-plane Ready

Karmada Cluster twinx:
- READY=True
- Ready condition reason=ClusterReady
- taints 없음
```

controller 로그:

```text
Taint cluster succeed: cluster now does not have taints.
```

최종 member 상태:

```text
- twinx: demo-cluster-failover-nginx Deployment 1/1, Pod Running 1개, restart 1회
- edgex: demo-cluster-failover-nginx Deployment 1/1, Pod Running 1개
- datax: demo-cluster-failover-nginx Deployment 1/1, Pod Running 1개
```

최종 ResourceBinding:

```text
- datax replicas=1
- edgex replicas=1
- twinx replicas=1
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 판단 |
| --- | --- | --- | --- |
| baseline 배치 | twinx=1, edgex=1, datax=1 | twinx=1, edgex=1, datax=1 | 성공 |
| 장애 감지 | twinx READY False/Unknown | READY=False, ClusterNotReachable | 성공 |
| 자동 not-ready taint | cluster 장애 taint 확인 | `cluster.karmada.io/not-ready:NoSchedule` | 성공 |
| 기존 workload failover | edgex/datax로 이동 | 이동하지 않음 | 미확인/설정 필요 |
| 복구 | twinx READY True | READY=True, taint 제거 | 성공 |

---

## 문제/에러

### 1. `failover.cluster`만으로 기존 workload가 이동하지 않음

`PropagationPolicy`에 다음을 넣었지만 기존 workload는 이동하지 않았다.

```yaml
failover:
  cluster:
    purgeMode: Directly
```

확인된 원인 후보:

```text
- 현재 controller-manager에 --feature-gates=Failover=true가 없다.
- help 기준 Failover feature gate 기본값은 false이다.
- cluster 장애 시 자동 taint는 NoSchedule이고, 기존 workload eviction은 NoExecute taint 또는 failover 기능 활성화와 관련 있어 보인다.
- --enable-no-execute-taint-eviction도 현재 활성화되어 있지 않다.
```

### 2. scheduler-estimator 관련 로그

이전 실험과 동일하게 scheduler-estimator 관련 로그가 계속 보인다.

```text
Failed to dial cluster(...): karmada-scheduler-estimator-... timeout
Max cluster available replicas error: cluster ... does not exist in estimator cache
```

현재 `karmada-scheduler`는 다음 옵션으로 실행 중이다.

```text
--enable-scheduler-estimator=true
```

하지만 `karmada-system`에는 scheduler-estimator pod/service가 보이지 않았다.

```bash
kubectl --context kind-tower -n karmada-system get pods,svc | grep scheduler-estimator
```

출력 없음.

static weight scheduling은 동작했지만, estimator 관련 설정은 별도 정리가 필요하다.

---

## ScaleX-POD에 주는 의미

이번 실험으로 확인한 점:

```text
1. Karmada는 TwinX API 장애를 감지하고 Cluster READY=False로 표시할 수 있다.
2. 자동으로 cluster.karmada.io/not-ready:NoSchedule taint를 붙인다.
3. 장애가 복구되면 READY=True로 돌아오고 not-ready taint도 제거된다.
4. 하지만 현재 설치 옵션에서는 기존 workload가 자동으로 EdgeX/DataX로 이동하지 않는다.
```

ScaleX-POD 설계 의미:

```text
단순히 failover.cluster policy를 쓰는 것만으로는 충분하지 않을 수 있다.
실제 운영 전에는 Karmada control plane의 feature gate와 eviction 옵션까지 검증해야 한다.
```

운영 후보 패턴:

```text
TwinX 장애 감지:
  -> Karmada Cluster READY=False
  -> 새 workload는 not-ready cluster 회피
  -> 기존 workload 이동은 Failover feature gate / NoExecute eviction / WorkloadRebalancer 실험 필요
```

---

## 다음 액션

- `--feature-gates=Failover=true` 활성화 후 같은 장애 실험 반복
- `--enable-no-execute-taint-eviction=true`와 수동 NoExecute taint eviction 실험
- WorkloadRebalancer / reschedule 실험
- scheduler-estimator를 설치하거나 `--enable-scheduler-estimator=false`로 정리하는 실험
