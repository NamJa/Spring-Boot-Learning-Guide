# Service 계층과 DI

컨트롤러가 모든 일을 직접 하면 어떻게 될까요? HTTP 파싱, 비즈니스 로직, 데이터 저장이 한 클래스에 뒤섞여 테스트도 어렵고 재사용도 안 됩니다. 그래서 우리는 **서비스 계층(service layer)**을 둡니다.

## 1. 왜 서비스 계층인가 — 관심사의 분리

각 계층의 책임을 명확히 나누는 것이 **관심사의 분리(separation of concerns)**입니다.

| 계층 | 책임 | 알아야 할 것 / 몰라야 할 것 |
|---|---|---|
| **Controller** | HTTP ↔ 객체 변환, 상태 코드 결정 | HTTP는 알지만, 데이터 저장 방식은 모름 |
| **Service** | 비즈니스 로직, 트랜잭션 경계 | 도메인 규칙은 알지만, HTTP는 모름 |
| **Repository/Store** | 데이터 저장·조회 | 저장 기술(메모리/DB)만 담당 |

이렇게 나누면 얻는 이점:

- **테스트 용이성**: 서비스는 HTTP 없이 단위 테스트할 수 있습니다.
- **재사용**: 같은 서비스 로직을 웹 컨트롤러, 배치, 메시지 컨슈머 등에서 공유할 수 있습니다.
- **교체 용이성**: 저장소를 메모리에서 JPA로 바꿔도(Phase 3) 서비스 인터페이스는 그대로일 수 있습니다.

## 2. @Service와 의존성 주입(DI)

`@Service`는 `@Component`의 특수형으로, "이 클래스는 비즈니스 로직을 담은 빈"임을 나타냅니다. `@ComponentScan`이 이를 발견해 컨테이너에 등록하고, `BookController`가 생성될 때 자동으로 주입합니다.

```kotlin
// 컨트롤러는 생성자 파라미터로 받기만 하면, Spring이 알아서 주입
class BookController(private val bookService: BookService)
```

> **Kotlin과 생성자 주입**: Spring은 **생성자 주입(constructor injection)**을 권장합니다. Kotlin의 주 생성자가 이 패턴에 자연스럽게 맞습니다. 생성자가 하나뿐이면 `@Autowired`도 생략할 수 있습니다. `private val`로 받으면 불변이고 테스트 시 가짜 객체를 넣기도 쉽습니다.

## 3. 메모리 저장소 — ConcurrentHashMap + AtomicLong

Phase 3에서 JPA 리포지토리로 교체하기 전까지, 데이터를 **메모리**에 저장합니다. 웹 서버는 여러 스레드가 동시에 요청을 처리하므로, 스레드 안전한 자료구조가 필요합니다.

- **`ConcurrentHashMap<Long, Book>`**: 여러 스레드가 동시에 읽고 써도 안전한 맵.
- **`AtomicLong`**: 동시성 환경에서 안전하게 증가하는 ID 생성기.

먼저 저장소 내부에서 쓸 간단한 도메인 모델을 정의합니다. (이것은 DTO가 아니라 서버 내부 표현입니다. Phase 3에서 JPA 엔티티로 발전합니다.)

`src/main/kotlin/com/example/bookapi/domain/Book.kt`:

```kotlin
package com.example.bookapi.domain

import java.time.LocalDate

data class Book(
    val id: Long,
    val title: String,
    val author: String,
    val isbn: String,
    val price: Int,
    val publishedAt: LocalDate,
)
```

## 4. 커스텀 예외 — BookNotFoundException

존재하지 않는 도서를 조회/수정/삭제할 때 던질 예외를 정의합니다. `@ResponseStatus(HttpStatus.NOT_FOUND)`를 붙이면, 별도 핸들러 없이도 Spring이 이 예외를 **404 응답**으로 변환합니다.

`src/main/kotlin/com/example/bookapi/exception/BookNotFoundException.kt`:

```kotlin
package com.example.bookapi.exception

import org.springframework.http.HttpStatus
import org.springframework.web.bind.annotation.ResponseStatus

@ResponseStatus(HttpStatus.NOT_FOUND)
class BookNotFoundException(id: Long) :
    RuntimeException("ID가 ${id}인 도서를 찾을 수 없습니다.")
```

> **Phase 4 예고**: 지금은 `@ResponseStatus`로 간단히 404를 내지만, Phase 4에서 `@RestControllerAdvice`로 **전역 예외 처리기**를 만들어 일관된 에러 JSON 형식(`{ "code": ..., "message": ... }`)을 응답하도록 개선합니다. 그때 이 `@ResponseStatus`는 제거됩니다.

## 5. 전체 서비스 코드

`src/main/kotlin/com/example/bookapi/service/BookService.kt`:

