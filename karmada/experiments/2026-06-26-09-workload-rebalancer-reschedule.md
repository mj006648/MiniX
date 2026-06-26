# 실험 09. WorkloadRebalancer로 복구 cluster 재균형

## 목적

실험 08에서 수동 `NoExecute` taint로 `twinx` workload를 `edgex/datax`로 이동시키는 것은 성공했다.
하지만 `twinx` taint를 제거한 뒤에도 workload가 자동으로 다시 `twinx`까지 분산되지는 않았다.

이번 실험은 Karmada `WorkloadRebalancer`를 사용해 복구된 `twinx`로 workload를 다시 재분산할 수 있는지 확인한다.

ScaleX-POD 기준 의미:

```text
TwinX 장애/점검
  -> NoExecute로 workload를 EdgeX/DataX로 이동
  -> TwinX 복구
  -> WorkloadRebalancer로 TwinX까지 다시 재균형
```

---

## 가설

```text
WorkloadRebalancer가 target Deployment를 다시 scheduling하면,
현재 edgex/datax에 몰려 있는 replica가 policy의 weight 1:1:1에 맞게 twinx/edgex/datax로 재분산될 것이다.
```

---

## 현재 상태

실험 08 이후 `twinx`는 정상 복구되어 있고 taint도 없다.

```text
- datax READY=True
- edgex READY=True
- twinx READY=True
- twinx taints: empty
```

하지만 `demo-noexecute-eviction` workload는 아직 `edgex/datax`에 남아 있다.

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

## WorkloadRebalancer API 확인

설치된 Karmada API 기준으로 `WorkloadRebalancer` 리소스가 존재한다.

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config api-resources | grep -i rebalance
```

결과:

```text
workloadrebalancers  apps.karmada.io/v1alpha1  false  WorkloadRebalancer
```

필드 확인:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config explain workloadrebalancer.spec \
  --api-version=apps.karmada.io/v1alpha1
```

핵심 필드:

```text
spec.workloads[] required
- apiVersion
- kind
- namespace
- name

spec.ttlSecondsAfterFinished optional
```

상태 필드:

```text
status.finishTime
status.observedGeneration
status.observedWorkloads[].result
status.observedWorkloads[].reason
```

---

## 매니페스트

```text
karmada/manifests/demo-workload-rebalancer/
  10-workload-rebalancer.yaml
```

내용:

```yaml
apiVersion: apps.karmada.io/v1alpha1
kind: WorkloadRebalancer
metadata:
  name: demo-noexecute-eviction-rebalance
spec:
  workloads:
    - apiVersion: apps/v1
      kind: Deployment
      namespace: demo-noexecute-eviction
      name: demo-noexecute-eviction-nginx
```

주의:

```text
이번 매니페스트에는 ttlSecondsAfterFinished를 넣지 않았다.
그래서 실험 후 WorkloadRebalancer status를 계속 확인할 수 있다.
단, 같은 이름의 finished WorkloadRebalancer를 다시 apply해도 새 작업처럼 반복 실행되지는 않을 수 있다.
반복 실험하려면 기존 WorkloadRebalancer를 삭제하거나 새 이름을 사용한다.
```

---

## 실행 명령

서버 dry-run:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply --dry-run=server \
  -f karmada/manifests/demo-workload-rebalancer/
```

결과:

```text
workloadrebalancer.apps.karmada.io/demo-noexecute-eviction-rebalance created (server dry run)
```

적용:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-workload-rebalancer/
```

결과:

```text
workloadrebalancer.apps.karmada.io/demo-noexecute-eviction-rebalance created
```

---

## 확인 명령

WorkloadRebalancer 상태:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get workloadrebalancer \
  demo-noexecute-eviction-rebalance -o yaml
```

ResourceBinding 확인:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb \
  -n demo-noexecute-eviction demo-noexecute-eviction-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}{"lastScheduledTime="}{.status.lastScheduledTime}{"\n"}{"gracefulEvictionTasks="}{.spec.gracefulEvictionTasks}{"\n"}'
```

member cluster 확인:

```bash
for c in twinx edgex datax; do
  echo "--- $c"
  kubectl --context kind-$c get deploy,pods -n demo-noexecute-eviction -o wide
done
```

---

## 기대 결과

| 단계 | 기대 결과 |
| --- | --- |
| WorkloadRebalancer 생성 | status result가 Successful |
| ResourceBinding 재계산 | twinx/edgex/datax = 1/1/1 |
| member cluster 반영 | twinx에 Deployment/Pod 재생성 |
| gracefulEvictionTasks | 비어 있음 |

---

## 실제 결과

### 1. WorkloadRebalancer 생성

생성 시각:

```text
2026-06-26T03:02:50Z
```

즉시 `Successful` 상태가 되었다.

```yaml
status:
  finishTime: "2026-06-26T03:02:50Z"
  observedGeneration: 1
  observedWorkloads:
    - result: Successful
      workload:
        apiVersion: apps/v1
        kind: Deployment
        name: demo-noexecute-eviction-nginx
        namespace: demo-noexecute-eviction
```

