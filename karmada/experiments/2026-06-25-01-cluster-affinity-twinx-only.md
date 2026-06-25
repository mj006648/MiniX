# 실험 01. clusterAffinity labelSelector로 TwinX에만 배포

## 목적

Karmada `PropagationPolicy`와 `ClusterPropagationPolicy`의 `clusterAffinity.labelSelector`를 사용해 특정 역할 label을 가진 cluster에만 리소스를 전파할 수 있는지 확인한다.

ScaleX-POD 기준 의미:

```text
TwinX 전용 workload는 TwinX에만 배포
EdgeX/DataX에는 배포하지 않음
```

이번 실험에서는 `twinx` cluster에만 다음 label이 있다.

```text
scalex.io/role=gpu-render
```

따라서 `labelSelector.matchLabels.scalex.io/role=gpu-render`를 사용하면 `twinx`만 선택되어야 한다.

---

## 사전 상태

실험 00에서 이미 다음 kind/Karmada 환경이 준비되어 있다.

```text
kind-tower  = Karmada control plane
kind-twinx  = member cluster, scalex.io/role=gpu-render
kind-edgex  = member cluster, scalex.io/role=edge-gpu
kind-datax  = member cluster, scalex.io/role=data
```

확인 명령:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusters --show-labels
```

---

## 가설

```text
demo-twinx namespace, Deployment, Service는 twinx에만 생성된다.
edgex/datax에는 demo-twinx namespace가 생성되지 않는다.
```

---

## 매니페스트

```text
karmada/manifests/demo-twinx-only/
  00-namespace.yaml
  01-cluster-propagation-policy-namespace.yaml
  10-deployment.yaml
  20-service.yaml
  30-propagation-policy.yaml
```

핵심 정책:

```yaml
placement:
  clusterAffinity:
    labelSelector:
      matchLabels:
        scalex.io/role: gpu-render
```

---

## 실행 명령

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-twinx-only/
```

---

## 확인 명령

Karmada API Server:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get ns demo-twinx
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusterpropagationpolicy demo-twinx-namespace-policy
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get propagationpolicy -n demo-twinx
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-twinx -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusterresourcebinding demo-twinx -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get work -A | grep demo-twinx
```

member cluster:

```bash
kubectl --context kind-twinx get all -n demo-twinx
kubectl --context kind-edgex get ns demo-twinx
kubectl --context kind-datax get ns demo-twinx
```

---

## 기대 결과

| 대상 | 기대 결과 |
| --- | --- |
| Karmada API Server | `demo-twinx` namespace, Deployment, Service, 정책 생성 |
| twinx | `demo-twinx-nginx` Deployment/Pod/Service 생성 |
| edgex | `demo-twinx` namespace 없음 |
| datax | `demo-twinx` namespace 없음 |

---

## 실제 결과

```text
적용 결과:
- namespace/demo-twinx created
- clusterpropagationpolicy.policy.karmada.io/demo-twinx-namespace-policy created
- deployment.apps/demo-twinx-nginx created
- service/demo-twinx-nginx created
- propagationpolicy.policy.karmada.io/demo-twinx-nginx-policy created

cluster label 상태:
- twinx: scalex.io/role=gpu-render, scalex.io/pool=gpu
- edgex: scalex.io/role=edge-gpu, scalex.io/pool=gpu, scalex.io/location=edge
- datax: scalex.io/role=data, scalex.io/storage=ssd, scalex.io/workload=data

Karmada scheduling 결과:
- demo-twinx-nginx Deployment ResourceBinding spec.clusters = twinx only
- demo-twinx-nginx Service ResourceBinding spec.clusters = twinx only
- demo-twinx Namespace ClusterResourceBinding spec.clusters = twinx only

member cluster 실제 workload 상태:
- twinx: demo-twinx-nginx Deployment 1/1, Pod Running 1개, Service 생성됨
- edgex: demo-twinx namespace는 존재하지만 Deployment/Service/Pod 없음
- datax: demo-twinx namespace는 존재하지만 Deployment/Service/Pod 없음

