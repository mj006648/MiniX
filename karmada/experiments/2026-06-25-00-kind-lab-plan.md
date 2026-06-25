# 실험 00. kind 기반 ScaleX-POD 축소 Karmada Lab 실행 계획

## 목적

MiniX 실클러스터를 바로 건드리지 않고, 로컬 `kind` 클러스터 4개로 ScaleX-POD 멀티클러스터의 가장 기본 구조를 축소 검증한다.

```text
실제 목표: ScaleX-POD = Tower + TwinX + EdgeX + DataX + Resource Pool
이번 실험: kind lab   = tower + twinx + edgex + datax
```

이번 실험에서 확인할 핵심 질문:

1. `kind`로 한 머신에서 Kubernetes 클러스터 4개를 만들 수 있는가?
2. `tower`에 Karmada control plane을 설치할 수 있는가?
3. `twinx`, `edgex`, `datax`를 Karmada member cluster로 등록할 수 있는가?
4. Karmada API Server에 적용한 `demo-nginx`가 실제 member cluster 3개에 전파되는가?
5. 실행 명령, 출력, 실패 지점을 기록하면 다음 ScaleX-POD 설계 근거로 쓸 수 있는가?

---

## 참고한 공식 문서

- kind: <https://kind.sigs.k8s.io/>
- Karmada Installation Overview: <https://karmada.io/docs/installation/>
- Karmada CLI Tools: <https://karmada.io/docs/installation/install-cli-tools/>

공식 문서 기준:

- kind는 Docker 컨테이너 노드로 로컬 Kubernetes cluster를 실행하는 도구다.
- Karmada 공식 문서는 `kubectl karmada init`으로 control plane을 설치하는 흐름을 안내한다.
- `kubectl karmada`를 쓰려면 `kubectl-karmada` plugin 설치가 필요하다.

---

## 실험 범위

이번에 하는 것:

- Docker/kind 설치 여부 확인 및 필요 시 설치
- kind cluster 4개 생성
- Karmada CLI/plugin 설치 확인
- `tower`에 Karmada control plane 설치
- `twinx`, `edgex`, `datax`를 Push 모드 member cluster로 등록
- ScaleX-POD 역할 label 부여
- `demo-nginx`를 3개 member cluster로 전파
- Karmada 쪽 리소스와 member cluster 쪽 리소스 비교
- 결과 기록

이번에 하지 않는 것:

- 실제 MiniX cluster 변경
- 실제 GPU 검증
- Rook Ceph / Confluent / Trino / Milvus 같은 stateful workload 전파
- ArgoCD 연동
- Kueue 연동
- EdgeX Pull 모드 검증
- Resource Pool 별도 cluster 구성

---

## 실험 환경 계획

| 이름 | kind context | 역할 | ScaleX-POD에서 대응되는 개념 |
| --- | --- | --- | --- |
| `tower` | `kind-tower` | Karmada control plane 설치용 host cluster | Tower |
| `twinx` | `kind-twinx` | 애플리케이션 전파 대상 1 | TwinX |
| `edgex` | `kind-edgex` | 애플리케이션 전파 대상 2 | EdgeX |
| `datax` | `kind-datax` | 애플리케이션 전파 대상 3 | DataX |

예상 구조:

```text
Docker host
  ├─ kind-tower
  │   └─ Karmada control plane
  ├─ kind-twinx
  │   └─ demo-nginx 실제 실행 대상
  ├─ kind-edgex
  │   └─ demo-nginx 실제 실행 대상
  └─ kind-datax
      └─ demo-nginx 실제 실행 대상
```

---

## 성공 기준

최종적으로 아래가 모두 만족되면 성공으로 판단한다.

