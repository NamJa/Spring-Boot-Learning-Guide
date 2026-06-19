# Phase 5 · 실전 기능 (Spring Boot 4)

Phase 4까지 우리의 Book API는 데이터를 영속화하고, 입력을 검증하며, 예외를 일관되게 처리하고, 환경별 설정을 분리할 수 있게 되었습니다. 기능적으로는 꽤 완성된 모습입니다. 하지만 실제 서비스로 배포하려면 **운영(production)에 필요한 횡단 관심사**들이 더 필요합니다.

Phase 5는 "내 코드가 잘 도는가"를 넘어 **"세상과 잘 연결되고, 안전하며, 관측 가능하고, 검증된 코드인가"** 를 다룹니다. 구체적으로는 네 가지입니다.

- **다른 서비스를 호출**해야 한다 → 선언적 HTTP 클라이언트
- **아무나 데이터를 바꾸면 안 된다** → 인증/인가 (Spring Security)
- **운영 중 무슨 일이 벌어지는지 알아야 한다** → Actuator와 관측성
- **배포 전에 깨지지 않음을 증명해야 한다** → 테스트 전략

이 네 가지는 모두 Spring Boot가 강력하게 지원하는 영역이며, 특히 **Spring Boot 4 / Spring Framework 7 / Spring Security 7** 에서 API가 크게 현대화되었습니다. 이 Phase는 그 최신 방식을 기준으로 설명합니다.

## 이 Phase에서 다루는 내용

| # | 문서 | 핵심 주제 |
|---|------|-----------|
| 1 | [선언적 HTTP 클라이언트](01-http-interface-client.md) | `RestClient`, `@HttpExchange` 인터페이스, `@ImportHttpServices`, `@Retryable`/`@ConcurrencyLimit` |
| 2 | [Spring Security 7 기초](02-security-basics.md) | `SecurityFilterChain`, Kotlin DSL, BCrypt, CSRF, JWT/OAuth2 Resource Server 소개 |
| 3 | [Actuator와 관측성](03-actuator-observability.md) | health/metrics/info, 커스텀 헬스 인디케이터, Micrometer + OpenTelemetry, Prometheus |
| 4 | [테스트 전략](04-testing.md) | 테스트 슬라이스, `@WebMvcTest`/`@DataJpaTest`/`@SpringBootTest`, `@MockitoBean`, Testcontainers |

## 학습 목표

이 Phase를 마치면 다음을 할 수 있습니다.

- **`@HttpExchange` 인터페이스**로 외부 API 클라이언트를 선언적으로 정의하고, Spring Boot 4의 **`@ImportHttpServices`** 로 등록할 수 있다.
- **`SecurityFilterChain`** 빈과 Kotlin DSL로 Book API의 엔드포인트별 인가 정책을 구성하고, BCrypt로 비밀번호를 안전하게 다룰 수 있다.
- **Actuator**로 헬스/메트릭 엔드포인트를 노출하고, 커스텀 헬스 인디케이터와 Micrometer 커스텀 메트릭을 작성하며, **OpenTelemetry** 기반 분산 추적을 이해한다.
- **테스트 슬라이스**를 적재적소에 골라 쓰고, `@MockitoBean`·AssertJ·Testcontainers로 빠르고 신뢰할 수 있는 테스트를 작성할 수 있다.

> [!TIP]
> 이 네 주제는 "있으면 좋은 것"이 아니라 **운영 배포의 전제 조건**입니다. 보안 없는 API는 사고이고, 관측성 없는 서비스는 장님이며, 테스트 없는 코드는 배포 때마다 도박입니다. Phase 6에서 실제로 배포하기 전에 반드시 갖춰야 할 기반입니다.

## 다음 단계

먼저 우리 서비스가 외부 세계와 통신하는 방법 — 선언적 HTTP 클라이언트부터 시작합니다.

→ [선언적 HTTP 클라이언트](01-http-interface-client.md)
