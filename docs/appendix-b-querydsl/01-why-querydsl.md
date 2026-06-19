# 01. 왜 Querydsl인가

JPQL 문자열로도 대부분의 쿼리는 작성할 수 있습니다. 그런데도 수많은 실무 프로젝트가 Querydsl을 도입하는 이유는 무엇일까요? 이 페이지에서는 **문자열 쿼리의 근본적 한계**와 **Querydsl이 해결하는 문제**, 그리고 **2026년 현재 Querydsl 프로젝트의 현황**을 정리합니다.

## 1. 문자열 JPQL의 한계

부록 A-05에서 본 것처럼, JPQL은 `@Query`에 문자열로 작성합니다.

```kotlin
@Query("select b from Book b where b.author = :author and b.price >= :minPrice")
fun findByAuthorAndMinPrice(author: String, minPrice: Int): List<Book>
```

이 방식은 단순할 때는 잘 동작하지만, 몇 가지 구조적 약점이 있습니다.

### 1.1 컴파일 타임 검증이 불가능하다

문자열 쿼리는 **컴파일러가 검사하지 못합니다.** 다음 오류들은 모두 애플리케이션을 **실행하기 전까지** 발견되지 않습니다.

```kotlin
// 오타: 'titel' — 컴파일 OK, 실행하면 그제서야 예외
@Query("select b from Book b where b.titel = :title")
fun findByTitle(title: String): List<Book>

// 존재하지 않는 필드 'category' — 역시 런타임에야 터진다
@Query("select b from Book b where b.category = :c")
fun byCategory(c: String): List<Book>
```

엔티티의 `price` 필드 이름을 `salePrice`로 리팩터링해도, IDE는 문자열 안의 `b.price`를 **자동으로 바꿔 주지 않습니다.** 즉, **리팩터링 안전성이 없습니다.**

### 1.2 동적 쿼리 지옥

가장 큰 문제입니다. "검색 조건이 들어온 것만 적용"하는 화면을 상상해 봅시다. 제목·저자·최소가격이 모두 선택 입력이라면, 문자열 JPQL로는 이렇게 됩니다.

```kotlin
// 안티패턴: 문자열을 손으로 조립
fun search(title: String?, author: String?, minPrice: Int?): List<Book> {
    val jpql = StringBuilder("select b from Book b where 1=1")
    val params = mutableMapOf<String, Any>()
    if (title != null)    { jpql.append(" and b.title like :title");   params["title"] = "%$title%" }
    if (author != null)   { jpql.append(" and b.author = :author");    params["author"] = author }
    if (minPrice != null) { jpql.append(" and b.price >= :minPrice");  params["minPrice"] = minPrice }
    // 띄어쓰기 하나만 빠져도 'whereb.title'이 되어 터진다. where 1=1 같은 꼼수도 필요.
    val query = em.createQuery(jpql.toString(), Book::class.java)
    params.forEach { (k, v) -> query.setParameter(k, v) }
    return query.resultList
}
```

`where 1=1` 트릭, 공백 누락 버그, 파라미터 바인딩 누락 — 조건이 5개, 10개로 늘어나면 유지보수가 사실상 불가능해집니다.

## 2. Querydsl의 강점

Querydsl은 동일한 검색을 **타입 안전한 Kotlin 코드**로 표현합니다.

```kotlin
// Querydsl: 같은 동적 검색
fun search(title: String?, author: String?, minPrice: Int?): List<Book> {
    val book = QBook.book
    return queryFactory
        .selectFrom(book)
        .where(
            title?.let { book.title.contains(it) },     // null이면 조건에서 자동 제외
            author?.let { book.author.eq(it) },
            minPrice?.let { book.price.goe(it) },
        )
        .fetch()
}
```

여기서 얻는 이점은 다음과 같습니다.