| 항목 | 성공 기준 |
| --- | --- |
| kind cluster 생성 | `kind get clusters`에 `tower`, `twinx`, `edgex`, `datax`가 보인다. |
| Karmada 설치 | `karmada-system` namespace의 주요 Pod가 `Running` 또는 `Ready` 상태다. |
| member 등록 | Karmada API에서 `twinx`, `edgex`, `datax` cluster가 `READY=True`로 보인다. |
| demo 전파 | `twinx`, `edgex`, `datax`에 `demo-nginx` Deployment/Pod/Service가 생성된다. |
| 기록 | 실행 명령, 실제 출력, 문제/해결, ScaleX-POD 의미가 이 문서에 남는다. |

---

## 사전 확인

실험 시작 전에 로컬 도구 상태를 기록한다.

### 실행 명령

```bash
pwd
git status --short

docker version
kind version
kubectl version --client

kubectl config current-context || true
kubectl config get-contexts
```

### 기대 결과

- Docker daemon이 동작해야 한다.
- `kind`, `kubectl` 명령이 실행되어야 한다.
- 현재 MiniX context가 무엇인지 확인만 하고, 이번 실험에서는 MiniX context에 리소스를 적용하지 않는다.

### 실제 결과 기록

```text
초기 확인 결과:
- kubectl은 설치되어 있었다.
- docker 명령은 없었다.
- kind 명령은 없었다.
- 현재 kubectl context는 kubernetes-admin@cluster.local 이었다.
- 따라서 Docker와 kind 설치가 먼저 필요하다.
```

---

## Step 0. Docker/kind 설치

### 목적

kind cluster를 만들기 위해 Docker와 kind를 설치한다.

### 실행 명령

Docker 설치:

```bash
sudo apt-get update
sudo apt-get install -y docker.io
```

kind 설치:

```bash
curl -Lo /tmp/kind https://kind.sigs.k8s.io/dl/v0.30.0/kind-linux-amd64
chmod +x /tmp/kind
sudo mv /tmp/kind /usr/local/bin/kind
```

### 확인 명령

```bash
sudo systemctl enable --now docker
sudo docker version
kind version
```

### 기대 결과

- `sudo docker version`이 정상 출력된다.
- `kind version`이 정상 출력된다.

### 실제 결과 기록

```text
Docker:
- 최초 docker 명령 없음: docker: command not found
- sudo apt-get install -y docker.io 로 설치 완료
- sudo systemctl enable --now docker 실행 완료
- Docker version: 29.1.3

kind:
- 최초 kind 명령 없음: kind: command not found
- kind v0.30.0 linux/amd64 바이너리를 /usr/local/bin/kind 로 설치
- kind version: kind v0.30.0 go1.24.6 linux/amd64

Docker socket 권한:
- 최초 일반 사용자 docker ps 실패: permission denied while trying to connect to the docker API
- chang 사용자를 docker 그룹에 추가
- 현재 세션에서 바로 쓰기 위해 /var/run/docker.sock ACL 부여
```

---

## Step 1. kind cluster 4개 생성

### 목적

Tower host cluster와 member cluster 3개를 만든다.

### 실행 명령

```bash
kind create cluster --name tower
kind create cluster --name twinx
kind create cluster --name edgex
kind create cluster --name datax
```

### 확인 명령

```bash
kind get clusters
kubectl config get-contexts

kubectl --context kind-tower get nodes
kubectl --context kind-twinx get nodes
kubectl --context kind-edgex get nodes
kubectl --context kind-datax get nodes
```

### 기대 결과

```text
kind get clusters

datax
edgex
tower
twinx
```

각 cluster마다 node가 `Ready` 상태여야 한다.

### 실제 결과 기록

