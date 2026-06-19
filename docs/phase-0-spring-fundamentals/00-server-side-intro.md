# 서버 사이드 개발 입문

> Kotlin은 알지만 서버는 처음인 분들을 위한 출발점입니다. Spring을 배우기 전에 "서버가 무엇을 하는 소프트웨어인가"부터 정리합니다.

## 1. 서버 사이드 개발이란?

여러분이 그동안 만들어 온 프로그램(안드로이드 앱, CLI 도구, 데스크톱 앱 등)은 대부분 **한 명의 사용자**, 한 대의 기기에서 동작합니다. 반면 **서버**는 다음과 같은 소프트웨어입니다.

- **수많은 클라이언트의 요청을 동시에** 처리한다 (모바일 앱, 웹 브라우저, 다른 서버 등).
- **UI가 없다.** 화면 대신 HTTP 요청을 받아 데이터를 돌려준다.
- **24시간 365일 실행**된다. 사용자가 켜고 끄는 것이 아니라 항상 떠 있다.

```
┌──────────────────────────────────────────────────────────┐
│                    클라이언트 vs 서버                       │
├────────────────────────┬─────────────────────────────────┤
│      클라이언트 앱       │            서버 (Spring Boot)    │
├────────────────────────┼─────────────────────────────────┤
│ 사용자 1명 / 1기기       │ 동시에 수천~수만 클라이언트       │
│ UI/화면 중심            │ 데이터·비즈니스 로직 중심          │
│ 실행/종료 생명주기 있음   │ 항상 실행 중 (always running)     │
│ 로컬 저장 (파일/SQLite)  │ DB 서버 (PostgreSQL, MySQL …)    │
│ 기기 리소스 제한         │ 서버 리소스 (CPU/RAM/네트워크)    │
│ 앱 스토어/실행파일로 배포 │ JAR / Docker / 클라우드로 배포    │
└────────────────────────┴─────────────────────────────────┘
```

이 가이드에서 우리는 **도서(Book) 관리 REST API** 서버를 Kotlin + Spring Boot로 만들면서 이 개념들을 하나씩 체득합니다.

---

## 2. 클라이언트-서버 통신 구조

클라이언트가 네트워크 라이브러리(예: Retrofit, Ktor Client, `fetch`)로 API를 호출할 때, 그 **반대편에서 요청을 받아 응답을 만드는 쪽**이 바로 우리가 만들 서버입니다.

```
┌─────────────┐          HTTP Request            ┌─────────────────┐
│             │  ──────────────────────────────>  │                 │
│  클라이언트   │  GET /api/books/42               │  Spring Boot    │
│  (앱/웹/etc) │  Host: api.example.com           │  서버 (4.1.0)   │
│             │  Authorization: Bearer xxx       │                 │
│             │                                  │  @RestController │
│             │          HTTP Response           │                 │
│             │  <──────────────────────────────  │                 │
│             │  200 OK                          │                 │
│             │  Content-Type: application/json  │                 │
│             │  {"id":42,"title":"이펙티브 코틀린"} │                 │
└─────────────┘                                  └─────────────────┘
```

### HTTP Request의 구성요소

```
POST /api/books HTTP/1.1              ← 메서드 + 경로 + 프로토콜 버전
Host: api.example.com                 ← 헤더 시작
Content-Type: application/json        ← 요청 바디의 형식
Authorization: Bearer eyJhbGci...     ← 인증 토큰
Content-Length: 73                    ← 바디 길이
                                      ← 빈 줄 (헤더와 바디 구분)
{"title":"이펙티브 코틀린","author":"마르친 모스칼라","price":36000}  ← 바디(JSON)
```

| 구성요소 | 설명 | Spring에서 다루는 방법 |
|---|---|---|
| **Method** | GET, POST, PUT, DELETE … | `@GetMapping`, `@PostMapping` … |
| **Path(URL)** | 리소스의 위치 | `@RequestMapping("/api/books")` |
| **Headers** | 메타데이터(인증·타입 등) | `@RequestHeader` |
| **Body** | 전송할 데이터 | `@RequestBody` |

### HTTP Response의 구성요소

