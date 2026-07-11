# AnoPKI Edition Boundary Matrix

이 문서는 공개 Community 저장소와 비공개 Enterprise 저장소의 소유권과
제품 target을 정의합니다.

## 기본 원칙

- Community는 backend-neutral AnoPKI Core와 OpenSSL adapter를 소유합니다.
- Enterprise는 Community 전체를 재사용하고 Enterprise layer와
  AnoCrypto-C adapter를 추가합니다.
- AnoCrypto-C 구현은 별도 저장소와 SDK가 소유합니다.
- Enterprise/OpenSSL과 Enterprise/AnoCrypto-C는 별도 명시적 target입니다.
- AnoCrypto-C profile에서 OpenSSL 자동 fallback을 금지합니다.
- Community 코드는 MPL-2.0으로 공개합니다.
- Enterprise 전용 파일은 상용 라이선스 경계에서 관리합니다.

## 제품 조립

| Target | 조립 | 기능/릴리즈 상태 |
| --- | --- | --- |
| Community/OpenSSL | Core + OpenSSL adapter | Community 전체 기능; 공개 릴리즈 가능 |
| Enterprise/OpenSSL | Core + OpenSSL adapter + Enterprise layer | Community 전체 + Enterprise 기능; AnoCrypto/KCMVP claim 금지 |
| Enterprise/AnoCrypto-C | Core + AnoCrypto-C adapter + Enterprise layer | 구현 capability만 제공; full parity 전 production release 금지 |

## 에디션 기준표

| 영역 | Community | Enterprise |
| --- | --- | --- |
| 저장소 | Public GitHub | Private GitHub/GitLab |
| 라이선스 | MPL-2.0 | Community-derived MPL files + Commercial/EULA Enterprise files |
| Core | Backend-neutral operation contract | Community Core 재사용 |
| OpenSSL adapter | 소유 및 기본 조립 | 그대로 재사용하는 Enterprise/OpenSSL profile |
| AnoCrypto-C adapter | 없음 | Enterprise 전용, external SDK consumer |
| AnoCrypto-C 구현 | 없음 | 없음; 별도 AnoCrypto-C repo/SDK에서 제공 |
| Backend 선택 | Community/OpenSSL 고정 | Enterprise/OpenSSL 또는 Enterprise/AnoCrypto-C 명시 선택 |
| Fallback | 해당 없음 | 자동 fallback 금지 |
| HSM/KMS/PKCS#11 | 공통 interface/문서/mock 가능 | 실제 provider/vendor adapter |
| 인증/권한 | API key scopes | SSO/OIDC/SAML, RBAC/ABAC, 승인 workflow |
| UI | 없음 또는 최소 demo | 운영자 UI, dashboard, reports |
| 배포 어댑터 | 없음 또는 예제 | Kubernetes, LB, Nginx/Apache/IIS, Java keystore |
| 감사 | 기본 audit events | tamper evidence, SIEM exporter, compliance report |
| 릴리즈 증거 | Community/OpenSSL public baseline | profile별 customer evidence, exact SDK/runtime matrix |
| 지원 | GitHub issues/best-effort | SLA, hotfix, private advisory, migration support |

## 제품 가치

Enterprise의 가치는 AnoCrypto-C 사용 여부 하나가 아니라 Enterprise layer,
provider, 운영 자동화, 감사 대응, 배포 어댑터, 지원과 검증된 패키징에서
나옵니다.
