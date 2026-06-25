# 실험 04. OverridePolicy로 cluster별 env 변경

## 목적

Karmada `OverridePolicy`를 사용해 같은 Deployment를 여러 member cluster에 배포하면서 cluster별 설정을 다르게 바꿀 수 있는지 확인한다.

ScaleX-POD 기준 의미:

```text
TwinX / EdgeX / DataX는 같은 서비스라도 실행 환경이 다를 수 있다.
예를 들어 cluster 역할, workload type, image registry, storageClass, nodeSelector가 다를 수 있다.
```

이번 실험에서는 가장 단순하게 Pod 환경변수를 cluster별로 다르게 바꾼다.

---

## 가설

```text
원본 Deployment env:
- CLUSTER_ROLE=default
- WORKLOAD_TYPE=default

OverridePolicy 적용 후 기대 결과:
- twinx: CLUSTER_ROLE=twinx, WORKLOAD_TYPE=rendering
- edgex: CLUSTER_ROLE=edgex, WORKLOAD_TYPE=edge
- datax: CLUSTER_ROLE=datax, WORKLOAD_TYPE=data
```

---

## 매니페스트

```text
karmada/manifests/demo-override-env/
  00-namespace.yaml
  10-deployment.yaml
  20-service.yaml
  30-propagation-policy.yaml
  40-override-policy.yaml
```

핵심 policy:

```yaml
overrideRules:
  - targetCluster:
      clusterNames:
        - twinx
    overriders:
      plaintext:
        - path: /spec/template/spec/containers/0/env/0/value
          operator: replace
          value: twinx
        - path: /spec/template/spec/containers/0/env/1/value
          operator: replace
          value: rendering
```

---

## 실행 명령

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-override-env/
```

실제 출력:

```text
namespace/demo-override created
deployment.apps/demo-override-nginx created
service/demo-override-nginx created
propagationpolicy.policy.karmada.io/demo-override-nginx-policy created
overridepolicy.policy.karmada.io/demo-override-nginx-env created
```

---

## 확인 명령

Karmada API Server:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get propagationpolicy -n demo-override
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get overridepolicy -n demo-override
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-override -o wide
```

member cluster:

```bash
for c in twinx edgex datax; do
  echo "--- $c"
  kubectl --context kind-$c get deploy demo-override-nginx -n demo-override
  kubectl --context kind-$c get pods -n demo-override
  kubectl --context kind-$c get deploy demo-override-nginx -n demo-override \
    -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}'
 done
```

Pod 내부 env 확인:

```bash
for c in twinx edgex datax; do
  echo "--- $c"
  pod=$(kubectl --context kind-$c get pod -n demo-override \
    -l app=demo-override-nginx -o jsonpath='{.items[0].metadata.name}')
  kubectl --context kind-$c exec -n demo-override "$pod" -- \
    printenv CLUSTER_ROLE WORKLOAD_TYPE
 done
```

---

## 기대 결과

| cluster | 기대 Deployment replicas | CLUSTER_ROLE | WORKLOAD_TYPE |
| --- | --- | --- | --- |
| twinx | 1 | twinx | rendering |
| edgex | 1 | edgex | edge |
| datax | 1 | datax | data |

---

## 실제 결과

```text
Karmada policy:
- propagationpolicy.policy.karmada.io/demo-override-nginx-policy created
- overridepolicy.policy.karmada.io/demo-override-nginx-env created

Karmada ResourceBinding 최종 상태:
- demo-override-nginx-deployment: SCHEDULED=True, FULLYAPPLIED=True
- demo-override-nginx-service: SCHEDULED=True, FULLYAPPLIED=True

Karmada ResourceBinding replica 배치:
- datax replicas=1
- edgex replicas=1
- twinx replicas=1

member cluster 실제 Deployment/Pod 상태:
- twinx: demo-override-nginx Deployment 1/1, Pod Running 1개
- edgex: demo-override-nginx Deployment 1/1, Pod Running 1개
- datax: demo-override-nginx Deployment 1/1, Pod Running 1개
```

member cluster Deployment env:

```text
--- twinx
CLUSTER_ROLE=twinx
WORKLOAD_TYPE=rendering

--- edgex
CLUSTER_ROLE=edgex
WORKLOAD_TYPE=edge

--- datax
CLUSTER_ROLE=datax
WORKLOAD_TYPE=data
```

Pod 내부 `printenv` 결과:

```text
--- twinx
twinx
rendering

--- edgex
edgex
edge

--- datax
datax
data
```

Work 확인:

```text
Karmada API Server에서 works.work.karmada.io 리소스 확인 가능:
- karmada-es-twinx: Namespace / Deployment / Service Applied=True
- karmada-es-edgex: Namespace / Deployment / Service Applied=True
- karmada-es-datax: Namespace / Deployment / Service Applied=True
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 판단 |
| --- | --- | --- | --- |
| twinx env override | twinx/rendering | twinx/rendering | 성공 |
| edgex env override | edgex/edge | edgex/edge | 성공 |
| datax env override | datax/data | datax/data | 성공 |
| replica 분산 | 각 cluster 1개 | 각 cluster 1개 | 성공 |
| ResourceBinding 상태 | SCHEDULED=True, FULLYAPPLIED=True | SCHEDULED=True, FULLYAPPLIED=True | 성공 |

---

## 문제/에러

새로운 적용 실패는 없음.

관찰 사항:

```text
kind-tower host cluster API에서 `kubectl --context kind-tower get work -A`를 실행하면 work 리소스가 없다고 나온다.
works.work.karmada.io는 Karmada API Server kubeconfig로 조회해야 한다.
```

확인 명령:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get work -A
```

이번에도 `demo-override` namespace는 twinx/edgex/datax 모두에 생성되었다. 이 동작은 실험 02에서 확인한 namespace 자동 생성 패턴과 동일하다.

---

## ScaleX-POD에 주는 의미

이 실험으로 확인한 점:

```text
Karmada OverridePolicy의 plaintext overrider로 member cluster별 YAML 일부를 다르게 바꿀 수 있다.
```

ScaleX-POD에서 사용할 수 있는 패턴:

```text
하나의 공통 Deployment YAML 유지
+ Karmada OverridePolicy로 TwinX / EdgeX / DataX별 차이만 분리
```

예상 활용:

- TwinX 전용 image registry
- EdgeX 전용 env / nodeSelector / toleration
- DataX 전용 storageClass / PVC 설정
- cluster별 sidecar 또는 command 차이

---

## 다음 액션

- failover/taint 실험
- cluster별 image registry override 실험
- storageClass override 실험