```
HTTP/1.1 201 Created                  ← 상태 코드
Content-Type: application/json        ← 응답 바디의 형식
Location: /api/books/43               ← 생성된 리소스 위치
                                      ← 빈 줄
{"id":43,"title":"이펙티브 코틀린", ...}  ← 응답 바디
```

| 구성요소 | 설명 | Spring에서 다루는 방법 |
|---|---|---|
| **Status Code** | 200·201·404·500 … | `ResponseEntity`, `@ResponseStatus` |
| **Headers** | 응답 메타데이터 | `ResponseEntity.headers(...)` |
| **Body** | 응답 데이터 | 반환 객체를 Jackson이 JSON으로 직렬화 |

> **핵심**: 클라이언트 라이브러리가 숨겨주던 HTTP의 세부 사항(메서드·경로·헤더·상태 코드)을, 서버에서는 **직접 설계하고 다루게** 됩니다. Spring Boot는 이 작업을 애너테이션으로 간결하게 만들어 줍니다.

---

## 3. REST API 기초

**REST**(Representational State Transfer)는 HTTP를 활용한 API 설계 관례입니다. "리소스(자원)"를 URL로 표현하고, "행위"를 HTTP 메서드로 표현합니다.

### CRUD와 HTTP 메서드 대응

| 작업 | HTTP 메서드 | URL 예시 | 설명 |
|---|---|---|---|
| **C**reate (생성) | POST | `/api/books` | 새 도서 생성 |
| **R**ead (목록) | GET | `/api/books` | 도서 목록 조회 |
| **R**ead (단건) | GET | `/api/books/42` | 특정 도서 조회 |
| **U**pdate (수정) | PUT | `/api/books/42` | 도서 전체 수정 |
| **U**pdate (부분) | PATCH | `/api/books/42` | 도서 일부 수정 |
| **D**elete (삭제) | DELETE | `/api/books/42` | 도서 삭제 |

### URL 설계 규칙

```
https://api.example.com/api/books/{id}/reviews/{reviewId}
│                       │   │     │      │
│                       │   │     │      └─ 하위 리소스(복수형 명사)
│                       │   │     └─ 리소스 식별자 (Path Variable)
│                       │   └─ 리소스 이름 (복수형 명사)
│                       └─ API 접두사 (버전을 넣기도 함: /api/v1)
└─ 베이스 URL
```

원칙: **URL에는 명사(리소스)를, 행위는 HTTP 메서드로.** `GET /api/getBooks` 같은 동사형 URL은 REST 관점에서 지양합니다.

### 실제 요청/응답 예시

**도서 목록 조회 (GET)**
```http
GET /api/books?page=0&size=20 HTTP/1.1
Host: api.example.com
Accept: application/json
```
```json
{
  "content": [
    { "id": 1, "title": "코틀린 인 액션", "author": "드미트리 제메로프", "price": 38000 },
    { "id": 2, "title": "이펙티브 코틀린", "author": "마르친 모스칼라", "price": 36000 }
  ],
  "totalElements": 2,
  "page": 0,
  "size": 20
}
```

**도서 생성 (POST)**
```http
POST /api/books HTTP/1.1
Host: api.example.com
Content-Type: application/json

{ "title": "코틀린 코루틴", "author": "마르친 모스칼라", "price": 33000 }
```
```http
HTTP/1.1 201 Created
Location: /api/books/3
Content-Type: application/json

{ "id": 3, "title": "코틀린 코루틴", "author": "마르친 모스칼라", "price": 33000 }
```

---

## 4. Stateless — 서버는 기본적으로 상태를 기억하지 않는다

서버는 각 요청을 **독립적으로** 처리합니다. 이전 요청을 기억하지 않으므로, 같은 클라이언트가 두 번 요청해도 서버 입장에서는 별개의 요청입니다.

```
요청 1: GET /api/me  (헤더에 토큰 포함)  → "토큰 확인 후 사용자 정보 응답"
요청 2: GET /api/me  (헤더에 토큰 포함)  → "토큰 확인 후 사용자 정보 응답"
                                          (요청 1의 기억은 없음)
```

이 "기억 없음"을 보완하는 방법:

| 방법 | 설명 | 이 가이드에서 다루는 곳 |
|---|---|---|
| **JWT 토큰** | 클라이언트가 매 요청마다 토큰 전송 (`Authorization: Bearer …`) | Phase 5 (보안) |
| **Session** | 서버가 세션 ID 발급, 서버/Redis에 상태 보관 | Phase 5 (보안) |
| **Database** | 영구 데이터는 DB에 저장 | Phase 3 (JPA) |

