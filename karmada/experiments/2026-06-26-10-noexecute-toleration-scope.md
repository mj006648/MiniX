# 실험 10. NoExecute 영향 범위와 clusterTolerations 보호

## 목적

실험 08에서 `NoExecute` taint가 기존 workload를 실제로 이동시키는 것을 확인했다.
하지만 동시에 `NoExecute`는 cluster 전체에 영향을 주기 때문에, 이동시키면 안 되는 workload까지 같이 빠질 수 있다는 위험도 확인했다.

이번 실험은 같은 `NoExecute` taint에 대해 다음 두 workload를 비교한다.

```text
unprotected: clusterTolerations 없음
protected  : 같은 key/value/effect의 clusterTolerations 있음
```

ScaleX-POD 기준 의미:

```text
TwinX 장애/점검 시 모든 workload를 무조건 이동시키는 것이 아니라,
이동해야 하는 workload와 TwinX에 남겨도 되는 workload를 정책으로 분리할 수 있는지 확인한다.
```

---

## 가설

```text
같은 NoExecute taint가 twinx에 붙어도,
clusterTolerations가 없는 workload는 twinx에서 eviction되고,
matching clusterTolerations가 있는 workload는 twinx replica를 유지할 것이다.
```

---

## 실험 taint

```text
key: scalex.io/eviction-test
value: protected
effect: NoExecute
```

protected workload toleration:

```yaml
clusterTolerations:
  - key: scalex.io/eviction-test
    operator: Equal
    value: protected
    effect: NoExecute
```

---

## controller-manager 실험 옵션

이번 실험에서도 기존 workload eviction을 확인해야 하므로 controller-manager에 다음 옵션을 임시로 켰다.

```text
--feature-gates=Failover=true
--enable-no-execute-taint-eviction=true
--no-execute-taint-eviction-purge-mode=Directly
```

원래 옵션:

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

## 매니페스트

```text
karmada/manifests/demo-noexecute-toleration-scope/
  00-namespaces.yaml
  10-unprotected-deployment.yaml
  11-protected-deployment.yaml
  20-unprotected-service.yaml
  21-protected-service.yaml
  30-unprotected-propagation-policy.yaml
  31-protected-propagation-policy.yaml
```

비보호 workload:

```text
namespace: demo-noexecute-unprotected
workload : Deployment/demo-noexecute-unprotected-nginx
policy   : clusterTolerations 없음
```

보호 workload:

```text
namespace: demo-noexecute-protected
workload : Deployment/demo-noexecute-protected-nginx
policy   : scalex.io/eviction-test=protected:NoExecute toleration 있음
```

두 workload 모두 baseline placement는 같다.

```text
replicas: 3
weight  : twinx=1, edgex=1, datax=1
```

---

## 실행 명령

server dry-run:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply --dry-run=server \
  -f karmada/manifests/demo-noexecute-toleration-scope/
```

실제 적용:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-noexecute-toleration-scope/
```

controller-manager 옵션 패치:

```bash
kubectl --context kind-tower -n karmada-system patch deploy karmada-controller-manager --type json \
  -p '[{"op":"replace","path":"/spec/template/spec/containers/0/command","value":["/bin/karmada-controller-manager","--kubeconfig=/etc/karmada/config/karmada.config","--metrics-bind-address=$(POD_IP):8080","--health-probe-bind-address=$(POD_IP):10357","--cluster-status-update-frequency=10s","--leader-elect-resource-namespace=karmada-system","--v=2","--feature-gates=Failover=true","--enable-no-execute-taint-eviction=true","--no-execute-taint-eviction-purge-mode=Directly"]}]'
```

수동 NoExecute taint 추가:

```bash
TAINT_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

kubectl --kubeconfig ~/.kube/karmada-apiserver.config patch cluster twinx --type=json \
  -p "[{\"op\":\"add\",\"path\":\"/spec/taints\",\"value\":[{\"key\":\"scalex.io/eviction-test\",\"value\":\"protected\",\"effect\":\"NoExecute\",\"timeAdded\":\"$TAINT_TIME\"}]}]"
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

ResourceBinding 확인:

```bash
for ns in demo-noexecute-unprotected demo-noexecute-protected; do
  echo "### $ns"
  kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb -n $ns -o name | grep deployment | while read rb; do
    kubectl --kubeconfig ~/.kube/karmada-apiserver.config get $rb -n $ns \
      -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}{"lastScheduledTime="}{.status.lastScheduledTime}{"\n"}{"gracefulEvictionTasks="}{.spec.gracefulEvictionTasks}{"\n"}'
  done
done
```

member cluster 확인:

```bash
for ns in demo-noexecute-unprotected demo-noexecute-protected; do
  echo "### $ns"
  for c in twinx edgex datax; do
    echo "--- $c"
    kubectl --context kind-$c get deploy,pods -n $ns -o wide
  done
