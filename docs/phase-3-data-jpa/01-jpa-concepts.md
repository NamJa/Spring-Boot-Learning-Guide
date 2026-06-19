# Spring Data JPA 개념

데이터베이스 코드를 작성하기 전에, 우리가 사용할 기술 스택이 정확히 무엇인지부터 정리합시다. **JPA**, **Hibernate**, **Spring Data JPA** — 이름이 비슷해 보이지만 서로 다른 계층의 것들입니다. 이 셋의 관계를 이해하는 것이 JPA 학습의 첫걸음입니다.

## 1. ORM이란 무엇인가

관계형 데이터베이스(RDB)는 데이터를 **테이블의 행(row)** 으로 저장합니다. 반면 Kotlin/Java 같은 객체지향 언어는 데이터를 **객체(object)** 로 다룹니다. 이 둘 사이에는 근본적인 불일치가 있습니다.

- 객체는 **참조**로 다른 객체를 가리키지만, 테이블은 **외래 키(FK)** 로 다른 행을 가리킨다.
- 객체는 상속·다형성을 갖지만, 테이블에는 그런 개념이 없다.
- 객체 그래프는 자유롭게 탐색되지만, 테이블은 JOIN으로 연결된다.

이런 차이를 흔히 **객체-관계 임피던스 불일치(impedance mismatch)** 라고 부릅니다. **ORM(Object-Relational Mapping)** 은 이 간극을 자동으로 메워 주는 기술입니다. 즉, 객체를 저장하면 알아서 `INSERT` SQL을 만들어 주고, 행을 조회하면 알아서 객체로 변환해 줍니다. 개발자는 SQL이 아니라 **객체** 중심으로 코드를 작성할 수 있게 됩니다.

## 2. JPA / Hibernate / Spring Data JPA의 관계

세 가지를 한 문장으로 요약하면 다음과 같습니다.

- **JPA (Jakarta Persistence API)**: ORM을 위한 **표준 명세(specification)**. 인터페이스와 애너테이션의 집합일 뿐, 그 자체로는 동작하지 않는다. `jakarta.persistence.*` 패키지가 여기에 해당한다.
- **Hibernate**: JPA 명세를 **실제로 구현한 ORM 프레임워크(구현체)**. SQL을 생성하고 실행하는 진짜 엔진. Spring Boot의 기본 JPA 구현체다.
- **Spring Data JPA**: JPA/Hibernate를 더 **편하게 쓰도록 감싸 주는 Spring 모듈**. Repository 인터페이스만 선언하면 구현 코드를 자동 생성해 보일러플레이트를 제거해 준다.

> [!NOTE]
> 과거에는 `javax.persistence.*` 패키지를 사용했지만, Jakarta EE로 이관되면서 **`jakarta.persistence.*`** 로 바뀌었습니다. Spring Boot 4.x / Spring Framework 7.x는 전부 `jakarta` 네임스페이스를 사용합니다. 오래된 예제에서 `javax`를 보면 구버전이라고 생각하세요.

계층을 그림으로 표현하면 다음과 같습니다. 위쪽이 우리가 직접 다루는 추상화, 아래로 갈수록 실제 DB에 가까워집니다.

```
┌──────────────────────────────────────────┐
│   우리 코드 (BookRepository, BookService)   │
├──────────────────────────────────────────┤
│   Spring Data JPA                          │  ← Repository 추상화, 쿼리 메서드 자동 생성
├──────────────────────────────────────────┤
│   JPA (Jakarta Persistence) 명세            │  ← @Entity, EntityManager 등 표준 인터페이스
├──────────────────────────────────────────┤
│   Hibernate (JPA 구현체)                    │  ← 실제 SQL 생성·실행, 영속성 컨텍스트 관리
├──────────────────────────────────────────┤
│   JDBC                                      │  ← 표준 Java DB 연결 API
├──────────────────────────────────────────┤
│   Database (H2 / PostgreSQL)                │
└──────────────────────────────────────────┘
```

요점은 **Spring Data JPA를 사용한다고 해서 JPA와 Hibernate를 안 쓰는 게 아니라는 것**입니다. 우리는 가장 위층의 편리한 추상화를 사용하지만, 그 아래에서는 여전히 JPA 명세에 따라 Hibernate가 SQL을 만들어 JDBC로 DB에 보냅니다.

## 3. 영속성 컨텍스트와 EntityManager

JPA의 핵심 개념 중 가장 중요한 것이 **영속성 컨텍스트(Persistence Context)** 입니다. 이것은 "Entity 객체를 보관하는 1차 캐시이자 작업 공간"이라고 생각하면 됩니다. 이 컨텍스트를 관리하는 주체가 **`EntityManager`** 입니다.

영속성 컨텍스트가 제공하는 대표적인 기능은 다음과 같습니다.

- **1차 캐시**: 같은 트랜잭션 안에서 같은 ID로 조회하면 DB에 다시 가지 않고 캐시된 객체를 반환한다.
- **변경 감지(Dirty Checking)**: 영속 상태인 Entity의 필드를 바꾸면, 트랜잭션이 끝날 때 자동으로 `UPDATE` SQL이 나간다. **`save()`를 명시적으로 호출하지 않아도 된다.**
- **쓰기 지연(Write-behind)**: `INSERT`/`UPDATE`를 모았다가 트랜잭션 커밋 시점(flush)에 한 번에 보낸다.

