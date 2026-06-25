# demo-failover-taint 실험

이 실험은 Karmada cluster taint와 기존 ResourceBinding의 failover 동작을 확인한다.

## 목표

1. `twinx`, `edgex`, `datax`에 `demo-failover-nginx`를 1개씩 배치한다.
2. Karmada Cluster 리소스의 `twinx`에 `NoExecute` taint를 추가한다.
3. 이미 배치된 workload가 자동으로 이동하는지 확인한다.
4. taint를 제거해 lab 상태를 원복한다.

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-failover-taint/
```

## twinx taint 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config patch cluster twinx --type merge \
  -p '{"spec":{"taints":[{"key":"scalex.io/maintenance","value":"true","effect":"NoExecute"}]}}'
```

## twinx taint 제거

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config patch cluster twinx --type json \
  -p '[{"op":"remove","path":"/spec/taints"}]'
```

## 확인

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-failover -o wide

for c in twinx edgex datax; do
  echo "--- $c"
  kubectl --context kind-$c get deploy,pods -n demo-failover
 done
```

## 확인된 결과

```text
- baseline: twinx=1, edgex=1, datax=1
- twinx NoExecute taint 후: 기존 ResourceBinding은 자동으로 twinx를 제외하지 않음
- gracefulEvictionTasks: 비어 있음
```

따라서 기존 workload 즉시 이동은 별도 failover/rebalance 실험이 더 필요하다.
