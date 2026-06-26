# 실험 07. Failover feature gate 활성화 후 실제 장애 재실험

## 목적

실험 06에서 `twinx` 실제 장애는 감지되었지만 기존 workload 자동 failover는 일어나지 않았다.
이번 실험은 `karmada-controller-manager`에 failover 관련 옵션을 활성화한 뒤 같은 장애 시나리오를 반복한다.

ScaleX-POD 기준 의미:

```text
TwinX가 죽었을 때 기존 workload를 EdgeX/DataX/Resource Pool로 자동 이동하려면
Karmada control plane 옵션까지 포함해 검증해야 한다.
```

---

## 가설

```text
controller-manager에 Failover feature gate를 켜고 NoExecute eviction 옵션을 켠다.
그 후 twinx-control-plane을 중지하면 기존 twinx replica가 edgex/datax로 이동할 가능성이 있다.
```

---

## controller-manager 원래 옵션

```text
/bin/karmada-controller-manager
--kubeconfig=/etc/karmada/config/karmada.config
--metrics-bind-address=$(POD_IP):8080
--health-probe-bind-address=$(POD_IP):10357
--cluster-status-update-frequency=10s
--leader-elect-resource-namespace=karmada-system
--v=2
```

---

## controller-manager 실험 옵션

추가한 옵션:

```text
--feature-gates=Failover=true
--enable-no-execute-taint-eviction=true
--no-execute-taint-eviction-purge-mode=Directly
```

---

## 매니페스트

```text
karmada/manifests/demo-failover-enabled/
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

controller-manager 옵션 패치:

```bash
kubectl --context kind-tower -n karmada-system patch deploy karmada-controller-manager --type json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/command","value":["/bin/karmada-controller-manager","--kubeconfig=/etc/karmada/config/karmada.config","--metrics-bind-address=$(POD_IP):8080","--health-probe-bind-address=$(POD_IP):10357","--cluster-status-update-frequency=10s","--leader-elect-resource-namespace=karmada-system","--v=2","--feature-gates=Failover=true","--enable-no-execute-taint-eviction=true","--no-execute-taint-eviction-purge-mode=Directly"]}]'
```

rollout 확인:

```bash
kubectl --context kind-tower -n karmada-system rollout status deploy/karmada-controller-manager
```

single-node kind lab에서 anti-affinity 때문에 rollout이 멈춰 기존 pod를 직접 삭제했다.

```bash
kubectl --context kind-tower -n karmada-system delete pod <old-controller-manager-pod> --wait=false
```

baseline 배포:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-failover-enabled/
```

`twinx` 장애 시뮬레이션:

```bash
docker stop twinx-control-plane
```

`twinx` 복구:

```bash
docker start twinx-control-plane
```

controller-manager 옵션 원복:

```bash
kubectl --context kind-tower -n karmada-system patch deploy karmada-controller-manager --type json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/command","value":["/bin/karmada-controller-manager","--kubeconfig=/etc/karmada/config/karmada.config","--metrics-bind-address=$(POD_IP):8080","--health-probe-bind-address=$(POD_IP):10357","--cluster-status-update-frequency=10s","--leader-elect-resource-namespace=karmada-system","--v=2"]}]'
```

원복 rollout도 같은 anti-affinity 문제로 기존 실험 옵션 pod를 직접 삭제해 마무리했다.

---

## 확인 명령

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusters -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb -n demo-failover-enabled -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb -n demo-failover-enabled demo-failover-enabled-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}'

for c in twinx edgex datax; do
  echo "--- $c"
  kubectl --context kind-$c get deploy,pods -n demo-failover-enabled
 done
```

---

## 기대 결과

| 단계 | 기대 결과 |
| --- | --- |
| 옵션 패치 | controller-manager 정상 rollout |
| baseline | twinx=1, edgex=1, datax=1 |
| twinx stop | Karmada Cluster twinx READY=False |
| failover | 기존 twinx replica가 edgex/datax로 이동 가능 |
| 복구 | twinx READY=True |
| 원복 | controller-manager 원래 옵션으로 복구 |

---

## 실제 결과

### 1. 옵션 패치와 rollout

패치 자체는 성공했다.

```text
deployment.apps/karmada-controller-manager patched
```

하지만 single-node `kind-tower`에서는 새 controller-manager pod가 기존 pod와 anti-affinity 때문에 같은 node에 뜨지 못했다.

```text
FailedScheduling:
0/1 nodes are available: 1 node(s) didn't match pod anti-affinity rules.
```

그래서 기존 controller-manager pod를 삭제해 새 pod가 scheduling되도록 했다.

```text
pod "karmada-controller-manager-75dc7b84f9-2mdgp" deleted
deployment "karmada-controller-manager" successfully rolled out
```

패치 후 command:

```text
/bin/karmada-controller-manager
--kubeconfig=/etc/karmada/config/karmada.config
--metrics-bind-address=$(POD_IP):8080
--health-probe-bind-address=$(POD_IP):10357
--cluster-status-update-frequency=10s
--leader-elect-resource-namespace=karmada-system
--v=2
--feature-gates=Failover=true
--enable-no-execute-taint-eviction=true
--no-execute-taint-eviction-purge-mode=Directly
```

### 2. baseline 배치

```text
ResourceBinding:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1

