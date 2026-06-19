# Repository 인터페이스

Entity를 정의했으니 이제 그것을 저장하고 조회할 차례입니다. Spring Data JPA의 진짜 마법은 여기서 드러납니다. **인터페이스만 선언하면 구현체가 자동으로 생성**됩니다. 직접 작성할 코드가 거의 없습니다.

## 1. JpaRepository 상속

Repository는 인터페이스로 선언하고 `JpaRepository<Entity타입, ID타입>`을 상속하기만 하면 됩니다.

```kotlin
package com.example.bookapi.repository

import com.example.bookapi.domain.Book
import org.springframework.data.jpa.repository.JpaRepository

interface BookRepository : JpaRepository<Book, Long>
```

이게 전부입니다. `@Repository` 애너테이션조차 필요 없습니다(Spring Data가 자동 인식). Spring은 애플리케이션 시작 시 이 인터페이스의 **프록시 구현체**를 만들어 빈으로 등록하고, 우리는 그것을 주입받아 사용합니다.

### 상속받는 CRUD 메서드

`JpaRepository`를 상속하면 다음 메서드들을 **공짜로** 얻습니다.

| 메서드 | 설명 |
|--------|------|
| `save(entity)` | 저장 또는 수정 (id가 없으면 INSERT, 있으면 UPDATE) |
| `saveAll(entities)` | 여러 건 일괄 저장 |
| `findById(id): Optional<Book>` | id로 1건 조회 |
| `findAll(): List<Book>` | 전체 조회 |
| `findAll(pageable): Page<Book>` | 페이징 조회 |
| `findAllById(ids)` | 여러 id로 조회 |
| `existsById(id): Boolean` | 존재 여부 확인 |
| `count(): Long` | 전체 개수 |
| `deleteById(id)` | id로 삭제 |
| `delete(entity)` | Entity로 삭제 |
| `deleteAll()` | 전체 삭제 |

> [!NOTE]
> `findById`는 Java의 `Optional<Book>`을 반환합니다. Kotlin에서는 `.orElse(null)`이나 `.getOrNull()`(Kotlin 확장)로 nullable로 변환해 다루는 것이 자연스럽습니다.

## 2. 파생 쿼리 메서드 (Derived Query)

CRUD만으로는 부족합니다. "저자로 검색", "제목에 특정 단어가 포함된 책 검색" 같은 조회가 필요하죠. Spring Data JPA는 **메서드 이름을 파싱해 쿼리를 자동 생성**합니다. 정해진 규칙대로 이름만 지으면 됩니다.

```kotlin
interface BookRepository : JpaRepository<Book, Long> {

    fun findByAuthor(author: String): List<Book>

    fun findByTitleContaining(keyword: String): List<Book>

    fun findByAuthorAndPriceLessThan(author: String, price: Int): List<Book>

    fun findByPublishedAtBetween(start: LocalDate, end: LocalDate): List<Book>

    fun existsByIsbn(isbn: String): Boolean

    fun findByIsbn(isbn: String): Book?

    fun countByAuthor(author: String): Long

    fun deleteByIsbn(isbn: String)
}
```

### 메서드 이름 규칙

메서드 이름은 `[동작] + By + [조건]` 형태로 구성됩니다.

| 키워드 | 예시 메서드 | 생성되는 조건 (JPQL) |
|--------|------------|---------------------|
| `findBy` | `findByAuthor` | `WHERE author = ?` |
| `existsBy` | `existsByIsbn` | 존재 여부 (Boolean) |
| `countBy` | `countByAuthor` | 개수 (Long) |
| `deleteBy` | `deleteByIsbn` | 삭제 |
| `And` / `Or` | `findByAuthorAndIsbn` | `WHERE a=? AND i=?` |
| `Containing` | `findByTitleContaining` | `LIKE %?%` |
| `StartingWith` | `findByTitleStartingWith` | `LIKE ?%` |
| `LessThan` / `GreaterThan` | `findByPriceLessThan` | `WHERE price < ?` |
| `Between` | `findByPublishedAtBetween` | `BETWEEN ? AND ?` |
| `In` | `findByAuthorIn` | `WHERE author IN (?)` |
| `IsNull` / `IsNotNull` | `findByAuthorIsNull` | `IS NULL` |
| `OrderBy...Asc/Desc` | `findByAuthorOrderByPriceDesc` | `ORDER BY price DESC` |

> [!TIP]
> 메서드 이름이 너무 길어지면(조건 4개 이상) 가독성이 떨어집니다. 그럴 때는 다음 절의 `@Query`를 쓰는 것이 낫습니다.

## 3. @Query — 직접 쿼리 작성

복잡한 쿼리는 `@Query`로 직접 작성합니다. 기본은 **JPQL**(Entity 대상 쿼리 언어)이고, `nativeQuery = true`를 주면 진짜 SQL을 씁니다.

