# Omniverse Nucleus Kubernetes PoC Runbook

이 문서는 MiniX/TwinX 환경에서 NVIDIA Omniverse Nucleus를 Kubernetes 위에 올리기 위해 실제로 어떤 판단을 했고, NVIDIA 공식 Compose Stack을 어떤 식으로 Kubernetes manifest로 옮겼는지 기록한 런북이다.

- 대상 경로: `argocd/minix/apps/omniverse-nucleus-poc/`
- ArgoCD Application: `omniverse-nucleus-poc`
- Namespace: `omniverse`
- 현재 외부 접속: `http://10.34.48.221:8080/`
- 현재 스토리지: `rook-ceph-block` RBD PVC `10Gi`

> 주의: 이 구성은 NVIDIA가 공식으로 제공하는 Kubernetes Helm chart가 아니라, NVIDIA Enterprise Nucleus Server Compose Stack을 실험적으로 Kubernetes StatefulSet으로 옮긴 PoC이다. 운영 전에는 보안, 백업, TLS, scheduler, 리소스 request/limit, Secret 관리 방식을 보강해야 한다.

## 1. 왜 이 실험을 했는가

기존 목표는 다음 두 가지였다.

1. 로컬/단일 서버 Docker Compose 기반 Nucleus를 Kubernetes 위에서 실행할 수 있는지 확인한다.
2. Nucleus 데이터를 노드 로컬 디스크가 아니라 Rook-Ceph RBD PVC에 저장할 수 있는지 확인한다.

즉, 바로 `smartx-k8s`나 `twinx-k8s` preset 구조에 넣기 전에 먼저 순수 Kubernetes + ArgoCD + RBD 조합으로 실제 Nucleus가 뜨는지를 검증했다.

검증하고 싶었던 핵심은 다음이다.

- NVIDIA 실제 Nucleus 이미지가 pull 되는가?
- Nucleus가 StatefulSet으로 떠도 되는가?
- Nucleus 실제 데이터/로그 경로를 RBD PVC로 마운트해도 동작하는가?
- Bare-metal 환경에서 MetalLB LoadBalancer IP로 접속 가능한가?
- ArgoCD로 GitOps 관리 가능한가?

## 2. NVIDIA 공식 방식은 무엇인가

NVIDIA Enterprise Nucleus Server는 기본적으로 Kubernetes용 chart가 아니라 Docker Compose package로 제공된다.

NVIDIA 공식 문서 기준 흐름은 다음이다.

1. NVIDIA Developer Program 또는 Enterprise Entitlement Organization 권한이 있는 NGC 계정 준비
2. NGC Catalog에서 Enterprise Nucleus Server / Nucleus Compose Stack 다운로드
3. 서버에 artifact 압축 해제
4. `base_stack/nucleus-stack.env` 수정
5. `docker login nvcr.io` 수행
6. `docker compose --env-file ... -f nucleus-stack-no-ssl.yml pull`
7. `docker compose --env-file ... -f nucleus-stack-no-ssl.yml up -d`
8. `http://<SERVER_IP_OR_HOST>:8080`으로 Nucleus Navigator 접속 확인

공식 문서에서 중요한 포인트는 다음이다.

- Enterprise Nucleus Server software는 Docker Compose 및 configuration file 묶음으로 배포된다.
- Compose file은 NVIDIA hosted Docker registry에서 Nucleus service container들을 가져온다.
- `nucleus-stack.env`에서 `ACCEPT_EULA`, `SECURITY_REVIEWED`, `SERVER_IP_OR_HOST`, `MASTER_PASSWORD`, `SERVICE_PASSWORD`, `DATA_ROOT` 등을 설정한다.
- `DATA_ROOT` 기본값은 `/var/lib/omni/nucleus-data`이다.
- 기본 web port는 `8080`이다.
- Docker login 시 username은 `$oauthtoken`, password는 NGC key를 사용한다.
- Nucleus는 데이터 서버 성격이 강하므로 백업/복구와 Secret 관리를 별도로 설계해야 한다.

참고한 공식 문서:

