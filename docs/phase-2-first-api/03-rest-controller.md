# @RestController 구현

이제 실제 HTTP 요청을 받아 처리하는 **웹 계층**을 만듭니다. Spring MVC에서 이 역할을 하는 것이 **컨트롤러(Controller)**이며, REST API에서는 `@RestController`를 사용합니다.

## 1. @RestController와 @RequestMapping

```kotlin
@RestController
@RequestMapping("/api/books")
class BookController(
    private val bookService: BookService,
)
```

- **`@RestController`**: `@Controller` + `@ResponseBody`의 합성 애너테이션입니다. 이 클래스의 모든 메서드 반환값이 **JSON 본문으로 직렬화**되어 응답됩니다. (일반 `@Controller`는 뷰 이름을 반환합니다.)
- **`@RequestMapping("/api/books")`**: 이 컨트롤러의 모든 엔드포인트에 공통 경로 접두사를 붙입니다. 개별 메서드의 경로는 여기에 이어 붙습니다.
- **생성자 주입**: `BookService`를 생성자 파라미터로 받습니다. Spring이 `BookService` 빈을 자동으로 주입(DI)합니다. `BookService`는 다음 페이지에서 만들지만, 먼저 컨트롤러 관점에서 어떻게 쓰는지 봅니다.

## 2. HTTP 메서드 매핑 애너테이션

| 애너테이션 | HTTP 메서드 | 용도 |
|---|---|---|
| `@GetMapping` | GET | 조회 |
| `@PostMapping` | POST | 생성 |
| `@PutMapping` | PUT | 수정(전체 교체) |
| `@DeleteMapping` | DELETE | 삭제 |
| `@PatchMapping` | PATCH | 부분 수정 |

요청 데이터를 메서드 파라미터로 받는 방법은 세 가지입니다.

| 애너테이션 | 받는 위치 | 예 |
|---|---|---|
| `@PathVariable` | URL 경로의 일부 | `/api/books/{id}` 의 `id` |
| `@RequestBody` | 요청 본문(JSON) | POST/PUT 본문 → DTO |
| `@RequestParam` | 쿼리 스트링 | `?author=...` |

## 3. 상태 코드 다루기 — ResponseEntity vs @ResponseStatus

REST API는 적절한 **HTTP 상태 코드**를 돌려줘야 합니다. 두 가지 방식이 있습니다.

### ResponseEntity (세밀한 제어)

상태 코드 + 헤더 + 본문을 모두 직접 제어합니다. 201 Created에 `Location` 헤더를 넣는 등 정밀한 응답에 적합합니다.

```kotlin
return ResponseEntity
    .created(URI.create("/api/books/${created.id}"))  // 201 + Location 헤더
    .body(created)
```

### @ResponseStatus (간단한 선언)

본문만 반환하고 상태 코드는 애너테이션으로 고정합니다. 단순한 경우에 깔끔합니다.

```kotlin
@PostMapping
@ResponseStatus(HttpStatus.CREATED)   // 항상 201
fun create(@RequestBody request: CreateBookRequest): BookResponse { ... }
```

본 가이드는 생성(201+Location)과 삭제(204)에는 의미를 명확히 드러내는 **`ResponseEntity`**를 사용합니다.

## 4. 전체 컨트롤러 코드

`src/main/kotlin/com/example/bookapi/controller/BookController.kt`:

```kotlin
package com.example.bookapi.controller

import com.example.bookapi.dto.BookResponse
import com.example.bookapi.dto.CreateBookRequest
import com.example.bookapi.dto.UpdateBookRequest
import com.example.bookapi.service.BookService
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.DeleteMapping
import org.springframework.web.bind.annotation.GetMapping
import org.springframework.web.bind.annotation.PathVariable
import org.springframework.web.bind.annotation.PostMapping
import org.springframework.web.bind.annotation.PutMapping
import org.springframework.web.bind.annotation.RequestBody
import org.springframework.web.bind.annotation.RequestMapping
import org.springframework.web.bind.annotation.RequestParam
import org.springframework.web.bind.annotation.RestController
import java.net.URI

@RestController
@RequestMapping("/api/books")
class BookController(
    private val bookService: BookService,
) {

    // GET /api/books  또는  GET /api/books?author=한강
    @GetMapping
    fun getAll(
        @RequestParam(required = false) author: String?,
    ): List<BookResponse> {
        return if (author != null) {
            bookService.findByAuthor(author)
        } else {
            bookService.findAll()
        }
    }

    // GET /api/books/{id}
    @GetMapping("/{id}")
    fun getOne(@PathVariable id: Long): BookResponse {
        // 존재하지 않으면 서비스가 BookNotFoundException을 던짐 → 404 (Phase 4에서 전역 처리)
        return bookService.findById(id)
    }

    // POST /api/books
    @PostMapping
    fun create(@RequestBody request: CreateBookRequest): ResponseEntity<BookResponse> {
        val created = bookService.create(request)
        // 201 Created + Location 헤더(생성된 리소스 위치)
        return ResponseEntity
            .created(URI.create("/api/books/${created.id}"))
            .body(created)
    }

    // PUT /api/books/{id}
    @PutMapping("/{id}")
    fun update(
        @PathVariable id: Long,
        @RequestBody request: UpdateBookRequest,
    ): BookResponse {
        // 반환값만 있으면 기본 200 OK
        return bookService.update(id, request)
    }

    // DELETE /api/books/{id}
    @DeleteMapping("/{id}")
    fun delete(@PathVariable id: Long): ResponseEntity<Void> {
        bookService.delete(id)
        return ResponseEntity.noContent().build()  // 204 No Content
    }
}
```

