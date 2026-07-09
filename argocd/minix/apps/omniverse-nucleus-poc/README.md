# Omniverse Nucleus StatefulSet PoC

이 앱은 실제 NVIDIA Omniverse Nucleus 이미지를 배포하기 전, ArgoCD가 `StatefulSet + Rook-Ceph RBD PVC + Service` 구조를 정상적으로 만들 수 있는지 검증하기 위한 PoC이다.

## 현재 범위

- NVIDIA NGC `nvidia/omniverse/nucleus-compose-stack:2023.2.10` 기반 실제 Nucleus 서비스 사용
- Compose stack의 12개 서비스를 Kubernetes StatefulSet의 12개 컨테이너로 변환
- `rook-ceph-block` RBD StorageClass 사용
- `volumeClaimTemplates`로 Pod 전용 PVC 생성
- Nucleus DATA_ROOT `/var/lib/omni/nucleus-data`를 RBD PVC로 마운트
- `nvcr.io/nvidia/omniverse/*` 실제 Nucleus 이미지 사용


## 현재 클러스터 주의사항

2026-07-09 기준 kube-scheduler-master가 CrashLoopBackOff 상태라 신규 Pod가 일반 scheduler 경로로 배치되지 않는다.
PoC에서는 RBD PVC 마운트와 StatefulSet 구조 검증을 먼저 하기 위해 임시로 nodeName: com3을 지정했다. 처음에는 com1을 사용했지만 CPU request 여유가 부족해 Pod 생성이 반복 실패했고, com3의 allocatable 여유가 더 커서 변경했다.

- 최종 운영 전에는 nodeName: com3을 제거해야 한다.
- kube-scheduler가 정상화되면 일반 scheduler가 node labels/taints/affinity 기준으로 Pod를 배치한다.

## 다음 단계

현재는 NGC artifact를 확보했고 실제 이미지를 사용한다. 다음 항목은 아직 운영화 전 보완 대상이다.

- kube-scheduler 정상화 후 `nodeName: com1` 제거
- 운영 DNS/TLS 적용 여부 결정
- Nucleus admin/service password를 OpenBao/External-Secrets로 이관
- readiness/liveness probe 추가
- PVC 용량을 운영 크기로 확장

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
   - 해결: 운영 최종안은 아니지만 PoC 검증을 위해 StatefulSet template에 임시 nodeName: com3을 지정했다.
   - 관련 커밋: 032fe33d test: pin Nucleus PoC during scheduler outage


3. `nucleus-api`가 `nucleus-resolver-cache`에 연결하지 못하고 CrashLoopBackOff
   - 원인: Kubernetes Service는 기본적으로 Ready Pod만 Endpoint로 넣는다. Nucleus compose stack은 같은 Pod 안의 여러 컨테이너가 bootstrap 중 서로의 Service DNS로 접근해야 해서, `nucleus-api -> nucleus-resolver-cache`가 Pod Ready 이전에 막혔다.
   - 해결: compose 내부 통신용 Service들에 `publishNotReadyAddresses: true`를 추가했다.


4. `nucleus-log-processor`가 `nucleus-api:3006`에 연결하지 못하고 CrashLoopBackOff
   - 원인: Docker Compose에서는 같은 네트워크 안의 컨테이너 포트가 바로 보이지만, Kubernetes Service는 `ports`에 명시된 포트만 프록시한다.
   - 해결: 외부 LoadBalancer가 아니라 내부 `nucleus-api` ClusterIP Service에만 `service-api` 포트 3006을 추가했다. 이 포트는 관리용 성격이 있으므로 외부 노출 금지.


5. LoadBalancer 8080이 Navigator UI가 아니라 metrics로 연결됨
   - 원인: 같은 Pod 안에서 `utl-monpx`가 8080을 사용하고, Nucleus Navigator UI는 80을 사용한다. Service `targetPort: 8080`은 Pod IP의 8080으로 가므로 metrics가 응답했다.
   - 해결: 외부 접속 주소는 `http://10.34.48.221:8080/` 그대로 두고, `omniverse-nucleus` LoadBalancer Service의 `web` 포트 `targetPort`만 80으로 변경했다.

### 남은 작업

- kube-scheduler / kube-controller-manager CrashLoop 원인 복구
- scheduler 복구 후 10-statefulset.yaml에서 nodeName: com3 제거
- 실제 접속 도메인/IP와 TLS/Ingress 노출 방식 확정
- readiness/liveness probe 추가
- 실제 운영 전에 Nucleus 데이터 백업/복구 절차 확정

## 실제 Nucleus 전환 내역

2026-07-09에 placeholder `python:3.12-alpine` 컨테이너를 제거하고 NVIDIA Enterprise Nucleus Compose Stack 기반 구성으로 전환했다.

### 사용한 artifact

```bash
ngc registry resource download-version nvidia/omniverse/nucleus-compose-stack:2023.2.10
```

다운로드 위치는 로컬 작업용이며 Git에는 커밋하지 않는다.

```text
.artifacts/ngc/nucleus-compose-stack_v2023.2.10/
.artifacts/nucleus-stack-2023.2.10/
```

### 실제 이미지

현재 StatefulSet에는 다음 실제 NVIDIA Nucleus 이미지가 들어간다.

