# 부록 B — Querydsl로 타입 안전한 쿼리 작성하기

**Querydsl**은 Java/Kotlin 코드로 **타입 안전한(type-safe) 쿼리**를 작성하게 해 주는 라이브러리입니다. 즉, 문자열로 된 JPQL을 손으로 조립하는 대신, 컴파일러가 검증해 주는 Kotlin 코드로 SQL/JPQL을 표현합니다.

부록 A에서 우리는 Spring Data JPA의 메서드 이름 쿼리와 `@Query`(JPQL) 문자열을 다뤘습니다. 특히 [부록 A-05](../appendix-a-jpa-advanced/05-jpql.md) 류의 JPQL 문자열은 강력하지만, **검색 조건이 동적으로 바뀌는 순간** 문자열을 `+`로 이어 붙이거나 `if` 분기로 쿼리를 조립하는 지옥이 펼쳐집니다. Querydsl은 바로 이 지점 — **타입 안전성**과 **동적 쿼리** — 에서 빛을 발합니다.

> [!TIP]
> 실무에서 가장 흔한 조합은 **Spring Data JPA(단순 CRUD·파생 쿼리) + Querydsl(복잡·동적 쿼리)** 입니다. 둘은 경쟁 관계가 아니라 보완 관계입니다. 본 부록의 목표는 이 조합을 자연스럽게 쓰는 것입니다.

## 1. 이 부록에서 다루는 내용

| # | 페이지 | 핵심 주제 |
|---|---|---|
| 01 | [왜 Querydsl인가](01-why-querydsl.md) | 문자열 JPQL의 한계, 타입 안전·동적 쿼리, 2026년 프로젝트 현황(OpenFeign 포크) |
| 02 | [Kotlin + Gradle 설정](02-setup-kotlin.md) | `kotlin("kapt")`, OpenFeign 의존성(`:jakarta`), `JPAQueryFactory` 빈, Q타입 생성 확인 |
| 03 | [기본 쿼리](03-basic-queries.md) | `selectFrom`, `where`/`and`/`or`, 비교 연산자, 정렬·페이징, `fetch` 결과 처리 |
| 04 | [동적 쿼리와 조인](04-dynamic-and-join.md) | `BooleanBuilder`, 다중 `BooleanExpression`, `join`/`fetchJoin`, 서브쿼리 |
| 05 | [DTO 프로젝션 & 리포지토리 통합](05-dto-and-repository.md) | `Projections`, `@QueryProjection`, 사용자 정의 리포지토리, `Page`/`Pageable` |

## 2. 선수 지식

이 부록은 다음 내용을 이미 안다고 가정합니다.

- **[Phase 3 — 데이터 영속성](../phase-3-data-jpa/01-jpa-concepts.md)**: Entity 매핑, `JpaRepository`, 트랜잭션의 기본
- **[부록 A — JPA 심화](../appendix-a-jpa-advanced/README.md)**: 영속성 컨텍스트, 연관관계 매핑, N+1 문제, JPQL 문자열 쿼리

특히 부록 A에서 만든 `Category`·`Review` 연관 엔티티는 [04 페이지](04-dynamic-and-join.md)의 조인 예제에서 다시 등장합니다.

## 3. 실습 예제 도메인

본 부록의 모든 예제는 Phase 3·부록 A와 동일한 **도서 API**(`com.example.bookapi`)를 사용합니다.

```kotlin
// 도서 엔티티 (Phase 3·부록 A와 동일)
@Entity
class Book(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,
    var title: String,
    var author: String,
    var isbn: String,
    var price: Int,                 // 가격(원 단위 정수)
    var publishedAt: LocalDate,     // 출간일
)
```

응답으로는 동일한 `BookResponse` DTO를 재사용합니다.

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

> [!WARNING]
> Querydsl은 **컴파일 시점에 Q타입(예: `QBook`)을 생성**합니다. 따라서 엔티티를 만든 직후 한 번은 빌드를 돌려야 `QBook`이 생성됩니다. 설정과 생성 확인 방법은 [02 페이지](02-setup-kotlin.md)에서 자세히 다룹니다.

## 다음 단계

→ [01. 왜 Querydsl인가](01-why-querydsl.md)
