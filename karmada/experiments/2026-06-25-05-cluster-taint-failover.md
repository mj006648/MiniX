# 실험 05. cluster taint / toleration / failover 관찰

## 목적

Karmada Cluster 리소스의 taint를 사용해 특정 member cluster를 배치 대상에서 제외할 수 있는지 확인한다.
또한 이미 배치된 workload가 taint만으로 자동 이동하는지와, `clusterTolerations`를 가진 workload가 taint된 cluster에 들어갈 수 있는지도 함께 확인한다.

ScaleX-POD 기준 의미:

```text
TwinX가 장애/점검 상태가 되면 일반 workload는 TwinX로 새로 들어가지 않아야 한다.
단, 점검 중에도 허용해야 하는 특정 workload는 toleration으로 예외 처리할 수 있어야 한다.
```

이번 실험에서는 실제 cluster를 끄지는 않고, Karmada Cluster 리소스의 `NoExecute` taint를 사용해 `twinx`를 점검 상태처럼 만든다.

---

## 가설

```text
1. baseline workload
   - demo-failover-nginx replicas=3
   - twinx=1, edgex=1, datax=1

2. twinx에 scalex.io/maintenance=true:NoExecute taint 추가
   - 이미 배치된 workload가 자동으로 빠지는지 확인한다.

3. twinx taint 상태에서 새 workload 생성
   - clusterTolerations가 없으면 twinx를 제외하고 edgex/datax에 배치되어야 한다.

4. twinx taint 상태에서 toleration이 있는 새 workload 생성
   - clusterTolerations가 있으면 twinx에도 배치될 수 있어야 한다.
```

---

## 매니페스트

```text
karmada/manifests/demo-failover-taint/
  00-namespace.yaml
  10-deployment.yaml
  20-service.yaml
  30-propagation-policy.yaml

karmada/manifests/demo-taint-new-scheduling/
  00-namespace.yaml
  10-deployment.yaml
  20-service.yaml
  30-propagation-policy.yaml

karmada/manifests/demo-taint-tolerated/
  00-namespace.yaml
  10-deployment.yaml
  20-service.yaml
  30-propagation-policy.yaml
```

`demo-failover-taint` 핵심 policy:

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

`demo-taint-tolerated` 핵심 policy:

```yaml
placement:
  clusterTolerations:
    - key: scalex.io/maintenance
      operator: Equal
      value: "true"
      effect: NoExecute
```

---

## 실행 명령

baseline 배포:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-failover-taint/
```

실제 출력:

```text
namespace/demo-failover created
deployment.apps/demo-failover-nginx created
service/demo-failover-nginx created
propagationpolicy.policy.karmada.io/demo-failover-nginx-policy created
```

`twinx` taint 적용:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config patch cluster twinx --type merge \
  -p '{"spec":{"taints":[{"key":"scalex.io/maintenance","value":"true","effect":"NoExecute"}]}}'
```

실제 출력:

```text
cluster.cluster.karmada.io/twinx patched
[{"effect":"NoExecute","key":"scalex.io/maintenance","timeAdded":"2026-06-25T08:37:18Z","value":"true"}]
```

`twinx` taint 상태에서 새 workload 생성:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-taint-new-scheduling/
```

`twinx` taint 상태에서 toleration 있는 새 workload 생성:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-taint-tolerated/
```

`twinx` taint 제거:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config patch cluster twinx --type json \
  -p '[{"op":"remove","path":"/spec/taints"}]'
```

실제 출력:

```text
cluster.cluster.karmada.io/twinx patched
```

---

## 확인 명령

Karmada API Server:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusters -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get cluster twinx -o jsonpath='{.spec.taints}'
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-failover -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-taint-new -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-taint-tolerated -o wide
```

ResourceBinding replica 확인:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb -n demo-failover demo-failover-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}'

kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb -n demo-taint-new demo-taint-new-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}'

kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb -n demo-taint-tolerated demo-taint-tolerated-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}'
```

member cluster:

```bash
for ns in demo-failover demo-taint-new demo-taint-tolerated; do
  echo "### $ns"
  for c in twinx edgex datax; do
    echo "--- $c"
    kubectl --context kind-$c get deploy,pods -n "$ns"
  done
 done
```

---

## 기대 결과

| 단계 | 기대 배치 |
| --- | --- |
| baseline | twinx=1, edgex=1, datax=1 |
| twinx NoExecute taint 적용 후 기존 workload | twinx에서 빠질 가능성 확인 |
| taint 상태에서 새 workload, toleration 없음 | twinx=0, edgex/datax 합계=3 |
| taint 상태에서 새 workload, toleration 있음 | twinx 포함 가능 |
| taint 제거 후 | twinx taint 없음 |

---

## 실제 결과

### 1. baseline 배치

```text
ResourceBinding:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1

member cluster:
- twinx: demo-failover-nginx Deployment 1/1, Pod Running 1개
- edgex: demo-failover-nginx Deployment 1/1, Pod Running 1개
- datax: demo-failover-nginx Deployment 1/1, Pod Running 1개
```

### 2. twinx에 NoExecute taint 적용 후 기존 workload 관찰

```text
수분간 관찰했지만 demo-failover-nginx ResourceBinding은 바뀌지 않았다.

ResourceBinding:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1

member cluster:
- twinx: 기존 Pod 계속 Running
- edgex: 기존 Pod 계속 Running
- datax: 기존 Pod 계속 Running