```text
생성 결과:
- tower 생성 성공
- twinx 생성 성공
- edgex 최초 생성 실패
- datax 최초 생성 실패

실패 메시지:
ERROR: failed to create cluster: could not find a log line that matches "Reached target .*Multi-User System.*|detected cgroup v1"

원인 확인:
- kind create cluster --name edgex --retain 으로 실패 컨테이너 유지
- docker logs edgex-control-plane 확인
- 주요 로그:
  Failed to create control group inotify object: Too many open files
  Failed to allocate manager object: Too many open files

해결:
- fs.inotify.max_user_instances 128 -> 1024
- fs.inotify.max_user_watches 123422 -> 1048576
- /etc/sysctl.d/99-kind-inotify.conf 에 영구 설정 기록
- 실패한 edgex-control-plane 컨테이너 삭제 후 재시도

최종 결과:
- tower Ready
- twinx Ready
- edgex Ready
- datax Ready

주의사항:
- kind create cluster 실행 후 kubectl current-context가 마지막 생성 cluster로 자동 변경됨.
- 실제로 current-context가 kind-datax로 바뀌었고, kubectl get nodes 실행 시 원래 MiniX 노드가 사라진 것처럼 보였다.
- kubectl config use-context kubernetes-admin@cluster.local 로 원래 MiniX context 복구 완료.
- 원래 MiniX 노드 com1/com2/com3/gpu/master 모두 Ready 확인.
```

---

## Step 2. Karmada CLI/plugin 설치 확인

### 목적

Karmada control plane 설치와 member join에 사용할 CLI를 준비한다.

`kubectl karmada` 형태를 쓰려면 `kubectl-karmada` plugin이 필요하다.
`karmadactl`을 설치해서 같은 역할로 사용할 수도 있다.

### 실행 명령

`kubectl karmada` plugin 설치:

```bash
curl -s https://raw.githubusercontent.com/karmada-io/karmada/master/hack/install-cli.sh \
  | sudo bash -s kubectl-karmada
```

선택 사항: `karmadactl`도 설치하고 싶다면 아래를 추가 실행한다.

```bash
curl -s https://raw.githubusercontent.com/karmada-io/karmada/master/hack/install-cli.sh \
  | sudo bash
```

### 확인 명령

```bash
kubectl karmada version
karmadactl version || true
```

### 기대 결과

- `kubectl karmada version`이 정상 출력된다.
- `karmadactl`은 설치했다면 정상 출력되고, 설치하지 않았다면 실패해도 된다.

### 실제 결과 기록

```text
최초 확인:
- kubectl karmada version 실패
- error: unknown command "karmada" for "kubectl"

공식 install-cli.sh 시도:
- release v1.18.0 metadata/download/hash 검증까지 진행
- 설치 단계에서 실패
- 에러 메시지:
  main: line 258: /dev/tty: No such device or address

원인 추정:
- 비대화형 실행 환경에서 install-cli.sh가 /dev/tty 입력 또는 확인을 요구하면서 실패한 것으로 보임.

해결:
- v1.18.0 release tarball을 직접 다운로드
- sha256sum -c 검증 성공
- tarball에서 kubectl-karmada 추출
- sudo install -m 0755 karmada-cli-install/kubectl-karmada /usr/local/bin/kubectl-karmada 실행

최종 확인:
- kubectl karmada version 정상 출력
- version: v1.18.0
- commit: 18d5e4a39371d5618495357833df6336fd642b3a
```

---

## Step 3. tower에 Karmada control plane 설치

### 목적

`kind-tower` cluster를 Tower 축소판으로 보고, 여기에 Karmada control plane을 설치한다.

### 실행 명령

```bash
kubectl config use-context kind-tower
kubectl karmada init
```

> 참고: Karmada 공식 문서 기준 기본 설치는 `/etc/karmada` 아래에 인증서와 kubeconfig를 만든다. 권한 문제가 나면 에러 메시지를 기록하고, `sudo -E kubectl karmada init` 또는 Karmada data/pki 경로 변경을 검토한다.

### 확인 명령

```bash
kubectl --context kind-tower get ns
kubectl --context kind-tower get pods -n karmada-system
kubectl --context kind-tower get deployments -n karmada-system
kubectl --context kind-tower get statefulsets -n karmada-system

ls -l /etc/karmada/karmada-apiserver.config
```

