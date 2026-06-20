# 연관관계 매핑

객체는 **참조**로 다른 객체를 가리키고(`book.category`), 테이블은 **외래 키(FK)** 로 다른 행을 가리킵니다(`book.category_id`). JPA 연관관계 매핑은 이 둘을 이어 붙이는 작업입니다. Phase 3에서는 단순 단방향 `@ManyToOne` 정도만 맛봤지만, 이번엔 방향·다중성·주인 개념을 제대로 분해합니다.

교재 예제를 위해 두 엔티티를 새로 도입합니다. `Book`은 그대로 두고(price는 Int, author는 String 유지), 분류용 `Category`와 후기용 `Review`를 추가합니다.

## 1. 방향과 다중성

연관관계를 설계할 때 결정할 것은 두 가지입니다.

- **방향(direction)**: 한쪽에서만 참조하면 **단방향**, 양쪽에서 서로 참조하면 **양방향**. (테이블은 FK 하나로 양쪽 조인이 가능하므로 방향 개념이 없다. 방향은 순수하게 **객체 세계의 개념**이다.)
- **다중성(multiplicity)**: `@ManyToOne`, `@OneToMany`, `@OneToOne`, `@ManyToMany` 중 무엇인가.

```
객체:   Book ───category──▶ Category      (단방향: Book만 Category를 안다)
        Book ◀──reviews──── Review        (양방향: 서로 안다)

테이블:  book(.., category_id FK) ──▶ category
        review(.., book_id FK)   ──▶ book
```

| 다중성 | 의미 | 예제 |
|--------|------|------|
| `@ManyToOne` | 다(N) 쪽 → 일(1) 쪽 | 여러 Book → 하나의 Category |
| `@OneToMany` | 일(1) 쪽 → 다(N) 쪽 | 하나의 Book → 여러 Review |
| `@OneToOne` | 일대일 | Book → BookDetail |
| `@ManyToMany` | 다대다 | (지양 — 아래 참고) |

## 2. @ManyToOne 단방향 — Book → Category

가장 단순하고 가장 많이 쓰는 형태입니다. FK가 있는 쪽(`book.category_id`)에 참조를 둡니다.

```kotlin
package com.example.bookapi.domain

import jakarta.persistence.*

@Entity
class Category(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,

    var name: String
)
```

```kotlin
@Entity
class Book(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,
    var title: String,
    var author: String,           // 그대로 String 유지
    var isbn: String,
    var price: Int,               // 그대로 Int(원화) 유지
    var publishedAt: LocalDate,

    @ManyToOne(fetch = FetchType.LAZY)   // 항상 LAZY 권장 (04장 참고)
    @JoinColumn(name = "category_id")    // FK 컬럼명 지정
    var category: Category? = null
)
```

- `@JoinColumn`은 **FK 컬럼**을 지정합니다. 생략하면 `category_id`가 기본 추정됩니다.
- `@ManyToOne`의 기본 fetch는 `EAGER`지만, **반드시 `LAZY`로 바꾸는 것**이 정석입니다(이유는 [04장](04-proxy-fetch.md)).

## 3. 양방향과 연관관계의 주인 (mappedBy)

이제 `Category`에서 "이 카테고리에 속한 책 목록"을 보고 싶다고 합시다. 양방향으로 만들면 됩니다. 하지만 여기서 JPA의 가장 헷갈리는 개념 — **연관관계의 주인(owner)** 이 등장합니다.

테이블에는 FK가 **딱 하나**뿐입니다(`book.category_id`). 그런데 객체에는 참조가 둘이 됩니다(`book.category`, `category.books`). 둘 중 **어느 쪽이 FK를 관리할지** JPA에게 알려줘야 합니다. 이때 규칙은 단순합니다.

> **FK가 있는 쪽(= 다(N) 쪽 = `@ManyToOne` 쪽)이 항상 연관관계의 주인이다.** 반대쪽(`@OneToMany`)은 `mappedBy`로 "나는 주인이 아니라 거울일 뿐"이라고 선언한다.