### 2. ResourceBinding 재균형

관찰 시각:

```text
2026-06-26T03:03:50Z
2026-06-26T03:04:06Z
2026-06-26T03:04:21Z
```

ResourceBinding:

```text
datax replicas=1
edgex replicas=1
twinx replicas=1
lastScheduledTime=2026-06-26T03:02:50Z
schedulerObservedGeneration=9
gracefulEvictionTasks=
```

`lastScheduledTime`이 WorkloadRebalancer 생성 시각과 같은 `2026-06-26T03:02:50Z`로 갱신되었다.

### 3. member cluster 반영

member cluster 상태:

```text
- twinx: Deployment 1/1, Pod Running 1개
- edgex: Deployment 1/1, Pod Running 1개
- datax: Deployment 1/1, Pod Running 1개
```

즉, 실험 08에서 `edgex=2`, `datax=1`, `twinx=0`이던 상태가 policy의 weight 1:1:1에 맞게 복구되었다.

### 4. Service 상태

Deployment만 WorkloadRebalancer 대상으로 지정했지만, Service ResourceBinding은 이미 `twinx/edgex/datax`에 모두 적용된 상태였다.

```text
Service ResourceBinding:
- datax
- edgex
- twinx

member service:
- twinx: demo-noexecute-eviction-nginx Service 있음
- edgex: demo-noexecute-eviction-nginx Service 있음
- datax: demo-noexecute-eviction-nginx Service 있음
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 판단 |
| --- | --- | --- | --- |
| API 존재 | WorkloadRebalancer 사용 가능 | apps.karmada.io/v1alpha1 확인 | 성공 |
| dry-run | 서버 검증 통과 | created server dry run | 성공 |
| 생성 | WorkloadRebalancer 생성 | created | 성공 |
| status | Successful | Successful | 성공 |
| ResourceBinding 재균형 | 1:1:1 | datax=1, edgex=1, twinx=1 | 성공 |
| twinx 복귀 | twinx Pod 재생성 | twinx Deployment 1/1 | 성공 |
| gracefulEvictionTasks | 비어 있음 | 비어 있음 | 성공 |

---

## 문제/에러

이번 실험 자체에서는 기능 실패는 없었다.

주의할 점은 있다.

### 1. WorkloadRebalancer는 명시한 workload 대상의 one-shot 작업이다

이번 실험에서는 다음 대상만 지정했다.

```text
Deployment/demo-noexecute-eviction-nginx
```

따라서 다른 실험 workload까지 자동으로 모두 재균형하는 기능으로 보면 안 된다.
여러 workload를 재균형하려면 `spec.workloads`에 여러 대상을 넣거나 별도 WorkloadRebalancer를 만들어야 한다.

### 2. 같은 이름 재사용 주의

이번 manifest는 상태 확인을 위해 `ttlSecondsAfterFinished`를 설정하지 않았다.
따라서 finished object가 남는다.

반복 실험 방식:

```text
1. 기존 WorkloadRebalancer 삭제 후 같은 이름으로 다시 생성
2. 또는 새 이름의 WorkloadRebalancer 생성
3. 또는 ttlSecondsAfterFinished를 사용해 완료 후 정리
```

### 3. WorkloadRebalancer는 장애 감지 기능이 아니다

이번 기능은 장애 감지가 아니라 이미 존재하는 workload placement를 다시 계산하는 작업에 가깝다.
장애 감지/격리는 여전히 cluster health, taint, 운영 판단과 함께 설계해야 한다.

---

## ScaleX-POD에 주는 의미

이번 실험으로 ScaleX-POD 장애/복구 흐름의 한 조각이 완성됐다.

```text
1. TwinX 장애/점검 시 NoExecute taint로 workload를 EdgeX/DataX로 이동할 수 있다.
2. TwinX 복구 후 taint 제거만으로 자동 재균형되지는 않는다.
3. WorkloadRebalancer를 사용하면 복구된 TwinX까지 workload를 다시 재분산할 수 있다.
```

운영 후보 흐름:

```text
TwinX 장애/점검 판단
  -> twinx Cluster에 NoExecute taint 추가
  -> 기존 TwinX workload가 EdgeX/DataX/Resource Pool로 이동
  -> TwinX 복구
  -> twinx taint 제거
  -> WorkloadRebalancer 생성
  -> policy 기준으로 TwinX/EdgeX/DataX 재균형
```

ScaleX-POD에서 중요한 설계 포인트:

```text
- 장애 시 자동 failover와 운영자 판단 failover를 분리한다.
- 기존 workload 강제 이동은 NoExecute taint로 처리할 수 있다.
- 복구 후 재분산은 WorkloadRebalancer로 처리할 수 있다.
- workload별로 이동 대상과 재균형 대상을 명확히 정의해야 한다.
```

---

## 다음 액션

- NoExecute 영향 범위와 clusterTolerations 설계 실험
- 여러 workload를 한 번에 WorkloadRebalancer로 재균형하는 실험
- WorkloadRebalancer TTL/반복 실행 방식 정리
- ScaleX-POD role label 기반 placement 고도화
