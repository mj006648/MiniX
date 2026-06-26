# demo-noexecute-eviction

수동 `NoExecute` cluster taint가 기존 ResourceBinding replica를 실제로 eviction/re-schedule하는지 확인하기 위한 Karmada 실험 매니페스트다.

## 구성

```text
00-namespace.yaml
10-deployment.yaml
20-service.yaml
30-propagation-policy.yaml
```

## 의도

- `replicas: 3`
- `twinx`, `edgex`, `datax`에 weight 1:1:1
- `twinx`에 `NoExecute` taint를 수동 추가
- `twinx` replica가 `edgex`/`datax`로 이동하는지 확인

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-noexecute-eviction/
```

## 실험 결과 요약

- baseline: `twinx=1`, `edgex=1`, `datax=1`
- `twinx`에 수동 `NoExecute` taint 추가 후: `edgex=2`, `datax=1`, `twinx=0`
- taint 제거 후에도 자동으로 `twinx`까지 재균형되지는 않았다.
- 자세한 기록: `karmada/experiments/2026-06-26-08-noexecute-eviction.md`