### 기대 결과

- `karmada-system` namespace가 생성된다.
- Karmada 관련 Deployment가 `READY` 상태가 된다.
- `etcd` StatefulSet이 `READY` 상태가 된다.
- `/etc/karmada/karmada-apiserver.config`가 생성된다.

### 실제 결과 기록

```text
최초 실행:
- kubectl karmada init --context kind-tower
- 실패: /etc/karmada 생성 권한 없음
- 에러: failed to create directory: /etc/karmada, error: mkdir /etc/karmada: permission denied

재시도:
- sudo -E kubectl karmada init --kubeconfig /home/chang/.kube/config --context kind-tower
- 성공: Karmada is installed successfully.

생성/준비 상태:
- karmada-system namespace 생성됨
- etcd StatefulSet READY 1/1
- karmada-apiserver READY 1/1
- karmada-aggregated-apiserver READY 1/1
- karmada-controller-manager READY 1/1
- karmada-scheduler READY 1/1
- karmada-webhook READY 1/1
- kube-controller-manager READY 1/1

주의:
- /etc/karmada 는 root:root 700 권한으로 생성됨.
- 일반 사용자로 /etc/karmada/karmada-apiserver.config 접근 시 Permission denied 발생.
- /home/chang/.kube/karmada-apiserver.config 로 복사하고 chown/chmod 600 후 사용.
- kubectl --kubeconfig /home/chang/.kube/karmada-apiserver.config get clusters 정상 동작.
- current-context는 kubernetes-admin@cluster.local 로 유지됨.
```

---

## Step 4. member cluster 등록

### 목적

`twinx`, `edgex`, `datax`를 Karmada control plane에 Push 모드로 등록한다.

### 실행 명령

```bash
kubectl karmada --kubeconfig /etc/karmada/karmada-apiserver.config join twinx \
  --cluster-kubeconfig ~/.kube/config \
  --cluster-context kind-twinx

kubectl karmada --kubeconfig /etc/karmada/karmada-apiserver.config join edgex \
  --cluster-kubeconfig ~/.kube/config \
  --cluster-context kind-edgex

kubectl karmada --kubeconfig /etc/karmada/karmada-apiserver.config join datax \
  --cluster-kubeconfig ~/.kube/config \
  --cluster-context kind-datax
```

### 확인 명령

```bash
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config get clusters
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config describe cluster twinx
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config describe cluster edgex
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config describe cluster datax
```

### 기대 결과

예상 형태:

```text
NAME    VERSION   MODE   READY   AGE
twinx   v...      Push   True    ...
edgex   v...      Push   True    ...
datax   v...      Push   True    ...
```

### 실제 결과 기록

```text
중요 조정:
- kind get kubeconfig --name <cluster> --internal 로 만든 kubeconfig는 server가 https://<cluster>-control-plane:6443 형태다.
- host에서는 twinx-control-plane 같은 Docker 내부 이름을 DNS로 해석하지 못했다.
- Karmada Push 등록용 kubeconfig를 다음 형태로 수정했다.

  twinx: https://172.18.0.3:6443, tls-server-name=twinx-control-plane
  edgex: https://172.18.0.4:6443, tls-server-name=edgex-control-plane
  datax: https://172.18.0.5:6443, tls-server-name=datax-control-plane

- 수정한 kubeconfig 위치:
  /tmp/karmada-kind-kubeconfigs/twinx.kubeconfig
  /tmp/karmada-kind-kubeconfigs/edgex.kubeconfig
  /tmp/karmada-kind-kubeconfigs/datax.kubeconfig

등록 결과:
- cluster(twinx) is joined successfully
- cluster(edgex) is joined successfully
- cluster(datax) is joined successfully

최종 확인:
NAME    VERSION   MODE   READY   API-ENDPOINT
twinx   v1.34.0   Push   True    https://172.18.0.3:6443
edgex   v1.34.0   Push   True    https://172.18.0.4:6443
datax   v1.34.0   Push   True    https://172.18.0.5:6443
```

