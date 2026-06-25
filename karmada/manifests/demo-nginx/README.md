# demo-nginx 전파 실험

이 디렉터리는 Karmada의 가장 기본적인 전파 기능을 확인하기 위한 예제 매니페스트다.

## 포함 리소스

| 파일 | 설명 |
| --- | --- |
| `00-namespace.yaml` | demo 네임스페이스 생성 |
| `01-cluster-propagation-policy-namespace.yaml` | demo 네임스페이스를 twinx/edgex/datax로 전파 |
| `10-deployment.yaml` | nginx Deployment 생성 |
| `20-service.yaml` | nginx ClusterIP Service 생성 |
| `30-propagation-policy.yaml` | twinx/edgex/datax로 리소스 전파 |

## 적용 대상

이 YAML은 일반 member cluster가 아니라 **Karmada API server**에 적용해야 한다.

예:

```bash
kubectl --kubeconfig ~/.kube/karmada-apiserver.config apply -f karmada/manifests/demo-nginx/
```

## 확인

```bash
kubectl --context kind-twinx get all -n demo
kubectl --context kind-edgex get all -n demo
kubectl --context kind-datax get all -n demo
```

예상 결과:

- `demo-nginx` Deployment가 twinx/edgex/datax에 생성된다.
- Deployment replica 3개가 `PropagationPolicy`에 따라 세 클러스터로 나뉘어 배치된다.
