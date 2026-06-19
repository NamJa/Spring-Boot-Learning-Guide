# Entity 매핑 (Kotlin)

이제 Phase 2에서 평범한 데이터 클래스였던 `Book`을 **JPA Entity**로 바꿔 DB 테이블과 매핑합니다. Kotlin과 JPA를 함께 쓰는 것은 Java보다 미묘한 함정이 많습니다. 이 문서에서는 **올바른 Entity 작성 패턴**을 먼저 제시하고, 왜 그렇게 써야 하는지 설명합니다.

## 1. Entity란

`@Entity` 애너테이션이 붙은 클래스는 **DB 테이블과 1:1로 매핑되는 객체**입니다. 클래스는 테이블, 인스턴스는 행(row), 프로퍼티는 컬럼에 대응합니다. JPA는 이 매핑 정보를 보고 SQL을 자동으로 생성합니다.

## 2. Book Entity (권장 패턴)

먼저 완성된 `Book` Entity를 봅시다. 이어지는 절에서 각 선택의 이유를 설명합니다.

```kotlin
package com.example.bookapi.domain

import jakarta.persistence.*
import java.math.BigDecimal
import java.time.LocalDate

@Entity
@Table(
    name = "books",
    uniqueConstraints = [UniqueConstraint(name = "uk_books_isbn", columnNames = ["isbn"])]
)
class Book(
    // 식별자: DB가 auto-increment로 생성 (IDENTITY 전략)
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,

    @Column(nullable = false, length = 200)
    var title: String,

    @Column(nullable = false, length = 100)
    var author: String,

    // isbn은 유일해야 하므로 unique 제약 (위 @Table에서 선언)
    @Column(nullable = false, length = 20)
    var isbn: String,

    @Column(nullable = false, precision = 10, scale = 2)
    var price: BigDecimal,

    @Column(name = "published_at", nullable = false)
    var publishedAt: LocalDate,
) {
    // 식별자 기반 equals/hashCode (이유는 4절 참고)
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is Book) return false
        return id != null && id == other.id
    }

    override fun hashCode(): Int = javaClass.hashCode()

    override fun toString(): String =
        "Book(id=$id, title='$title', author='$author', isbn='$isbn')"
}
```

> [!NOTE]
> `price`를 `Double`이 아니라 `BigDecimal`로 둔 점에 주목하세요. 돈을 다루는 값은 부동소수점 오차를 피하기 위해 항상 `BigDecimal`을 쓰는 것이 원칙입니다.

## 3. Kotlin + JPA 함정 ①: no-arg 플러그인

JPA 명세는 모든 Entity가 **인자 없는 기본 생성자**를 가질 것을 요구합니다. Hibernate가 DB에서 행을 읽어 객체를 만들 때, 리플렉션으로 빈 객체를 먼저 생성한 뒤 필드를 채우기 때문입니다.

그런데 위 `Book` 클래스의 주 생성자에는 인자가 가득합니다. Kotlin은 기본 생성자를 자동으로 만들지 않으므로, 그대로 두면 Hibernate가 객체를 생성하지 못해 예외가 납니다.

해결책은 [Phase 3-1](01-jpa-concepts.md)에서 추가한 **`kotlin("plugin.jpa")`** 플러그인입니다. 이 플러그인(내부적으로 no-arg 플러그인)은 `@Entity` 클래스에 대해 컴파일 시점에 인자 없는 생성자를 **합성(synthetic)** 해 줍니다. 우리 소스 코드에는 보이지 않지만 바이트코드에는 존재하게 됩니다.

```kotlin
// build.gradle.kts
plugins {
    kotlin("plugin.jpa") version "2.3.21"   // @Entity에 no-arg 생성자 합성
}
```

## 4. Kotlin + JPA 함정 ②: data class를 피하라

Phase 2의 `Book`은 `data class`였습니다. 하지만 **Entity는 `data class`로 만들면 안 됩니다.** 이유는 `data class`가 자동 생성하는 `equals()`/`hashCode()`/`toString()`이 JPA와 충돌하기 때문입니다.

**(1) equals/hashCode 문제 — 모든 프로퍼티를 비교한다**

`data class`의 `equals`는 모든 프로퍼티를 비교합니다. 그런데 Entity는 영속화 전(ID가 `null`)과 후(ID가 채워짐)에 상태가 바뀌고, `Set`에 담은 뒤 필드가 변경되면 `hashCode`가 달라져 컬렉션이 깨집니다. 또 양방향 연관관계가 있으면 `toString`/`equals`가 **무한 재귀**에 빠질 수 있습니다.

권장 패턴은 위 예제처럼 **식별자(id) 기반**으로 직접 구현하는 것입니다.

- `equals`: `id`가 `null`이 아니고 서로 같을 때만 동등하다고 본다.
- `hashCode`: `id`는 나중에 채워지므로 해시값에 쓰면 위험하다. 그래서 **`javaClass.hashCode()`** 같이 인스턴스 수명 동안 변하지 않는 고정값을 반환한다. (모든 인스턴스가 같은 해시를 갖지만, 같은 트랜잭션 내 1차 캐시 크기를 생각하면 성능 문제는 거의 없다.)

**(2) var vs val — Entity는 var로**

`data class`는 보통 `val`(불변)을 쓰지만, Entity는 **`var`(가변)** 로 두는 것이 좋습니다. JPA의 핵심 기능인 **변경 감지(Dirty Checking)** 가 "객체 필드를 바꾸면 UPDATE가 나간다"는 것에 기반하기 때문입니다. 모든 필드가 `val`이면 값을 바꿀 수 없어 이 기능을 활용하기 어렵습니다.

