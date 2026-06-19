# 전역 예외 처리

지금 우리 API에서 예외가 발생하면 어떤 일이 벌어질까요? 존재하지 않는 도서를 조회해 `BookNotFoundException`이 던져지면, Spring Boot의 기본 에러 처리기가 작동해 다음과 같은 다소 투박한 JSON을 돌려줍니다.

```json
{
  "timestamp": "2026-06-20T01:30:00.123+00:00",
  "status": 500,
  "error": "Internal Server Error",
  "path": "/api/books/999"
}
```

문제가 두 가지입니다. 첫째, **상태 코드가 틀렸습니다** — "도서를 못 찾음"은 500(서버 오류)이 아니라 404(찾을 수 없음)여야 합니다. 둘째, 클라이언트가 무엇이 잘못됐는지 알 수 있는 **상세 정보가 부족**합니다. 검증 실패 시에는 "어떤 필드가 왜 틀렸는지"를 알려줘야 하죠.

이 문서에서는 **모든 예외를 한곳에서** 잡아 의미 있는 HTTP 상태와 일관된 본문으로 변환하는 방법을 배웁니다.

## 1. `@RestControllerAdvice`와 `@ExceptionHandler`

Spring은 컨트롤러에서 던져진 예외를 가로채는 **`@ControllerAdvice`** (REST에서는 `@RestControllerAdvice`)를 제공합니다. 이 클래스 안에 **`@ExceptionHandler`** 메서드를 정의하면, 해당 예외 타입이 발생할 때마다 그 메서드가 호출됩니다.

```
컨트롤러에서 예외 throw
        │
        ▼
@RestControllerAdvice 가 가로챔
        │
        ├─ BookNotFoundException        → handleNotFound()      → 404
        ├─ MethodArgumentNotValidException → handleValidation() → 400
        └─ Exception (그 밖의 모든 것)    → handleGeneric()      → 500
```

`@RestControllerAdvice`는 `@ControllerAdvice` + `@ResponseBody`의 조합으로, 핸들러의 반환값을 자동으로 JSON 본문에 직렬화해 줍니다.

## 2. 일관된 에러 응답 DTO

먼저 모든 에러가 공유할 응답 형태를 정의합니다. 클라이언트는 어떤 에러든 같은 구조를 받게 되어 처리하기 편합니다.

```kotlin
package com.example.bookapi.web

import java.time.OffsetDateTime

data class ErrorResponse(
    val timestamp: OffsetDateTime,   // 발생 시각
    val status: Int,                 // HTTP 상태 코드 (예: 404)
    val error: String,               // 상태 코드의 이름 (예: "Not Found")
    val message: String,             // 사람이 읽을 메시지
    val path: String,                // 요청 경로
    val fieldErrors: List<FieldError> = emptyList(), // 검증 실패 시 필드별 상세
)

data class FieldError(
    val field: String,    // 문제가 된 필드명 (예: "title")
    val message: String,  // 그 필드의 에러 메시지
)
```

## 3. ControllerAdvice 구현

이제 세 종류의 예외를 처리하는 어드바이스를 작성합니다.

