# 실험 08. 수동 NoExecute taint eviction 단독 실험

## 목적

실험 07에서 실제 `twinx` cluster 장애는 Karmada가 감지했지만, 자동으로 붙은 taint가 `NoSchedule`이라 기존 workload 이동이 일어나지 않았다.
이번 실험은 실제 cluster를 내리지 않고, Karmada `Cluster` 객체에 수동 `NoExecute` taint를 붙였을 때 기존 ResourceBinding이 eviction/re-schedule 되는지 확인한다.

ScaleX-POD 기준 의미:

```text
TwinX를 운영자가 장애/점검 상태로 판단했을 때
NoExecute taint를 사용하면 기존 workload를 EdgeX/DataX로 강제로 이동시킬 수 있는지 검증한다.
```

---

## 가설

```text
controller-manager에서 NoExecute eviction을 활성화한 상태로 twinx에 NoExecute taint를 추가하면,
기존 twinx replica가 제거되고 edgex/datax 중 가능한 cluster로 재배치될 것이다.
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
karmada/manifests/demo-noexecute-eviction/
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

single-node kind lab에서 anti-affinity로 rollout이 멈추면 기존 pod를 삭제한다.

```bash
kubectl --context kind-tower -n karmada-system delete pod <old-controller-manager-pod> --wait=false
kubectl --context kind-tower -n karmada-system rollout status deploy/karmada-controller-manager
```

실험 workload 적용:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-noexecute-eviction/
```

처음 시도한 taint 명령:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config taint cluster twinx \
  scalex.io/manual-noexecute=lab:NoExecute --overwrite
```

이 명령은 실패했다. `kubectl taint`는 node type만 지원한다고 나왔다.

그래서 `Cluster` CR의 `spec.taints`를 직접 patch했다.

```bash
TAINT_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

kubectl --kubeconfig ~/.kube/karmada-apiserver.config patch cluster twinx --type=json \
  -p "[{\"op\":\"add\",\"path\":\"/spec/taints\",\"value\":[{\"key\":\"scalex.io/manual-noexecute\",\"value\":\"lab\",\"effect\":\"NoExecute\",\"timeAdded\":\"$TAINT_TIME\"}]}]"
```

수동 taint 제거:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config patch cluster twinx --type=json \
  -p '[{"op":"remove","path":"/spec/taints"}]'
```

controller-manager 옵션 원복:

```bash
kubectl --context kind-tower -n karmada-system patch deploy karmada-controller-manager --type json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/command","value":["/bin/karmada-controller-manager","--kubeconfig=/etc/karmada/config/karmada.config","--metrics-bind-address=$(POD_IP):8080","--health-probe-bind-address=$(POD_IP):10357","--cluster-status-update-frequency=10s","--leader-elect-resource-namespace=karmada-system","--v=2"]}]'
```

---

## 확인 명령

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get cluster twinx -o jsonpath='{.spec.taints}'

kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb \
  -n demo-noexecute-eviction demo-noexecute-eviction-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}{"gracefulEvictionTasks="}{.spec.gracefulEvictionTasks}{"\n"}'

for c in twinx edgex datax; do
  echo "--- $c"
  kubectl --context kind-$c get deploy,pods -n demo-noexecute-eviction -o wide
done
```

---

## 기대 결과

| 단계 | 기대 결과 |
| --- | --- |
| 옵션 패치 | controller-manager 정상 rollout |
| baseline | twinx=1, edgex=1, datax=1 |
| 수동 NoExecute taint | twinx가 기존 workload에서 제외됨 |
| eviction/re-schedule | twinx replica가 edgex/datax로 이동 |
| taint 제거 | twinx taint 없음 |
| 원복 | controller-manager 원래 옵션으로 복구 |

---

## 실제 결과

### 1. 옵션 패치와 rollout

실행 시각:

```text
2026-06-26T02:28:31Z
```

패치 자체는 성공했다.

```text
deployment.apps/karmada-controller-manager patched
```

이번에도 single-node `kind-tower`에서는 새 controller-manager pod가 기존 pod와 anti-affinity 때문에 같은 node에 뜨지 못했다.

```text
0/1 nodes are available: 1 node(s) didn't match pod anti-affinity rules.
```

기존 pod 삭제 후 rollout 성공:

```text
pod "karmada-controller-manager-75dc7b84f9-rzmg8" deleted
deployment "karmada-controller-manager" successfully rolled out
```

실험 옵션 pod:

```text
karmada-controller-manager-5b9b4d799b-7pjct     1/1     Running
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

적용 시각:

```text
2026-06-26T02:30:53Z
```

적용 결과:

