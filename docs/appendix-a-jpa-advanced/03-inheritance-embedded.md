# 상속 매핑과 값 타입

객체지향에는 있지만 관계형 DB에는 없는 두 가지가 **상속**과 **값 타입**입니다. 테이블에는 `extends`도 없고, "주소"처럼 여러 컬럼을 묶은 의미 단위도 없습니다. JPA는 이 간극을 상속 전략과 임베디드 타입으로 메웁니다.

## 1. 상속 매핑 전략 세 가지

"콘텐츠(Content)"라는 부모 아래 `Book`과 `Ebook`이 있다고 가정합시다. 이 상속 구조를 테이블로 어떻게 풀어낼지에 세 가지 전략이 있습니다.

```
        Content (공통: title, price)
         /            \
      Book           Ebook
   (isbn 등)      (fileSize 등)
```

| 전략 | 애너테이션 | 테이블 구조 | 장점 | 단점 |
|------|-----------|-------------|------|------|
| **단일 테이블** | `SINGLE_TABLE` (기본) | 부모·자식을 **한 테이블**에 다 담고 구분 컬럼으로 식별 | 조인 없음, 조회 빠름, 단순 | 자식 컬럼이 전부 **nullable**, 테이블 비대 |
| **조인** | `JOINED` | 부모/자식마다 테이블, PK로 조인 | **정규화**, 무결성, NULL 없음 | 조회 시 **JOIN** 필요, INSERT 2회 |
| **구현 클래스마다** | `TABLE_PER_CLASS` | 자식마다 독립 테이블(부모 컬럼 중복) | 부모 추상 클래스일 때 명확 | 여러 자식 통합 조회 시 `UNION`, **비권장** |

```kotlin
@Entity
@Inheritance(strategy = InheritanceType.JOINED)
@DiscriminatorColumn(name = "content_type")  // 구분 컬럼 (SINGLE_TABLE에서 특히 중요)
abstract class Content(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,
    var title: String = "",
    var price: Int = 0
)

@Entity
@DiscriminatorValue("BOOK")
class Book(
    var isbn: String = ""
    // title, price, id는 부모에서 상속
) : Content()

@Entity
@DiscriminatorValue("EBOOK")
class Ebook(
    var fileSizeMb: Int = 0
) : Content()
```

- **`@DiscriminatorColumn`** 은 한 행이 어느 자식 타입인지 구분하는 컬럼을 정의합니다. `SINGLE_TABLE`에서는 필수에 가깝습니다.
- **`@DiscriminatorValue`** 는 각 자식이 그 컬럼에 넣을 값을 지정합니다.

> [!TIP]
> 전략 선택의 실전 가이드 — **기본은 `SINGLE_TABLE`**(단순·빠름), 자식별 컬럼이 많고 NOT NULL 제약이 중요하면 `JOINED`. `TABLE_PER_CLASS`는 사실상 쓰지 마세요. 참고로 우리 `Book`은 상속이 필요 없는 단순 엔티티이므로, 실제 프로젝트에서는 상속을 도입하지 않습니다. 위 예제는 **개념 학습용**입니다.

## 2. @MappedSuperclass — 공통 매핑 정보 상속

모든 엔티티가 `createdAt`/`updatedAt` 같은 공통 필드를 가지는 경우, 상속 매핑(엔티티 간 상속)이 아니라 **`@MappedSuperclass`** 를 씁니다. 이것은 **테이블을 만들지 않고**, 단지 매핑 정보(컬럼 정의)만 자식에게 물려주는 부모입니다.

```kotlin
import jakarta.persistence.*
import org.springframework.data.annotation.CreatedDate
import org.springframework.data.annotation.LastModifiedDate
import org.springframework.data.jpa.domain.support.AuditingEntityListener
import java.time.LocalDateTime

@MappedSuperclass
@EntityListeners(AuditingEntityListener::class)   // Auditing 이벤트 수신
abstract class BaseEntity(
    @CreatedDate
    @Column(updatable = false)          // 생성 후 수정 금지
    var createdAt: LocalDateTime? = null,

    @LastModifiedDate
    var updatedAt: LocalDateTime? = null
)
```

`@MappedSuperclass`와 `@Inheritance`의 차이는 분명합니다.

| 구분 | `@Inheritance` (상속 매핑) | `@MappedSuperclass` |
|------|--------------------------|---------------------|
| 부모도 테이블이 있나? | O (조회·다형성 대상) | X (컬럼 정보만 제공) |
| 부모로 조회 가능? | O (`em.find(Content, id)`) | X |
| 용도 | 도메인 상속(is-a) | 공통 컬럼 재사용 |

## 3. JPA Auditing — 생성/수정 시각 자동 기록

위 `BaseEntity`의 `@CreatedDate`/`@LastModifiedDate`가 자동으로 채워지게 하려면, 설정 클래스에 **`@EnableJpaAuditing`** 한 줄이 필요합니다.

```kotlin
import org.springframework.context.annotation.Configuration
import org.springframework.data.jpa.repository.config.EnableJpaAuditing

@Configuration
@EnableJpaAuditing
class JpaConfig
```

이제 `Book`이 `BaseEntity`를 상속하면, `save` 시 `createdAt`이, 변경 시 `updatedAt`이 자동으로 채워집니다.

```kotlin
@Entity
class Book(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,
    var title: String,
    var author: String,
    var isbn: String,
    var price: Int,
    var publishedAt: LocalDate
) : BaseEntity()   // createdAt / updatedAt 를 물려받음
```