`Book ↔ Review`로 양방향을 만들어 봅시다. FK는 `review.book_id`에 있으므로 **`Review`가 주인**, `Book`은 거울입니다.

```kotlin
@Entity
class Review(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,
    var content: String,
    var rating: Int,

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "book_id")   // ← 주인: 이쪽이 FK를 관리
    var book: Book? = null
)
```

```kotlin
@Entity
class Book(
    // ... 위 필드들 ...

    @OneToMany(mappedBy = "book", cascade = [CascadeType.ALL], orphanRemoval = true)
    var reviews: MutableList<Review> = mutableListOf()
    //               ▲ "Review.book 필드가 주인이다" — 나는 읽기 전용 거울
)
```

| 구분 | 주인 (`Review.book`) | 거울 (`Book.reviews`) |
|------|:---:|:---:|
| FK 관리(INSERT/UPDATE) | O | X (`mappedBy`) |
| 값 읽기(조회) | O | O |

> [!WARNING]
> **거울 쪽에만 값을 세팅하면 DB에 반영되지 않습니다.** `book.reviews.add(review)`만 하고 `review.book = book`을 안 하면, FK(`book_id`)는 `null`로 저장됩니다. JPA는 **주인 쪽 필드만 보고 FK를 결정**하기 때문입니다. 초보자가 가장 많이 겪는 "값을 넣었는데 왜 null이지?" 버그가 여기서 나옵니다.

## 4. 연관관계 편의 메서드

위 함정을 막으려면 **양쪽을 동시에 세팅**해야 합니다. 매번 두 줄을 쓰는 대신, 주인이 아닌 쪽(또는 자연스러운 쪽)에 **편의 메서드**를 둡니다.

```kotlin
@Entity
class Book(
    // ...
    @OneToMany(mappedBy = "book", cascade = [CascadeType.ALL], orphanRemoval = true)
    var reviews: MutableList<Review> = mutableListOf()
) {
    // 연관관계 편의 메서드: 양쪽을 한 번에 일관되게 세팅
    fun addReview(review: Review) {
        reviews.add(review)        // 거울 쪽 컬렉션에 추가
        review.book = this         // 주인 쪽 FK 세팅 — 이게 핵심!
    }

    fun removeReview(review: Review) {
        reviews.remove(review)
        review.book = null
    }
}
```

```kotlin
// 사용
val book = bookRepository.findById(1L).get()
book.addReview(Review(content = "좋아요", rating = 5))
// → book.reviews 에도 들어가고, review.book = book 도 세팅됨 → FK 정상 저장
```

> [!TIP]
> 편의 메서드는 **한쪽에만** 두세요(보통 호출 빈도가 높은 쪽). 양쪽에 다 두면 서로를 호출하다 무한 재귀에 빠질 위험이 있습니다. 또한 `toString()`/`equals()`/`hashCode()`에 **양방향 연관 필드를 절대 포함하지 마세요** — 순환 참조로 `StackOverflowError`가 납니다. Kotlin `data class`를 엔티티로 쓰지 말라는 [Phase 3-2](../phase-3-data-jpa/02-entity-mapping.md)의 조언이 여기서도 유효합니다.

## 5. 외래 키 주인 결정 정리

```
       Book (1)                       Review (N)
   ┌──────────────┐              ┌──────────────────┐
   │ reviews       │◀─ mappedBy ─│ @ManyToOne book  │ ← 주인 (FK: book_id)
   │ (@OneToMany)  │             │                  │
   └──────────────┘              └──────────────────┘

규칙: @ManyToOne(=N=FK 보유) 쪽이 주인.
      @OneToMany 쪽은 mappedBy 로 주인 필드명을 가리킨다.
```