done
```

---

## 기대 결과

| 대상 | 기대 결과 |
| --- | --- |
| unprotected | `twinx` replica 제거, `edgex/datax`로 이동 |
| protected | `twinx=1`, `edgex=1`, `datax=1` 유지 |
| twinx taint 제거 | taint 없음 |
| controller 원복 | 원래 command로 복구 |

---

## 실제 결과

### 1. server dry-run 이슈

실행 결과:

```text
namespace/demo-noexecute-unprotected created (server dry run)
namespace/demo-noexecute-protected created (server dry run)
Error from server (NotFound): namespaces "demo-noexecute-unprotected" not found
Error from server (NotFound): namespaces "demo-noexecute-protected" not found
```

판단:

```text
server dry-run에서는 같은 apply 묶음의 Namespace 생성이 실제로 지속되지 않으므로,
뒤의 namespaced resource 검증에서 namespace not found가 발생했다.
실제 apply는 정상 동작했다.
```

### 2. controller-manager 옵션 패치

실행 시각:

```text
2026-06-26T03:21:27Z
```

이번에도 single-node `kind-tower` anti-affinity 때문에 새 pod가 Pending에 걸렸다.

```text
0/1 nodes are available: 1 node(s) didn't match pod anti-affinity rules.
```

기존 pod 삭제 후 rollout 성공:

```text
pod "karmada-controller-manager-75dc7b84f9-nfll9" deleted
deployment "karmada-controller-manager" successfully rolled out
```

### 3. baseline 배치

적용 시각:

```text
2026-06-26T03:24:42Z
```

적용 결과:

```text
namespace/demo-noexecute-unprotected created
namespace/demo-noexecute-protected created
deployment.apps/demo-noexecute-unprotected-nginx created
deployment.apps/demo-noexecute-protected-nginx created
service/demo-noexecute-unprotected-nginx created
service/demo-noexecute-protected-nginx created
propagationpolicy.policy.karmada.io/demo-noexecute-unprotected-nginx-policy created
propagationpolicy.policy.karmada.io/demo-noexecute-protected-nginx-policy created
```

baseline ResourceBinding:

```text
demo-noexecute-unprotected:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1

demo-noexecute-protected:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1
```

baseline member 상태:

```text
unprotected:
- twinx: 1/1
- edgex: 1/1
- datax: 1/1

protected:
- twinx: 1/1
- edgex: 1/1
- datax: 1/1
```

### 4. 수동 NoExecute taint 추가

실행 시각:

```text
2026-06-26T03:26:39Z
```

추가된 taint:

```json
[
  {
    "effect": "NoExecute",
    "key": "scalex.io/eviction-test",
    "timeAdded": "2026-06-26T03:26:39Z",
    "value": "protected"
  }
]
```

### 5. unprotected workload 결과

관찰 시각:

```text
2026-06-26T03:27:28Z
```

ResourceBinding:

```text
datax replicas=2
edgex replicas=1
lastScheduledTime=2026-06-26T03:26:41Z
gracefulEvictionTasks=
```

member 상태:

```text
- twinx: No resources found
- edgex: Deployment 1/1, Pod Running 1개
- datax: Deployment 2/2, Pod Running 2개
```

판단:

```text
clusterTolerations가 없는 workload는 twinx에서 제거되고 datax/edgex로 이동했다.
```

### 6. protected workload 결과

같은 관찰 시각:

```text
2026-06-26T03:27:28Z
```

ResourceBinding:

```text
datax replicas=1
edgex replicas=1
twinx replicas=1
lastScheduledTime=2026-06-26T03:24:43Z
gracefulEvictionTasks=
```

member 상태:

```text
- twinx: Deployment 1/1, Pod Running 1개
- edgex: Deployment 1/1, Pod Running 1개
- datax: Deployment 1/1, Pod Running 1개
```

판단:

```text
matching clusterTolerations가 있는 workload는 NoExecute taint가 붙은 twinx에서도 계속 유지됐다.
```

### 7. 영향 범위 확인

같은 `NoExecute` taint는 실험 대상 외 기존 workload에도 영향을 줄 수 있다.

관찰된 예:

```text
demo-noexecute-eviction:
- taint 전: datax=1, edgex=1, twinx=1
- taint 후: datax=1, edgex=2, twinx 없음
```

이 점은 실험 08의 결론과 같다.

```text
NoExecute taint는 workload 단위가 아니라 cluster 단위 영향이다.
따라서 clusterTolerations가 없는 기존 workload는 같은 key의 taint에도 eviction 대상이 된다.
```

### 8. taint 제거와 controller 원복

수동 taint 제거 시각:

```text
2026-06-26T03:29:22Z
```

controller-manager 원복 시작 시각:

```text
2026-06-26T03:30:32Z
```

원복 rollout도 anti-affinity 때문에 기존 실험 옵션 pod를 삭제해서 완료했다.

```text
pod "karmada-controller-manager-5b9b4d799b-xfhfv" deleted
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

### 9. cleanup 재균형

실험용 taint가 기존 demo workload에도 영향을 줄 수 있으므로, 실험 후 cleanup 용도로 `WorkloadRebalancer`를 한 번 실행했다.