```kotlin
interface BookRepository : JpaRepository<Book, Long> {

    // JPQL: 테이블이 아니라 Entity(Book)와 필드(title)를 대상으로 한다
    @Query("SELECT b FROM Book b WHERE b.title LIKE %:keyword%")
    fun searchByTitle(@Param("keyword") keyword: String): List<Book>

    // 특정 가격 이하의 책을 저자별로 정렬
    @Query("SELECT b FROM Book b WHERE b.price <= :max ORDER BY b.author")
    fun findCheaperThan(@Param("max") max: Int): List<Book>

    // 네이티브 SQL (DB 고유 기능이 필요할 때만 사용)
    @Query(
        value = "SELECT * FROM books WHERE author = :author",
        nativeQuery = true,
    )
    fun findByAuthorNative(@Param("author") author: String): List<Book>
}
```

`@Param`으로 메서드 인자를 쿼리의 `:이름` 바인딩 변수와 연결합니다.

> [!WARNING]
> **JPQL ≠ SQL**입니다. JPQL은 테이블/컬럼이 아니라 **Entity 클래스명/프로퍼티명**을 사용합니다. 위 예에서 `Book`, `b.title`은 Kotlin 클래스/프로퍼티 이름이지 테이블/컬럼명이 아닙니다. 네이티브 쿼리는 DB에 종속되므로 H2↔PostgreSQL 전환 시 깨질 수 있어 꼭 필요할 때만 씁니다.

## 4. 페이징과 정렬 (Pageable / Page / Sort)

목록 API는 보통 페이징이 필요합니다. 메서드에 `Pageable`을 받고 `Page<Book>`을 반환하면 됩니다.

```kotlin
interface BookRepository : JpaRepository<Book, Long> {
    fun findByAuthor(author: String, pageable: Pageable): Page<Book>
}
```

```kotlin
// 사용 예: 0번 페이지, 페이지당 20건, 가격 내림차순
val pageable = PageRequest.of(0, 20, Sort.by(Sort.Direction.DESC, "price"))
val page: Page<Book> = bookRepository.findByAuthor("김작가", pageable)

page.content          // 현재 페이지의 List<Book>
page.totalElements    // 전체 건수
page.totalPages       // 전체 페이지 수
page.number           // 현재 페이지 번호
page.hasNext()        // 다음 페이지 존재 여부
```

| 타입 | 역할 | 비고 |
|------|------|------|
| `Pageable` | 페이지 번호·크기·정렬 정보 | `PageRequest.of(...)`로 생성 |
| `Page<T>` | 결과 + **전체 개수**(count 쿼리 추가 실행) | 총 페이지 수가 필요할 때 |
| `Slice<T>` | 결과 + **다음 페이지 유무만** (count 쿼리 없음) | "더 보기" 무한 스크롤에 적합, 더 가벼움 |
| `Sort` | 정렬 조건 | `Sort.by("price").descending()` |

> [!TIP]
> 전체 페이지 수를 화면에 표시할 필요가 없다면(예: 무한 스크롤) `Page` 대신 **`Slice`** 를 쓰세요. 비싼 `COUNT(*)` 쿼리를 생략해 성능이 좋아집니다.

## 5. Entity ↔ DTO 매핑 헬퍼

Phase 2의 `BookService`는 **DTO를 받아 DTO를 돌려주는(DTO-in / DTO-out)** 형태였습니다. 컨트롤러와 주고받는 것은 `CreateBookRequest`·`UpdateBookRequest`·`BookResponse`이고, 그 사이에서만 `Book`을 다룹니다. JPA로 바꾸어도 이 계약은 그대로 유지하므로, 먼저 Entity와 DTO를 변환하는 확장 함수를 마련합니다. (매퍼는 별도 파일이나 서비스 상단 어디에 두어도 됩니다.)

```kotlin
package com.example.bookapi.mapper

import com.example.bookapi.domain.Book
import com.example.bookapi.dto.BookResponse
import com.example.bookapi.dto.CreateBookRequest

// Entity → 응답 DTO
fun Book.toResponse() = BookResponse(
    id = id!!,                  // 영속 후에는 id가 반드시 채워져 있으므로 !! 가 안전하다
    title = title,
    author = author,
    isbn = isbn,
    price = price,
    publishedAt = publishedAt,
)

// 생성 요청 DTO → 새 Entity (id는 null로 두고 DB가 채우게 한다)
fun CreateBookRequest.toEntity() = Book(
    title = title,
    author = author,
    isbn = isbn,
    price = price,
    publishedAt = publishedAt,
)
```

> [!NOTE]
> Entity의 `id`는 `Long?`(nullable)이지만, `toResponse()`는 **항상 영속화된(save된) Book에 대해서만** 호출됩니다. 저장이 끝나면 DB가 id를 채워 주므로 이 시점의 `id`는 절대 null이 아닙니다. 그래서 `id!!`로 단언해도 안전합니다.

## 6. BookService 리팩터링 (Before → After)

이제 Phase 2의 인메모리 `BookService`를 `BookRepository` 기반으로 바꿉니다. 핵심은 **메서드 시그니처는 그대로 유지되므로 Phase 2의 컨트롤러는 한 줄도 바꾸지 않아도 됩니다**. 저장 방식(메모리 → DB)만 갈아끼우는 것이죠. 이것이 Phase 2에서 계층을 분리하며 약속했던 바로 그 효과입니다.

