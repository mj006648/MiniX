# demo-cluster-failover 실험

이 실험은 `twinx` kind cluster 자체를 중지해서 Karmada가 실제 member cluster 장애를 어떻게 감지하고 처리하는지 확인한다.

## 목표

1. `demo-cluster-failover-nginx`를 `twinx`, `edgex`, `datax`에 1개씩 배치한다.
2. `docker stop twinx-control-plane`으로 `twinx` API를 중단한다.
3. Karmada Cluster Ready 상태와 ResourceBinding 변화, member cluster 배치를 관찰한다.
4. `docker start twinx-control-plane`으로 복구한다.

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-cluster-failover/
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
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-cluster-failover -o wide
kubectl --kubeconfig ~/.kube/karmada-apiserver.config get resourcebinding -n demo-cluster-failover demo-cluster-failover-nginx-deployment \
  -o jsonpath='{range .spec.clusters[*]}{.name}{" replicas="}{.replicas}{"\n"}{end}'
```

## 확인된 결과

```text
- twinx 중지 후 Karmada Cluster READY=False, reason=ClusterNotReachable
- 자동 taint: cluster.karmada.io/not-ready:NoSchedule
- 약 7분 관찰 동안 기존 ResourceBinding은 datax=1, edgex=1, twinx=1 유지
- gracefulEvictionTasks는 비어 있음
- twinx 복구 후 READY=True, taint 제거
```

현재 설치 옵션에서는 `failover.cluster` policy만으로 기존 workload 자동 이동은 확인되지 않았다.
다음 실험에서는 `Failover` feature gate와 `NoExecute` eviction 옵션을 확인한다.
