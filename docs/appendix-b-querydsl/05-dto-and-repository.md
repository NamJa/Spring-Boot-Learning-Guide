# 05. DTO 프로젝션 & 리포지토리 통합

마지막 페이지입니다. 엔티티 대신 **DTO로 결과를 받는 프로젝션**, Querydsl을 Spring Data 리포지토리에 자연스럽게 녹이는 **사용자 정의 리포지토리 패턴**, 그리고 Spring Data의 **`Pageable`/`Page` 연동**을 다룹니다.

## 1. DTO 프로젝션

엔티티 전체가 아니라 필요한 필드만 `BookResponse`로 받고 싶을 때 사용합니다. `select`에 변환식을 지정합니다.

```kotlin
data class BookResponse(
    val id: Long,
    val title: String,
    val author: String,
    val isbn: String,
    val price: Int,
    val publishedAt: LocalDate,
)
```

### 1.1 Projections.constructor — 생성자 기반

DTO의 **생성자 파라미터 순서·타입**에 맞춰 값을 매핑합니다. 가장 무난한 방식입니다.

```kotlin
fun findResponses(): List<BookResponse> {
    val book = QBook.book
    return queryFactory
        .select(
            Projections.constructor(
                BookResponse::class.java,
                book.id, book.title, book.author,
                book.isbn, book.price, book.publishedAt,   // 생성자 순서와 일치해야 함
            ),
        )
        .from(book)
        .fetch()
}
```

> [!WARNING]
> `Projections.constructor`는 **컴파일 타임에 순서/타입을 검증하지 못합니다.** 필드 순서를 바꾸면 런타임에야 매핑 오류가 드러납니다. 안전성이 중요하면 아래 `@QueryProjection`을 쓰세요.

### 1.2 Projections.fields — 필드명 기반

생성자 순서 대신 **필드명**으로 매핑합니다. 표현식에 별칭(`as`)을 주면 이름이 달라도 매핑됩니다.

```kotlin
Projections.fields(
    BookResponse::class.java,
    book.id, book.title, book.author, book.isbn, book.price, book.publishedAt,
)
// 이름이 다르면: book.title.`as`("title") 처럼 별칭 지정
```

> [!TIP]
> Kotlin의 `data class`는 보통 `val` + 주생성자라 `Projections.fields`(세터/필드 주입)와 궁합이 나쁠 수 있습니다. **Kotlin에서는 `Projections.constructor` 또는 `@QueryProjection`을 우선** 고려하세요.

### 1.3 @QueryProjection — 가장 타입 안전

DTO 생성자에 `@QueryProjection`을 붙이면, 빌드 시 **DTO의 Q타입(`QBookResponse`)** 이 생성되어 생성자를 타입 안전하게 호출할 수 있습니다.

```kotlin
data class BookResponse @QueryProjection constructor(
    val id: Long,
    val title: String,
    val author: String,
    val isbn: String,
    val price: Int,
    val publishedAt: LocalDate,
)
```

```kotlin
// QBookResponse 생성자를 직접 사용 — 인자 순서/타입을 컴파일러가 검증
fun findResponses(): List<BookResponse> =
    queryFactory
        .select(QBookResponse(book.id, book.title, book.author, book.isbn, book.price, book.publishedAt))
        .from(book)
        .fetch()
```

| 방식 | 타입 안전 | 단점 |
|---|---|---|
| `Projections.constructor` | ✗ (런타임 검증) | 순서 실수 시 런타임 오류 |
| `Projections.fields` | ✗ | 이름 매핑·Kotlin val 궁합 |
| `@QueryProjection` | **○ (컴파일 검증)** | **DTO가 Querydsl에 의존**(import 발생), DTO도 kapt 대상 |

> [!TIP]
> `@QueryProjection`은 가장 안전하지만, DTO가 `com.querydsl` 애너테이션에 의존하게 됩니다. "DTO를 순수하게 유지"하려는 팀은 `Projections.constructor`를, "타입 안전이 최우선"인 팀은 `@QueryProjection`을 선택합니다. 정답은 없으며 팀 컨벤션을 따르세요.

## 2. 사용자 정의 리포지토리 패턴

지금까지는 별도의 `BookQueryRepository`를 만들었습니다. 하지만 실무에서는 **하나의 `BookRepository`** 로 Spring Data의 기본 CRUD와 Querydsl 쿼리를 **모두** 쓰고 싶습니다. 이를 위한 표준 패턴이 **사용자 정의 리포지토리**입니다.

구조는 세 조각입니다.

```
BookRepository (interface)
   ├── extends JpaRepository<Book, Long>     ← 기본 CRUD·파생 쿼리
   └── extends BookRepositoryCustom          ← Querydsl 메서드 선언

BookRepositoryCustom (interface)   ← Querydsl 메서드 시그니처
BookRepositoryImpl  (class)        ← 위 인터페이스의 Querydsl 구현
                                     (이름은 반드시 [리포지토리명]Impl)
```

```
   호출부 (Service)
        │  BookRepository 주입
        ▼
  ┌──────────────────────────────┐
  │ BookRepository               │
  │  : JpaRepository<Book, Long> │──► save/findById/findAll ... (Spring Data 자동 구현)
  │  , BookRepositoryCustom      │──► searchByConditions ...    (BookRepositoryImpl가 구현)
  └──────────────────────────────┘
```

### 2.1 커스텀 인터페이스

```kotlin
interface BookRepositoryCustom {
    fun searchByConditions(title: String?, author: String?, minPrice: Int?): List<BookResponse>
    fun searchPage(cond: BookSearchCond, pageable: Pageable): Page<BookResponse>
}
```

