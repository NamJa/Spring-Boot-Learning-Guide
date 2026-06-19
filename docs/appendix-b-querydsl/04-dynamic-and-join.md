# 04. 동적 쿼리와 조인

이 페이지는 Querydsl을 도입하는 **가장 큰 이유** 두 가지를 다룹니다. 검색 조건이 런타임에 결정되는 **동적 쿼리**, 그리고 연관 엔티티를 함께 다루는 **조인**입니다. 조인 예제에는 부록 A에서 만든 `Category`(다대일)와 `Review`(일대다)를 사용합니다.

```kotlin
// 부록 A에서 추가한 연관관계 (요약)
@Entity
class Book(
    @Id @GeneratedValue var id: Long? = null,
    var title: String, var author: String, var isbn: String,
    var price: Int, var publishedAt: LocalDate,
    @ManyToOne(fetch = FetchType.LAZY)
    var category: Category? = null,                 // 도서 → 분류 (N:1)
    @OneToMany(mappedBy = "book")
    var reviews: MutableList<Review> = mutableListOf(),  // 도서 → 리뷰 (1:N)
)
```

## 1. BooleanBuilder로 조건 누적하기

가장 전통적인 동적 쿼리 방식은 `BooleanBuilder`에 조건을 조건부로 `and`/`or`로 쌓는 것입니다.

```kotlin
fun search(title: String?, author: String?, minPrice: Int?): List<Book> {
    val book = QBook.book
    val builder = BooleanBuilder()

    // 값이 있을 때만 조건을 누적한다
    if (!title.isNullOrBlank()) builder.and(book.title.contains(title))
    if (!author.isNullOrBlank()) builder.and(book.author.eq(author))
    if (minPrice != null) builder.and(book.price.goe(minPrice))

    return queryFactory
        .selectFrom(book)
        .where(builder)          // 누적된 조건을 한 번에 적용
        .fetch()
}
```

동작은 잘 하지만, `if` 블록이 본문을 차지하고 조건 생성 로직을 **재사용하기 어렵다**는 단점이 있습니다.

## 2. 권장 패턴 — where(...)에 다중 BooleanExpression

Querydsl의 `where(...)`는 **여러 개의 조건을 콤마로 받고, 그중 `null`인 것은 무시**합니다. 이 성질을 이용하면 `if` 없이도 동적 쿼리를 만들 수 있습니다. 핵심은 "조건이 없으면 `null`을 반환하는 메서드"를 만드는 것입니다.

```kotlin
@Repository
class BookSearchRepository(
    private val queryFactory: JPAQueryFactory,
) {
    private val book = QBook.book

    fun search(title: String?, author: String?, minPrice: Int?): List<Book> =
        queryFactory
            .selectFrom(book)
            .where(
                titleContains(title),     // null이면 자동 무시
                authorEq(author),
                priceGoe(minPrice),
            )
            .fetch()

    // 조건이 없으면 null → where에서 제외된다
    private fun titleContains(title: String?): BooleanExpression? =
        title?.takeIf { it.isNotBlank() }?.let { book.title.contains(it) }

    private fun authorEq(author: String?): BooleanExpression? =
        author?.takeIf { it.isNotBlank() }?.let { book.author.eq(it) }

    private fun priceGoe(minPrice: Int?): BooleanExpression? =
        minPrice?.let { book.price.goe(it) }
}
```

이 패턴의 장점은 다음과 같습니다.

- **본문이 선언적**입니다. `where`만 봐도 "제목·저자·최소가격으로 검색"임이 한눈에 보입니다.
- **조건 메서드를 재사용**할 수 있습니다. `authorEq`는 다른 쿼리에서도 그대로 씁니다.
- **조합이 가능**합니다. `BooleanExpression`은 `.and()`/`.or()`로 묶어 더 복잡한 조건을 만들 수 있습니다.

```kotlin
// 조건 메서드끼리 조합도 가능
private fun inPriceRange(min: Int?, max: Int?): BooleanExpression? {
    val lower = min?.let { book.price.goe(it) }
    val upper = max?.let { book.price.loe(it) }
    return when {
        lower != null && upper != null -> lower.and(upper)
        else -> lower ?: upper          // 한쪽만 있으면 그것만, 둘 다 없으면 null
    }
}
```

> [!TIP]
> **둘 중 무엇을 쓸까?** 조건이 단순하고 메서드 재사용이 필요하면 **다중 `BooleanExpression`(권장)**, 조건들이 복잡하게 `and`/`or`로 얽혀 동적으로 그룹핑돼야 하면 **`BooleanBuilder`** 가 편합니다. 실무에선 다중 `BooleanExpression`이 기본이고, 정 복잡할 때만 `BooleanBuilder`를 섞습니다.

