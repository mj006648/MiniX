# demo-twinx-only clusterAffinity 실험

이 디렉터리는 Karmada `clusterAffinity.labelSelector`를 이용해 특정 역할 label을 가진 cluster에만 리소스를 전파하는 실험이다.

## 목표

```text
scalex.io/role=gpu-render cluster만 선택
=> twinx에만 배포
=> edgex/datax에는 배포되지 않음
```

## 포함 리소스

| 파일 | 설명 |
| --- | --- |
| `00-namespace.yaml` | `demo-twinx` 네임스페이스 생성 |
| `01-cluster-propagation-policy-namespace.yaml` | `demo-twinx` 네임스페이스를 `scalex.io/role=gpu-render` cluster로만 전파 |
| `10-deployment.yaml` | `demo-twinx-nginx` Deployment 생성 |
| `20-service.yaml` | `demo-twinx-nginx` Service 생성 |
| `30-propagation-policy.yaml` | Deployment/Service를 `scalex.io/role=gpu-render` cluster로만 전파 |

## 적용

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-twinx-only/
```

## 확인

```bash
kubectl --context kind-twinx get all -n demo-twinx
kubectl --context kind-edgex get ns demo-twinx
kubectl --context kind-datax get ns demo-twinx
```

예상 결과:

- `twinx`에는 `demo-twinx-nginx` Deployment/Pod/Service가 생성된다.
- `edgex`, `datax`에는 `demo-twinx` namespace가 없어야 한다.