- **타입 안전성**: `book.titel`이라고 쓰면 **컴파일 에러**입니다. 필드를 리팩터링하면 Q타입이 재생성되며 사용처도 함께 깨져 알 수 있습니다.
- **동적 쿼리의 우아함**: `where(...)`에 넘긴 값이 `null`이면 Querydsl이 **그 조건을 무시**합니다. `1=1` 트릭도, 문자열 연결도 필요 없습니다. (이 권장 패턴은 [04 페이지](04-dynamic-and-join.md)에서 깊이 다룹니다.)
- **IDE 지원**: 자동완성·메서드 체이닝·인라인 문서가 모두 동작합니다.
- **재사용**: 조건 생성 로직을 메서드로 빼서 여러 쿼리에서 공유할 수 있습니다.

### 2.1 무엇을 포기하는가

물론 비용도 있습니다. **Q타입 생성을 위한 빌드 단계(애너테이션 프로세서)** 가 추가되고, Kotlin에서는 `kapt` 때문에 빌드가 다소 느려집니다([02 페이지](02-setup-kotlin.md) 참고). 또한 아주 단순한 단건 조회까지 Querydsl로 쓰는 것은 과합니다 — 그건 Spring Data JPA의 파생 쿼리로 충분합니다.

## 3. 2026년 Querydsl 프로젝트 현황

여기는 **버전·좌표 선택에 직결되는 중요한 부분**입니다. 입문자가 가장 많이 혼동하는 지점이기도 합니다.

원조 Querydsl(group id **`com.querydsl`**, 5.x 라인)은 사실상 **유지보수가 멈춘 상태**입니다. 최신 Jakarta·Spring Boot 3/4 환경과의 호환성 패치가 더디게 진행되면서, 커뮤니티는 새로운 메인테이너를 찾았습니다.

그 결과 현재의 사실상 표준은 **OpenFeign 조직이 관리하는 포크**입니다.

| 구분 | 원조 (레거시) | OpenFeign 포크 (현행 표준) |
|---|---|---|
| Group ID | `com.querydsl` | **`io.github.openfeign.querydsl`** |
| 최신 라인 | 5.x (정체) | **7.x** (활발히 유지보수) |
| Jakarta 지원 | 제한적 | `:jakarta` classifier로 완전 지원 |
| Spring Boot 4 | 권장하지 않음 | 권장 |

> [!WARNING]
> 인터넷의 옛 블로그·StackOverflow 답변은 대부분 `com.querydsl:querydsl-jpa:5.0.0`을 안내합니다. **Spring Boot 4 + Jakarta 환경에서는 이 좌표를 쓰지 마세요.** 본 부록은 **`io.github.openfeign.querydsl`** 좌표를 기준으로 합니다. 정확한 버전과 의존성은 [02 페이지](02-setup-kotlin.md)에서 다룹니다.

## 4. 다른 대안과의 비교 — JPA Criteria API

표준 JPA에도 타입 안전 동적 쿼리 수단이 있습니다. 바로 **Criteria API**입니다. 하지만 코드가 극도로 장황합니다.

```kotlin
// JPA Criteria: "제목에 'Spring'이 포함된 책"
val cb = em.criteriaBuilder
val cq = cb.createQuery(Book::class.java)
val root = cq.from(Book::class.java)
cq.select(root).where(cb.like(root.get("title"), "%Spring%"))
val result = em.createQuery(cq).resultList
```

같은 일을 Querydsl로는 한 줄입니다.

```kotlin
queryFactory.selectFrom(book).where(book.title.contains("Spring")).fetch()
```

세 방식을 정리하면 다음과 같습니다.

| 방식 | 타입 안전 | 동적 쿼리 | 가독성 | 비고 |
|---|---|---|---|---|
| **JPQL 문자열** | ✗ | △ (문자열 조립) | △ | 표준, 학습 비용 낮음 |
| **JPA Criteria** | ○ | ○ | ✗ (매우 장황) | 표준이지만 실무 기피 |
| **Querydsl** | ○ | ○ (우아함) | ○ | 별도 라이브러리·빌드 설정 필요 |

결론적으로, Querydsl은 "타입 안전성"과 "가독성 좋은 동적 쿼리"를 **동시에** 제공하는 거의 유일한 실용적 선택지입니다.

## 다음 단계

이제 *왜* 쓰는지를 이해했으니, *어떻게* 설정하는지로 넘어갑시다.

→ [02. Kotlin + Gradle 설정](02-setup-kotlin.md)
