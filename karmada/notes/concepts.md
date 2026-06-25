# Karmada 개념 정리

## Karmada란?

Karmada는 여러 Kubernetes 클러스터를 하나의 control plane에서 관리하기 위한 멀티클러스터 오케스트레이션 시스템이다.
기존 Kubernetes YAML을 최대한 그대로 사용하면서, 어떤 클러스터에 배포할지와 클러스터별 차이를 정책으로 분리한다.

---

## 핵심 구성

### 1. Host Cluster

Karmada control plane이 설치되는 클러스터다.
일반 애플리케이션이 실제로 실행되는 곳이라기보다는, 멀티클러스터 배포를 조정하는 본부 역할이다.

### 2. Karmada API Server

사용자가 리소스와 정책을 제출하는 중앙 API 서버다.
`kubectl`이나 ArgoCD가 이 API server를 대상으로 YAML을 적용할 수 있다.

### 3. Member Cluster

실제 애플리케이션 Pod가 실행되는 Kubernetes 클러스터다.
Karmada는 사용자가 작성한 정책에 따라 member cluster에 리소스를 전파한다.

---

## 핵심 리소스

### Resource Template

배포할 원본 Kubernetes 리소스다.
예: Deployment, Service, ConfigMap, Secret 등

```text
무엇을 배포할 것인가?
```

### PropagationPolicy

Resource Template을 어느 클러스터로 보낼지 정의하는 정책이다.

```text
어디에 배포할 것인가?
```

예:

- member1에만 배포
- member1/member2에 모두 배포
- replica를 member1/member2에 나눠서 배포
- 특정 label이 붙은 클러스터에만 배포

### OverridePolicy

클러스터별로 설정을 다르게 바꾸는 정책이다.

```text
클러스터마다 무엇을 다르게 바꿀 것인가?
```

예:

- 클러스터별 image registry 변경
- 클러스터별 StorageClass 변경
- 클러스터별 replica 수 변경
- 클러스터별 Service type 변경

---

## Push 모드와 Pull 모드

### Push 모드

Karmada control plane이 member cluster API server에 직접 접근해서 리소스를 적용한다.

장점:

- 구조가 단순하다.
- 처음 학습하기 좋다.

주의:

- Karmada control plane에서 member cluster API server에 접근 가능해야 한다.

### Pull 모드

member cluster 안에 `karmada-agent`가 설치되고, agent가 Karmada control plane에서 작업을 가져간다.

장점:

- member cluster가 외부에서 직접 접근되기 어려운 환경에 적합하다.

주의:

- Push 모드보다 구조가 조금 더 복잡하다.

---

## ArgoCD와 같이 쓸 때의 흐름

기존 흐름:

```text
GitHub MiniX repo
  -> ArgoCD
    -> MiniX Kubernetes cluster
```

Karmada 실험 흐름:

```text
GitHub MiniX repo
  -> ArgoCD
    -> Karmada API server
      -> member1 Kubernetes cluster
      -> member2 Kubernetes cluster
```

즉 ArgoCD는 Karmada API server에 YAML을 넣고, 실제 멤버 클러스터로 보내는 일은 Karmada가 담당한다.
