# Phase 4 · 검증, 예외 처리, 외부화된 설정

Phase 3까지 우리는 Book API를 데이터베이스에 완전히 영속화했습니다. 이제 API를 **견고하게(robust)** 만들 차례입니다. 사용자가 빈 제목이나 음수 가격을 보내면 어떻게 막을까요? 존재하지 않는 도서를 조회하면 어떤 형태의 에러를 돌려줘야 할까요? 운영 환경과 개발 환경의 DB 비밀번호는 어떻게 분리할까요?

Phase 4는 바로 이 세 가지 — **입력 검증(Validation)**, **전역 예외 처리(Exception Handling)**, **외부화된 설정(Externalized Configuration)** — 을 다룹니다. 이 셋은 "장난감 API"와 "실무에서 굴러가는 API"를 가르는 핵심 요소입니다.

## 이 Phase에서 다루는 내용

| # | 문서 | 핵심 주제 |
|---|------|-----------|
| 1 | [Bean Validation 입력 검증](01-bean-validation.md) | `jakarta.validation` 애너테이션, Kotlin `@field:` 함정, `@Valid`, 커스텀 검증기 |
| 2 | [전역 예외 처리](02-exception-handling.md) | `@RestControllerAdvice`, 일관된 에러 응답, `ProblemDetail` (RFC 9457) |
| 3 | [외부화된 설정과 프로파일](03-profiles-config.md) | 프로퍼티 우선순위, `application-{profile}.yml`, `@Profile`, 환경 변수 |
| 4 | [@ConfigurationProperties](04-configuration-properties.md) | 타입 안전 설정, 생성자 바인딩, 설정 검증, `@Value` 비교 |

## 학습 목표

이 Phase를 마치면 다음을 할 수 있습니다.

- **Bean Validation** 애너테이션으로 요청 DTO를 선언적으로 검증하고, Kotlin에서 `@field:` use-site target을 올바르게 사용할 수 있다.
- `@RestControllerAdvice`로 **모든 예외를 한곳에서** 처리하고, RFC 9457 표준인 **`ProblemDetail`** 형태로 일관된 에러를 응답할 수 있다.
- **프로파일**로 환경별 설정을 분리하고, 프로퍼티 **우선순위**와 환경 변수 오버라이드를 이해한다.
- **`@ConfigurationProperties`** 로 설정을 타입 안전한 Kotlin 클래스에 바인딩하고 검증할 수 있다.

> [!TIP]
> 검증·예외·설정은 따로 노는 주제가 아닙니다. 검증 실패는 예외로 이어지고(`MethodArgumentNotValidException`), 예외 처리 정책은 환경별 설정(스택트레이스 노출 여부 등)과 맞물립니다. 네 문서를 하나의 흐름으로 읽어 보세요.

## 다음 단계

먼저 사용자가 보낸 입력을 선언적으로 검증하는 Bean Validation부터 시작합니다.

→ [Bean Validation 입력 검증](01-bean-validation.md)
