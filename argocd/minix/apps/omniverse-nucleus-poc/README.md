# Omniverse Nucleus StatefulSet PoC

이 앱은 실제 NVIDIA Omniverse Nucleus 이미지를 배포하기 전, ArgoCD가 `StatefulSet + Rook-Ceph RBD PVC + Service` 구조를 정상적으로 만들 수 있는지 검증하기 위한 PoC이다.

## 현재 범위

- 실제 Nucleus 이미지 사용 전 단계
- `rook-ceph-block` RBD StorageClass 사용
- `volumeClaimTemplates`로 Pod 전용 PVC 생성
- Nucleus DATA_ROOT 후보 경로 `/var/lib/omni/nucleus-data`에 PVC 마운트
- 컨테이너는 임시 `python:3.12-alpine` hold/web container 사용

## 다음 단계

NGC Enterprise Nucleus compose artifact 확보 후 다음 항목을 교체한다.

- image
- command/args
- env / nucleus-stack.env
- secrets
- exposed ports
- readiness/liveness probe

## 확인 명령

```bash
kubectl -n omniverse get sts,pvc,pod,svc
kubectl -n omniverse logs sts/omniverse-nucleus
kubectl -n omniverse port-forward svc/omniverse-nucleus 8080:8080
```

브라우저 또는 curl:

```bash
curl http://127.0.0.1:8080/
```