예상과 달랐던 점:
- Namespace demo-twinx는 twinx에만 생기길 기대했지만 edgex/datax에도 생성됨.
- 하지만 Deployment/Service/Pod는 twinx에만 생성됨.
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 성공 여부 |
| --- | --- | --- | --- |
| labelSelector 대상 선택 | twinx만 선택 | Deployment/Service ResourceBinding은 twinx만 선택 | 성공 |
| twinx 배포 | Pod Running | `demo-twinx-nginx` Pod 1개 Running | 성공 |
| edgex workload 제외 | Deployment/Service/Pod 없음 | namespace는 있지만 workload 없음 | 부분 성공 |
| datax workload 제외 | Deployment/Service/Pod 없음 | namespace는 있지만 workload 없음 | 부분 성공 |
| namespace 제외 | edgex/datax에 namespace 없음 | edgex/datax에도 namespace 생성됨 | 실패/관찰 이슈 |

---

## 문제/에러

### 문제 1. Namespace가 edgex/datax에도 생성됨

- 발생 단계: demo-twinx-only 매니페스트 적용 후 member cluster 확인
- 기대 결과:

```text
scalex.io/role=gpu-render label을 가진 twinx에만 demo-twinx namespace 생성
edgex/datax에는 demo-twinx namespace 없음
```

- 실제 결과:

```text
twinx: demo-twinx namespace 있음, Deployment/Service/Pod 있음
edgex: demo-twinx namespace 있음, Deployment/Service/Pod 없음
datax: demo-twinx namespace 있음, Deployment/Service/Pod 없음
```

- Karmada 객체 상태:

```text
demo-twinx-namespace ClusterResourceBinding spec.clusters:
- twinx

demo-twinx-nginx Deployment ResourceBinding spec.clusters:
- twinx

demo-twinx-nginx Service ResourceBinding spec.clusters:
- twinx
```

- Work 상태:

```text
karmada-es-twinx   demo-twinx-7fc4858b4c       Namespace   True
karmada-es-edgex   demo-twinx-7fc4858b4c       Namespace   True
karmada-es-datax   demo-twinx-7fc4858b4c       Namespace   True
karmada-es-twinx   demo-twinx-nginx-...        Deployment  True
karmada-es-twinx   demo-twinx-nginx-...        Service     True
```

- 관찰:
  - Karmada 스케줄러의 binding 결과는 `twinx`만 선택한 것으로 보인다.
  - Deployment/Service는 정확히 twinx에만 생성되었다.
  - Namespace Work만 edgex/datax에도 생성되었다.
  - edgex/datax namespace에는 workload가 없다.

- 원인 추정:
  - Karmada가 namespaced resource 전파 과정에서 namespace를 보조적으로 생성했을 가능성.
  - 또는 Namespace 같은 cluster-scoped resource의 Work 정리/상태 집계와 관련된 별도 동작일 가능성.
  - 실험 00에서도 Namespace ClusterResourceBinding 상태가 `FULLYAPPLIED=False`로 남는 관찰 이슈가 있었다.

- 영향:
  - workload 배치 정책 검증에는 성공했다.
  - 하지만 namespace 자체까지 엄격히 특정 cluster에만 존재해야 하는 요구사항이라면 추가 검증이 필요하다.

- 다음 확인 후보:
  - Namespace ClusterPropagationPolicy 없이 namespaced Deployment/Service만 전파하면 namespace가 어떻게 생성되는지 확인
  - Namespace를 사전에 member cluster에 만들지 않고 Karmada가 자동 생성하는 동작 확인
  - Karmada upstream issue 검색/작성 후보로 남김


---

## ScaleX-POD에 주는 의미

이 실험으로 확인한 점:

```text
clusterAffinity.labelSelector로 workload를 특정 역할 cluster에만 배치할 수 있다.
이번 실험에서는 Deployment/Service/Pod가 twinx에만 생성되었다.
```

다만 namespace는 edgex/datax에도 생성되었으므로, namespace 격리까지 필요한 경우 추가 실험이 필요하다.

ScaleX-POD에서 다음 정책 패턴을 사용할 수 있다.

```text
TwinX 전용 GPU rendering workload
  -> scalex.io/role=gpu-render cluster에만 배포

EdgeX 전용 edge workload
  -> scalex.io/role=edge-gpu cluster에만 배포

DataX 전용 data workload
  -> scalex.io/role=data cluster에만 배포
```

---

## 다음 액션

- Namespace가 edgex/datax에도 생성된 이유를 추가 실험으로 확인한다.
- EdgeX-only / DataX-only도 같은 방식으로 검증한다.
- 이후 replica weight 분산 실험으로 넘어간다.
- GitHub issue 후보로 남길 수 있도록 관련 Karmada 객체 YAML과 controller-manager 로그를 보존한다.