```text
nvcr.io/nvidia/omniverse/nucleus-api:1.14.55
nvcr.io/nvidia/omniverse/nucleus-lft:1.14.55
nvcr.io/nvidia/omniverse/nucleus-lft-lb:1.14.55
nvcr.io/nvidia/omniverse/nucleus-log-processor:1.14.55
nvcr.io/nvidia/omniverse/nucleus-resolver-cache:1.14.55
nvcr.io/nvidia/omniverse/utl-monpx:1.14.55
nvcr.io/nvidia/omniverse/nucleus-discovery:1.5.6
nvcr.io/nvidia/omniverse/nucleus-auth:1.5.9
nvcr.io/nvidia/omniverse/nucleus-navigator:3.3.7
nvcr.io/nvidia/omniverse/nucleus-search:3.2.14
nvcr.io/nvidia/omniverse/nucleus-thumbnails:1.5.15
nvcr.io/nvidia/omniverse/nucleus-tagging:3.1.36
```


### MetalLB 접속 IP

`omniverse-nucleus` Service는 MetalLB `LoadBalancer`로 노출한다. 현재 MetalLB 정책상 `spec.loadBalancerIP`와 `metallb.io/loadBalancerIPs`를 동시에 쓰면 할당이 실패하므로, Git manifest에는 `metallb.io/loadBalancerIPs` annotation만 사용한다.

```text
LoadBalancer IP: 10.34.48.221
Service: omniverse/omniverse-nucleus
```

Nucleus compose stack의 `SERVER_IP_OR_HOST`와 외부 advertised URL도 같은 IP로 맞췄다. 브라우저 접속은 우선 다음 주소를 사용한다.

```text
http://10.34.48.221:8080/
```

운영 단계에서 DNS를 붙이면 `SERVER_IP_OR_HOST`와 Service annotation/loadBalancerIP를 DNS/IP 정책에 맞춰 다시 조정한다.

### Runtime Secret

다음 Secret은 Git에 넣지 않고 클러스터에 직접 생성했다.

```text
nvcr-io             # nvcr.io imagePullSecret
nucleus-secrets     # auth signing key, discovery token, salts, SAML blank metadata
nucleus-passwords   # admin/service password
```

관리자 계정은 compose 기본값에 맞춰 `omniverse`이다. 비밀번호는 아래 명령으로 클러스터에서 조회한다.

```bash
kubectl -n omniverse get secret nucleus-passwords   -o jsonpath='{.data.master-password}' | base64 -d; echo
```

### 배포 구조

```text
ArgoCD Application omniverse-nucleus-poc
  -> StatefulSet omniverse-nucleus
     -> 12 containers from NVIDIA Nucleus Compose Stack
     -> PVC nucleus-data-omniverse-nucleus-0
        -> rook-ceph-block RBD
        -> /var/lib/omni/nucleus-data
  -> Service omniverse-nucleus
  -> Internal Services nucleus-api, nucleus-auth, nucleus-discovery, ...
```

### 검증 명령

```bash
kubectl -n argocd get app omniverse-nucleus-poc -o wide
kubectl -n omniverse get sts,pvc,pod,svc -o wide
kubectl -n omniverse get pod omniverse-nucleus-0 -o jsonpath='{range .status.containerStatuses[*]}{.name}{"\t"}{.ready}{"\t"}{.state}{"\n"}{end}'
kubectl -n omniverse logs omniverse-nucleus-0 -c nucleus-api --tail=100
kubectl -n omniverse logs omniverse-nucleus-0 -c nucleus-auth --tail=100
kubectl -n omniverse port-forward svc/omniverse-nucleus 8080:8080
```


## 2026-07-09 최종 검증 결과: 실제 Nucleus + RBD + MetalLB

검증 당시 manifest Git revision: `4ba532c4` (`fix: route Nucleus web port to Navigator`)

검증 상태:

```text
ArgoCD Application: omniverse-nucleus-poc / Synced / Healthy
StatefulSet: omniverse-nucleus / 1/1 Ready
Pod: omniverse-nucleus-0 / 12/12 Running / node=com3
PVC: nucleus-data-omniverse-nucleus-0 / rook-ceph-block / 10Gi / Bound
LoadBalancer IP: 10.34.48.221
Web URL: http://10.34.48.221:8080/
```

HTTP 검증:

```bash
curl -fsS -D - http://10.34.48.221:8080/
```

응답 요약:

```text
HTTP/1.1 200 OK
Server: nginx/1.28.1
<title>Omniverse Navigator</title>
<base id="public-url" href="http://10.34.48.221:8080/" />
```

이번 PoC에서 실제로 확인한 것:

- NVIDIA NGC Enterprise Nucleus Compose Stack `2023.2.10` artifact 기반 실제 이미지 사용
- Compose의 12개 서비스를 Kubernetes StatefulSet의 12개 컨테이너로 구동
- Rook-Ceph RBD PVC를 Nucleus DATA_ROOT로 마운트
- MetalLB LoadBalancer IP `10.34.48.221`로 외부 접속 노출
- 내부 Compose DNS 대체용 ClusterIP Service 구성
- Kubernetes와 Compose 차이로 발생한 bootstrap 문제 해결
  - Ready 전 Endpoint 필요: `publishNotReadyAddresses: true`
  - 내부 Service API 3006 필요: `nucleus-api` ClusterIP에만 `service-api` 포트 추가
  - Navigator UI 포트 보정: 외부 8080 -> Pod targetPort 80

주의:

- 현재 `nodeName: com3`는 kube-scheduler / kube-controller-manager 불안정 상태를 우회하기 위한 임시 설정이다.
- 운영 전에는 control-plane 안정화 후 `nodeName`을 제거하고 node affinity/toleration/resource request 기반으로 배치해야 한다.
- `nvcr-io`, `nucleus-secrets`, `nucleus-passwords`는 Git에 넣지 않고 런타임 Secret으로 생성했다. 운영 전에는 OpenBao + External-Secrets로 이관해야 한다.
- NGC API Key 또는 Docker registry credential은 개인 키를 그대로 재사용하지 말고, 테스트 후 revoke/rotate하고 조직 정책에 맞게 Secret Store에 넣어야 한다.

