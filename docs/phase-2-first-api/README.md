# Phase 2 — 첫 번째 REST API 만들기

Phase 1에서 Spring Boot 프로젝트를 생성하고 빌드 도구와 의존성을 이해했다면, 이제 실제로 동작하는 **REST API**를 만들 차례입니다. 이 단계에서는 **도서(Book) 관리 API**를 처음부터 끝까지 구현하면서 Spring Boot 웹 애플리케이션의 핵심 구성 요소를 익힙니다.

## 이 단계에서 만드는 것

우리는 메모리(in-memory)에 도서 데이터를 저장하는 CRUD REST API를 구현합니다. 데이터베이스 연동은 Phase 3에서 JPA로 교체할 예정이므로, 이번 단계에서는 **웹 계층의 구조와 흐름**에 집중합니다.

도서 도메인의 필드 구성은 다음과 같습니다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | `Long` | 도서 식별자 (서버가 자동 생성) |
| `title` | `String` | 제목 |
| `author` | `String` | 저자 |
| `isbn` | `String` | ISBN |
| `price` | `Int` | 가격(원) |
| `publishedAt` | `LocalDate` | 출간일 |

## API 엔드포인트

이번 단계에서 구현할 5개의 엔드포인트입니다.

| 메서드 | 경로 | 설명 | 성공 상태 코드 |
|---|---|---|---|
| `GET` | `/api/books` | 전체 도서 목록 조회 | 200 OK |
| `GET` | `/api/books/{id}` | 단일 도서 조회 | 200 OK |
| `POST` | `/api/books` | 도서 등록 | 201 Created |
| `PUT` | `/api/books/{id}` | 도서 수정 | 200 OK |
| `DELETE` | `/api/books/{id}` | 도서 삭제 | 204 No Content |

## 전체 구조 미리보기

이번 단계가 끝나면 다음과 같은 계층 구조가 완성됩니다.

```
HTTP 요청
   │
   ▼
┌─────────────────────┐
│   BookController     │  ← @RestController (HTTP ↔ DTO 변환)
│   (웹 계층)           │
└──────────┬──────────┘
           │ 호출
           ▼
┌─────────────────────┐
│   BookService        │  ← @Service (비즈니스 로직)
│   (서비스 계층)        │
└──────────┬──────────┘
           │ 사용
           ▼
┌─────────────────────┐
│   ConcurrentHashMap  │  ← 메모리 저장소 (Phase 3에서 JPA로 교체)
│   (저장 계층)          │
└─────────────────────┘
```

## 학습 페이지

1. [진입점 — @SpringBootApplication](01-application-entry-point.md)
2. [DTO와 JSON 직렬화](02-dto-and-serialization.md)
3. [@RestController 구현](03-rest-controller.md)
4. [Service 계층과 DI](04-service-layer.md)
5. [로컬 실행과 테스트](05-local-run-and-test.md)

> **팁**: 이 단계의 코드는 한 번에 다 작성하기보다, 각 페이지를 따라가며 점진적으로 쌓아 올리는 것을 권장합니다. DTO → Service → Controller 순서로 만들면 컴파일 오류 없이 자연스럽게 연결됩니다.

## 다음 단계

먼저 애플리케이션의 시작점인 `@SpringBootApplication`부터 살펴봅니다. [진입점 — @SpringBootApplication](01-application-entry-point.md)으로 이동하세요.