```kotlin
package com.example.bookapi.web

import com.example.bookapi.exception.BookNotFoundException
import jakarta.servlet.http.HttpServletRequest
import org.slf4j.LoggerFactory
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import java.time.OffsetDateTime

@RestControllerAdvice
class GlobalExceptionHandler {

    private val log = LoggerFactory.getLogger(javaClass)

    // 1) 도메인 예외 → 404
    @ExceptionHandler(BookNotFoundException::class)
    fun handleNotFound(
        ex: BookNotFoundException,
        request: HttpServletRequest,
    ): ResponseEntity<ErrorResponse> {
        val body = ErrorResponse(
            timestamp = OffsetDateTime.now(),
            status = HttpStatus.NOT_FOUND.value(),
            error = HttpStatus.NOT_FOUND.reasonPhrase,
            message = ex.message ?: "도서를 찾을 수 없습니다",
            path = request.requestURI,
        )
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(body)
    }

    // 2) @Valid 검증 실패 → 400 + 필드별 상세
    @ExceptionHandler(MethodArgumentNotValidException::class)
    fun handleValidation(
        ex: MethodArgumentNotValidException,
        request: HttpServletRequest,
    ): ResponseEntity<ErrorResponse> {
        val fieldErrors = ex.bindingResult.fieldErrors.map {
            FieldError(field = it.field, message = it.defaultMessage ?: "유효하지 않은 값")
        }
        val body = ErrorResponse(
            timestamp = OffsetDateTime.now(),
            status = HttpStatus.BAD_REQUEST.value(),
            error = HttpStatus.BAD_REQUEST.reasonPhrase,
            message = "입력 검증에 실패했습니다",
            path = request.requestURI,
            fieldErrors = fieldErrors,
        )
        return ResponseEntity.badRequest().body(body)
    }

    // 3) 그 밖의 모든 예외 → 500 (스택트레이스는 로그로만, 응답엔 노출 금지)
    @ExceptionHandler(Exception::class)
    fun handleGeneric(
        ex: Exception,
        request: HttpServletRequest,
    ): ResponseEntity<ErrorResponse> {
        log.error("처리되지 않은 예외 발생", ex) // 내부 상세는 서버 로그에만 남긴다
        val body = ErrorResponse(
            timestamp = OffsetDateTime.now(),
            status = HttpStatus.INTERNAL_SERVER_ERROR.value(),
            error = HttpStatus.INTERNAL_SERVER_ERROR.reasonPhrase,
            message = "서버 내부 오류가 발생했습니다",
            path = request.requestURI,
        )
        return ResponseEntity.internalServerError().body(body)
    }
}
```

> [!WARNING]
> 마지막 `Exception` 핸들러에서 `ex.message`나 스택트레이스를 **응답 본문에 그대로 넣지 마세요.** 내부 구현(테이블명, SQL, 파일 경로 등)이 외부에 노출되면 보안 위험입니다. 상세는 **로그**로만 남기고, 클라이언트에는 일반적인 메시지만 돌려줍니다.

이제 검증 실패 시 응답은 다음과 같이 풍부해집니다.

```json
{
  "timestamp": "2026-06-20T01:30:00.123+09:00",
  "status": 400,
  "error": "Bad Request",
  "message": "입력 검증에 실패했습니다",
  "path": "/api/books",
  "fieldErrors": [
    { "field": "title", "message": "제목은 필수입니다" },
    { "field": "price", "message": "가격은 0보다 커야 합니다" }
  ]
}
```

## 4. `@ResponseStatus` — 더 간단한 방식

예외 클래스 자체에 **`@ResponseStatus`** 를 붙이면, 어드바이스 없이도 해당 예외가 자동으로 지정된 상태 코드로 매핑됩니다. 도메인 예외에 잘 어울립니다.

```kotlin
package com.example.bookapi.exception

import org.springframework.http.HttpStatus
import org.springframework.web.bind.annotation.ResponseStatus

@ResponseStatus(HttpStatus.NOT_FOUND) // 이 예외는 항상 404
class BookNotFoundException(id: Long) : RuntimeException("ID가 ${id}인 도서를 찾을 수 없습니다")
```

다만 `@ResponseStatus`만 쓰면 응답 **본문 형태를 커스터마이즈할 수 없습니다.** 본문까지 일관되게 다루려면 결국 `@ExceptionHandler`가 필요합니다. 둘은 함께 쓸 수 있습니다.

## 5. `ProblemDetail` — RFC 9457 표준 (권장)

위에서 만든 `ErrorResponse`는 잘 동작하지만 **우리만의 임의 형태**입니다. API마다 에러 형태가 제각각이면 클라이언트가 매번 새로 적응해야 합니다. 그래서 IETF는 HTTP API 에러의 **표준 형태**를 정의했습니다 — **RFC 9457 (Problem Details for HTTP APIs)**.

Spring Framework 6부터 이를 위한 **`ProblemDetail`** 클래스를 기본 제공합니다(Spring Boot 4.x에 포함). 표준 필드는 다음과 같습니다.

| 필드 | 의미 |
|------|------|
| `type` | 문제 유형을 식별하는 URI (기본 `about:blank`) |
| `title` | 사람이 읽는 짧은 제목 |
| `status` | HTTP 상태 코드 |
| `detail` | 이번 발생에 대한 구체적 설명 |
| `instance` | 문제가 발생한 리소스 URI |
| (확장) | 임의의 커스텀 필드 추가 가능 |