### 2.2 구현 클래스 — 이름 규칙이 핵심

```kotlin
// 클래스 이름은 반드시 "BookRepository" + "Impl"  → BookRepositoryImpl
// 이 규칙을 지켜야 Spring Data가 자동으로 엮어 준다.
class BookRepositoryImpl(
    private val queryFactory: JPAQueryFactory,
) : BookRepositoryCustom {

    private val book = QBook.book

    override fun searchByConditions(
        title: String?, author: String?, minPrice: Int?,
    ): List<BookResponse> =
        queryFactory
            .select(QBookResponse(book.id, book.title, book.author, book.isbn, book.price, book.publishedAt))
            .from(book)
            .where(
                title?.let { book.title.contains(it) },
                author?.let { book.author.eq(it) },
                minPrice?.let { book.price.goe(it) },
            )
            .fetch()

    override fun searchPage(cond: BookSearchCond, pageable: Pageable): Page<BookResponse> {
        TODO("3절에서 구현")
    }
}
```

> [!WARNING]
> 구현 클래스 이름은 반드시 **`[JpaRepository 인터페이스 이름]Impl`** 이어야 합니다(`BookRepository` → `BookRepositoryImpl`). 접미사가 다르면 Spring Data가 찾지 못해 빈 생성에 실패합니다. (접미사는 설정으로 바꿀 수 있지만 기본값을 따르는 것이 좋습니다.)

### 2.3 다중 상속으로 합치기

```kotlin
interface BookRepository :
    JpaRepository<Book, Long>,        // 기본 CRUD
    BookRepositoryCustom {            // Querydsl 메서드
    // 파생 쿼리도 그대로 추가 가능
    fun findByIsbn(isbn: String): Book?
}
```

이제 서비스는 `BookRepository` **하나만** 주입받아 `save()`, `findByIsbn()`, `searchByConditions()`를 모두 호출합니다.

```kotlin
@Service
class BookService(private val bookRepository: BookRepository) {
    fun register(book: Book) = bookRepository.save(book)                    // Spring Data
    fun byIsbn(isbn: String) = bookRepository.findByIsbn(isbn)              // 파생 쿼리
    fun search(t: String?, a: String?, p: Int?) =
        bookRepository.searchByConditions(t, a, p)                          // Querydsl
}
```

## 3. Pageable / Page 연동 — content와 count 분리

Spring Data의 `Page`는 **현재 페이지의 내용**과 **전체 개수**를 모두 담습니다. 따라서 Querydsl로 페이징할 때는 **content 쿼리**와 **count 쿼리**를 따로 실행합니다([03 페이지](03-basic-queries.md)에서 `fetchCount`가 사라진 이유가 여기 있습니다).

```kotlin
data class BookSearchCond(val title: String?, val author: String?, val minPrice: Int?)

override fun searchPage(cond: BookSearchCond, pageable: Pageable): Page<BookResponse> {
    val book = QBook.book

    // (1) content: 현재 페이지 데이터
    val content: List<BookResponse> = queryFactory
        .select(QBookResponse(book.id, book.title, book.author, book.isbn, book.price, book.publishedAt))
        .from(book)
        .where(conds(cond))                       // 조건 재사용
        .orderBy(book.publishedAt.desc())
        .offset(pageable.offset)                  // Pageable이 offset/limit 제공
        .limit(pageable.pageSize.toLong())
        .fetch()

    // (2) count: 전체 개수 (select·orderBy 없이 가볍게)
    val total: Long = queryFactory
        .select(book.count())
        .from(book)
        .where(conds(cond))
        .fetchOne() ?: 0L

    return PageImpl(content, pageable, total)
}

// where 조건을 content/count가 공유
private fun conds(c: BookSearchCond): Array<BooleanExpression?> {
    val book = QBook.book
    return arrayOf(
        c.title?.let { book.title.contains(it) },
        c.author?.let { book.author.eq(it) },
        c.minPrice?.let { book.price.goe(it) },
    )
}
```

> [!TIP]
> **count 쿼리는 가볍게 유지하세요.** `orderBy`, fetch join, 불필요한 select 컬럼은 count에서 빼야 성능에 유리합니다. 마지막 페이지처럼 "content 수 < pageSize"인 경우엔 count 쿼리를 **생략**하는 최적화(`PageableExecutionUtils.getPage`)도 있지만, 입문 단계에서는 명시적 분리로 충분합니다.

## 4. 마무리 — 언제 무엇을 쓰는가

Querydsl을 배웠다고 모든 쿼리를 Querydsl로 쓸 필요는 없습니다. 실무의 표준 분담은 다음과 같습니다.

| 상황 | 도구 |
|---|---|
| 단건 조회, 단순 CRUD | **Spring Data JPA** (`findById`, `save`) |
| 조건 1~2개의 고정 쿼리 | **Spring Data 파생 쿼리** (`findByAuthor`) |
| 동적 검색(조건 가변) | **Querydsl** (다중 `BooleanExpression`) |
| 복잡한 조인·서브쿼리·DTO 프로젝션 | **Querydsl** |

> [!TIP]
> 핵심 결론: **Spring Data JPA(간단) + Querydsl(복잡·동적)** 조합이 2026년 Kotlin·Spring Boot 실무의 표준입니다. 사용자 정의 리포지토리 패턴 덕분에 이 둘을 하나의 인터페이스로 매끄럽게 합칠 수 있습니다.

## 다음 단계

부록 B를 모두 마쳤습니다. 다음 부록에서는 횡단 관심사를 우아하게 분리하는 **AOP**를 다룹니다.

→ [부록 C — AOP](../appendix-c-aop/README.md)