```text
namespace/demo-noexecute-eviction created
deployment.apps/demo-noexecute-eviction-nginx created
service/demo-noexecute-eviction-nginx created
propagationpolicy.policy.karmada.io/demo-noexecute-eviction-nginx-policy created
```

ResourceBinding:

```text
datax replicas=1
edgex replicas=1
twinx replicas=1
```

member cluster:

```text
- twinx: Deployment 1/1, Pod Running 1개
- edgex: Deployment 1/1, Pod Running 1개
- datax: Deployment 1/1, Pod Running 1개
```

### 3. `kubectl taint cluster` 실패

실행 시각:

```text
2026-06-26T02:34:28Z
```

결과:

```text
error: invalid resource type cluster, only node types are supported
```

판단:

```text
Karmada Cluster CR에는 kubectl taint 명령을 바로 사용할 수 없었다.
spec.taints를 직접 patch해야 했다.
```

### 4. 수동 NoExecute taint 추가

실행 시각:

```text
2026-06-26T02:36:27Z
```

추가된 taint:

```json
[
  {
    "effect": "NoExecute",
    "key": "scalex.io/manual-noexecute",
    "timeAdded": "2026-06-26T02:36:27Z",
    "value": "lab"
  }
]
```

### 5. eviction/re-schedule 결과

관찰 시각:

```text
2026-06-26T02:36:45Z
```

수동 NoExecute taint 추가 후 약 18초 안에 `twinx` replica가 제거되고 `edgex`로 이동했다.

ResourceBinding:

```text
datax replicas=1
edgex replicas=2
gracefulEvictionTasks=
```

member cluster:

```text
- twinx: Deployment missing, Pod 0개
- edgex: Deployment 2/2, Pod 2개
- datax: Deployment 1/1, Pod 1개
```

두 번째/세 번째 관찰에서도 상태는 유지됐다.

```text
2026-06-26T02:37:16Z
2026-06-26T02:37:46Z

ResourceBinding:
- datax replicas=1
- edgex replicas=2
- twinx 없음

member cluster:
- twinx: Deployment missing, Pod 0개
- edgex: 2/2
- datax: 1/1
```

판단:

```text
NoExecute taint + controller-manager NoExecute eviction 옵션 조합에서는 기존 workload eviction/re-schedule이 실제로 동작했다.
```

### 6. 다른 기존 실험 workload 영향

`NoExecute`는 cluster 전체에 적용되는 taint라서 `twinx`에 있던 다른 기존 실험 workload도 같이 영향을 받았다.

관찰 결과 일부:

```text
demo:
- demo-nginx-deployment: datax=1, edgex=2

demo-weighted:
- demo-weighted-nginx-deployment: datax=3, edgex=3

demo-override:
- demo-override-nginx-deployment: datax=2, edgex=1

demo-failover-enabled:
- demo-failover-enabled-nginx-deployment: datax=1, edgex=2

demo-noexecute-eviction:
- demo-noexecute-eviction-nginx-deployment: datax=1, edgex=2
```

`twinx-only` 계열은 다른 cluster로 갈 수 없어서 `gracefulEvictionTasks`가 남았다.

```text
demo-twinx-nginx-deployment:
- fromCluster: twinx
- producer: TaintManager
- purgeMode: Directly
- reason: TaintUntolerated
- replicas: 1
```

ScaleX-POD 관점에서 중요한 점:

```text
NoExecute taint는 특정 실험 workload 하나만 움직이는 기능이 아니라,
해당 cluster의 NoExecute를 toleration하지 않는 기존 workload 전체에 영향을 준다.
```

### 7. taint 제거 후 자동 재균형 확인

수동 taint 제거 시각:

```text
2026-06-26T02:40:06Z
```

제거 후 twinx taint:

```text
empty
```

관찰 시각:

```text
2026-06-26T02:41:39Z ~ 2026-06-26T02:42:41Z
```

결과:

```text
ResourceBinding은 계속 동일:
- datax replicas=1
- edgex replicas=2
- twinx 없음

member cluster:
- twinx: Deployment missing, Pod 0개
- edgex: 2/2
- datax: 1/1
```

판단:

```text
NoExecute taint를 제거해도 이미 edgex/datax로 이동한 workload가 자동으로 twinx까지 재균형되지는 않았다.
복구 후 재분산이 필요하면 WorkloadRebalancer 또는 별도 reschedule 절차를 검증해야 한다.
```

### 8. controller-manager 원복

원복 시작 시각:

```text
2026-06-26T02:45:12Z
```

원복 rollout도 anti-affinity 때문에 기존 실험 옵션 pod를 삭제해서 완료했다.