- Planning Your Installation: https://docs.omniverse.nvidia.com/nucleus/latest/enterprise/installation/planning.html
- Installing an Enterprise Nucleus Server: https://docs.omniverse.nvidia.com/nucleus/latest/enterprise/installation/install-ove-nucleus.html
- Networking and TCP/IP Ports: https://docs.omniverse.nvidia.com/nucleus/latest/ports_connectivity.html
- Backups and Data Restoration: https://docs.omniverse.nvidia.com/nucleus/latest/enterprise/backing-up-and-restoring-nucleus.html
- NGC Enterprise Nucleus collection: https://catalog.ngc.nvidia.com/orgs/nvidia/omniverse/collections/enterprise-nucleus/-/artifacts

## 3. 우리가 공식 방식에서 바꾼 것

공식 방식은 Docker Compose이다. 우리는 Kubernetes에서 돌려야 하므로 다음과 같이 치환했다.

| NVIDIA Compose 방식 | MiniX Kubernetes PoC 방식 | 이유 |
| --- | --- | --- |
| `docker compose up` | ArgoCD Application + StatefulSet | GitOps로 관리하기 위해 |
| Compose service 12개 | StatefulSet Pod 안의 container 12개 | Compose의 tightly-coupled 서비스들을 한 번에 검증하기 위해 |
| Docker named/bind volume | Rook-Ceph RBD PVC | Nucleus 데이터를 클러스터 스토리지에 저장하기 위해 |
| Docker network service name | Kubernetes ClusterIP Service | `nucleus-api`, `nucleus-auth` 같은 DNS 이름 유지 |
| host port 8080 | MetalLB LoadBalancer `10.34.48.221:8080` | Bare-metal 클러스터 외부 접속을 위해 |
| `.env` 평문 설정 | Kubernetes env + Secret | GitOps/Kubernetes 방식으로 이관하기 위해 |
| Compose local secret files | Kubernetes Secret | 이후 OpenBao/External-Secrets로 바꾸기 위해 |

## 4. 왜 StatefulSet인가

Nucleus는 무상태 웹앱이 아니라 데이터 서버에 가깝다. 따라서 Deployment보다 StatefulSet이 맞다.

StatefulSet을 선택한 이유:

- Pod 이름이 안정적이다: `omniverse-nucleus-0`
- PVC 이름이 안정적이다: `nucleus-data-omniverse-nucleus-0`
- `volumeClaimTemplates`로 Pod 전용 RBD PVC를 만들 수 있다.
- 단일 writer 데이터 서버 구조를 명확히 표현할 수 있다.
- 나중에 백업/복구, 스냅샷, 마이그레이션 절차를 고정된 PVC 기준으로 만들 수 있다.

현재는 `replicas: 1`이다. Nucleus를 단순히 replica 수만 늘려 HA로 만드는 것은 검증하지 않았다. Nucleus 자체의 HA/백업/복구 정책을 별도로 확인해야 한다.

## 5. 왜 Pod가 `12/12`인가

`kubectl get pod` 출력의 `12/12`는 Pod 1개 안에 container가 12개 있고, 그 12개가 모두 Ready라는 뜻이다.

NVIDIA Compose Stack의 service 12개를 Kubernetes StatefulSet의 container 12개로 옮겼기 때문에 `1/1`이 아니라 `12/12`로 보인다.

현재 container 목록:

| Container | 역할 | Image |
| --- | --- | --- |
| `nucleus-api` | Nucleus core/API | `nvcr.io/nvidia/omniverse/nucleus-api:1.14.55` |
| `nucleus-lft` | Large File Transfer | `nvcr.io/nvidia/omniverse/nucleus-lft:1.14.55` |
| `nucleus-lft-lb` | LFT load balancing | `nvcr.io/nvidia/omniverse/nucleus-lft-lb:1.14.55` |
| `nucleus-log-processor` | Nucleus log processing/metrics | `nvcr.io/nvidia/omniverse/nucleus-log-processor:1.14.55` |
| `nucleus-resolver-cache` | Resolver cache | `nvcr.io/nvidia/omniverse/nucleus-resolver-cache:1.14.55` |
| `utl-monpx` | Monitoring exporter | `nvcr.io/nvidia/omniverse/utl-monpx:1.14.55` |
| `nucleus-discovery` | Service discovery | `nvcr.io/nvidia/omniverse/nucleus-discovery:1.5.6` |
| `nucleus-auth` | Authentication | `nvcr.io/nvidia/omniverse/nucleus-auth:1.5.9` |
| `nucleus-navigator` | Web UI/Navigator | `nvcr.io/nvidia/omniverse/nucleus-navigator:3.3.7` |
| `nucleus-search` | Search | `nvcr.io/nvidia/omniverse/nucleus-search:3.2.14` |
| `nucleus-thumbnails` | Thumbnail service | `nvcr.io/nvidia/omniverse/nucleus-thumbnails:1.5.15` |
| `nucleus-tagging` | Tagging service | `nvcr.io/nvidia/omniverse/nucleus-tagging:3.1.36` |