member cluster:
- twinx: demo-failover-enabled-nginx Deployment 1/1, Pod Running 1개
- edgex: demo-failover-enabled-nginx Deployment 1/1, Pod Running 1개
- datax: demo-failover-enabled-nginx Deployment 1/1, Pod Running 1개
```

### 3. twinx 장애 시뮬레이션

실행 시각:

```text
2026-06-26T01:52:13Z
```

명령:

```bash
docker stop twinx-control-plane
```

Karmada cluster 상태:

```text
- twinx READY=False
- reason=ClusterNotReachable
```

자동 taint:

```text
[{
  "effect": "NoSchedule",
  "key": "cluster.karmada.io/not-ready",
  "timeAdded": "2026-06-26T01:53:00Z"
}]
```

### 4. 장애 상태에서 ResourceBinding 관찰

관찰 시간:

```text
2026-06-26T01:53:06Z ~ 2026-06-26T02:02:22Z
약 9분 16초
```

관찰 결과:

```text
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
Failover feature gate와 NoExecute eviction 옵션을 켰지만,
실제 cluster 장애에서 자동으로 추가되는 taint가 NoSchedule이어서 기존 workload는 이동하지 않았다.
```

### 5. twinx 복구

실행 시각:

```text
2026-06-26T02:02:48Z
```

복구 후:

```text
- twinx node Ready
- Karmada Cluster twinx READY=True
- reason=ClusterReady
- twinx taints 없음
```

최종 member 상태:

```text
- twinx: demo-failover-enabled-nginx Deployment 1/1, Pod Running 1개, restart 1회
- edgex: demo-failover-enabled-nginx Deployment 1/1, Pod Running 1개
- datax: demo-failover-enabled-nginx Deployment 1/1, Pod Running 1개
```

최종 ResourceBinding:

```text
- datax replicas=1
- edgex replicas=1
- twinx replicas=1
```

### 6. controller-manager 원복

원복 command:

```text
/bin/karmada-controller-manager
--kubeconfig=/etc/karmada/config/karmada.config
--metrics-bind-address=$(POD_IP):8080
--health-probe-bind-address=$(POD_IP):10357
--cluster-status-update-frequency=10s
--leader-elect-resource-namespace=karmada-system
--v=2
```

원복 rollout도 anti-affinity 때문에 기존 실험 옵션 pod를 삭제해서 완료했다.

```text
pod "karmada-controller-manager-5b9b4d799b-mzxwb" deleted
deployment "karmada-controller-manager" successfully rolled out
```

최종 상태:

```text
- controller-manager 원래 command로 복구
- twinx READY=True
- twinx taints 없음
- tower/twinx/edgex/datax Docker container 모두 Up
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 판단 |
| --- | --- | --- | --- |
| 옵션 패치 | rollout 성공 | anti-affinity로 지연, 기존 pod 삭제 후 성공 | 부분 성공 |
| baseline 배치 | twinx=1, edgex=1, datax=1 | twinx=1, edgex=1, datax=1 | 성공 |
| 장애 감지 | twinx READY=False | READY=False, ClusterNotReachable | 성공 |
| 기존 workload failover | edgex/datax로 이동 | 이동하지 않음 | 실패/추가 확인 필요 |
| 복구 | twinx READY=True | READY=True, taint 제거 | 성공 |
| controller 원복 | 원래 옵션으로 복구 | 복구 완료 | 성공 |

---

## 문제/에러

### 1. single-node kind에서 controller-manager rollout anti-affinity 문제

`kind-tower`가 single-node라서 controller-manager Deployment의 pod anti-affinity가 rolling update를 막았다.

```text
0/1 nodes are available: 1 node(s) didn't match pod anti-affinity rules.
```

해결:

```text
기존 controller-manager pod를 직접 삭제해 새 ReplicaSet pod가 scheduling되도록 했다.
```

이 문제는 운영 이슈라기보다 single-node kind lab 특성에 가깝다.

### 2. Failover feature gate만으로 실제 cluster 장애 failover는 안 됨

이번 설정에서도 cluster offline 시 자동 taint는 다음과 같았다.

```text
cluster.karmada.io/not-ready:NoSchedule
```

`--enable-no-execute-taint-eviction=true`는 NoExecute taint에 대한 eviction 옵션이므로, NoSchedule 자동 taint에는 기존 workload eviction이 발생하지 않은 것으로 보인다.

### 3. gracefulEvictionTasks 비어 있음

```text
gracefulEvictionTasks: empty
```

즉, 기존 ResourceBinding에 대해 eviction 작업이 생성되지 않았다.

---

## ScaleX-POD에 주는 의미

이번 실험으로 확인한 점:

```text
1. Failover feature gate를 켜도 실제 cluster offline 자동 taint는 NoSchedule이었다.
2. NoSchedule은 새 scheduling 회피에는 의미가 있지만 기존 workload eviction에는 충분하지 않았다.
3. 기존 workload 자동 이동을 원하면 NoExecute taint eviction 또는 WorkloadRebalancer 계열을 별도로 검증해야 한다.
```

ScaleX-POD 운영 후보:

```text
TwinX 장애 감지:
  -> Karmada Cluster READY=False
  -> 새 workload는 TwinX 회피
  -> 기존 workload 이동은 별도 eviction/rebalance 절차 필요
```

---

## 다음 액션

- NoExecute eviction 단독 실험
- WorkloadRebalancer / reschedule 실험
- scheduler-estimator 정리
