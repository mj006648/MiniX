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

## 2026-07-09 실행 결과

### 성공한 것

- MiniX ArgoCD child Application omniverse-nucleus-poc 생성 확인
- ArgoCD 상태: Synced / Healthy
- StatefulSet omniverse-nucleus: 1/1 Ready
- PVC nucleus-data-omniverse-nucleus-0: rook-ceph-block, 10Gi, Bound
- Pod omniverse-nucleus-0: com1 노드에서 Running
- PVC 마운트 경로 /var/lib/omni/nucleus-data에 marker 파일 생성 확인
- Pod 내부에서 localhost와 Service DNS 양쪽 HTTP 응답 확인

검증 출력 요약:



### 발견한 문제와 해결

1. ArgoCD repo-server가 MiniX repo를 읽지 못함
   - 원인: trident-ui/streamlit/bin/python3가 /usr/bin/python3를 가리키는 out-of-bounds symlink였다.
   - 해결: trident-ui/streamlit 가상환경과 trident-ui/__pycache__를 Git 추적에서 제거하고 .gitignore에 추가했다.
   - 관련 커밋: 00b772a6 chore: remove tracked Streamlit virtualenv

2. 신규 Pod가 Pending에 머묾
   - 원인: kube-scheduler-master가 CrashLoopBackOff 상태였고, lease 갱신 시 API Server timeout이 발생했다.
   - 해결: 운영 최종안은 아니지만 PoC 검증을 위해 StatefulSet template에 임시 nodeName: com1을 지정했다.
   - 관련 커밋: 032fe33d test: pin Nucleus PoC during scheduler outage

### 남은 작업

- kube-scheduler / kube-controller-manager CrashLoop 원인 복구
- scheduler 복구 후 10-statefulset.yaml에서 nodeName: com1 제거
- NVIDIA NGC Enterprise Nucleus artifact 확보
- placeholder python container를 실제 Nucleus 이미지/compose 구성/secret/env/probe로 교체
- 실제 운영 전에 Nucleus 데이터 백업/복구 절차 확정