나중에 운영화할 때는 각 서비스를 별도 Deployment/StatefulSet으로 분리할 수도 있다. 다만 그 경우 Compose의 내부 DNS, shared volume, startup order, health check, port mapping을 모두 다시 설계해야 한다. 이번 PoC에서는 먼저 “공식 Compose Stack 전체가 Kubernetes에서 뜨는가”를 확인하는 것이 목적이라 한 Pod 안에 묶었다.

## 6. 왜 Rook-Ceph RBD인가

NVIDIA 문서에서는 Nucleus 데이터가 로컬/전용 서버 디스크 성격을 갖는 것을 전제로 한다. 또한 SMB/CIFS, NFS, iSCSI 같은 원격 mount 방식은 Nucleus의 transactional storage/database 특성 때문에 주의 또는 비지원으로 언급된다.

그래서 Kubernetes에서는 shared filesystem보다 block PVC인 RBD가 더 적합하다고 판단했다.

현재 구조:

```text
Rook-Ceph RBD image
  -> Kubernetes PVC nucleus-data-omniverse-nucleus-0
    -> Pod에 filesystem으로 마운트
      -> /var/lib/omni/nucleus-data
        -> Nucleus DATA_ROOT
```

중요한 점:

- 현재 Kubernetes manifest에서 실제 Nucleus 컨테이너들은 주로 `/omni/data`, `/omni/log`, `/omni/temp`, `/omni/scratch-meta-dump` 경로를 본다. NVIDIA Compose env의 기본 `DATA_ROOT=/var/lib/omni/nucleus-data` 개념과 다르게, live Pod에서는 `DATA_ROOT` env가 비어 있고 실제 mount path 기준으로 동작함을 확인했다.
- 실제 물리 위치가 Ceph RBD인지 로컬 디스크인지는 컨테이너 입장에서는 중요하지 않다.
- Kubernetes가 RBD block device를 노드에 attach하고 filesystem으로 mount해준다.
- 단, RBD는 기본적으로 `ReadWriteOnce` 단일 writer로 보는 것이 안전하다.
- 따라서 현재처럼 `replicas: 1` StatefulSet과 잘 맞는다.

## 7. 파일별 역할

```text
argocd/minix/apps/omniverse-nucleus-poc/
├── README.md
├── RUNBOOK.md
├── 00-namespace.yaml
├── 00-headless-service.yaml
├── 10-statefulset.yaml
├── 15-internal-services.yaml
└── 20-service.yaml
```

| 파일 | 역할 |
| --- | --- |
| `README.md` | 현재 상태, 검증 결과, 문제 해결 요약 |
| `RUNBOOK.md` | 왜 이렇게 했는지, 재현 절차, NVIDIA 공식 방식과 차이 |
| `00-namespace.yaml` | `omniverse` namespace 생성 |
| `00-headless-service.yaml` | StatefulSet용 headless service |
| `10-statefulset.yaml` | 실제 Nucleus 12개 container + RBD PVC 정의 |
| `15-internal-services.yaml` | Compose service DNS를 Kubernetes Service로 대체 |
| `20-service.yaml` | MetalLB LoadBalancer 외부 노출 |

## 7.1 Manifest 상세와 다음에 수정할 값

