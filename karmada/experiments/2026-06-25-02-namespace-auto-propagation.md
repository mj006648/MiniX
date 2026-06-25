# 실험 02. Namespace ClusterPropagationPolicy 없이 twinx-only workload 전파

## 목적

실험 01에서 `clusterAffinity.labelSelector`로 workload는 `twinx`에만 배포되었지만, namespace는 `edgex`와 `datax`에도 생성되었다.

이번 실험은 Namespace 전파용 `ClusterPropagationPolicy`를 만들지 않고, namespaced Deployment/Service만 전파했을 때 namespace가 어디에 생성되는지 확인한다.

---

## 배경

실험 01 결과:

```text
Deployment/Service/Pod: twinx에만 생성됨
Namespace demo-twinx: twinx/edgex/datax 모두 생성됨
```

Karmada 객체 기준:

```text
demo-twinx Namespace ClusterResourceBinding spec.clusters = twinx only
Deployment ResourceBinding spec.clusters = twinx only
Service ResourceBinding spec.clusters = twinx only
```

그런데 Work 기준으로는 Namespace Work가 `edgex`, `datax`에도 생성되었다.

---

## 가설

### 가설 A. Karmada 자동 namespace 생성 동작

Karmada가 namespaced resource를 member cluster에 적용하기 위해 namespace를 자동 생성한다.

이 경우 이번 실험에서도 namespace가 생성될 수 있다.

### 가설 B. 실험 01의 Namespace ClusterPropagationPolicy 처리 이슈

Namespace 전파용 ClusterPropagationPolicy와 workload 전파 정책이 동시에 적용되면서 Work가 예상보다 넓게 생성되었을 수 있다.

이 경우 이번 실험에서는 namespace가 `twinx`에만 생성될 가능성이 있다.

---

## 매니페스트

```text
karmada/manifests/demo-twinx-auto-namespace/
  00-namespace.yaml
  10-deployment.yaml
  20-service.yaml
  30-propagation-policy.yaml
```

중요한 차이:

```text
Namespace용 ClusterPropagationPolicy를 만들지 않는다.
Deployment/Service만 PropagationPolicy로 twinx 선택한다.
```

핵심 policy:

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
  -f karmada/manifests/demo-twinx-auto-namespace/
```

---

## 확인 명령

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get propagationpolicy -n demo-twinx-auto
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-twinx-auto -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusterresourcebinding | grep demo-twinx-auto || true
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get work -A | grep demo-twinx-auto || true

kubectl --context kind-twinx get all -n demo-twinx-auto
kubectl --context kind-edgex get ns demo-twinx-auto
kubectl --context kind-datax get ns demo-twinx-auto
```

---

## 기대 결과

| 대상 | 기대/관찰 포인트 |
| --- | --- |
| twinx | Deployment/Service/Pod 생성 |
| edgex | workload 없음. namespace 생성 여부 관찰 |
| datax | workload 없음. namespace 생성 여부 관찰 |
| Karmada | ResourceBinding은 twinx만 선택해야 함 |

---

## 실제 결과

```text
적용 결과:
- namespace/demo-twinx-auto created
- deployment.apps/demo-twinx-auto-nginx created
- service/demo-twinx-auto-nginx created
- propagationpolicy.policy.karmada.io/demo-twinx-auto-nginx-policy created

Karmada ResourceBinding:
- demo-twinx-auto-nginx-deployment: clusters=twinx, FULLYAPPLIED=True
- demo-twinx-auto-nginx-service: clusters=twinx, FULLYAPPLIED=True

Karmada ClusterResourceBinding:
- demo-twinx-auto namespace에 대한 ClusterResourceBinding 없음
- Namespace용 ClusterPropagationPolicy를 만들지 않았기 때문에 예상된 상태

Karmada Work:
- karmada-es-twinx: Namespace, Deployment, Service Work 생성
- karmada-es-edgex: Namespace Work 생성
- karmada-es-datax: Namespace Work 생성

member cluster 실제 상태:
- twinx: demo-twinx-auto namespace 있음, Deployment/Service/Pod 있음
- edgex: demo-twinx-auto namespace 있음, workload 없음
- datax: demo-twinx-auto namespace 있음, workload 없음
```

---

## 성공/실패 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 판단 |
| --- | --- | --- | --- |
| workload twinx-only | twinx에만 Pod 생성 | twinx에만 Deployment/Service/Pod 생성 | 성공 |
| edgex namespace | 관찰 대상 | namespace 생성됨, workload 없음 | 관찰됨 |
| datax namespace | 관찰 대상 | namespace 생성됨, workload 없음 | 관찰됨 |
| ResourceBinding | twinx only | Deployment/Service 모두 twinx only | 성공 |
| Namespace 자동 생성 | 확인 필요 | ClusterResourceBinding 없이도 모든 member에 Namespace Work 생성 | 중요 관찰 |

---

## 문제/에러

### 관찰 1. Namespace용 정책이 없어도 모든 member cluster에 namespace가 생성됨

- 발생 단계: demo-twinx-auto-namespace 적용 후 Work/member cluster 확인
- 기대/질문:

```text
Namespace용 ClusterPropagationPolicy가 없으면 namespace는 어디에 생성되는가?
```

- 실제 결과:

```text
twinx: namespace 있음, workload 있음
edgex: namespace 있음, workload 없음
datax: namespace 있음, workload 없음
```

- Karmada 객체 상태:

```text
ResourceBinding:
- Deployment clusters=twinx, FULLYAPPLIED=True
- Service clusters=twinx, FULLYAPPLIED=True

ClusterResourceBinding:
- demo-twinx-auto namespace binding 없음

Work:
- Namespace Work가 twinx/edgex/datax 모두에 생성됨
- Deployment/Service Work는 twinx에만 생성됨
```

- 해석:
  - Karmada는 namespaced workload 전파 시 namespace를 보조적으로 생성하는 것으로 보인다.
  - 이 namespace 자동 생성은 이번 실험에서는 선택된 cluster인 `twinx`뿐 아니라 모든 member cluster에 발생했다.
  - workload 자체는 정책대로 `twinx`에만 갔다.

- 영향:
  - 역할별 workload 배치는 문제없이 가능하다.
  - namespace 존재 자체를 cluster별로 엄격하게 격리하고 싶다면 Karmada 기본 동작을 더 확인해야 한다.
  - GitOps/운영 관점에서는 빈 namespace가 다른 member cluster에 생기는 것을 허용할지 정책 결정이 필요하다.

- 후속 후보:
  - Karmada 공식 문서/issue에서 namespace auto propagation 동작 확인
  - upstream issue 또는 discussion으로 문의
  - namespace 자동 생성 범위를 제어할 수 있는 옵션이 있는지 확인


---

## ScaleX-POD에 주는 의미

이 실험은 ScaleX-POD에서 역할별 workload를 분리할 때 namespace 관리 전략을 정하는 데 중요하다.

확인한 점:

```text
workload 배치는 labelSelector로 충분히 제어 가능하다.
namespace는 workload 대상이 아닌 member cluster에도 자동 생성될 수 있다.
namespace까지 cluster별로 엄격하게 격리하려면 별도 전략 또는 Karmada 동작 확인이 필요하다.
```