```yaml
apiVersion: apps.karmada.io/v1alpha1
kind: WorkloadRebalancer
metadata:
  name: demo-scope-rebalance-202606260331
spec:
  ttlSecondsAfterFinished: 60
  workloads:
    - apiVersion: apps/v1
      kind: Deployment
      namespace: demo-noexecute-unprotected
      name: demo-noexecute-unprotected-nginx
    - apiVersion: apps/v1
      kind: Deployment
      namespace: demo-noexecute-protected
      name: demo-noexecute-protected-nginx
    - apiVersion: apps/v1
      kind: Deployment
      namespace: demo-noexecute-eviction
      name: demo-noexecute-eviction-nginx
    - apiVersion: apps/v1
      kind: Deployment
      namespace: demo-weighted
      name: demo-weighted-nginx
    # 그 외 기존 demo deployment들도 포함
```

`ttlSecondsAfterFinished: 60` 때문에 완료 후 object는 빠르게 삭제되었다.
관찰 시점에는 이미 `wlr missing`으로 보였지만, ResourceBinding은 재균형되어 있었다.

cleanup 후 주요 상태:

```text
demo-noexecute-unprotected: datax=1, edgex=1, twinx=1
demo-noexecute-protected  : datax=1, edgex=1, twinx=1
demo-noexecute-eviction   : datax=1, edgex=1, twinx=1
demo-weighted             : datax=1, edgex=1, twinx=4
demo-twinx                : twinx=1
demo-twinx-auto           : twinx=1
```

최종 상태:

```text
- datax READY=True
- edgex READY=True
- twinx READY=True
- twinx taints: empty
- controller-manager 원래 command로 복구
- tower/twinx/edgex/datax Docker container 모두 Up
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 판단 |
| --- | --- | --- | --- |
| baseline | 두 workload 모두 1:1:1 | 둘 다 1:1:1 | 성공 |
| unprotected eviction | twinx 제거 | twinx 제거, datax=2/edgex=1 | 성공 |
| protected 유지 | twinx 유지 | twinx=1 유지 | 성공 |
| 영향 범위 확인 | 기존 workload 영향 가능 | demo-noexecute-eviction도 이동 | 확인 |
| taint 제거 | twinx taint 없음 | empty | 성공 |
| controller 원복 | 원래 command | 복구 완료 | 성공 |
| cleanup 재균형 | 주요 demo workload 복구 | WorkloadRebalancer로 복구 | 성공 |

---

## 문제/에러

### 1. server dry-run namespace not found

server dry-run에서는 같은 묶음 안의 Namespace가 실제로 생성되지 않아 뒤의 namespaced resource가 실패했다.

```text
Error from server (NotFound): namespaces "demo-noexecute-unprotected" not found
Error from server (NotFound): namespaces "demo-noexecute-protected" not found
```

실제 apply는 정상 동작했다.

### 2. controller-manager rollout anti-affinity 반복

single-node `kind-tower`에서는 controller-manager rolling update가 anti-affinity 때문에 멈춘다.

```text
0/1 nodes are available: 1 node(s) didn't match pod anti-affinity rules.
```

해결은 이전 실험들과 동일했다.

```text
기존 controller-manager pod를 삭제해 새 pod가 scheduling되도록 했다.
```

### 3. NoExecute taint의 전역 영향

이번 실험의 핵심 이슈다.

```text
NoExecute taint는 특정 workload 하나만 이동시키지 않는다.
해당 cluster에 배치된 모든 workload 중 matching toleration이 없는 workload가 영향 대상이 된다.
```

운영에서는 taint 적용 전에 영향 범위를 반드시 확인해야 한다.

---

## ScaleX-POD에 주는 의미

이번 실험으로 확인한 점:

```text
1. clusterTolerations가 없으면 NoExecute taint로 기존 workload가 이동한다.
2. matching clusterTolerations가 있으면 taint된 cluster에서도 workload가 유지된다.
3. NoExecute는 cluster 전체 영향이므로 workload별 이동 정책을 미리 설계해야 한다.
4. taint 후 원래 분산을 회복하려면 WorkloadRebalancer가 필요하다.
```

ScaleX-POD 운영 후보:

```text
TwinX 장애/점검 taint:
  scalex.io/eviction-test=protected:NoExecute 같은 운영용 key 사용

이동해야 하는 workload:
  clusterTolerations 없음
  -> TwinX에서 EdgeX/DataX/Resource Pool로 이동

TwinX에 남겨도 되는 workload:
  matching clusterTolerations 설정
  -> TwinX 유지
```

실제 운영에서는 key를 더 명확히 분리하는 것이 좋다.

```text
예:
- scalex.io/twinx-maintenance=true:NoExecute
- scalex.io/twinx-critical=true:NoExecute
- scalex.io/manual-eviction=true:NoExecute
```

---

## 다음 액션

- 여러 workload를 한 번에 WorkloadRebalancer로 재균형하는 절차 정리
- ScaleX-POD role label 기반 placement 고도화
- OverridePolicy image/storageClass 실험
- scheduler-estimator 정리
- ArgoCD -> Karmada API Server GitOps 흐름 검증