전체 YAML 본문은 런북에 중복 복붙하지 않고 같은 디렉터리의 실제 적용 원본을 기준으로 관리한다. 즉, ArgoCD가 실제로 읽는 원본은 아래 manifest 파일들이고, 런북은 각 파일이 무엇을 만들고 다음 사람이 어디를 바꿔야 하는지 설명한다.

### `00-namespace.yaml`

생성 리소스:

```text
kind: Namespace
metadata.name: omniverse
```

역할:

- Nucleus 전용 namespace를 만든다.
- Secret, StatefulSet, Service가 모두 이 namespace에 생성된다.

다음에 바꿀 수 있는 값:

- namespace 이름을 바꾸려면 모든 manifest의 `metadata.namespace`도 같이 바꿔야 한다.
- 현재는 `omniverse` 유지가 권장된다.

### `00-headless-service.yaml`

생성 리소스:

```text
kind: Service
metadata.name: omniverse-nucleus-headless
spec.clusterIP: None
```

역할:

- StatefulSet `serviceName`으로 사용한다.
- Pod identity와 DNS를 안정적으로 잡기 위한 headless service이다.

다음에 바꿀 수 있는 값:

- 보통 변경하지 않는다.
- StatefulSet 이름을 바꾸면 selector label만 같이 맞춘다.

### `10-statefulset.yaml`

생성 리소스:

```text
kind: StatefulSet
metadata.name: omniverse-nucleus
spec.replicas: 1
volumeClaimTemplates:
  storageClassName: rook-ceph-block
  size: 10Gi
```

역할:

- 실제 NVIDIA Nucleus container 12개를 실행한다.
- `nvcr.io/nvidia/omniverse/*` 이미지를 사용한다.
- Rook-Ceph RBD PVC를 만들고 실제 Nucleus 데이터/로그 경로인 `/omni/data`, `/omni/log`, 일부 `/omni/temp`, `/omni/scratch-meta-dump` 등에 마운트한다.
- `imagePullSecrets: nvcr-io`로 NGC private registry 인증을 사용한다.

현재 중요한 값:

```text
persistent mount paths=/omni/data,/omni/log,/omni/temp,/omni/scratch-meta-dump
SERVER_IP_OR_HOST=10.34.48.221
WEB_PORT=8080
SERVICE_API_PORT=3006
storageClassName=rook-ceph-block
storage=10Gi
nodeName=com3    # 임시 우회값
```

다음에 반드시 확인/수정할 값:

| 항목 | 현재 값 | 다음 작업 |
| --- | --- | --- |
| `SERVER_IP_OR_HOST` | `10.34.48.221` | MetalLB IP 또는 DNS에 맞게 변경 |
| `storageClassName` | `rook-ceph-block` | 실제 클러스터 StorageClass에 맞게 변경 |
| PVC size | `10Gi` | 운영 용량으로 증설 |
| `nodeName` | `com3` | scheduler 복구 후 제거 |
| image tag | NVIDIA Compose Stack `2023.2.10` 기준 | 새 버전 사용 시 Compose artifact와 함께 재검증 |
| Secret refs | `nvcr-io`, `nucleus-secrets`, `nucleus-passwords` | 운영 전 ExternalSecrets로 변경 |

중요:

- `nodeName: com3`는 운영 설정이 아니라 현재 클러스터 scheduler 문제를 우회하기 위한 임시값이다.
- 운영 전에는 `nodeName`을 제거하고 `nodeSelector`, `affinity`, `tolerations`, `resources` 기반으로 배치해야 한다.

### `15-internal-services.yaml`

생성 리소스:

```text
kind: Service
metadata.name: nucleus-api
metadata.name: nucleus-lft
metadata.name: nucleus-lft-lb
metadata.name: nucleus-log-processor
metadata.name: nucleus-resolver-cache
metadata.name: nucleus-discovery
metadata.name: nucleus-auth
metadata.name: nucleus-navigator
metadata.name: nucleus-search
metadata.name: nucleus-thumbnails
metadata.name: nucleus-tagging
metadata.name: utl-monpx
```

역할:

- Docker Compose의 service name DNS를 Kubernetes Service DNS로 대체한다.
- 예를 들어 Compose에서 `nucleus-api:3006`으로 붙던 것을 Kubernetes에서도 같은 이름으로 붙을 수 있게 한다.
- 내부 bootstrap 문제를 피하기 위해 `publishNotReadyAddresses: true`를 사용한다.

