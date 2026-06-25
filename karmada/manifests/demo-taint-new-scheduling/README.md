# demo-taint-new-scheduling 실험

이 실험은 `twinx` Cluster에 taint가 이미 있는 상태에서 새 workload를 만들면 Karmada scheduler가 `twinx`를 제외하는지 확인한다.

## 전제 조건

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config patch cluster twinx --type merge \
  -p '{"spec":{"taints":[{"key":"scalex.io/maintenance","value":"true","effect":"NoExecute"}]}}'
```

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-taint-new-scheduling/
```

## 확인

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-taint-new -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-taint-new demo-taint-new-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}'
```


## 확인된 결과

```text
- twinx: 배치되지 않음
- edgex: replicas=1
- datax: replicas=2
```

`twinx`에 taint가 있고 policy에 `clusterTolerations`가 없으면 새 workload는 `twinx`를 회피했다.