```kotlin
package com.example.bookapi.service

import com.example.bookapi.domain.Book
import com.example.bookapi.dto.BookResponse
import com.example.bookapi.dto.CreateBookRequest
import com.example.bookapi.dto.UpdateBookRequest
import com.example.bookapi.exception.BookNotFoundException
import org.springframework.stereotype.Service
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong

@Service
class BookService {

    // 스레드 안전한 메모리 저장소 (Phase 3에서 JpaRepository로 교체)
    private val store = ConcurrentHashMap<Long, Book>()
    private val idGenerator = AtomicLong(0)

    // 전체 조회
    fun findAll(): List<BookResponse> {
        return store.values
            .sortedBy { it.id }
            .map { it.toResponse() }
    }

    // 저자로 필터링
    fun findByAuthor(author: String): List<BookResponse> {
        return store.values
            .filter { it.author == author }
            .sortedBy { it.id }
            .map { it.toResponse() }
    }

    // 단건 조회 (없으면 404 예외)
    fun findById(id: Long): BookResponse {
        val book = store[id] ?: throw BookNotFoundException(id)
        return book.toResponse()
    }

    // 생성
    fun create(request: CreateBookRequest): BookResponse {
        val newId = idGenerator.incrementAndGet()
        val book = Book(
            id = newId,
            title = request.title,
            author = request.author,
            isbn = request.isbn,
            price = request.price,
            publishedAt = request.publishedAt,
        )
        store[newId] = book
        return book.toResponse()
    }

    // 수정 (없으면 404 예외)
    fun update(id: Long, request: UpdateBookRequest): BookResponse {
        // 존재 확인
        if (!store.containsKey(id)) throw BookNotFoundException(id)

        val updated = Book(
            id = id,
            title = request.title,
            author = request.author,
            isbn = request.isbn,
            price = request.price,
            publishedAt = request.publishedAt,
        )
        store[id] = updated
        return updated.toResponse()
    }

    // 삭제 (없으면 404 예외)
    fun delete(id: Long) {
        // remove는 없으면 null 반환 → 404 예외
        store.remove(id) ?: throw BookNotFoundException(id)
    }

    // 내부 도메인 → 응답 DTO 변환
    private fun Book.toResponse() = BookResponse(
        id = id,
        title = title,
        author = author,
        isbn = isbn,
        price = price,
        publishedAt = publishedAt,
    )
}
```

코드 해설:

- **`toResponse()` 확장 함수**: 도메인 `Book` → `BookResponse` 변환을 한 곳에 모았습니다. Kotlin 확장 함수로 가독성을 높였습니다.
- **엘비스 연산자 `?:`**: `store[id] ?: throw ...` — 값이 없으면(null이면) 예외를 던지는 관용구입니다. null 안정성을 활용한 깔끔한 처리입니다.
- **PUT은 전체 교체**: `update`는 모든 필드를 새 값으로 바꿉니다(PUT의 의미론). 부분 수정이 필요하면 PATCH를 별도로 구현합니다.
- **정렬**: `ConcurrentHashMap`은 순서를 보장하지 않으므로, 목록 조회 시 `sortedBy { it.id }`로 일관된 순서를 만듭니다.

## 6. 컨트롤러 ↔ 서비스 연결 확인

이제 두 계층이 완성되어 다음과 같이 연결됩니다.

<figure class="flowchart branch-flow">
<ol class="fc-steps">
<li class="fc-step"><span class="fc-num fc-dot"></span><div class="fc-body"><div class="fc-head"><code>BookController.getOne(id)</code></div><div class="fc-desc"><code>bookService.findById(id)</code> 호출</div></div></li>
<li class="fc-step fc-fork"><span class="fc-num fc-dot"></span><div class="fc-body"><div class="fc-head"><code>BookService.findById(id)</code></div><div class="fc-desc"><code>store[id]</code> 조회</div></div></li>
</ol>
<ul class="fc-branches">
<li class="fc-branch"><span class="fc-tag t-yes">있음</span><span class="fc-arrow">→</span><span class="fc-seg"><code>BookResponse</code> 반환</span><span class="fc-status s-200">200 OK</span></li>
<li class="fc-branch"><span class="fc-tag t-no">없음</span><span class="fc-arrow">→</span><span class="fc-seg"><code>BookNotFoundException</code></span><span class="fc-status s-404">404</span></li>
</ul>
</figure>

컨트롤러는 "어떻게 저장되는지" 전혀 모릅니다. 그저 서비스에게 시키고, 결과를 HTTP 응답으로 포장할 뿐입니다. 이것이 계층 분리의 힘입니다.

> **Phase 3 예고**: `BookService` 안의 `ConcurrentHashMap`은 임시방편입니다. Phase 3에서 `JpaRepository<Book, Long>`를 주입받아 실제 DB에 저장하도록 바꿉니다. 그때 컨트롤러는 거의 그대로 둘 수 있다는 점이, 우리가 계층을 분리한 이유를 증명합니다.

## 다음 단계

DTO, 컨트롤러, 서비스가 모두 갖춰졌습니다. 이제 애플리케이션을 실제로 실행하고 모든 엔드포인트를 테스트해 봅니다. [로컬 실행과 테스트](05-local-run-and-test.md)로 이동하세요.
