# 실험 00. kind 기반 Karmada Lab 계획

## 목적

MiniX 실클러스터를 바로 건드리지 않고, 로컬 `kind` 클러스터 3개로 Karmada의 기본 동작을 검증한다.

검증 목표:

- Karmada control plane 설치
- member cluster 등록
- PropagationPolicy를 이용한 demo-nginx 전파
- member cluster별 리소스 생성 여부 확인

---

## 실험 환경

예정 구성:

| 이름 | 역할 | 설명 |
| --- | --- | --- |
| karmada-host | host cluster | Karmada control plane 설치 |
| member1 | member cluster | 애플리케이션 배포 대상 1 |
| member2 | member cluster | 애플리케이션 배포 대상 2 |

---

## 예상 작업 순서

### 1. kind 클러스터 생성

```bash
kind create cluster --name karmada-host
kind create cluster --name member1
kind create cluster --name member2
```

확인:

```bash
kubectl config get-contexts
kind get clusters
```

---

### 2. Karmada CLI 설치

```bash
curl -s https://raw.githubusercontent.com/karmada-io/karmada/master/hack/install-cli.sh | sudo bash
```

확인:

```bash
karmadactl version
kubectl karmada version
```

---

### 3. Karmada control plane 설치

```bash
kubectl config use-context kind-karmada-host
kubectl karmada init
```

확인:

```bash
kubectl get pods -n karmada-system
kubectl get deployments -n karmada-system
kubectl get statefulsets -n karmada-system
```

---

### 4. member cluster 등록

Push 모드로 먼저 등록한다.

```bash
kubectl karmada --kubeconfig /etc/karmada/karmada-apiserver.config join member1 \
  --cluster-kubeconfig ~/.kube/config \
  --cluster-context kind-member1

kubectl karmada --kubeconfig /etc/karmada/karmada-apiserver.config join member2 \
  --cluster-kubeconfig ~/.kube/config \
  --cluster-context kind-member2
```

확인:

```bash
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config get clusters
```

---

### 5. demo-nginx 배포

```bash
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config apply -f karmada/manifests/demo-nginx/
```

확인:

```bash
kubectl --context kind-member1 get all -n demo
kubectl --context kind-member2 get all -n demo
```

---

## 결과 기록

아직 실행 전.

| 항목 | 결과 |
| --- | --- |
| kind 클러스터 생성 | 예정 |
| Karmada init | 예정 |
| member1 등록 | 예정 |
| member2 등록 | 예정 |
| demo-nginx 전파 | 예정 |

---

## 문제/에러 기록

아직 없음.

---

## 다음 액션

- 실제 kind 클러스터 생성
- Karmada CLI 설치
- `kubectl karmada init` 실행
