# demo-weighted-replicas 실험

이 실험은 Karmada `replicaScheduling`의 `Divided + Weighted` 동작을 확인한다.

## 목표

```text
replicas=6
weight twinx:edgex:datax = 4:1:1

기대 결과:
- twinx: 4 replicas
- edgex: 1 replica
- datax: 1 replica
```

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-weighted-replicas/
```

## 확인

```bash
for c in twinx edgex datax; do
  kubectl --context kind-$c get deploy demo-weighted-nginx -n demo-weighted
  kubectl --context kind-$c get pods -n demo-weighted
 done
```