핵심 포인트:

- **반환값 처리**: `getAll`, `getOne`, `update`는 DTO를 그대로 반환합니다. `@RestController`가 자동으로 JSON 직렬화 + 기본 200 OK 응답을 만듭니다.
- **`@RequestParam(required = false) author: String?`**: 쿼리 파라미터는 선택적이며, 없으면 `null`이 들어옵니다. nullable 타입으로 받는 것이 Kotlin다운 방식입니다.
- **404 처리**: `getOne`에서 없는 `id`를 조회하면 서비스가 `BookNotFoundException`을 던집니다. 이 예외를 404로 변환하는 전역 핸들러는 Phase 4에서 만듭니다. (지금은 기본적으로 500이 나오므로, 다음 페이지에서 예외에 `@ResponseStatus`를 붙여 404가 나오게 합니다.)

## 5. curl로 각 엔드포인트 테스트

서버가 8080에서 실행 중이라고 가정합니다. (실행 방법은 5번째 페이지 참고)

### POST — 도서 등록 (201)

```bash
curl -i -X POST http://localhost:8080/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "채식주의자",
    "author": "한강",
    "isbn": "9788936433598",
    "price": 13500,
    "publishedAt": "2007-10-30"
  }'
```

응답:

```
HTTP/1.1 201 Created
Location: /api/books/1
Content-Type: application/json
```
```json
{
  "id": 1,
  "title": "채식주의자",
  "author": "한강",
  "isbn": "9788936433598",
  "price": 13500,
  "publishedAt": "2007-10-30"
}
```

### GET 목록 — 전체 조회 (200)

```bash
curl http://localhost:8080/api/books
```
```json
[
  {
    "id": 1,
    "title": "채식주의자",
    "author": "한강",
    "isbn": "9788936433598",
    "price": 13500,
    "publishedAt": "2007-10-30"
  }
]
```

### GET 목록 — 저자 필터 (200)

```bash
curl "http://localhost:8080/api/books?author=한강"
```

`author` 쿼리 파라미터가 `findByAuthor`로 전달되어 해당 저자의 책만 반환됩니다.

### GET 단건 — 단일 조회 (200)

```bash
curl http://localhost:8080/api/books/1
```
```json
{
  "id": 1,
  "title": "채식주의자",
  "author": "한강",
  "isbn": "9788936433598",
  "price": 13500,
  "publishedAt": "2007-10-30"
}
```

### PUT — 수정 (200)

```bash
curl -X PUT http://localhost:8080/api/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "채식주의자 (개정판)",
    "author": "한강",
    "isbn": "9788936433598",
    "price": 15000,
    "publishedAt": "2007-10-30"
  }'
```
```json
{
  "id": 1,
  "title": "채식주의자 (개정판)",
  "author": "한강",
  "isbn": "9788936433598",
  "price": 15000,
  "publishedAt": "2007-10-30"
}
```

### DELETE — 삭제 (204)

```bash
curl -i -X DELETE http://localhost:8080/api/books/1
```
```
HTTP/1.1 204 No Content
```

204 응답에는 본문이 없습니다.

## 6. HTTP 상태 코드 참고표

이 API에서 사용하는 상태 코드 정리입니다.

| 코드 | 의미 | 발생 상황 |
|---|---|---|
| `200 OK` | 성공 | GET, PUT 성공 |
| `201 Created` | 생성됨 | POST 성공, `Location` 헤더 포함 |
| `204 No Content` | 성공, 본문 없음 | DELETE 성공 |
| `400 Bad Request` | 잘못된 요청 | JSON 형식 오류, 검증 실패(Phase 4) |
| `404 Not Found` | 리소스 없음 | 존재하지 않는 `id` 조회/수정/삭제 |
| `415 Unsupported Media Type` | 지원 안 하는 형식 | `Content-Type: application/json` 누락 |
| `500 Internal Server Error` | 서버 오류 | 처리되지 않은 예외 |

## 다음 단계

컨트롤러는 `BookService`에 모든 처리를 위임하고 있습니다. 이제 그 서비스를 만들 차례입니다. [Service 계층과 DI](04-service-layer.md)로 이동하세요.