`ProblemDetail`을 사용하도록 어드바이스를 다시 쓰면 다음과 같습니다.

```kotlin
package com.example.bookapi.web

import com.example.bookapi.exception.BookNotFoundException
import org.springframework.http.HttpStatus
import org.springframework.http.ProblemDetail
import org.springframework.web.bind.MethodArgumentNotValidException
import org.springframework.web.bind.annotation.ExceptionHandler
import org.springframework.web.bind.annotation.RestControllerAdvice
import org.springframework.web.context.request.WebRequest
import java.net.URI
import java.time.OffsetDateTime

@RestControllerAdvice
class ProblemDetailExceptionHandler {

    @ExceptionHandler(BookNotFoundException::class)
    fun handleNotFound(ex: BookNotFoundException): ProblemDetail {
        val problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.NOT_FOUND,
            ex.message ?: "도서를 찾을 수 없습니다",
        )
        problem.title = "Book Not Found"
        problem.type = URI.create("https://api.example.com/problems/book-not-found")
        problem.setProperty("timestamp", OffsetDateTime.now()) // 확장 필드
        return problem
    }

    @ExceptionHandler(MethodArgumentNotValidException::class)
    fun handleValidation(ex: MethodArgumentNotValidException): ProblemDetail {
        val problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.BAD_REQUEST,
            "입력 검증에 실패했습니다",
        )
        problem.title = "Validation Failed"
        val errors = ex.bindingResult.fieldErrors.associate {
            it.field to (it.defaultMessage ?: "유효하지 않은 값")
        }
        problem.setProperty("errors", errors) // 필드별 에러를 확장 필드로
        return problem
    }
}
```

핸들러가 `ProblemDetail`을 반환하면 Spring이 자동으로 적절한 상태 코드와 `application/problem+json` Content-Type으로 직렬화합니다. 응답 예시는 다음과 같습니다.

```json
{
  "type": "https://api.example.com/problems/book-not-found",
  "title": "Book Not Found",
  "status": 404,
  "detail": "ID가 999인 도서를 찾을 수 없습니다",
  "instance": "/api/books/999",
  "timestamp": "2026-06-20T01:30:00.123+09:00"
}
```

검증 실패는 다음과 같습니다.

```json
{
  "type": "about:blank",
  "title": "Validation Failed",
  "status": 400,
  "detail": "입력 검증에 실패했습니다",
  "instance": "/api/books",
  "errors": {
    "title": "제목은 필수입니다",
    "price": "가격은 0보다 커야 합니다"
  }
}
```

> [!TIP]
> **신규 프로젝트라면 `ProblemDetail`을 권장합니다.** 표준이라 클라이언트 라이브러리·문서화 도구(OpenAPI)와 호환이 좋고, 직접 DTO를 유지보수할 필요가 없습니다. 기존에 커스텀 `ErrorResponse`를 쓰던 프로젝트라도 점진적으로 옮겨가는 것을 고려하세요.

## 6. `ResponseEntityExceptionHandler` 상속

Spring MVC 내부 예외(잘못된 JSON 본문 → `HttpMessageNotReadableException`, 지원하지 않는 메서드 → `HttpRequestMethodNotSupportedException` 등)까지 일관되게 다루려면, 어드바이스가 **`ResponseEntityExceptionHandler`** 를 상속하면 됩니다. 이 추상 클래스는 표준 MVC 예외들을 이미 `ProblemDetail` 기반으로 처리하므로, 우리는 도메인 예외만 추가로 오버라이드/추가하면 됩니다.

```kotlin
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler

@RestControllerAdvice
class GlobalExceptionHandler : ResponseEntityExceptionHandler() {
    // MVC 표준 예외(400, 405, 415 등)는 부모가 ProblemDetail 로 처리.
    // 여기서는 도메인 예외만 추가한다.
    @ExceptionHandler(BookNotFoundException::class)
    fun handleNotFound(ex: BookNotFoundException): ProblemDetail = /* ... */
        ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.message ?: "")
}
```

## 다음 단계

이제 검증과 예외가 견고해졌습니다. 다음은 환경마다 다른 설정값(DB 주소, 비밀번호, 기능 플래그 등)을 코드 밖으로 빼내는 외부화된 설정과 프로파일을 다룹니다.

→ [외부화된 설정과 프로파일](03-profiles-config.md)
