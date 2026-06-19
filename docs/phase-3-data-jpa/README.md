# Phase 3 · Spring Data JPA로 영속성 다루기

Phase 2에서 우리는 도서(Book) 관리 REST API를 만들었지만, 데이터를 **메모리 상의 `Map`** 에 저장했습니다. 애플리케이션을 재시작하면 데이터가 모두 사라지는 한계가 있었죠. Phase 3에서는 이 인메모리 저장소를 **실제 데이터베이스**로 교체합니다.

이를 위해 Spring 생태계의 표준 데이터 접근 기술인 **Spring Data JPA**를 사용합니다. Kotlin 개발자 입장에서 JPA는 처음엔 다소 낯설고, 특히 Kotlin과 함께 쓸 때 주의해야 할 함정들이 있습니다. 이 Phase에서는 개념부터 시작해 Entity 매핑, Repository, 트랜잭션, 데이터베이스 설정까지 한 단계씩 짚어가며 Book API를 완전히 영속화합니다.

## 이 Phase에서 다루는 내용

| # | 문서 | 핵심 주제 |
|---|------|-----------|
| 1 | [Spring Data JPA 개념](01-jpa-concepts.md) | JPA / Hibernate / Spring Data JPA의 관계, ORM, 영속성 컨텍스트 |
| 2 | [Entity 매핑 (Kotlin)](02-entity-mapping.md) | `@Entity`, Kotlin+JPA 함정, 연관관계, N+1 |
| 3 | [Repository 인터페이스](03-repository.md) | `JpaRepository`, 파생 쿼리, `@Query`, 페이징 |
| 4 | [트랜잭션 관리](04-transactions.md) | `@Transactional`, 전파/격리, 프록시 AOP, LazyInitializationException |
| 5 | [데이터베이스 설정 (H2 / PostgreSQL)](05-database-setup.md) | H2 개발 환경, PostgreSQL 운영 프로필, `ddl-auto`, 마이그레이션 |

## 학습 목표

이 Phase를 마치면 다음을 할 수 있습니다.

- **JPA, Hibernate, Spring Data JPA**가 각각 무엇이고 어떻게 협력하는지 설명할 수 있다.
- Kotlin으로 **함정 없는 Entity 클래스**를 작성할 수 있다.
- `JpaRepository`를 상속한 인터페이스만으로 CRUD와 **파생 쿼리 메서드**를 구현할 수 있다.
- `@Transactional`로 **트랜잭션 경계**를 올바르게 설정할 수 있다.
- 개발 환경(H2)과 운영 환경(PostgreSQL)을 **프로필**로 분리해 설정할 수 있다.

> [!TIP]
> Phase 2의 인메모리 `BookService`를 옆에 띄워 두고 진행하면, JPA가 어떤 보일러플레이트를 대신 처리해 주는지 직접 비교하며 체감할 수 있습니다.

## 다음 단계

먼저 JPA가 무엇이고 Hibernate, Spring Data JPA와 어떤 관계인지부터 정리합니다.

→ [Spring Data JPA 개념](01-jpa-concepts.md)