```text
pod "karmada-controller-manager-5b9b4d799b-7pjct" deleted
deployment "karmada-controller-manager" successfully rolled out
```

최종 command:

```text
/bin/karmada-controller-manager
--kubeconfig=/etc/karmada/config/karmada.config
--metrics-bind-address=$(POD_IP):8080
--health-probe-bind-address=$(POD_IP):10357
--cluster-status-update-frequency=10s
--leader-elect-resource-namespace=karmada-system
--v=2
```

최종 상태 확인:

```text
- datax READY=True
- edgex READY=True
- twinx READY=True
- twinx taints: empty
- controller-manager 원래 command로 복구
- tower/twinx/edgex/datax Docker container 모두 Up
```

실험 workload 최종 상태:

```text
ResourceBinding:
- datax replicas=1
- edgex replicas=2
- twinx 없음

member cluster:
- twinx: No resources found
- edgex: Deployment 2/2, Pod Running 2개
- datax: Deployment 1/1, Pod Running 1개
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 판단 |
| --- | --- | --- | --- |
| 옵션 패치 | rollout 성공 | anti-affinity로 지연, 기존 pod 삭제 후 성공 | 부분 성공 |
| baseline 배치 | twinx=1, edgex=1, datax=1 | twinx=1, edgex=1, datax=1 | 성공 |
| `kubectl taint cluster` | taint 추가 | cluster type 미지원 에러 | 실패/우회 필요 |
| JSON patch taint | NoExecute taint 추가 | spec.taints 추가 성공 | 성공 |
| 기존 workload eviction | twinx replica 제거 | twinx 제거, edgex로 이동 | 성공 |
| taint 제거 | twinx taint 없음 | taint 제거 성공 | 성공 |
| taint 제거 후 재균형 | twinx로 자동 복귀 가능성 확인 | 자동 복귀 없음 | 추가 실험 필요 |
| controller 원복 | 원래 옵션으로 복구 | 복구 완료 | 성공 |

---

## 문제/에러

### 1. `kubectl taint cluster` 미지원

```text
error: invalid resource type cluster, only node types are supported
```

Karmada `Cluster` taint는 일반 `kubectl taint`가 아니라 `spec.taints` patch로 처리해야 했다.

### 2. single-node kind controller-manager rollout anti-affinity 문제 반복

실험 옵션 적용/원복 모두 다음 문제로 rollout이 지연됐다.

```text
0/1 nodes are available: 1 node(s) didn't match pod anti-affinity rules.
```

해결:

```text
기존 controller-manager pod를 삭제해 새 ReplicaSet pod가 scheduling되도록 했다.
```

### 3. NoExecute taint의 전역 영향

수동 `NoExecute` taint는 특정 실험 workload만 대상으로 동작하지 않았다.
`twinx`에 있던 여러 기존 실험 workload가 같이 `edgex/datax`로 이동했다.

운영 환경에서는 다음이 필요하다.

```text
- 점검/장애 대상으로 삼을 workload 범위 정의
- 이동하면 안 되는 workload에는 clusterTolerations 설계
- taint 적용 전 영향 범위 확인
- taint 제거 후 재균형 절차 준비
```

### 4. taint 제거 후 자동 재균형 없음

`twinx` taint를 제거해도 workload가 자동으로 다시 `twinx`까지 분산되지는 않았다.

```text
복구 후 재분산은 WorkloadRebalancer 또는 reschedule 기능을 별도로 확인해야 한다.
```

---

## ScaleX-POD에 주는 의미

이번 실험으로 확인한 점:

```text
1. NoExecute taint는 기존 workload 이동을 실제로 발생시킨다.
2. 실제 cluster offline에서 자동으로 붙는 NoSchedule taint와는 동작이 다르다.
3. NoExecute는 강력하지만 cluster 전체 기존 workload에 영향을 주므로 운영 절차가 필요하다.
4. taint 제거만으로 복구 cluster에 workload가 자동 재분산되지는 않는다.
```

ScaleX-POD 운영 후보 흐름:

```text
TwinX 장애/점검 판단
  -> twinx Cluster에 NoExecute taint 추가
  -> 기존 TwinX workload가 EdgeX/DataX/Resource Pool로 이동
  -> TwinX 복구
  -> taint 제거
  -> WorkloadRebalancer 또는 reschedule로 재균형
```

---

## 다음 액션

- WorkloadRebalancer / reschedule 실험
- NoExecute taint 적용 전 영향 범위 확인 절차 정리
- clusterTolerations로 이동 제외 workload 설계
- scheduler-estimator 정리
