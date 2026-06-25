# demo-taint-tolerated 실험

이 실험은 `twinx` Cluster에 taint가 있는 상태에서도 `clusterTolerations`를 가진 workload가 `twinx`에 배치될 수 있는지 확인한다.

## 전제 조건

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config patch cluster twinx --type merge \
  -p '{"spec":{"taints":[{"key":"scalex.io/maintenance","value":"true","effect":"NoExecute"}]}}'
```

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-taint-tolerated/
```

## 핵심 설정

```yaml
placement:
  clusterTolerations:
    - key: scalex.io/maintenance
      operator: Equal
      value: "true"
      effect: NoExecute
```


## 확인된 결과

```text
- twinx: replicas=1
- edgex: replicas=1
- datax: replicas=1
```

`twinx`에 taint가 있어도 policy에 맞는 `clusterTolerations`가 있으면 `twinx` 배치가 가능했다.
