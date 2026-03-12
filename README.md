# MiniX
---

## Welcome!

이 레포는 Kubernetes 기반 인프라 실습, 오픈소스 도구 활용, 운영 트러블슈팅, 그리고 실전 배포 경험을 한 곳에 모으기 위해 만들어졌습니다.
실습 환경, 인프라 자동화, GitOps, 고가용성(HA) 구성, 운영 노하우, 문제 해결 경험까지 모두 기록합니다.

---

## Repository Structure

- `/kubespray/` : Kubespray를 활용한 클러스터 자동화 배포 실습
- `/kube-vip/` : kube-vip를 통한 Control Plane 고가용성(VIP) 구성
- `/kubeadm/` : kubeadm 기반 클러스터 설치 및 관리
- `/gitops/` : ArgoCD, Flux 등 GitOps 실습 및 선언적 배포 사례
- `/docs/` : 공통 개념, 운영 노트, 트러블슈팅, 비교 분석 등

---

## Cluster Info

아래는 실제 실습/운영 중인 Kubernetes 클러스터의 노드 정보 예시입니다.

<summary><b>MiniX Cluster</b></summary>

<table>
  <thead>
    <tr>
      <th>Node</th>
      <th>역할(Role)</th>
      <th>MGMT IP</th>
      <th>K8S IP</th>
      <th>K8S Version</th>
      <th>OS-Image</th>
      <th>Container Runtime</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>com1</td>
      <td>worker1</td>
      <td>10.34.48.100</td>
      <td>10.34.48.100</td>
      <td>v1.32.2</td>
      <td>Ubuntu 24.04.2 LTS</td>
      <td>containerd://2.0.3</td>
    </tr>
    <tr>
      <td>com2</td>
      <td>worker2</td>
      <td>10.34.48.101</td>
      <td>10.34.48.101</td>
      <td>v1.32.2</td>
      <td>Ubuntu 24.04.2 LTS</td>
      <td>containerd://2.0.3</td>
    </tr>
    <tr>
      <td>com3</td>
      <td>worker3</td>
      <td>10.34.48.102</td>
      <td>10.34.48.102</td>
      <td>v1.32.2</td>
      <td>Ubuntu 24.04.2 LTS</td>
      <td>containerd://2.0.3</td>
    </tr>
    <tr>
      <td>Master</td>
      <td>control-plane</td>
      <td>10.34.48.103</td>
      <td>10.34.48.103</td>
      <td>v1.32.2</td>
      <td>Ubuntu 24.04.2 LTS</td>
      <td>containerd://2.0.3</td>
    </tr>
  </tbody>
</table>

---

## [활용법 및 참고]

- 각 폴더의 README/실습.md 파일에서 상세 실습/설정/트러블슈팅 과정을 확인할 수 있습니다.
- 실습 환경, 버전, 시행착오, 개선점 등도 함께 기록해 두었습니다.
- 실전 운영/학습, 포트폴리오, 팀 내 공유 자료로 활용 가능합니다.

---

## [Contributing & Contact]

- 실습 경험, 트러블슈팅, 개선 제안, 질문 등 언제든 환영합니다!
- Issue, PR, Discussions를 통해 자유롭게 참여해 주세요.