> [!WARNING]
> 정리: **Entity는 (1) 일반 `class`로, (2) 프로퍼티는 `var`로, (3) equals/hashCode는 id 기반으로 직접 구현**합니다. `data class`의 편의는 포기하는 대신 JPA와의 충돌을 피합니다. (요청/응답 DTO는 여전히 `data class`로 만드는 것이 좋습니다 — DTO는 영속 객체가 아니니까요.)

## 5. 주요 매핑 애너테이션

| 애너테이션 | 역할 |
|-----------|------|
| `@Entity` | 이 클래스가 JPA Entity임을 선언 |
| `@Table` | 매핑할 테이블 이름·제약조건 지정 (생략 시 클래스명 사용) |
| `@Id` | 기본 키(PK) 필드 지정 |
| `@GeneratedValue` | PK 생성 전략 지정 |
| `@Column` | 컬럼 속성(이름, nullable, length, precision 등) 지정 |
| `@Enumerated` | enum 매핑 (반드시 `EnumType.STRING` 권장) |
| `@Transient` | 이 필드는 컬럼으로 매핑하지 않음 |

### @GeneratedValue 전략

PK를 어떻게 생성할지 정합니다. 우리는 **`IDENTITY`** 를 사용합니다.

- `IDENTITY`: DB의 auto-increment 컬럼에 위임 (MySQL `AUTO_INCREMENT`, PostgreSQL `SERIAL`/`IDENTITY`, H2 등). 가장 직관적이며 H2·PostgreSQL 모두 잘 동작한다.
- `SEQUENCE`: DB 시퀀스 사용. 대량 INSERT 시 성능 이점이 있으나 시퀀스를 지원하는 DB 필요.
- `AUTO`: 구현체가 알아서 선택.

### Kotlin 타입 ↔ 컬럼 nullability

Kotlin의 **null 가능 여부**와 DB 컬럼의 **NULL 허용 여부**를 일치시키는 것이 중요합니다.

| Kotlin 타입 | 권장 `@Column` | 의미 |
|-------------|---------------|------|
| `var title: String` | `nullable = false` | NOT NULL 컬럼 |
| `var note: String?` | `nullable = true` (기본값) | NULL 허용 컬럼 |
| `var id: Long? = null` | `@Id @GeneratedValue` | 영속 전엔 null, DB가 채움 |

> [!TIP]
> `id`는 DB가 채워 주기 전까지(=저장 전)는 값이 없으므로 **`Long?`(nullable) + 기본값 `null`** 로 선언합니다. `@Column(nullable=false)`와 Kotlin의 non-null 타입을 일치시키면, 컴파일 단계에서 NPE를, DB 단계에서 제약 위반을 이중으로 방지할 수 있습니다.

`LocalDate`는 별도 설정 없이 DB의 `DATE` 컬럼으로 자동 매핑됩니다. (Hibernate 6+는 `LocalDate`/`LocalDateTime`/`Instant` 등 `java.time` 타입을 기본 지원합니다.)

## 6. 연관관계 매핑 (간단 소개)

실제 도메인에서는 Entity끼리 관계를 맺습니다. 예를 들어 한 명의 **저자(Author)** 가 여러 **도서(Book)** 를 쓴다면 1:N 관계입니다. 본격적인 연관관계 설계는 범위를 벗어나지만, 형태만 짚어 둡니다.

```kotlin
@Entity
@Table(name = "authors")
class Author(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,

    @Column(nullable = false)
    var name: String,

    // 한 저자가 여러 책을 가짐 (1:N). 연관관계의 주인은 Book.author 쪽
    @OneToMany(mappedBy = "author", fetch = FetchType.LAZY)
    var books: MutableList<Book> = mutableListOf(),
)

// Book 쪽 (N:1) — author_id 외래 키를 가진 연관관계의 주인
@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "author_id")
var author: Author? = null
```

### FetchType.LAZY와 N+1 문제

연관관계를 매핑할 때 **언제 연관 객체를 DB에서 가져올지**를 `FetchType`으로 정합니다.

- `FetchType.EAGER`: Entity를 조회하는 즉시 연관 객체도 함께 가져온다.
- `FetchType.LAZY`(지연 로딩): 연관 객체에 실제로 접근하는 순간 가져온다. **`@ManyToOne`/`@OneToMany` 모두 LAZY를 권장**한다.

> [!WARNING]
> **N+1 문제**: 책 목록 100건을 조회한 뒤(쿼리 1번) 각 책의 저자에 접근하면 저자 조회 쿼리가 100번 더 나갈 수 있습니다(총 1+N번). LAZY로 둔다고 N+1이 사라지는 게 아니라, **접근 패턴에 따라 발생**합니다. 해결책은 `@Query`의 **fetch join**, `@EntityGraph`, 또는 배치 사이즈 설정입니다. (이 가이드의 Book API는 단일 Entity라 N+1이 발생하지 않지만, 연관관계를 추가하는 순간 반드시 고려해야 합니다.)

## 다음 단계

Entity를 정의했으니, 이제 이 Entity를 저장하고 조회하는 **Repository 인터페이스**를 만들고 Phase 2의 `BookService`를 JPA 기반으로 리팩터링합니다.

→ [Repository 인터페이스](03-repository.md)
