# 03. 기본 쿼리

이제 `QBook`으로 실제 쿼리를 작성합니다. 이 페이지에서는 단건/목록 조회, `where` 조건과 비교 연산자, 정렬과 페이징, 그리고 결과를 꺼내는 `fetch` 계열 메서드를 다룹니다. 모든 예제는 `JPAQueryFactory` 빈을 주입받은 리포지토리 안에서 실행한다고 가정합니다.

```kotlin
@Repository
class BookQueryRepository(
    private val queryFactory: JPAQueryFactory,
) {
    private val book = QBook.book   // 모든 메서드에서 재사용
    // ... 아래 예제들이 이 클래스 안의 메서드라고 보면 됩니다.
}
```

## 1. selectFrom — 기본 조회

`selectFrom`은 "이 엔티티 전체를 조회"의 축약형입니다(`select(book).from(book)`과 동일).

```kotlin
// 모든 도서 조회
fun findAll(): List<Book> =
    queryFactory
        .selectFrom(book)
        .fetch()
```

생성되는 JPQL은 대략 다음과 같습니다.

```sql
select book from Book book
```

## 2. where — 조건 걸기

`where`에 조건식을 넣습니다. 조건식은 `book.필드.연산자(값)` 형태로 만듭니다.

```kotlin
// 특정 저자의 도서
fun findByAuthor(author: String): List<Book> =
    queryFactory
        .selectFrom(book)
        .where(book.author.eq(author))
        .fetch()
```

### 2.1 and / or 조합

조건을 여러 개 거는 방법은 두 가지입니다.

```kotlin
// 방법 A: 명시적 .and() 체이닝
queryFactory
    .selectFrom(book)
    .where(
        book.author.eq("김작가")
            .and(book.price.goe(15000)),
    )
    .fetch()

// 방법 B: where(...)에 콤마로 나열 → 자동으로 AND 결합 (권장)
queryFactory
    .selectFrom(book)
    .where(
        book.author.eq("김작가"),
        book.price.goe(15000),
    )
    .fetch()
```

> [!TIP]
> **방법 B(콤마 나열)** 가 더 읽기 좋고, [04 페이지](04-dynamic-and-join.md)의 동적 쿼리 패턴과도 자연스럽게 이어집니다. `or`가 필요할 때만 `.and()`/`.or()` 체이닝을 씁니다.

```kotlin
// OR 조합: 저자가 '김작가'이거나 가격이 30000 이상
queryFactory
    .selectFrom(book)
    .where(
        book.author.eq("김작가")
            .or(book.price.goe(30000)),
    )
    .fetch()
```

## 3. 비교·검색 연산자

Querydsl이 제공하는 주요 연산자입니다. 모두 컴파일러가 타입을 검사합니다(예: `Int` 필드에 문자열을 넣으면 컴파일 에러).

| 연산자 | 의미 | 예시 | SQL 상당 |
|---|---|---|---|
| `eq(v)` | 같다 | `book.author.eq("김작가")` | `= ?` |
| `ne(v)` | 다르다 | `book.author.ne("김작가")` | `<> ?` |
| `goe(v)` | ≥ | `book.price.goe(10000)` | `>= ?` |
| `gt(v)` | > | `book.price.gt(10000)` | `> ?` |
| `loe(v)` | ≤ | `book.price.loe(30000)` | `<= ?` |
| `lt(v)` | < | `book.price.lt(30000)` | `< ?` |
| `between(a,b)` | 범위 | `book.price.between(10000, 30000)` | `between ? and ?` |
| `in(coll)` | 포함 | `book.author.in(listOf("A","B"))` | `in (?, ?)` |
| `like(p)` | LIKE(직접 패턴) | `book.title.like("Spring%")` | `like ?` |
| `contains(s)` | `%s%` 포함 | `book.title.contains("Spring")` | `like %?%` |
| `startsWith(s)` | 접두사 | `book.title.startsWith("Spring")` | `like ?%` |
| `isNull` / `isNotNull` | NULL 검사 | `book.isbn.isNotNull()` | `is (not) null` |

```kotlin
// 가격이 1만~3만원, 제목에 'Spring' 포함, 저자는 목록 중 하나
fun search(): List<Book> =
    queryFactory
        .selectFrom(book)
        .where(
            book.price.between(10000, 30000),
            book.title.contains("Spring"),
            book.author.`in`(listOf("김작가", "이작가")),
        )
        .fetch()
```