다음에 바꿀 수 있는 값:

- 외부 노출용이 아니므로 대부분 변경하지 않는다.
- container port나 service name을 바꾸면 StatefulSet env와 같이 맞춰야 한다.
- `nucleus-api`의 `3006` 포트는 내부용으로만 유지하고 외부 LoadBalancer에는 열지 않는다.

### `20-service.yaml`

생성 리소스:

```text
kind: Service
type: LoadBalancer
metadata.name: omniverse-nucleus
annotation: metallb.io/loadBalancerIPs: 10.34.48.221
```

역할:

- 브라우저에서 접속할 수 있는 외부 IP를 제공한다.
- 현재 URL은 `http://10.34.48.221:8080/`이다.
- 외부 `8080`은 Pod 내부 Navigator `80`으로 연결한다.

현재 중요한 값:

```text
metallb.io/loadBalancerIPs=10.34.48.221
port=8080
targetPort=80
```

다음에 반드시 확인/수정할 값:

| 항목 | 현재 값 | 다음 작업 |
| --- | --- | --- |
| LoadBalancer IP | `10.34.48.221` | 사용 가능한 MetalLB IP로 변경 |
| web port | `8080` | 운영 정책에 맞게 80/443/Ingress로 변경 가능 |
| targetPort | `80` | Navigator UI가 뜨는 포트이므로 유지 |
| TLS | 없음 | 운영 시 Ingress/Gateway/TLS 검토 |

주의:

- `10.34.48.220`은 ArgoCD에서 이미 사용 중이어서 Nucleus는 `10.34.48.221`을 사용했다.
- MetalLB에서는 `spec.loadBalancerIP`와 `metallb.io/loadBalancerIPs`를 동시에 쓰지 않는다. 현재 manifest는 annotation만 사용한다.

### Git에 올리지 않는 것

아래 값들은 manifest 원본에 직접 넣지 않는다.

```text
NGC API Key
Nucleus admin password
Nucleus service password
Auth signing key
Discovery token
Salt 값
SAML metadata 실제 값
NVIDIA Compose artifact 원본
```

대신 다음 runtime Secret 또는 ExternalSecret으로 주입한다.

```text
nvcr-io
nucleus-secrets
nucleus-passwords
```

## 8. 실제 재현 절차

### 8.1 NGC artifact 다운로드

작업 서버에서 NGC CLI로 Compose Stack artifact를 받았다.

```bash
ngc registry resource download-version nvidia/omniverse/nucleus-compose-stack:2023.2.10
```

다운로드/압축해제 결과는 Git에 넣지 않는다.

```text
.artifacts/ngc/nucleus-compose-stack_v2023.2.10/
.artifacts/nucleus-stack-2023.2.10/
```

Git에 넣지 않는 이유:

- NVIDIA artifact는 외부 배포 대상이 아니다.
- NGC 권한/라이선스 범위 내에서 받아야 한다.
- Compose artifact와 secret material을 repo에 섞으면 안 된다.

### 8.2 Docker/NGC 인증

NVIDIA image pull에는 `nvcr.io` 인증이 필요하다.

공식 방식:

```bash
docker login nvcr.io
# Username: $oauthtoken
# Password: NGC API Key
```

Kubernetes에서는 Docker login 대신 imagePullSecret을 만든다. 여기서 사용자가 실제 NGC key를 입력해야 하는 위치는 `<NGC_API_KEY>` 한 곳이다. 이 값은 Git에 절대 커밋하지 않는다.

```bash
kubectl -n omniverse create secret docker-registry nvcr-io \
  --docker-server=nvcr.io \
  --docker-username='$oauthtoken' \
  --docker-password='<NGC_API_KEY>'
```

입력 기준:

| 값 | 입력 내용 | Git 커밋 여부 |
| --- | --- | --- |
| `--docker-server` | `nvcr.io` | 가능 |
| `--docker-username` | `$oauthtoken` | 가능 |
| `--docker-password` | NGC Personal/API Key | 금지 |