---

## Step 5. ScaleX-POD 역할 label 부여

### 목적

TwinX / EdgeX / DataX 배치 정책을 만들기 위해 kind member cluster에 역할 label을 붙인다.

### 실행 명령

```bash
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config label cluster twinx \
  scalex.io/role=gpu-render \
  scalex.io/pool=gpu \
  --overwrite

kubectl --kubeconfig /etc/karmada/karmada-apiserver.config label cluster edgex \
  scalex.io/role=edge-gpu \
  scalex.io/pool=gpu \
  scalex.io/location=edge \
  --overwrite

kubectl --kubeconfig /etc/karmada/karmada-apiserver.config label cluster datax \
  scalex.io/role=data \
  scalex.io/storage=ssd \
  scalex.io/workload=data \
  --overwrite
```

### 확인 명령

```bash
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config get clusters --show-labels
```

### 기대 결과

- `twinx`에 `scalex.io/role=gpu-render`가 보인다.
- `edgex`에 `scalex.io/role=edge-gpu`가 보인다.
- `datax`에 `scalex.io/role=data`가 보인다.

### 실제 결과 기록

```text
label 부여 성공:
- twinx: scalex.io/role=gpu-render, scalex.io/pool=gpu
- edgex: scalex.io/role=edge-gpu, scalex.io/pool=gpu, scalex.io/location=edge
- datax: scalex.io/role=data, scalex.io/storage=ssd, scalex.io/workload=data

확인 결과:
NAME    VERSION   MODE   READY   LABELS
datax   v1.34.0   Push   True    scalex.io/role=data,scalex.io/storage=ssd,scalex.io/workload=data
edgex   v1.34.0   Push   True    scalex.io/location=edge,scalex.io/pool=gpu,scalex.io/role=edge-gpu
twinx   v1.34.0   Push   True    scalex.io/pool=gpu,scalex.io/role=gpu-render
```

---

## Step 6. demo-nginx 전파

### 목적

Karmada API Server에 Kubernetes 리소스와 PropagationPolicy를 적용했을 때, `twinx`, `edgex`, `datax`로 실제 리소스가 전파되는지 확인한다.

### 적용 대상 manifest

```text
karmada/manifests/demo-nginx/
  00-namespace.yaml
  01-cluster-propagation-policy-namespace.yaml
  10-deployment.yaml
  20-service.yaml
  30-propagation-policy.yaml
```

### 실행 명령

```bash
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config apply \
  -f karmada/manifests/demo-nginx/
```

### Karmada API Server에서 확인

```bash
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config get ns demo
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config get deployment,service -n demo
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config get propagationpolicy -n demo
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config get resourcebinding -n demo
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config get work -A
```

### member cluster에서 확인

```bash
kubectl --context kind-twinx get all -n demo
kubectl --context kind-edgex get all -n demo
kubectl --context kind-datax get all -n demo

kubectl --context kind-twinx get pods -n demo -o wide
kubectl --context kind-edgex get pods -n demo -o wide
kubectl --context kind-datax get pods -n demo -o wide
```

### 기대 결과

- Karmada API Server에는 `demo-nginx` Deployment/Service와 PropagationPolicy가 보인다.
- `twinx`, `edgex`, `datax`에 `demo` namespace가 생성된다.
- `demo-nginx` Deployment replica 3개가 세 cluster에 1개씩 나뉘어 생성된다.
- 각 member cluster에서 `demo-nginx` Pod가 `Running` 상태가 된다.

### 실제 결과 기록