> **왜 Stateless가 좋은가?** 서버가 상태를 들고 있지 않으면, 인스턴스를 여러 개로 **수평 확장**하기 쉽습니다. 어떤 인스턴스가 요청을 받아도 결과가 같기 때문입니다. Phase 7에서 Cloud Run이 인스턴스를 0개에서 N개로 자동 확장할 수 있는 것도 이 성질 덕분입니다.

---

## 5. 클라이언트 코드의 "반대편" — 한눈에 보는 대응표

클라이언트에서 API를 **호출**하던 코드와, 서버에서 그 요청을 **처리**하는 Spring 코드를 나란히 놓고 보면 직관적으로 이해됩니다.

```kotlin
// === 클라이언트 (예: Retrofit) — 호출하는 쪽 ===
interface BookApi {
    @GET("/api/books/{id}")
    suspend fun getBook(@Path("id") id: Long): BookResponse

    @POST("/api/books")
    suspend fun createBook(@Body request: CreateBookRequest): BookResponse
}
```

```kotlin
// === 서버 (Spring Boot) — 요청을 받는 쪽 ===
@RestController
@RequestMapping("/api/books")
class BookController(private val bookService: BookService) {

    @GetMapping("/{id}")                              // @GET("/api/books/{id}")의 반대편
    fun getBook(@PathVariable id: Long): BookResponse =
        bookService.findById(id)

    @PostMapping                                      // @POST("/api/books")의 반대편
    @ResponseStatus(HttpStatus.CREATED)               // 201 Created
    fun createBook(@RequestBody request: CreateBookRequest): BookResponse =
        bookService.create(request)
}
```

### 종합 대응표

| 클라이언트 (호출) | Spring 서버 (처리) | 역할 |
|---|---|---|
| `@GET("/path")` | `@GetMapping("/path")` | GET 요청 |
| `@POST("/path")` | `@PostMapping("/path")` | POST 요청 |
| `@PUT` / `@DELETE` | `@PutMapping` / `@DeleteMapping` | 수정/삭제 |
| `@Path("id")` | `@PathVariable id` | 경로 변수 |
| `@Query("key")` | `@RequestParam key` | 쿼리 파라미터 |
| `@Header("Auth")` | `@RequestHeader("Auth")` | 헤더 읽기 |
| `@Body request` | `@RequestBody request` | 요청 바디 → 객체 역직렬화 |
| 응답 객체 자동 파싱 | 반환 객체 자동 직렬화(Jackson) | 응답 바디 |
| `Response<T>` / 상태 코드 | `ResponseEntity<T>` / `@ResponseStatus` | 상태 코드 제어 |

> **좋은 소식**: 서버를 만든다고 새 언어를 배울 필요가 없습니다. Kotlin 문법, 코루틴, 데이터 클래스, 빌더/DSL 같은 실력이 그대로 적용됩니다. 새로 배우는 것은 "프레임워크가 요청을 처리하는 방식" — 즉 Spring의 IoC/DI, 자동 설정, 그리고 웹 계층 애너테이션입니다.

---

## 6. 이 가이드에서 만들 것

우리는 다음 순서로 **도서 관리 REST API**를 키워 나갑니다.

```
Phase 0  서버·Spring 핵심 개념 이해 (지금 여기)
Phase 1  프로젝트 생성 & 빌드 설정
Phase 2  인메모리 저장소로 첫 REST API 완성
Phase 3  Spring Data JPA로 실제 DB 연동
Phase 4  입력 검증 · 예외 처리 · 환경별 설정
Phase 5  HTTP 클라이언트 · 보안 · 관측성 · 테스트
Phase 6  JAR · Docker · 네이티브 이미지로 빌드
Phase 7  Google Cloud Run으로 실제 배포
```

---

## 다음 단계

서버 사이드 개발의 큰 그림을 잡았습니다. 다음 문서 [Spring & Spring Boot 입문](01-what-is-spring.md)에서 Spring이 정확히 무엇이고, Spring Boot가 무엇을 더해 주는지 알아봅니다.