주의:

- API key는 Git에 넣지 않는다.
- README, RUNBOOK, YAML manifest에도 실제 key를 쓰지 않는다.
- 채팅/터미널 기록에 노출된 키는 테스트 후 revoke/rotate한다.
- 운영 전에는 OpenBao + External-Secrets로 관리한다.

### 8.3 Compose env에서 필요한 값 확인

NVIDIA artifact의 `base_stack/nucleus-stack.env`에서 중요한 값:

```text
ACCEPT_EULA=1
SECURITY_REVIEWED=1
SERVER_IP_OR_HOST=10.34.48.221
DATA_ROOT=/var/lib/omni/nucleus-data    # NVIDIA Compose env 기본 개념
WEB_PORT=8080
SERVICE_API_PORT=3006
REGISTRY=nvcr.io/nvidia/omniverse
CORE_VERSION=1.14.55
DISCOVERY_VERSION=1.5.6
AUTH_VERSION=1.5.9
NAV3_VERSION=3.3.7
SEARCH_VERSION=3.2.14
THUMBNAILING_VERSION=1.5.15
TAGGING_VERSION=3.1.36
```

Kubernetes manifest에서는 이 값들을 `10-statefulset.yaml`의 container env와 image tag로 옮겼다.

### 8.4 Secret 생성

PoC에서는 다음 Secret을 클러스터에 직접 만들었다.

```text
nvcr-io             # nvcr.io pull secret
nucleus-secrets     # auth signing key, discovery token, salts, SAML blank metadata
nucleus-passwords   # admin/service password
```

운영에서는 직접 생성하지 말고 ExternalSecret으로 바꿔야 한다.

### 8.5 Manifest 적용

ArgoCD가 이 경로를 읽어 적용한다.

```text
argocd/minix/apps/omniverse-nucleus-poc/
```

수동 확인 명령:

```bash
kubectl -n argocd get app omniverse-nucleus-poc -o wide
kubectl -n omniverse get sts,pvc,pod,svc -o wide
kubectl -n omniverse describe pod omniverse-nucleus-0
```

### 8.6 접속 확인

```bash
curl -fsS -D - http://10.34.48.221:8080/ | head
```

정상이라면 `Omniverse Navigator` HTML이 응답한다.

브라우저:

```text
http://10.34.48.221:8080/
```

## 9. Kubernetes 변환 중 중요했던 차이점

### 9.1 Compose DNS와 Kubernetes Service 차이

Compose에서는 같은 network 안의 service 이름으로 바로 통신한다.

예:

```text
nucleus-log-processor -> nucleus-api:3006
nucleus-api -> nucleus-resolver-cache
```

Kubernetes에서는 이 이름들을 ClusterIP Service로 만들어줘야 한다. 그래서 `15-internal-services.yaml`을 추가했다.

### 9.2 Ready 전 Endpoint 문제

Kubernetes Service는 기본적으로 Ready Pod만 Endpoint로 등록한다. 그런데 Nucleus container들은 bootstrap 중 서로 먼저 붙어야 한다.

문제:

```text
nucleus-api가 nucleus-resolver-cache에 붙어야 Ready가 됨
하지만 Pod가 Ready가 아니어서 Service endpoint가 비어 있음
```

해결:

```yaml
publishNotReadyAddresses: true
```

내부용 Service에 이 옵션을 넣어 bootstrap circular dependency를 풀었다.

### 9.3 `nucleus-api:3006` 포트 문제

Compose에서는 container port가 같은 network에서 바로 보인다. Kubernetes Service는 `ports`에 명시한 포트만 접근 가능하다.

문제 로그:

```text
attempting to connect to ws://nucleus-api:3006
ConnectionRefusedError: Connect call failed
```

해결:

- `nucleus-api` 내부 ClusterIP Service에 `service-api` port `3006` 추가
- 외부 LoadBalancer에는 3006을 열지 않음

### 9.4 Web 8080이 metrics로 붙던 문제

처음에는 LoadBalancer `8080 -> targetPort 8080`으로 잡았다. 그런데 Pod 내부 8080은 `utl-monpx` metrics 쪽이었다.