```text
적용 결과:
- namespace/demo created
- clusterpropagationpolicy.policy.karmada.io/demo-namespace-policy created
- deployment.apps/demo-nginx created
- service/demo-nginx created
- propagationpolicy.policy.karmada.io/demo-nginx-policy created

Karmada API Server 상태:
- demo namespace Active
- demo-nginx Deployment status: replicas=3, readyReplicas=3, availableReplicas=3
- demo-nginx-policy 생성됨
- demo-nginx Deployment ResourceBinding: SCHEDULED=True, FULLYAPPLIED=True
- demo-nginx Service ResourceBinding: SCHEDULED=True, FULLYAPPLIED=True
- Work는 twinx/edgex/datax namespace에 각각 생성되고 APPLIED=True

member cluster 실제 상태:
- twinx: demo-nginx Deployment 1/1, Pod Running 1개
- edgex: demo-nginx Deployment 1/1, Pod Running 1개
- datax: demo-nginx Deployment 1/1, Pod Running 1개

replica 분산 결과:
- 원본 Deployment replicas=3
- PropagationPolicy Divided + weight 1:1:1
- twinx/edgex/datax에 각각 replica 1개씩 배치됨

관찰된 특이 상태:
- clusterresourcebinding demo-namespace 는 SCHEDULED=True, FULLYAPPLIED=False 로 남음.
- 하지만 Work는 twinx/edgex/datax 모두 Namespace APPLIED=True.
- 실제 member cluster 세 곳 모두 demo namespace가 Active.
- describe 결과 status.aggregatedStatus에는 datax, edgex만 있고 twinx가 빠져 있음.
- controller-manager 로그에는 twinx Namespace SyncSucceed / ReflectStatusSucceed / AggregateStatusSucceed가 기록됨.
- 실제 기능에는 영향이 없지만 Karmada 상태 집계 이슈 후보로 기록한다.
```

---

## Step 7. 결과 판단

| 검증 항목 | 기대 결과 | 실제 결과 | 성공 여부 | 증거 명령 |
| --- | --- | --- | --- | --- |
| kind cluster 생성 | 4개 cluster 생성 | `tower`, `twinx`, `edgex`, `datax` 생성 및 Ready | 성공 | `kind get clusters`, `kubectl --context kind-* get nodes` |
| Karmada control plane | 주요 Pod Ready | `karmada-system` 주요 Pod 모두 `1/1 Running` | 성공 | `kubectl --context kind-tower get pods -n karmada-system` |
| member cluster 등록 | `twinx/edgex/datax READY=True` | 세 cluster 모두 `Push`, `READY=True` | 성공 | `kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusters -o wide` |
| cluster label | ScaleX 역할 label 표시 | twinx/edgex/datax 역할 label 확인 | 성공 | `kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusters --show-labels` |
| demo-nginx 전파 | 세 member에 Pod Running | twinx/edgex/datax에 Pod 1개씩 Running | 성공 | `kubectl --context kind-{twinx,edgex,datax} get all -n demo` |
| replica 분산 | replicas=3이 1:1:1로 분산 | twinx=1, edgex=1, datax=1 | 성공 | `kubectl --context kind-$c get deploy demo-nginx -n demo` |
| namespace binding 상태 | FullyApplied=True 기대 | 실제 namespace는 전파됐지만 `demo-namespace` ClusterResourceBinding은 `FULLYAPPLIED=False` | 관찰 이슈 | `kubectl --kubeconfig ~/.kube/karmada-apiserver.config get clusterresourcebinding demo-namespace` |

---

## 문제/에러 기록

### 문제 1. Docker/kind 미설치

- 발생 단계: 사전 확인
- 실행 명령: `docker version`, `kind version`
- 에러 메시지:

```text
/bin/bash: line 5: docker: command not found
/bin/bash: line 6: kind: command not found
```

- 원인 추정: 서버에 Docker와 kind가 아직 설치되어 있지 않음.
- 해결 시도: `sudo apt-get install -y docker.io` 실행.
- 해결 여부: Docker 설치 완료. kind 설치는 다음 단계에서 진행.
- 다음 액션: kind binary 설치 후 Docker daemon 상태 확인.

### 문제 2. kind cluster 추가 생성 실패: Too many open files

