# demo-failover-enabled 실험

이 실험은 `karmada-controller-manager`에 failover 관련 옵션을 활성화한 뒤, 실제 `twinx` cluster 장애에서 기존 workload가 이동하는지 확인한다.

## controller-manager 실험 옵션

```text
--feature-gates=Failover=true
--enable-no-execute-taint-eviction=true
--no-execute-taint-eviction-purge-mode=Directly
```

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-failover-enabled/
```

## 장애 시뮬레이션

```bash
docker stop twinx-control-plane
```

## 복구

```bash
docker start twinx-control-plane
```

## 확인

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusters -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-failover-enabled -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get rb -n demo-failover-enabled demo-failover-enabled-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}'
```

## 확인된 결과

```text
- baseline: datax=1, edgex=1, twinx=1
- twinx 장애 감지: READY=False, ClusterNotReachable
- 자동 taint: cluster.karmada.io/not-ready:NoSchedule
- 약 9분 관찰 동안 ResourceBinding은 datax=1, edgex=1, twinx=1 유지
- gracefulEvictionTasks 비어 있음
```

현재 옵션 조합만으로는 실제 cluster 장애에서 기존 workload 자동 이동이 확인되지 않았다.
다음은 NoExecute eviction 단독 실험 또는 WorkloadRebalancer 실험이 필요하다.
