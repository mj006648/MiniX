# 실험 03. weighted replicaScheduling으로 replica 가중 분산

## 목적

Karmada `PropagationPolicy`의 `replicaScheduling`을 사용해 하나의 Deployment replica를 여러 member cluster에 가중치 기반으로 나눠 배치할 수 있는지 확인한다.

ScaleX-POD 기준 의미:

```text
TwinX는 GPU/렌더링 용량이 크므로 더 많은 replica를 배치한다.
EdgeX는 edge 용도라 적은 replica만 배치한다.
DataX는 data workload 중심이라 일반 web replica는 적게 배치한다.
```

---

## 가설

```text
원본 Deployment replicas=6
weight twinx:edgex:datax = 4:1:1

기대 배치:
- twinx: 4 replicas
- edgex: 1 replica
- datax: 1 replica
```

---

## 매니페스트

```text
karmada/manifests/demo-weighted-replicas/
  00-namespace.yaml
  10-deployment.yaml
  20-service.yaml
  30-propagation-policy.yaml
```

핵심 policy:

```yaml
replicaScheduling:
  replicaSchedulingType: Divided
  replicaDivisionPreference: Weighted
  weightPreference:
    staticWeightList:
      - targetCluster:
          clusterNames:
            - twinx
        weight: 4
      - targetCluster:
          clusterNames:
            - edgex
        weight: 1
      - targetCluster:
          clusterNames:
            - datax
        weight: 1
```

---

## 실행 명령

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-weighted-replicas/
```

---

## 확인 명령

Karmada API Server:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get propagationpolicy -n demo-weighted
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-weighted -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-weighted demo-weighted-nginx-deployment -o yaml
```

member cluster:

```bash
for c in twinx edgex datax; do
  echo "--- $c"
  kubectl --context kind-$c get deploy demo-weighted-nginx -n demo-weighted
  kubectl --context kind-$c get pods -n demo-weighted
 done
```

---

## 기대 결과

| cluster | 기대 replica |
| --- | --- |
| twinx | 4 |
| edgex | 1 |
| datax | 1 |

---

## 실제 결과

```text
적용 결과:
- namespace/demo-weighted created
- deployment.apps/demo-weighted-nginx created
- service/demo-weighted-nginx created
- propagationpolicy.policy.karmada.io/demo-weighted-nginx-policy created

Karmada ResourceBinding 최종 상태:
- demo-weighted-nginx-deployment: SCHEDULED=True, FULLYAPPLIED=True
- demo-weighted-nginx-service: SCHEDULED=True, FULLYAPPLIED=True

Karmada ResourceBinding replica 배치:
- datax replicas=1
- edgex replicas=1
- twinx replicas=4

member cluster 실제 상태:
- twinx: demo-weighted-nginx Deployment 4/4, Pod Running 4개
- edgex: demo-weighted-nginx Deployment 1/1, Pod Running 1개
- datax: demo-weighted-nginx Deployment 1/1, Pod Running 1개

관찰:
- replicas=6, weight 4:1:1이 기대대로 4/1/1로 분산되었다.
- 이번에도 namespace demo-weighted는 twinx/edgex/datax 모두에 생성되었다.
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 판단 |
| --- | --- | --- | --- |
| ResourceBinding replica 배치 | twinx=4, edgex=1, datax=1 | twinx=4, edgex=1, datax=1 | 성공 |
| twinx 실제 Pod | 4개 Running | 4개 Running | 성공 |
| edgex 실제 Pod | 1개 Running | 1개 Running | 성공 |
| datax 실제 Pod | 1개 Running | 1개 Running | 성공 |

---

## 문제/에러

새로운 에러는 없음.

관찰 사항:

```text
Namespace demo-weighted는 twinx/edgex/datax 모두에 생성되었다.
```

이는 실험 02에서 확인한 namespace 자동 생성 동작과 같은 패턴이다. workload와 replica 수는 정책대로 정확히 분산되었다.

---

## ScaleX-POD에 주는 의미

이 실험으로 확인한 점:

```text
Karmada replicaScheduling의 Divided + Weighted 정책으로 replica를 cluster별 가중치에 따라 나눌 수 있다.
```

ScaleX-POD에서 다음 정책 패턴을 사용할 수 있다.

```text
용량이 큰 TwinX에 더 많은 replica 배치
EdgeX/DataX에는 적은 replica만 배치
추후 실제 GPU 수, CPU 수, cluster capacity에 맞춰 weight 조정
```

---

## 다음 액션

- OverridePolicy로 cluster별 env/image/storageClass 변경 실험
- failover/taint 실험