- 발생 단계: Step 1 kind cluster 생성
- 실행 명령: `kind create cluster --name edgex`, `kind create cluster --name datax`
- 에러 메시지:

```text
ERROR: failed to create cluster: could not find a log line that matches "Reached target .*Multi-User System.*|detected cgroup v1"
```

- 추가 확인 명령:

```bash
kind create cluster --name edgex --retain
docker logs edgex-control-plane
```

- 핵심 로그:

```text
Failed to create control group inotify object: Too many open files
Failed to allocate manager object: Too many open files
```

- 원인 추정: 여러 kind control-plane 컨테이너를 띄우면서 host의 `fs.inotify.max_user_instances` 제한에 걸림.
- 해결 방법:

```bash
sudo sysctl -w fs.inotify.max_user_instances=1024
sudo sysctl -w fs.inotify.max_user_watches=1048576
sudo sysctl -w fs.file-max=2097152
```

- 영구 설정 파일: `/etc/sysctl.d/99-kind-inotify.conf`
- 해결 여부: 해결됨. `edgex`, `datax` 재생성 성공.

### 문제 3. kind 생성 후 kubectl current-context 변경

- 발생 단계: Step 1 kind cluster 생성 이후
- 현상: 사용자가 `kubectl get nodes`를 실행했을 때 원래 MiniX 노드가 사라진 것처럼 보임.
- 원인: `kind create cluster`는 생성한 cluster context로 `kubectl current-context`를 자동 변경한다. 마지막 생성 cluster가 `kind-datax`였기 때문에 기본 `kubectl get nodes`가 MiniX가 아니라 datax를 보고 있었다.
- 확인 명령:

```bash
kubectl config current-context
kubectl config get-contexts
```

- 해결 명령:

```bash
kubectl config use-context kubernetes-admin@cluster.local
```

- 해결 여부: 해결됨. 원래 MiniX 노드 `com1`, `com2`, `com3`, `gpu`, `master` 모두 Ready 확인.

### 문제 4. Karmada install-cli.sh 비대화형 환경 실패

- 발생 단계: Step 2 Karmada CLI/plugin 설치
- 실행 명령:

```bash
curl -s https://raw.githubusercontent.com/karmada-io/karmada/master/hack/install-cli.sh \
  | sudo bash -s kubectl-karmada
```

- 에러 메시지:

```text
main: line 258: /dev/tty: No such device or address
```

- 원인 추정: install script가 비대화형 실행 환경에서 `/dev/tty`를 요구함.
- 해결 방법: Karmada v1.18.0 release tarball을 직접 다운로드하고 sha256 검증 후 `/usr/local/bin/kubectl-karmada`에 수동 설치.
- 해결 여부: 해결됨. `kubectl karmada version` 정상 출력.

### 문제 5. Karmada init /etc/karmada 권한 문제

- 발생 단계: Step 3 Karmada control plane 설치
- 실행 명령:

```bash
kubectl karmada init --context kind-tower
```

- 에러 메시지:

```text
error: failed to create directory: /etc/karmada, error: mkdir /etc/karmada: permission denied
```

- 원인 추정: 기본 Karmada init은 `/etc/karmada` 아래에 인증서/kubeconfig/CRD tarball을 생성하려고 하며 일반 사용자 권한으로는 쓸 수 없다.
- 해결 명령:

```bash
sudo -E kubectl karmada init --kubeconfig /home/chang/.kube/config --context kind-tower
```

- 추가 조치:

```bash
sudo cp /etc/karmada/karmada-apiserver.config /home/chang/.kube/karmada-apiserver.config
sudo chown chang:chang /home/chang/.kube/karmada-apiserver.config
chmod 600 /home/chang/.kube/karmada-apiserver.config
```

- 해결 여부: 해결됨. Karmada control plane 설치 성공.

### 문제 6. kind internal kubeconfig DNS 문제