gracefulEvictionTasks: 비어 있음
```

관찰:

```text
이번 lab에서는 Karmada Cluster에 수동 NoExecute taint를 추가하는 것만으로는 이미 배치된 ResourceBinding이 즉시 evict/failover 되지 않았다.
```

### 3. taint 상태에서 새 workload, toleration 없음

`twinx` taint가 있는 상태에서 `demo-taint-new-nginx`를 새로 생성했다.

```text
ResourceBinding:
- datax replicas=2
- edgex replicas=1
- twinx 없음

member cluster:
- twinx: Deployment 없음
- edgex: demo-taint-new-nginx Deployment 1/1, Pod Running 1개
- datax: demo-taint-new-nginx Deployment 2/2, Pod Running 2개
```

판단:

```text
Karmada scheduler는 새 scheduling 시점에 taint된 twinx를 제외했다.
```

### 4. taint 상태에서 새 workload, toleration 있음

`twinx` taint가 있는 상태에서 `clusterTolerations`를 가진 `demo-taint-tolerated-nginx`를 새로 생성했다.

```text
ResourceBinding:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1

member cluster:
- twinx: demo-taint-tolerated-nginx Deployment 1/1, Pod Running 1개
- edgex: demo-taint-tolerated-nginx Deployment 1/1, Pod Running 1개
- datax: demo-taint-tolerated-nginx Deployment 1/1, Pod Running 1개
```

판단:

```text
clusterTolerations가 있으면 taint된 twinx에도 배치될 수 있다.
```

### 5. taint 제거 후 최종 상태

```text
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get cluster twinx -o jsonpath='{.spec.taints}'

출력 없음: twinx taint 제거 완료
```

최종 ResourceBinding:

```text
demo-failover:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1

demo-taint-new:
- datax replicas=2
- edgex replicas=1
- twinx 없음

demo-taint-tolerated:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1
```

관찰:

```text
demo-taint-new은 taint 제거 직후 자동으로 twinx까지 재균형되지는 않았다.
이미 scheduling된 ResourceBinding을 다시 균형 맞추려면 별도 재스케줄/리밸런싱 실험이 필요하다.
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 판단 |
| --- | --- | --- | --- |
| baseline 배치 | twinx=1, edgex=1, datax=1 | twinx=1, edgex=1, datax=1 | 성공 |
| 기존 workload 자동 failover | twinx 제외 여부 확인 | 자동 제외되지 않음 | 관찰/이슈 후보 |
| 새 workload taint 회피 | twinx=0, edgex/datax 합계=3 | twinx=0, edgex=1, datax=2 | 성공 |
| toleration workload | twinx 포함 가능 | twinx=1, edgex=1, datax=1 | 성공 |
| taint 원복 | twinx taint 없음 | taint 제거 완료 | 성공 |

---

## 문제/에러

### 1. 수동 NoExecute taint만으로 기존 ResourceBinding이 즉시 evict되지 않음

```text
failover.cluster.purgeMode=Directly를 넣었지만,
수동으로 twinx Cluster에 NoExecute taint를 추가하는 것만으로는 기존 demo-failover-nginx가 이동하지 않았다.
```

가능한 해석:

```text
- cluster taint는 새 scheduling에는 확실히 반영된다.
- 이미 scheduling된 ResourceBinding의 자동 eviction/failover는 별도 조건, controller 옵션, 실제 cluster failure 상태, 또는 재스케줄 트리거가 필요할 수 있다.
- 이 부분은 추가 실험 또는 Karmada 이슈/문서 확인 후보이다.
```

### 2. scheduler-estimator 관련 로그

Karmada scheduler 로그에서 다음 계열의 메시지를 확인했다.

```text
Failed to dial cluster(...): karmada-scheduler-estimator-... timeout
Max cluster available replicas error: cluster twinx does not exist in estimator cache
```

현재 `kind-tower`의 `karmada-system`에는 scheduler-estimator pod/service가 보이지 않았다.

```bash
kubectl --context kind-tower -n karmada-system get pods,svc | grep scheduler-estimator
```

출력 없음.

이번 실험의 static weight scheduling은 정상 동작했지만, estimator 관련 로그는 별도 이슈 후보로 남긴다.

---

## ScaleX-POD에 주는 의미

이번 실험으로 확인한 점:

```text
1. TwinX를 maintenance taint 상태로 만들면 새 일반 workload는 TwinX에 들어가지 않는다.
2. 꼭 TwinX에 들어가야 하는 workload는 clusterTolerations로 예외 허용할 수 있다.
3. 단, 이미 배치된 workload를 taint만으로 즉시 빼는 동작은 이번 lab에서 확인되지 않았다.
```

ScaleX-POD 운영 패턴:

```text
TwinX 점검 전:
  -> twinx Cluster에 scalex.io/maintenance=true:NoExecute taint 부여
  -> 새 일반 workload는 EdgeX/DataX/Resource Pool로 배치
  -> 점검 중에도 허용할 workload만 clusterTolerations 부여

이미 TwinX에 올라간 workload 이동:
  -> 별도 failover/rebalance 절차 필요
  -> 다음 실험에서 실제 cluster NotReady 또는 WorkloadRebalancer를 확인
```

---

## 다음 액션

- 실제 member cluster stop/API 장애로 cluster failover 확인
- WorkloadRebalancer 또는 reschedule 방식 확인
- `clusterTolerations.tolerationSeconds` 동작 확인
- Resource Pool을 overflow cluster로 두는 정책 실험