```
조회/저장 → [ 영속성 컨텍스트 ]  ── flush ──▶  DB
              (1차 캐시 / 변경 감지)
```

> [!TIP]
> 변경 감지 덕분에 "객체의 필드만 바꾸면 DB가 갱신된다"는 점이 처음엔 마법처럼 느껴집니다. 단, 이 마법은 **트랜잭션 + 영속성 컨텍스트가 살아 있는 동안에만** 작동합니다. 이 경계는 [Phase 3-4 트랜잭션 관리](04-transactions.md)에서 자세히 다룹니다.

실무에서는 `EntityManager`를 직접 다루는 일이 드뭅니다. Spring Data JPA의 Repository가 내부적으로 `EntityManager`를 사용해 우리 대신 일을 처리해 주기 때문입니다. 다만 "내부적으로 영속성 컨텍스트가 동작한다"는 사실은 반드시 알고 있어야 합니다.

## 4. Spring Data JPA가 제거해 주는 보일러플레이트

순수 JPA만 쓰면 단순 조회 하나에도 다음과 같은 코드를 직접 작성해야 합니다.

```kotlin
// 순수 JPA (Spring Data 없이) - 직접 EntityManager를 다뤄야 한다
fun findById(id: Long): Book? {
    return entityManager.find(Book::class.java, id)
}

fun findByAuthor(author: String): List<Book> {
    return entityManager
        .createQuery("SELECT b FROM Book b WHERE b.author = :author", Book::class.java)
        .setParameter("author", author)
        .resultList
}
```

Spring Data JPA를 쓰면 위 코드가 **인터페이스 선언만으로** 사라집니다. 구현체는 Spring이 런타임에 자동 생성합니다.

```kotlin
interface BookRepository : JpaRepository<Book, Long> {
    fun findByAuthor(author: String): List<Book>   // 메서드 이름만으로 쿼리 생성
}
```

이 부분은 [Phase 3-3 Repository 인터페이스](03-repository.md)에서 본격적으로 다룹니다.

## 5. 의존성 추가

Spring Data JPA를 사용하려면 `build.gradle.kts`에 스타터 하나만 추가하면 됩니다. 이 스타터가 Spring Data JPA, Hibernate, 트랜잭션 관리, 커넥션 풀(HikariCP) 등을 한꺼번에 가져옵니다.

```kotlin
plugins {
    kotlin("jvm") version "2.2.21"
    kotlin("plugin.spring") version "2.2.21"
    kotlin("plugin.jpa") version "2.2.21"        // ← JPA Entity용 no-arg 플러그인
    id("org.springframework.boot") version "4.1.0"
    id("io.spring.dependency-management") version "1.1.7"
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    runtimeOnly("com.h2database:h2")             // 개발용 인메모리 DB
    // 운영용 PostgreSQL은 Phase 3-5에서 추가
}
```

> [!WARNING]
> `kotlin("plugin.jpa")` 플러그인을 빼먹으면 `@Entity` 클래스가 동작하지 않습니다. JPA 명세는 Entity에 **인자 없는 기본 생성자(no-arg constructor)** 를 요구하는데, Kotlin은 기본 생성자를 자동으로 만들지 않기 때문입니다. 이 플러그인이 컴파일 시점에 no-arg 생성자를 합성해 줍니다. 자세한 내용은 다음 문서에서 다룹니다.

## 6. 데이터 접근 기술 비교

같은 "도서 1건 조회"라도 어떤 기술을 쓰느냐에 따라 작성량과 추상화 수준이 크게 다릅니다.

| 기술 | 추상화 수준 | SQL 작성 | 객체 매핑 | 보일러플레이트 | 비고 |
|------|------------|----------|-----------|----------------|------|
| **Raw JDBC** | 가장 낮음 | 직접 | 직접 (ResultSet → 객체) | 매우 많음 | `Connection`/`Statement` 직접 관리 |
| **JdbcTemplate** | 낮음 | 직접 | `RowMapper`로 일부 자동화 | 보통 | 연결/예외 처리는 Spring이 대신 |
| **JPA / Hibernate (순수)** | 높음 | JPQL/자동 생성 | 자동 (ORM) | 보통 | `EntityManager` 직접 사용 |
| **Spring Data JPA** | 가장 높음 | 대부분 불필요 | 자동 (ORM) | 거의 없음 | 인터페이스 선언만으로 구현 |

이 가이드에서는 가장 생산성이 높은 **Spring Data JPA**를 사용합니다. 다만 추상화가 높다고 무조건 좋은 것은 아닙니다. 복잡한 통계 쿼리나 성능이 극도로 중요한 구간에서는 `@Query`나 JdbcTemplate을 함께 쓰는 것이 더 나을 수 있습니다.

## 다음 단계

이제 첫 번째 실습으로, Phase 2의 인메모리 `Book`을 실제 DB 테이블과 매핑되는 **JPA Entity**로 바꿔 봅니다. Kotlin과 JPA를 함께 쓸 때의 함정들도 함께 짚습니다.

→ [Entity 매핑 (Kotlin)](02-entity-mapping.md)
