# Karmada 실험 진행표

이 디렉터리는 MiniX/kind Lab에서 Karmada 기능을 하나씩 검증하고, ScaleX-POD 설계에 필요한 근거를 남기는 공간이다.

## 실험 원칙

각 실험은 다음을 반드시 기록한다.

- 목적
- 가설
- 실행 명령
- 기대 결과
- 실제 결과
- 성공/실패 판단
- 문제/에러
- ScaleX-POD에 주는 의미
- 다음 액션

---

## 진행된 실험

| 번호 | 문서 | 주제 | 상태 | 핵심 결과 |
| --- | --- | --- | --- | --- |
| 00 | [`2026-06-25-00-kind-lab-plan.md`](./2026-06-25-00-kind-lab-plan.md) | kind 기반 Karmada Lab 구성 | 성공 | `tower/twinx/edgex/datax` 구성, Karmada Push 등록, demo-nginx 1:1:1 전파 성공 |
| 01 | [`2026-06-25-01-cluster-affinity-twinx-only.md`](./2026-06-25-01-cluster-affinity-twinx-only.md) | labelSelector로 twinx-only 배치 | 부분 성공 | Deployment/Service/Pod는 twinx에만 배치, namespace는 다른 member에도 생성됨 |
| 02 | [`2026-06-25-02-namespace-auto-propagation.md`](./2026-06-25-02-namespace-auto-propagation.md) | namespace 자동 생성 동작 확인 | 관찰 완료 | Namespace 정책 없이도 workload namespace가 모든 member에 자동 생성되는 현상 확인 |
| 03 | [`2026-06-25-03-weighted-replica-scheduling.md`](./2026-06-25-03-weighted-replica-scheduling.md) | weighted replica 분산 | 성공 | replicas=6, weight 4:1:1을 twinx=4/edgex=1/datax=1로 분산 |
| 04 | [`2026-06-25-04-override-policy-env.md`](./2026-06-25-04-override-policy-env.md) | OverridePolicy env 변경 | 성공 | 같은 Deployment를 twinx/edgex/datax에 배포하면서 cluster별 env를 다르게 적용 |
| 05 | [`2026-06-25-05-cluster-taint-failover.md`](./2026-06-25-05-cluster-taint-failover.md) | cluster taint/toleration/failover | 부분 성공 | 새 workload는 taint된 twinx를 회피, toleration workload는 twinx 허용, 기존 workload 자동 eviction은 미확인 |

---

## 다음 실험 후보

| 우선순위 | 주제 | ScaleX-POD에서 의미 |
| --- | --- | --- |
| 1 | 실제 cluster 장애 failover | TwinX API/cluster NotReady 시 기존 workload 이동 여부 확인 |
| 2 | WorkloadRebalancer / reschedule | taint 해제 후 또는 정책 변경 후 기존 ResourceBinding 재균형 |
| 3 | OverridePolicy image/storageClass | EdgeX/DataX/TwinX별 image registry와 storageClass 차이 반영 |
| 4 | spreadConstraints | zone/role/provider 기준 분산 배치 |
| 5 | ArgoCD -> Karmada API Server | GitOps 흐름 검증 |
| 6 | Kueue와 조합 | cluster 배치는 Karmada, cluster 내부 job admission은 Kueue로 분리 |
| 7 | Pull mode | EdgeX처럼 외부에서 직접 접근하기 어려운 cluster 후보 검증 |

---

## 현재 우선순위

```text
1. 실제 cluster 장애 failover
2. WorkloadRebalancer / reschedule
3. OverridePolicy image/storageClass
4. ArgoCD 연동
5. Pull mode 후보 검토
```