### Before — 인메모리 Map (Phase 2)

```kotlin
@Service
class BookService {

    // 스레드 안전한 메모리 저장소
    private val store = ConcurrentHashMap<Long, Book>()
    private val idGenerator = AtomicLong(0)

    fun findAll(): List<BookResponse> =
        store.values.sortedBy { it.id }.map { it.toResponse() }

    fun findByAuthor(author: String): List<BookResponse> =
        store.values.filter { it.author == author }.sortedBy { it.id }.map { it.toResponse() }

    fun findById(id: Long): BookResponse =
        (store[id] ?: throw BookNotFoundException(id)).toResponse()

    fun create(request: CreateBookRequest): BookResponse {
        val newId = idGenerator.incrementAndGet()
        val book = Book(newId, request.title, request.author, request.isbn, request.price, request.publishedAt)
        store[newId] = book
        return book.toResponse()
    }

    fun update(id: Long, request: UpdateBookRequest): BookResponse {
        if (!store.containsKey(id)) throw BookNotFoundException(id)
        val updated = Book(id, request.title, request.author, request.isbn, request.price, request.publishedAt)
        store[id] = updated
        return updated.toResponse()
    }

    fun delete(id: Long) {
        store.remove(id) ?: throw BookNotFoundException(id)
    }
}
```

### After — Spring Data JPA

```kotlin
package com.example.bookapi.service

import com.example.bookapi.dto.BookResponse
import com.example.bookapi.dto.CreateBookRequest
import com.example.bookapi.dto.UpdateBookRequest
import com.example.bookapi.exception.BookNotFoundException
import com.example.bookapi.mapper.toEntity
import com.example.bookapi.mapper.toResponse
import com.example.bookapi.repository.BookRepository
import org.springframework.data.repository.findByIdOrNull
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional

@Service
@Transactional(readOnly = true)   // 기본은 읽기 전용 (4장에서 설명)
class BookService(
    private val bookRepository: BookRepository,   // 생성자 주입
) {
    fun findAll(): List<BookResponse> =
        bookRepository.findAll().map { it.toResponse() }

    fun findByAuthor(author: String): List<BookResponse> =
        bookRepository.findByAuthor(author).map { it.toResponse() }

    // findByIdOrNull은 Spring Data Kotlin 확장 (Optional → Book?)
    fun findById(id: Long): BookResponse =
        bookRepository.findByIdOrNull(id)?.toResponse() ?: throw BookNotFoundException(id)

    @Transactional   // 쓰기 작업은 읽기 전용을 해제
    fun create(request: CreateBookRequest): BookResponse =
        bookRepository.save(request.toEntity()).toResponse()

    @Transactional
    fun update(id: Long, request: UpdateBookRequest): BookResponse {
        val book = bookRepository.findByIdOrNull(id) ?: throw BookNotFoundException(id)
        book.title = request.title
        book.author = request.author
        book.isbn = request.isbn
        book.price = request.price
        book.publishedAt = request.publishedAt
        return book.toResponse()   // 변경 감지(dirty checking)로 자동 UPDATE (save 호출 불필요)
    }

    @Transactional
    fun delete(id: Long) {
        if (!bookRepository.existsById(id)) throw BookNotFoundException(id)
        bookRepository.deleteById(id)
    }
}
```

달라진 점을 정리하면 다음과 같습니다.

- **시그니처는 동일**: `findAll`/`findByAuthor`/`findById`/`create`/`update`/`delete` 6개 메서드 모두 입·출력 타입이 Phase 2와 똑같습니다. 그래서 컨트롤러는 그대로 둡니다.
- **저장소 코드가 사라졌다**: `ConcurrentHashMap`, `AtomicLong`, 수동 ID 채번 → 전부 JPA가 처리.
- **ID 생성**: `@GeneratedValue(IDENTITY)`로 DB가 채번하므로 `save()`만 호출하면 된다.
- **`update`는 변경 감지로**: Phase 2처럼 객체를 통째로 갈아끼우지 않고, 영속 상태인 `Book`의 필드를 바꾸기만 합니다. 트랜잭션이 끝날 때 Hibernate가 자동으로 `UPDATE`를 날립니다(`save()` 호출 불필요). 자세한 내용은 다음 문서에서 다룹니다.
- **`@Transactional` 등장**: 트랜잭션 경계를 명시. 다음 문서의 주제다.

> [!NOTE]
> `findByIdOrNull`은 `org.springframework.data.repository.findByIdOrNull` 패키지의 Kotlin 확장 함수로, `findById(id).orElse(null)`을 간결하게 표현합니다. import만 추가하면 쓸 수 있습니다.

## 다음 단계

`BookService`에 등장한 `@Transactional`이 무엇이고, 왜 어디에 붙여야 하는지를 다음 문서에서 자세히 다룹니다. 영속성 컨텍스트의 경계와도 직결되는 핵심 주제입니다.

→ [트랜잭션 관리](04-transactions.md)
