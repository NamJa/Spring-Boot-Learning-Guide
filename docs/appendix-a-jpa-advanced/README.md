# 부록 A · JPA 심화 (원리편)

Phase 3에서 우리는 Book REST API를 실제 데이터베이스에 영속화했습니다. 하지만 거기서 다룬 JPA는 "동작하게 만드는" 수준이었습니다. `JpaRepository`를 상속하면 CRUD가 되고, `@Transactional`을 붙이면 트랜잭션이 걸린다는 정도였죠. 정작 그 아래에서 **무슨 일이 벌어지는지**는 거의 들여다보지 않았습니다.

이 부록은 그 빈틈을 메웁니다. 김영한 님의 *"자바 ORM 표준 JPA 프로그래밍 - 기본편"* 에서 다루는 핵심 원리들을 Kotlin과 Spring Boot 4.1 맥락으로 재구성했습니다. **왜 `save()`를 안 불러도 `UPDATE`가 나가는지**, **왜 똑같은 조회를 두 번 했는데 SQL이 한 번만 나가는지**, **N+1 문제는 정확히 어떤 구조에서 터지는지** — 이런 질문에 자신 있게 답할 수 있게 되는 것이 목표입니다.

## 1. 이 부록이 다루는 것

Phase 3가 "JPA를 쓰는 법"이었다면, 이 부록은 **"JPA가 동작하는 원리"** 입니다. 같은 Book 예제를 사용하되, 연관관계를 가르치기 위해 `Category`와 `Review`라는 새 엔티티를 도입합니다.

| # | 문서 | 핵심 주제 |
|---|------|-----------|
| 1 | [영속성 컨텍스트](01-persistence-context.md) | `EntityManager`, 엔티티 생명주기, 1차 캐시, 쓰기 지연, 변경 감지, flush/merge |
| 2 | [연관관계 매핑](02-associations.md) | 단방향/양방향, 다중성, 연관관계의 주인(`mappedBy`), 편의 메서드, cascade |
| 3 | [상속 매핑과 값 타입](03-inheritance-embedded.md) | 상속 전략 3종, `@MappedSuperclass` + Auditing, `@Embeddable`, `@Enumerated` |
| 4 | [프록시와 지연 로딩, N+1](04-proxy-fetch.md) | 프록시, `LAZY`/`EAGER`, N+1 재현과 해결책 4종, OSIV |
| 5 | [JPQL](05-jpql.md) | JPQL 문법, 프로젝션, 페이징, 조인, 벌크 연산, 문자열 쿼리의 한계 |

## 2. 선수 지식

이 부록은 **[Phase 3 · Spring Data JPA](../phase-3-data-jpa/README.md)** 를 끝냈다고 가정합니다. 구체적으로 다음을 알고 있어야 합니다.

- `@Entity`, `@Id`, `@GeneratedValue`로 엔티티를 매핑하는 법 ([Phase 3-2](../phase-3-data-jpa/02-entity-mapping.md))
- `JpaRepository<Book, Long>`를 상속해 CRUD를 쓰는 법 ([Phase 3-3](../phase-3-data-jpa/03-repository.md))
- `@Transactional`이 트랜잭션 경계를 만든다는 사실 ([Phase 3-4](../phase-3-data-jpa/04-transactions.md))
- H2 콘솔과 `show-sql`/`format_sql`로 SQL 로그를 보는 법 ([Phase 3-5](../phase-3-data-jpa/05-database-setup.md))

> [!TIP]
> 이 부록의 SQL 로그 실험을 직접 따라 하려면 `application.yml`에 아래 설정을 켜 두세요. **무엇이 언제 실행되는지** 눈으로 확인하는 것이 원리 이해의 지름길입니다.
>
> ```yaml
> spring:
>   jpa:
>     show-sql: true
>     properties:
>       hibernate:
>         format_sql: true
> logging:
>   level:
>     org.hibernate.SQL: debug
>     org.hibernate.orm.jdbc.bind: trace   # 바인딩 파라미터 값까지 출력
> ```

## 3. 기준 스택

이 부록의 모든 코드는 다음 버전에서 검증되었습니다(2026-06-20 기준). Phase 3와 동일합니다.

| 항목 | 버전 |
|------|------|
| Spring Boot | 4.1.0 |
| Spring Framework | 7.0.8+ |
| Spring Data JPA | Spring Data 2025.1 |
| Hibernate ORM | 7.x (Boot 4.1 관리 버전) |
| Kotlin | 2.3.21 |
| JDK | 21 |

> [!NOTE]
> 패키지는 항상 **`jakarta.persistence.*`** 입니다. `javax`는 구버전이니 예제에서 보이면 무시하세요. Kotlin에서는 `kotlin("plugin.jpa")` 플러그인이 엔티티에 기본 생성자를 합성해 주므로([Phase 3-2](../phase-3-data-jpa/02-entity-mapping.md) 참고), 이 부록의 엔티티도 별도 no-arg 생성자를 직접 쓰지 않습니다.

## 다음 단계

가장 먼저, JPA의 모든 동작이 출발하는 지점 — **영속성 컨텍스트** 부터 분해합니다.

→ [영속성 컨텍스트](01-persistence-context.md)