Nucleus Navigator UI는 container port `80`에서 응답했다.

해결:

```yaml
ports:
  - name: web
    port: 8080
    targetPort: 80
```

그래서 외부 URL은 그대로 `http://10.34.48.221:8080/`이고, 내부 target만 Navigator의 80으로 보낸다.

### 9.5 MetalLB IP 문제

처음 `10.34.48.220`을 쓰려고 했지만 이미 ArgoCD LoadBalancer가 사용 중이었다.

현재 사용:

```text
10.34.48.221
```

또한 MetalLB에서는 `spec.loadBalancerIP`와 `metallb.io/loadBalancerIPs` annotation을 동시에 쓰면 Pending이 발생할 수 있어, 현재 manifest는 annotation만 사용한다.

## 10. 현재 restart가 있었던 이유

현재 Pod 상태에서 restart count가 보이는 이유는 전체 Pod가 실패한 것이 아니라 `nucleus-log-processor` container가 초기 부팅 중 2번 재시작했기 때문이다.

확인된 이전 로그:

```text
attempting to connect to ws://nucleus-api:3006
ConnectionRefusedError: Connect call failed
Detach cmd failed with 1
```

해석:

- `nucleus-log-processor`가 시작 직후 `nucleus-api:3006`에 붙으려고 했다.
- 그 순간 `nucleus-api`가 아직 3006을 받을 준비가 끝나지 않았다.
- `nucleus-log-processor`가 exit 1로 종료되고 kubelet이 재시작했다.
- 이후 `nucleus-api`가 준비되면서 정상 Running/Ready가 되었다.

현재 모든 container가 Ready라면 이 초기 restart는 치명적인 문제는 아니다. 다만 운영 전에는 startupProbe/readinessProbe 또는 init/startup ordering을 더 정리하는 것이 좋다.

## 11. 현재 검증 상태

마지막 확인 기준:

```text
ArgoCD Application: omniverse-nucleus-poc / Synced / Healthy
StatefulSet: omniverse-nucleus / 1/1 Ready
Pod: omniverse-nucleus-0 / 12/12 Running
PVC: nucleus-data-omniverse-nucleus-0 / rook-ceph-block / 10Gi / Bound
Service: omniverse-nucleus / LoadBalancer / 10.34.48.221
Web: http://10.34.48.221:8080/ -> Omniverse Navigator
```

검증 명령:

```bash
kubectl -n argocd get app omniverse-nucleus-poc -o wide
kubectl -n omniverse get pod omniverse-nucleus-0 -o wide
kubectl -n omniverse get svc omniverse-nucleus -o wide
curl -fsS -m 10 http://10.34.48.221:8080/ | grep -o '<title>[^<]*</title>'
```


## 11.1 Pod 삭제와 RBD 데이터 보존 기준

2026-07-10 live 확인 결과, `nucleus-auth` 로그에서 `omniverse` 사용자 인증 성공을 확인했다.

```text
InternalCredentials.auth: username=omniverse
status=OK
```

또한 PVC는 다음 상태였다.

```text
PVC: nucleus-data-omniverse-nucleus-0
STATUS: Bound
STORAGECLASS: rook-ceph-block
VOLUME: pvc-67dc9fed-3f61-4cf3-88d2-b65a433956bb
PV reclaimPolicy: Delete
```

실제 RBD mount는 다음 경로에서 확인했다.

```text
/omni/data                       -> /dev/rbd1
/omni/log                        -> /dev/rbd1
/omni/temp                       -> /dev/rbd1
/omni/scratch-meta-dump          -> /dev/rbd1
/var/lib/omni/nucleus-data/empty -> /dev/rbd1
```

`/omni/data`에는 Nucleus가 만든 실제 데이터 파일이 있다.

```text
/omni/data/usergroups.1.0
/omni/data/meta.1.1
/omni/data/content.1.1
/omni/data/omniobjects.1.0
/omni/data/__version_tag
```

데이터 보존 기준:

