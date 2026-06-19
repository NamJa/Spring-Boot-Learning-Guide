# JPQL

Spring Data JPA의 메서드 이름 쿼리(`findByTitleAndAuthor`)는 편하지만, 조건이 복잡해지면 메서드 이름이 외계어처럼 길어집니다. 그 너머에는 **JPQL(Jakarta Persistence Query Language)** 이 있습니다. JPQL은 SQL과 닮았지만, **테이블이 아니라 엔티티(객체)를 대상으로** 질의한다는 점이 결정적으로 다릅니다.

## 1. JPQL 기본 — 객체를 대상으로 한 질의

SQL은 `book` 테이블을, JPQL은 `Book` **엔티티**를 조회합니다. 별칭(`b`)은 필수이며, `*` 대신 별칭 자체를 select합니다.

```kotlin
@Transactional(readOnly = true)
fun basicJpql() {
    // 엔티티 b 를 그대로 조회
    val books = em.createQuery("select b from Book b where b.price >= 20000", Book::class.java)
        .resultList
}
```

```sql
-- 실제로 번역되어 나가는 SQL
select b.id, b.title, b.author, b.isbn, b.price, b.published_at, b.category_id
from book b
where b.price >= 20000;
```

JPQL의 식별자는 **테이블/컬럼명이 아니라 엔티티 클래스명과 필드명**입니다. `Book`(클래스명, 대소문자 구분), `b.price`(필드명)처럼 씁니다. Spring Data JPA에서는 `@Query`로 감싸 Repository 메서드로 노출합니다.

```kotlin
interface BookRepository : JpaRepository<Book, Long> {
    @Query("select b from Book b where b.author = :author and b.price >= :min")
    fun search(author: String, min: Int): List<Book>
}
```

## 2. 파라미터 바인딩

두 가지 방식이 있습니다. **이름 기준(`:name`)** 을 항상 권장합니다 — 가독성과 안전성 때문입니다.

```kotlin
// 이름 기준 (권장)
em.createQuery("select b from Book b where b.author = :author", Book::class.java)
    .setParameter("author", "김영한")
    .resultList

// 위치 기준 (?1) — 순서가 바뀌면 깨지므로 비권장
em.createQuery("select b from Book b where b.author = ?1", Book::class.java)
    .setParameter(1, "김영한")
    .resultList
```

> [!WARNING]
> 파라미터를 **문자열로 직접 이어 붙이지 마세요**(`"... where b.author = '" + name + "'"`). SQL 인젝션 취약점이 생기고, 바인딩 캐시 이점도 잃습니다. 반드시 `setParameter`(또는 `@Query`의 `:param`)로 바인딩하세요.

## 3. 프로젝션 — 무엇을 select할 것인가

**프로젝션(projection)** 은 select 절에 무엇을 담을지입니다. 세 종류가 있습니다.

### 3-1. 엔티티 프로젝션

```kotlin
// 조회한 Book 은 전부 영속 상태로 관리됨 (변경 감지 대상)
"select b from Book b"
```

### 3-2. 스칼라 프로젝션

```kotlin
// 컬럼/표현식 — 영속성 컨텍스트가 관리하지 않음
"select b.title, b.price from Book b"   // 결과: List<Array<Any>>
```

### 3-3. DTO 프로젝션 — `new` 구문 (실무 핵심)

특정 필드만 골라 **DTO로 직접 매핑**합니다. 화면에 필요한 데이터만 가볍게 가져올 때 씁니다.

```kotlin
package com.example.bookapi.dto

// 생성자가 있는 일반 클래스 (Kotlin data class 가능)
data class BookSummary(val title: String, val author: String, val price: Int)
```

```kotlin
@Query(
    """
    select new com.example.bookapi.dto.BookSummary(b.title, b.author, b.price)
    from Book b
    where b.price >= :min
    """
)
fun findSummaries(min: Int): List<BookSummary>
```

> [!TIP]
> `new` 구문에는 **DTO의 전체 패키지 경로(FQCN)** 를 적어야 하고, **생성자의 인자 순서·타입이 정확히 일치**해야 합니다. 길고 깨지기 쉽죠. 이 불편함이 바로 [부록 B Querydsl](../appendix-b-querydsl/README.md)에서 타입 안전 DTO 프로젝션으로 깔끔히 해결됩니다.

## 4. 페이징 — setFirstResult / setMaxResults

JPQL 페이징은 DB 방언(dialect)에 맞는 `LIMIT`/`OFFSET`을 JPA가 알아서 만들어 줍니다.

```kotlin
em.createQuery("select b from Book b order by b.id desc", Book::class.java)
    .setFirstResult(20)   // offset: 21번째부터
    .setMaxResults(10)    // limit: 10개
    .resultList
```

Spring Data JPA에서는 `Pageable`이 이 둘을 대신 처리하므로 직접 쓸 일은 드뭅니다([Phase 3-3](../phase-3-data-jpa/03-repository.md)의 `Page<Book>` 참고). 원리는 위와 같습니다.

## 5. 조인 — 내부 / 외부 / 페치

```kotlin
// 내부 조인 — 연관 경로로 조인
"select b from Book b join b.category c where c.name = :name"

// 외부 조인 — category 가 없는 Book 도 포함
"select b from Book b left join b.category c"

// 세타 조인(연관 없는 조인) — from 절에 나열
"select b from Book b, Category c where b.title = c.name"
```