> [!WARNING]
> `null` 무시는 편리하지만 위험할 수도 있습니다. **모든 조건이 `null`이면 `where`가 비어 전체 조회**가 됩니다. 적어도 하나의 필수 조건을 두거나, 페이징을 강제해 대량 조회를 막으세요.

## 3. 조인

### 3.1 inner join / left join

`join(연관필드, Q별칭)` 형태로 조인합니다. `Category`의 Q타입은 `QCategory.category`입니다.

```kotlin
val book = QBook.book
val category = QCategory.category

// 분류명이 '프로그래밍'인 도서 (inner join)
queryFactory
    .selectFrom(book)
    .join(book.category, category)
    .where(category.name.eq("프로그래밍"))
    .fetch()

// 분류가 없는 도서까지 포함 (left join)
queryFactory
    .selectFrom(book)
    .leftJoin(book.category, category)
    .fetch()
```

### 3.2 fetch join — N+1 해결

부록 A에서 본 **N+1 문제**(연관 엔티티를 지연 로딩하다 쿼리가 폭증)를 Querydsl에서는 `fetchJoin()`으로 해결합니다. 연관 엔티티를 같은 쿼리에서 함께 로딩합니다.

```kotlin
// 도서 + 분류를 한 방의 쿼리로 함께 로딩
queryFactory
    .selectFrom(book)
    .join(book.category, category).fetchJoin()   // ← fetchJoin
    .where(category.name.eq("프로그래밍"))
    .fetch()
```

```sql
-- fetch join이 만드는 SQL (분류를 join으로 함께 select)
select book.*, category.*
from book book
join category category on book.category_id = category.id
where category.name = ?
```

> [!WARNING]
> **컬렉션(1:N) fetch join은 페이징과 함께 쓰면 안 됩니다.** `book.reviews` 같은 일대다를 fetch join하면 결과 행이 뻥튀기되어, `offset`/`limit`을 적용하면 **JPA가 메모리에서 페이징**하게 됩니다(경고 로그 발생). 일대다 + 페이징이 필요하면, ToOne만 fetch join하고 컬렉션은 `@BatchSize`나 별도 조회로 푸는 것이 정석입니다(부록 A 참고).

```kotlin
// 일대다(reviews)와 페이징을 함께? → 안티패턴
queryFactory.selectFrom(book)
    .leftJoin(book.reviews).fetchJoin()   // reviews는 컬렉션
    .offset(0).limit(10)                  // 위험: 메모리 페이징 경고
    .fetch()
```

## 4. 서브쿼리 — JPAExpressions

서브쿼리는 `JPAExpressions`로 작성합니다. 메인 쿼리의 Q타입과 충돌하지 않도록 **서브쿼리용 별칭을 따로** 만드는 점이 중요합니다.

```kotlin
val book = QBook.book
val sub = QBook("sub")     // 서브쿼리 전용 별칭

// 가격이 전체 평균가 이상인 도서
queryFactory
    .selectFrom(book)
    .where(
        book.price.goe(
            JPAExpressions
                .select(sub.price.avg())
                .from(sub),
        ),
    )
    .fetch()
```

```sql
select book.* from book book
where book.price >= (select avg(sub.price) from book sub)
```

`in` 서브쿼리도 가능합니다.

```kotlin
// 리뷰가 하나라도 있는 도서 (review 테이블에 book_id가 존재)
val review = QReview.review
queryFactory
    .selectFrom(book)
    .where(
        book.id.`in`(
            JPAExpressions
                .select(review.book.id)
                .from(review),
        ),
    )
    .fetch()
```

> [!WARNING]
> JPA(JPQL) 표준상 **`from` 절 서브쿼리(인라인 뷰)는 지원되지 않습니다.** `where`/`select` 절 서브쿼리만 가능합니다. from 절 서브쿼리가 꼭 필요하면 쿼리를 둘로 나누거나 네이티브 쿼리를 검토하세요.

## 5. 동적 쿼리 + 조인을 한 번에

지금까지의 패턴을 합치면, 조인이 걸린 검색도 동적으로 깔끔하게 표현됩니다.

```kotlin
fun search(categoryName: String?, minPrice: Int?): List<Book> {
    val book = QBook.book
    val category = QCategory.category
    return queryFactory
        .selectFrom(book)
        .leftJoin(book.category, category).fetchJoin()
        .where(
            categoryName?.let { category.name.eq(it) },   // null이면 무시
            minPrice?.let { book.price.goe(it) },
        )
        .orderBy(book.publishedAt.desc())
        .fetch()
}
```

## 다음 단계

마지막으로, 결과를 DTO로 받고 사용자 정의 리포지토리로 Spring Data와 통합해 봅시다.

→ [05. DTO 프로젝션 & 리포지토리 통합](05-dto-and-repository.md)