| 상황 | 데이터 유지 여부 | 설명 |
| --- | --- | --- |
| Pod만 삭제 | 유지 | StatefulSet이 같은 PVC를 다시 붙인다. |
| Pod가 장애로 재시작 | 유지 | 컨테이너/Pod lifecycle과 PVC lifecycle은 분리된다. |
| StatefulSet 삭제, PVC 유지 | 유지 | PVC가 남아 있으면 재생성 시 같은 데이터를 다시 붙일 수 있다. |
| PVC 삭제 | 삭제 가능성 높음 | 현재 PV reclaimPolicy가 `Delete`라 underlying RBD image도 삭제될 수 있다. |
| namespace 삭제 | 삭제 가능성 높음 | namespace 안의 PVC가 삭제되면 RBD도 삭제될 수 있다. |

운영에서는 실수로 PVC가 삭제되지 않도록 다음을 검토한다.

- StatefulSet PVC retention policy 명시
- ArgoCD prune 대상에서 PVC 보호
- PV reclaimPolicy `Retain` 검토
- Rook/Ceph snapshot 또는 Velero 백업 정책 수립

## 12. 운영화 전에 해야 할 일

### 필수

- kube-scheduler / kube-controller-manager 불안정 원인 해결
- `10-statefulset.yaml`의 임시 `nodeName: com3` 제거
- Secret 직접 생성 방식 제거
- OpenBao + External-Secrets로 `nvcr-io`, `nucleus-secrets`, `nucleus-passwords` 관리
- 운영 DNS/TLS 결정
- backup/restore 절차 수립
- PVC 용량 산정
- resource requests/limits 재산정
- startupProbe/readinessProbe/livenessProbe 추가

### SmartX 구조로 옮길 때

현재 PoC는 MiniX ArgoCD app path에 직접 manifest로 들어가 있다. 다음 단계에서는 SmartX 구조에 맞춰 다음 중 하나로 옮긴다.

1. `smartx-k8s` 엔진에 `apps/omniverse-nucleus` catalog 추가
2. `twinx-k8s` preset의 `values.yaml`에서 feature 활성화
3. `twinx-k8s/patches/omniverse-nucleus/values.yaml`에 cluster별 IP, storageClass, domain, secret reference만 둠

예상 feature 이름:

```text
scalex.io/omniverse/nucleus
```

예상 의존성:

```yaml
scalex.io/omniverse/nucleus:
  requires:
    - scalex.io/storage/block
    - scalex.io/ingress/loadbalancer
    - scalex.io/secrets/external-secrets
```

이렇게 하면 `mobilex-k8s`처럼 cluster preset은 차이점만 들고, 실제 배포 방식은 engine/catalog 쪽에서 관리할 수 있다.

## 13. 빠른 점검 명령 모음

```bash
# ArgoCD 상태
kubectl -n argocd get app omniverse-nucleus-poc -o wide

# Kubernetes 리소스
kubectl -n omniverse get sts,pvc,pod,svc -o wide

# 12개 container ready/restart 확인
kubectl -n omniverse get pod omniverse-nucleus-0 \
  -o jsonpath='{range .status.containerStatuses[*]}{.name}{" ready="}{.ready}{" restart="}{.restartCount}{"\n"}{end}'

# Nucleus API/Auth 로그
kubectl -n omniverse logs omniverse-nucleus-0 -c nucleus-api --tail=100
kubectl -n omniverse logs omniverse-nucleus-0 -c nucleus-auth --tail=100
kubectl -n omniverse logs omniverse-nucleus-0 -c nucleus-log-processor --tail=100

# Web 접속
curl -fsS -D - http://10.34.48.221:8080/ | head
```

## 14. 결론

이번 PoC에서 확인한 결론은 다음이다.

- NVIDIA Enterprise Nucleus Compose Stack `2023.2.10`의 실제 이미지를 Kubernetes에서 실행할 수 있다.
- Compose service 12개를 한 StatefulSet Pod의 12개 container로 옮기면 초기 PoC는 가능하다.
- Rook-Ceph RBD PVC를 Nucleus 실제 데이터/로그 경로로 사용할 수 있다.
- MetalLB LoadBalancer IP를 통해 Nucleus Navigator에 접속할 수 있다.
- 다만 이 구성은 아직 운영용이 아니라 SmartX catalog/preset 이관 전 검증 단계이다.