`@OneToMany`를 주인으로 만드는 것(즉 `@OneToMany`에 `@JoinColumn`을 직접 붙이는 것)도 문법적으로는 가능하지만, **권장하지 않습니다.** 일(1) 쪽에서 컬렉션을 수정할 때 엉뚱한 `UPDATE` SQL이 추가로 나가기 때문입니다. 항상 **다(N) 쪽을 주인으로** 두세요.

## 6. @OneToOne과 @ManyToMany

**`@OneToOne`** 은 FK를 어느 테이블에 둘지 선택할 수 있습니다. 주 테이블(예: `book`)에 FK를 두면 조회가 편하고, 대상 테이블에 두면 `book` 테이블이 깔끔해집니다. 주 테이블에 두는 단방향을 기본으로 권장합니다.

```kotlin
@OneToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "detail_id")
var detail: BookDetail? = null
```

**`@ManyToMany`는 실무에서 지양합니다.** 이유는 명확합니다.

- 다대다는 JPA가 **중간 연결 테이블(join table)** 을 숨겨서 자동 생성하는데, 이 테이블에 **추가 컬럼을 넣을 수 없습니다**(예: 책-태그 관계에 "태그를 단 시각"을 기록 불가).
- 어떤 SQL이 나갈지 예측이 어렵고, 운영 중 요구사항이 거의 항상 "연결 테이블에 컬럼 추가"로 진화합니다.

> [!TIP]
> 해법은 **중간 엔티티를 직접 만드는 것**입니다. `Book ↔ Tag`라면 `BookTag` 엔티티를 두고, 양쪽을 각각 `@ManyToOne`으로 연결합니다(= `@OneToMany` + `@ManyToOne` 두 쌍). 이렇게 하면 연결 테이블이 1급 엔티티가 되어 컬럼을 자유롭게 추가할 수 있습니다.

## 7. cascade와 orphanRemoval

**`cascade`(영속성 전이)** 는 "부모 엔티티의 영속성 동작을 자식에게 전파"하는 옵션입니다. 위 `Book.reviews`에 `cascade = [CascadeType.ALL]`을 줬으므로, `book`을 저장하면 그 안의 `reviews`도 함께 `persist`됩니다.

```kotlin
val book = Book(title = "...", ...)
book.addReview(Review(content = "굿", rating = 5))
bookRepository.save(book)   // book 저장 시 review도 자동 INSERT (cascade)
```

**`orphanRemoval = true`** 는 "부모 컬렉션에서 빠진 자식을 고아로 보고 자동 삭제"합니다.

```kotlin
book.removeReview(someReview)   // 컬렉션에서 제거
// → orphanRemoval=true 이면 트랜잭션 커밋 시 DELETE FROM review ... 자동 실행
```

| 옵션 | 의미 | 안전하게 쓰는 조건 |
|------|------|----------|
| `cascade = ALL` | 모든 생명주기 전파 | 자식이 **이 부모에만 종속**될 때 |
| `orphanRemoval = true` | 컬렉션 이탈 자식 삭제 | 자식의 생명주기를 부모가 **독점**할 때 |

> [!WARNING]
> `cascade`와 `orphanRemoval`은 **자식이 오직 한 부모에게만 속할 때**만 켜세요. `Category`처럼 여러 `Book`이 공유하는 엔티티에 `cascade=ALL`을 걸면, 한 책을 지웠을 때 카테고리까지 삭제되어 다른 책들이 줄줄이 깨집니다. 그래서 우리는 `Book→Category`엔 cascade를 **걸지 않았습니다.** "리뷰는 책의 일부지만, 카테고리는 책의 일부가 아니다"라는 도메인 판단이 옵션 선택의 기준입니다.

## 다음 단계

엔티티 간 수평 관계를 봤으니, 이번엔 **상속 관계**와 엔티티가 품는 **값 타입**을 다룹니다.

→ [상속 매핑과 값 타입](03-inheritance-embedded.md)
