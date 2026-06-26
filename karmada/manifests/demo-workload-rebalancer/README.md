# demo-workload-rebalancer

`NoExecute` eviction 후 `twinx` taint를 제거해도 자동 재균형되지 않는 workload를 `WorkloadRebalancer`로 다시 분산할 수 있는지 확인하기 위한 Karmada 실험 매니페스트다.

## 대상

```text
namespace: demo-noexecute-eviction
workload : Deployment/demo-noexecute-eviction-nginx
```

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-workload-rebalancer/
```

## 결과 요약

- 적용 전: `edgex=2`, `datax=1`, `twinx=0`
- 적용 후: `twinx=1`, `edgex=1`, `datax=1`
- `WorkloadRebalancer.status.observedWorkloads[0].result`는 `Successful`

## 반복 실험 주의

이 매니페스트는 `ttlSecondsAfterFinished`를 설정하지 않는다.
완료된 `WorkloadRebalancer`가 남으므로 다시 실행하려면 기존 리소스를 삭제하거나 새 이름을 사용한다.
