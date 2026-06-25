# demo-override-env 실험

이 실험은 Karmada `OverridePolicy`의 cluster별 환경변수 override 동작을 확인한다.

## 목표

같은 Deployment를 `twinx`, `edgex`, `datax`에 배포하되, member cluster별로 Pod 환경변수를 다르게 만든다.

| cluster | CLUSTER_ROLE | WORKLOAD_TYPE |
| --- | --- | --- |
| twinx | twinx | rendering |
| edgex | edgex | edge |
| datax | datax | data |

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-override-env/
```

## 확인

```bash
for c in twinx edgex datax; do
  echo "--- $c"
  kubectl --context kind-$c get deploy demo-override-nginx -n demo-override
  kubectl --context kind-$c get pods -n demo-override
  kubectl --context kind-$c get deploy demo-override-nginx -n demo-override \
    -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{"\n"}{end}'
 done
```

## 확인된 결과

```text
- twinx: CLUSTER_ROLE=twinx, WORKLOAD_TYPE=rendering
- edgex: CLUSTER_ROLE=edgex, WORKLOAD_TYPE=edge
- datax: CLUSTER_ROLE=datax, WORKLOAD_TYPE=data
```
