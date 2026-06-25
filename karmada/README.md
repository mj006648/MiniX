# Karmada 실험실

이 디렉터리는 MiniX 환경에서 **Karmada 멀티클러스터 오케스트레이션**을 연습하고, 실험 과정과 결과를 기록하기 위한 공간입니다.

> 목표: 기존 MiniX/ArgoCD 기반 GitOps 구조를 유지하면서, Karmada를 이용해 여러 Kubernetes 클러스터에 애플리케이션을 전파/스케줄링/장애조치하는 흐름을 단계적으로 이해한다.

---

## 현재 상태

- 작성일: 2026-06-25
- 상태: 계획 수립 단계
- 실제 Karmada 설치: 아직 진행 전
- 우선 실험 방식: `kind` 기반 로컬 멀티클러스터 실습 권장

---

## 왜 바로 MiniX 클러스터에 붙이지 않는가?

MiniX에는 이미 ArgoCD, Rook Ceph, Confluent, Trino, Milvus, Ollama 등 무거운 컴포넌트가 많다.
처음부터 실클러스터를 Karmada 멤버로 붙이면 원인 파악이 어려워질 수 있으므로, 먼저 가벼운 `kind` 클러스터로 Karmada의 동작 원리를 확인한다.

권장 첫 실험 구조:

```text
karmada-host  : Karmada control plane 설치용 클러스터
member1       : 애플리케이션 배포 대상 클러스터 1
member2       : 애플리케이션 배포 대상 클러스터 2
```

---

## 학습/실험 로드맵

### 1단계. Karmada 기본 개념 정리

확인할 것:

- Karmada control plane이 무엇인지
- host cluster와 member cluster의 차이
- Push 모드와 Pull 모드의 차이
- ResourceTemplate / PropagationPolicy / OverridePolicy 역할

관련 기록:

- [`notes/concepts.md`](./notes/concepts.md)

---

### 2단계. kind 기반 실습 클러스터 준비

목표:

- `karmada-host`, `member1`, `member2` 클러스터 생성
- 각 클러스터 kubeconfig/context 확인

예상 명령:

```bash
kind create cluster --name karmada-host
kind create cluster --name member1
kind create cluster --name member2

kubectl config get-contexts
```

관련 기록:

- [`experiments/2026-06-25-00-kind-lab-plan.md`](./experiments/2026-06-25-00-kind-lab-plan.md)

---

### 3단계. Karmada CLI 설치 및 init

목표:

- `karmadactl` 또는 `kubectl-karmada` 설치
- `karmada-host` 클러스터에 Karmada control plane 설치

예상 명령:

```bash
curl -s https://raw.githubusercontent.com/karmada-io/karmada/master/hack/install-cli.sh | sudo bash

kubectl config use-context kind-karmada-host
kubectl karmada init
```

설치 후 확인:

```bash
kubectl get pods -n karmada-system
kubectl get deployments -n karmada-system
kubectl get statefulsets -n karmada-system
```

---

### 4단계. member cluster 등록

목표:

- `member1`, `member2`를 Karmada에 등록
- Push 모드부터 실습

예상 확인:

```bash
kubectl --kubeconfig /etc/karmada/karmada-apiserver.config get clusters
```

---

### 5단계. demo-nginx 전파 실험

목표:

- Karmada API server에 일반 Kubernetes Deployment/Service를 생성
- PropagationPolicy로 `member1`, `member2`에 배포
- replica 분산이 어떻게 되는지 확인

예제 매니페스트 위치:

- [`manifests/demo-nginx/`](./manifests/demo-nginx/)

---

### 6단계. ArgoCD와 Karmada 연결

목표:

현재 ArgoCD 흐름:

```text
ArgoCD -> MiniX cluster에 직접 배포
```

Karmada 실험 후 목표 흐름:

```text
ArgoCD -> Karmada API server에 배포
       -> Karmada가 member cluster로 전파
```

검증할 것:

- ArgoCD에 Karmada API server를 cluster로 등록할 수 있는지
- ArgoCD Application의 destination을 Karmada API server로 지정했을 때 정상 sync되는지
- Karmada 정책 리소스와 일반 Kubernetes 리소스를 GitOps로 관리할 수 있는지

---

## 실험 기록 방식

각 실험은 `experiments/` 아래에 날짜별 Markdown으로 기록한다.

권장 형식:

```markdown
# 실험명

## 목적

## 환경

## 실행 명령

## 결과

## 문제/에러

## 해결 방법

## 다음 액션
```

---

## 디렉터리 구조

```text
karmada/
  README.md                         # 전체 계획과 현재 상태
  notes/
    concepts.md                     # 개념 정리
  experiments/
    2026-06-25-00-kind-lab-plan.md  # 첫 실험 계획/기록
  manifests/
    demo-nginx/                     # 첫 전파 실험용 예제 YAML
```