> [!WARNING]
> Kotlin에서 `in`은 예약어이므로 백틱으로 감싸 **`` book.author.`in`(...) ``** 라고 써야 합니다. 자주 놓치는 부분입니다.

## 4. 정렬 — orderBy

`orderBy`에 `필드.asc()` / `필드.desc()`를 넘깁니다. 여러 개를 콤마로 주면 우선순위 순으로 적용됩니다.

```kotlin
// 출간일 내림차순, 같으면 가격 오름차순
fun findOrdered(): List<Book> =
    queryFactory
        .selectFrom(book)
        .orderBy(
            book.publishedAt.desc(),
            book.price.asc(),
        )
        .fetch()
```

## 5. 페이징 — offset / limit

```kotlin
// 한 페이지에 10개씩, 2페이지(0-based로 page=1)
fun findPage(page: Int, size: Int): List<Book> =
    queryFactory
        .selectFrom(book)
        .orderBy(book.publishedAt.desc())   // 페이징엔 정렬을 함께 주는 것이 안전
        .offset((page * size).toLong())     // 건너뛸 개수
        .limit(size.toLong())               // 가져올 개수
        .fetch()
```

> [!TIP]
> `offset`/`limit`은 `Long`을 받습니다. `Int`를 넘기면 컴파일 에러가 나므로 `.toLong()`을 붙입니다. Spring Data의 `Pageable`/`Page`와 연동하는 방법은 [05 페이지](05-dto-and-repository.md)에서 다룹니다.

## 6. 결과 꺼내기 — fetch 계열

쿼리를 실제로 실행해 결과를 받는 메서드입니다.

| 메서드 | 반환 | 0건일 때 | 2건 이상일 때 |
|---|---|---|---|
| `fetch()` | `List<T>` | 빈 리스트 | 전부 반환 |
| `fetchOne()` | `T?` | `null` | **예외**(`NonUniqueResultException`) |
| `fetchFirst()` | `T?` | `null` | 첫 건만 (`limit(1)` 내장) |

```kotlin
// 목록
val list: List<Book> = queryFactory.selectFrom(book).fetch()

// 단건 (없으면 null, 2건 이상이면 예외)
val one: Book? = queryFactory
    .selectFrom(book)
    .where(book.isbn.eq("978-89-000-0000-0"))
    .fetchOne()

// 조건에 맞는 첫 건만
val first: Book? = queryFactory
    .selectFrom(book)
    .where(book.author.eq("김작가"))
    .orderBy(book.publishedAt.desc())
    .fetchFirst()
```

### 6.1 fetchCount는 더 이상 쓰지 않는다

과거 Querydsl에는 `fetchCount()`/`fetchResults()`가 있었지만, **deprecated되어 현재 라인에서는 권장하지 않습니다.** 카운트는 별도의 count 쿼리로 명시적으로 작성하세요.

```kotlin
// 권장: count는 select(...count())로 직접
fun countByAuthor(author: String): Long =
    queryFactory
        .select(book.count())             // count(book)
        .from(book)
        .where(book.author.eq(author))
        .fetchOne() ?: 0L
```

> [!WARNING]
> 옛 예제의 `.fetchCount()` / `.fetchResults()`를 그대로 복붙하면 deprecated 경고 또는 미지원 에러를 만납니다. **content 쿼리와 count 쿼리를 분리**하는 방식이 표준이며, 페이징에서 이 분리가 왜 중요한지는 [05 페이지](05-dto-and-repository.md)에서 다룹니다.

## 7. 특정 컬럼만 select

엔티티 전체가 아니라 일부 값만 필요할 때는 `select`에 필드를 지정합니다.

```kotlin
// 제목만 (List<String>)
val titles: List<String> = queryFactory
    .select(book.title)
    .from(book)
    .fetch()

// 여러 컬럼 → Tuple
val rows: List<Tuple> = queryFactory
    .select(book.title, book.price)
    .from(book)
    .fetch()
val firstTitle = rows.firstOrNull()?.get(book.title)
```

> [!TIP]
> `Tuple`은 타입이 약하고 인덱스/키 접근이 번거롭습니다. 여러 컬럼을 꺼낼 때는 **DTO 프로젝션**이 훨씬 깔끔합니다 — [05 페이지](05-dto-and-repository.md)에서 `Projections`와 `@QueryProjection`으로 해결합니다.

## 다음 단계

기본 쿼리를 익혔습니다. 이제 Querydsl의 진짜 강점인 동적 쿼리와 조인으로 넘어갑니다.

→ [04. 동적 쿼리와 조인](04-dynamic-and-join.md)