- 발생 단계: Step 4 member cluster 등록 준비
- 실행 명령:

```bash
kind get kubeconfig --name twinx --internal > /tmp/karmada-kind-kubeconfigs/twinx.kubeconfig
kubectl --kubeconfig /tmp/karmada-kind-kubeconfigs/twinx.kubeconfig get nodes
```

- 에러 메시지:

```text
Unable to connect to the server: dial tcp: lookup twinx-control-plane on 127.0.0.53:53: server misbehaving
```

- 원인 추정: kind internal kubeconfig는 Docker network 내부 DNS 이름을 사용한다. Host에서는 `twinx-control-plane` 이름을 해석하지 못한다.
- 해결 방법: Docker container IP를 조회하고 kubeconfig server를 IP로 바꾼 뒤 `tls-server-name`을 원래 control-plane 이름으로 설정했다.

```bash
# 예: twinx
ip=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' twinx-control-plane)
kubectl --kubeconfig /tmp/karmada-kind-kubeconfigs/twinx.kubeconfig \
  config set-cluster kind-twinx \
  --server=https://${ip}:6443 \
  --tls-server-name=twinx-control-plane
```

- 해결 여부: 해결됨. 수정 kubeconfig로 host에서 member node 조회 성공, Karmada join 성공.

### 문제 7. Namespace ClusterResourceBinding FullyApplied=False 관찰

- 발생 단계: Step 6 demo-nginx 전파 후 상태 확인
- 현상:

```text
clusterresourcebinding demo-namespace: SCHEDULED=True, FULLYAPPLIED=False
```

- 실제 상태:

```text
Work demo namespace: twinx/edgex/datax 모두 APPLIED=True
member namespace: twinx/edgex/datax 모두 demo Active
```

- 상세 관찰:
  - `status.aggregatedStatus`에는 `datax`, `edgex`만 있고 `twinx`가 빠져 있었다.
  - controller-manager 로그에는 `twinx` namespace에 대해 `SyncSucceed`, `ReflectStatusSucceed`가 있었다.
  - Deployment/Service ResourceBinding은 `FULLYAPPLIED=True`였다.
- 영향: 실제 demo-nginx 전파와 Pod 실행에는 영향 없음.
- 상태: Karmada 상태 집계 관련 이슈 후보로 남김. 나중에 재현되면 upstream issue 작성 가능.

---

## ScaleX-POD에 주는 의미

이 실험이 성공하면 다음을 확인한 것이다.

```text
Karmada control plane은 Tower 역할을 할 수 있다.
Karmada member cluster는 TwinX / EdgeX / DataX 역할을 할 수 있다.
GitOps 또는 kubectl로 Karmada API Server에 넣은 리소스는 member cluster로 전파될 수 있다.
```

즉, ScaleX-POD에서 아래 구조를 검토할 근거가 생긴다.

```text
GitHub
  -> ArgoCD on Tower
    -> Karmada API Server on Tower
      -> TwinX / EdgeX / DataX / Resource Pool
```

---

## 정리/삭제 명령

실험이 끝났거나 처음부터 다시 하고 싶을 때 사용한다.

주의: 아래 명령은 kind 실험 cluster를 삭제한다. 실제 MiniX cluster를 삭제하는 명령은 아니다.

```bash
kind delete cluster --name tower
kind delete cluster --name twinx
kind delete cluster --name edgex
kind delete cluster --name datax
```

확인:

```bash
kind get clusters
kubectl config get-contexts
```

---

## 다음 실험 후보

실험 00이 성공하면 다음 순서로 진행한다.

1. `twinx`에만 배포하는 clusterAffinity 실험
2. `twinx/edgex/datax` replica 가중치 분산 실험
3. OverridePolicy로 cluster별 env/image/nodeSelector 변경 실험
4. cluster taint/failover 실험
5. ArgoCD가 Karmada API Server에 sync하는 GitOps 실험
6. Kueue와 Karmada 역할 분리 실험