> [!TIP]
> 생성자(`@CreatedBy`)/수정자(`@LastModifiedBy`)까지 기록하려면 `AuditorAware<String>` 빈을 등록해 현재 로그인 사용자를 반환하게 합니다. 보통 Spring Security의 `SecurityContext`에서 사용자명을 꺼내옵니다([Phase 5](../phase-5-production-features/README.md)의 보안과 연계).

## 4. 임베디드 값 타입 — @Embeddable / @Embedded

**값 타입(value type)** 은 식별자가 없는, "값 그 자체"인 객체입니다. 엔티티가 식별자(`@Id`)로 구분되는 것과 대조적입니다. 예를 들어 "주소"는 그 자체로 의미 있는 묶음이지만, 독립적인 식별자가 필요 없습니다. 이런 묶음을 **임베디드 타입**으로 만들면, 여러 컬럼을 응집력 있는 객체로 다룰 수 있습니다.

```kotlin
import jakarta.persistence.Embeddable

@Embeddable
class Address(
    var city: String = "",
    var street: String = "",
    var zipcode: String = ""
)

// 금액을 의미 있는 타입으로 (price는 Int지만, 별도 금액 묶음 예시)
@Embeddable
class Money(
    var amount: Int = 0,        // 원화 정수
    var currency: String = "KRW"
)
```

```kotlin
@Entity
class Publisher(
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    var id: Long? = null,
    var name: String = "",

    @Embedded
    var address: Address = Address(),      // 컬럼: city, street, zipcode 로 풀림

    @Embedded
    @AttributeOverrides(
        AttributeOverride(name = "amount", column = Column(name = "fee_amount")),
        AttributeOverride(name = "currency", column = Column(name = "fee_currency"))
    )
    var listingFee: Money = Money()        // 같은 타입을 두 번 쓰면 컬럼명 충돌 → 오버라이드
)
```

생성되는 테이블은 다음과 같습니다. 값 타입은 **별도 테이블이 아니라 소속 엔티티 테이블의 컬럼**이 됩니다.

```sql
CREATE TABLE publisher (
    id          BIGINT PRIMARY KEY,
    name        VARCHAR(255),
    city        VARCHAR(255),   -- Address.city
    street      VARCHAR(255),   -- Address.street
    zipcode     VARCHAR(255),   -- Address.zipcode
    fee_amount  INTEGER,        -- Money.amount (오버라이드)
    fee_currency VARCHAR(255)   -- Money.currency (오버라이드)
);
```

> [!WARNING]
> 값 타입은 **불변(immutable)으로 다루는 것이 안전**합니다. 여러 엔티티가 같은 값 타입 인스턴스를 **공유(share)** 하면, 한쪽을 바꿨을 때 다른 쪽까지 변경 감지로 함께 UPDATE되는 부작용이 생깁니다. 값을 바꿔야 한다면 인스턴스 자체를 **새로 만들어 통째로 교체**하세요. Kotlin에서는 `val` 위주로 설계하거나 `copy` 패턴을 쓰면 자연스럽습니다(단, JPA 매핑 제약상 `var`가 필요한 경우가 있으니 공유만 피하면 됩니다).

## 5. @Enumerated — Enum 매핑은 반드시 STRING

도메인에 자주 등장하는 `enum`을 매핑할 때 **`@Enumerated(EnumType.STRING)`** 을 쓰는 것은 거의 규칙입니다.

```kotlin
enum class BookStatus { ON_SALE, OUT_OF_STOCK, DISCONTINUED }

@Entity
class Book(
    // ...
    @Enumerated(EnumType.STRING)        // ← 반드시 STRING
    var status: BookStatus = BookStatus.ON_SALE
)
```

기본값인 `EnumType.ORDINAL`은 enum의 **순서(0, 1, 2…)** 를 정수로 저장하는데, 이것은 **재앙의 씨앗**입니다.

```
ORDINAL 저장:  ON_SALE=0, OUT_OF_STOCK=1, DISCONTINUED=2

── 나중에 enum 중간에 NEW 상수를 추가하면 ──
enum { ON_SALE, NEW, OUT_OF_STOCK, DISCONTINUED }
                 ▲ 삽입
이제:  ON_SALE=0, NEW=1, OUT_OF_STOCK=2(!), DISCONTINUED=3
       → 기존에 1로 저장된 행은 OUT_OF_STOCK 이었는데 이제 NEW 로 해석됨!
```

| 방식 | DB 저장 값 | enum 순서 변경 시 |
|------|-----------|------------------|
| `ORDINAL` (기본) | 0, 1, 2… | **데이터 의미가 깨짐** |
| `STRING` (권장) | `"ON_SALE"` 등 이름 | 안전, 순서 무관 |

> [!WARNING]
> `@Enumerated`를 **생략하면 기본이 `ORDINAL`** 입니다. 즉 아무 생각 없이 enum 필드를 두면 위험한 ORDINAL로 저장됩니다. enum 필드에는 **항상 명시적으로 `@Enumerated(EnumType.STRING)`** 을 붙이세요. 저장 용량이 약간 늘어나는 대신 미래의 데이터 깨짐을 막습니다.

## 다음 단계

엔티티 구조를 모두 다뤘으니, 이제 그 엔티티를 **조회할 때** 벌어지는 프록시·지연 로딩·N+1 문제로 들어갑니다. JPA 성능 학습의 핵심입니다.

→ [프록시와 지연 로딩, N+1](04-proxy-fetch.md)