**페치 조인(`join fetch`)** 은 [04장](04-proxy-fetch.md)에서 본 N+1 해결의 핵심입니다. 일반 조인과 달리 **연관 엔티티까지 함께 영속 상태로 로딩**합니다.

```kotlin
// 일반 조인: category 로 필터링만, b.category 는 여전히 프록시 (지연 로딩 대상)
"select b from Book b join b.category c where c.name = '소설'"

// 페치 조인: b.category 까지 즉시 함께 로딩 → 이후 접근해도 추가 SELECT 없음
"select b from Book b join fetch b.category"
```

> [!WARNING]
> 컬렉션(`@OneToMany`, 예: `b.reviews`) 페치 조인은 **결과가 중복**됩니다(책 1권에 리뷰 3개면 3행). `select distinct b ...`로 애플리케이션 레벨 중복을 제거하거나, 페이징이 필요하면 페치 조인 대신 **배치 페치**(`default_batch_fetch_size`)를 쓰세요([04장 4절](04-proxy-fetch.md)).

## 6. 벌크 연산 — executeUpdate와 영속성 컨텍스트

여러 행을 한 번에 수정/삭제할 때는 **벌크 연산**을 씁니다. 변경 감지는 엔티티를 하나씩 처리하므로, 수만 건을 한 번에 바꿀 땐 비효율적이기 때문입니다.

```kotlin
@Modifying          // Spring Data JPA: UPDATE/DELETE JPQL 임을 표시
@Query("update Book b set b.price = b.price * 11 / 10 where b.publishedAt < :date")
fun raisePriceForOldBooks(date: LocalDate): Int   // 반환: 영향받은 행 수
```

순수 `EntityManager`로는 `executeUpdate()`입니다.

```kotlin
val affected = em.createQuery("update Book b set b.price = b.price + 1000")
    .executeUpdate()   // DB에 직접 UPDATE, 한 방에 수천 건 처리
```

> [!WARNING]
> 벌크 연산의 **가장 위험한 함정**: 벌크 연산은 영속성 컨텍스트(1차 캐시)를 **거치지 않고 DB에 직접** SQL을 날립니다. 그래서 **벌크 연산 후의 1차 캐시는 DB와 어긋난** 상태가 됩니다. 같은 트랜잭션에서 이미 조회한 엔티티는 옛날 값을 그대로 들고 있습니다.
>
> ```kotlin
> val book = em.find(Book::class.java, 1L)      // price=10000 (1차 캐시)
> em.createQuery("update Book b set b.price = 9999").executeUpdate()  // DB는 9999
> println(book.price)   // 여전히 10000! (1차 캐시는 안 바뀜)
> ```
>
> **해결: 벌크 연산 직후 `em.clear()`로 영속성 컨텍스트를 비우세요.** 이후 다시 조회하면 DB의 최신 값을 가져옵니다. Spring Data JPA에서는 `@Modifying(clearAutomatically = true)`로 자동화할 수 있습니다.

```kotlin
@Modifying(clearAutomatically = true, flushAutomatically = true)
@Query("update Book b set b.price = b.price + 1000")
fun bumpAllPrices(): Int
```

## 7. 문자열 JPQL의 한계 — 그리고 Querydsl 예고

여기까지 JPQL의 힘을 봤지만, **문자열로 쿼리를 쓴다는 사실 자체**가 한계입니다.

- **타입 안전하지 않다.** `b.pirce`(오타)라고 써도 컴파일은 통과하고, **런타임에야** 터집니다. 필드명 변경 시 IDE 리팩터링이 문자열 안까지 못 들어갑니다.
- **동적 쿼리가 지옥이다.** "검색 조건이 입력된 것만 `where`에 추가"하는 화면을 만들려면, 문자열을 `if`로 이어 붙이고 `and`/공백/`where` 유무를 손으로 관리해야 합니다.

```kotlin
// 동적 쿼리를 문자열로 — 끔찍하다
val sb = StringBuilder("select b from Book b where 1=1")
if (author != null) sb.append(" and b.author = :author")
if (minPrice != null) sb.append(" and b.price >= :minPrice")
// 공백 빠뜨리면 "where1=1and..." 로 깨지고, 파라미터 바인딩도 if 로 또 분기...
```

```
문자열 JPQL의 문제
 ├─ 컴파일 시 검증 불가 → 오타가 런타임 예외로
 ├─ 리팩터링 안전성 X   → 필드명 바꿔도 문자열은 그대로
 └─ 동적 쿼리 = 문자열 조립 지옥
```

> [!TIP]
> 이 모든 문제를 **컴파일 타임에 잡아 주는** 타입 안전 쿼리 빌더가 **Querydsl**입니다. `book.author.eq(author)`처럼 메서드 체이닝으로 쿼리를 짜므로 오타는 컴파일 에러가 되고, 동적 쿼리는 `BooleanBuilder`로 우아하게 조립됩니다. 다음 부록에서 본격적으로 다룹니다.

## 다음 단계

부록 A를 마쳤습니다. 영속성 컨텍스트부터 JPQL까지, JPA의 동작 원리를 한 바퀴 돌았습니다. 이제 그 마지막 한계 — **문자열 쿼리의 타입 안전성과 동적 쿼리** 문제를 정면으로 해결하는 Querydsl로 넘어갑니다.

→ [부록 B · Querydsl](../appendix-b-querydsl/README.md)
