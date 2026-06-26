# demo-noexecute-toleration-scope

수동 `NoExecute` cluster taint의 영향 범위와 `clusterTolerations` 보호 동작을 비교하기 위한 Karmada 실험 매니페스트다.

## 구성

```text
demo-noexecute-unprotected: clusterTolerations 없음
demo-noexecute-protected  : scalex.io/eviction-test=protected:NoExecute toleration 있음
```

두 workload 모두 baseline은 `twinx`, `edgex`, `datax`에 1:1:1로 배치한다.

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply \
  -f karmada/manifests/demo-noexecute-toleration-scope/
```

## 실험 taint

```text
key: scalex.io/eviction-test
value: protected
effect: NoExecute
```

## 결과 요약

```text
unprotected:
  taint 전: twinx=1, edgex=1, datax=1
  taint 후: twinx=0, edgex=1, datax=2

protected:
  taint 전: twinx=1, edgex=1, datax=1
  taint 후: twinx=1, edgex=1, datax=1
```

결론:

```text
matching clusterTolerations가 있으면 NoExecute taint가 붙은 cluster에서도 workload가 유지된다.
```

자세한 기록: `karmada/experiments/2026-06-26-10-noexecute-toleration-scope.md`
