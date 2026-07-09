# Omniverse Nucleus StatefulSet PoC

이 앱은 실제 NVIDIA Omniverse Nucleus 이미지를 배포하기 전, ArgoCD가 `StatefulSet + Rook-Ceph RBD PVC + Service` 구조를 정상적으로 만들 수 있는지 검증하기 위한 PoC이다.

## 현재 범위

- 실제 Nucleus 이미지 사용 전 단계
- `rook-ceph-block` RBD StorageClass 사용
- `volumeClaimTemplates`로 Pod 전용 PVC 생성
- Nucleus DATA_ROOT 후보 경로 `/var/lib/omni/nucleus-data`에 PVC 마운트
- 컨테이너는 임시 `python:3.12-alpine` hold/web container 사용


## 현재 클러스터 주의사항

2026-07-09 기준 kube-scheduler-master가 CrashLoopBackOff 상태라 신규 Pod가 일반 scheduler 경로로 배치되지 않는다.
PoC에서는 RBD PVC 마운트와 StatefulSet 구조 검증을 먼저 하기 위해 임시로 nodeName: com1을 지정했다.

- 최종 운영 전에는 nodeName: com1을 제거해야 한다.
- kube-scheduler가 정상화되면 일반 scheduler가 node labels/taints/affinity 기준으로 Pod를 배치한다.

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
