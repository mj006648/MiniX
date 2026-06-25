# demo-twinx-auto-namespace 실험

이 실험은 Namespace 전파용 `ClusterPropagationPolicy`를 만들지 않고, namespaced Deployment/Service만 `PropagationPolicy`로 전파했을 때 Karmada가 namespace를 어떻게 처리하는지 확인한다.

## 목적

실험 01에서 Deployment/Service/Pod는 `twinx`에만 생성되었지만, Namespace는 `edgex`와 `datax`에도 생성되었다.

이번 실험에서는 namespace용 ClusterPropagationPolicy를 제거해서 다음을 구분한다.

```text
1. Karmada가 namespaced workload 전파 과정에서 namespace를 자동 생성하는가?
2. 자동 생성한다면 선택된 cluster에만 생성하는가, 모든 member cluster에 생성하는가?
```

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-twinx-auto-namespace/
```

## 기대 결과

```text
Deployment/Service/Pod: twinx에만 생성
Namespace: 이번 실험의 관찰 대상
```
