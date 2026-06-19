# 트랜잭션 관리

데이터베이스 작업의 신뢰성을 보장하는 핵심 개념이 **트랜잭션(Transaction)** 입니다. "여러 DB 작업을 하나의 원자적 단위로 묶어, 전부 성공하거나 전부 실패(롤백)하게 만드는 것"이죠. Spring에서는 `@Transactional` 애너테이션 하나로 이 경계를 선언적으로 지정합니다.

## 1. @Transactional 기본

서비스 메서드에 `@Transactional`을 붙이면, 그 메서드가 시작될 때 트랜잭션이 시작되고 정상 종료 시 커밋, 예외 발생 시 롤백됩니다.

```kotlin
import org.springframework.transaction.annotation.Transactional

@Service
class BookService(private val bookRepository: BookRepository) {

    @Transactional
    fun transferStock(/* ... */) {
        // 이 안의 모든 DB 작업은 하나의 트랜잭션
        // 중간에 예외가 나면 앞선 작업도 전부 롤백된다
    }
}
```

> [!WARNING]
> import에 주의하세요. **반드시 `org.springframework.transaction.annotation.Transactional`** 을 사용합니다. `jakarta.transaction.Transactional`도 있지만, Spring의 readOnly·propagation 등 풍부한 옵션을 쓰려면 Spring 버전을 써야 합니다.

## 2. 어디에 붙이는가 — 서비스 계층

`@Transactional`은 **서비스 계층(`@Service`)의 메서드**에 붙이는 것이 정석입니다.

- **Repository**: 한 메서드가 보통 쿼리 하나라 경계를 둘 의미가 적다.
- **Controller**: 웹 계층은 트랜잭션 책임을 갖지 않는다. 영속성 컨텍스트가 웹 계층까지 열려 있으면 문제가 된다.
- **Service**: 여러 Repository 호출을 하나의 업무 단위(유스케이스)로 묶는 자연스러운 위치.

Phase 3-3에서 본 패턴이 모범 답안입니다.

```kotlin
@Service
@Transactional(readOnly = true)   // 클래스 기본값: 읽기 전용
class BookService(private val bookRepository: BookRepository) {

    fun findAll(): List<Book> = bookRepository.findAll()   // readOnly 적용

    @Transactional                 // 쓰기 메서드만 개별 재정의
    fun create(book: Book): Book = bookRepository.save(book)
}
```

## 3. readOnly 최적화

조회만 하는 메서드에는 **`@Transactional(readOnly = true)`** 를 권장합니다.

- Hibernate가 **변경 감지(dirty checking)용 스냅샷을 만들지 않아** 메모리·CPU를 아낀다.
- flush 모드가 `MANUAL`이 되어 불필요한 flush가 일어나지 않는다.
- DB 드라이버/복제 환경에 따라 읽기 전용 커넥션·읽기 복제본으로 라우팅될 수 있다.

위 예처럼 클래스에 `readOnly = true`를 기본으로 깔고, 쓰기 메서드에만 `@Transactional`을 다시 붙여 덮어쓰는 패턴이 흔합니다.

## 4. 전파(Propagation)와 격리(Isolation)

### 전파 — 이미 트랜잭션이 있을 때 어떻게 할까

`@Transactional` 메서드가 다른 `@Transactional` 메서드를 호출할 때의 동작을 정합니다.

| 전파 옵션 | 동작 |
|-----------|------|
| `REQUIRED` (기본값) | 기존 트랜잭션이 있으면 참여, 없으면 새로 시작 |
| `REQUIRES_NEW` | 항상 새 트랜잭션 시작 (기존 것은 잠시 보류) |
| `SUPPORTS` | 있으면 참여, 없으면 트랜잭션 없이 실행 |
| `MANDATORY` | 반드시 기존 트랜잭션이 있어야 함 (없으면 예외) |
| `NEVER` | 트랜잭션이 있으면 예외 |
| `NESTED` | 중첩 트랜잭션 (savepoint 기반) |

대부분의 경우 기본값 `REQUIRED`로 충분합니다. "로그 기록처럼 본 작업이 롤백돼도 별도로 남기고 싶다" 같은 특수한 경우에 `REQUIRES_NEW`를 씁니다.

### 격리 수준(Isolation)

동시에 실행되는 트랜잭션들이 서로의 변경을 얼마나 볼 수 있는지를 정합니다.

| 격리 수준 | 막아 주는 문제 |
|-----------|----------------|
| `READ_UNCOMMITTED` | (가장 약함) 거의 막지 못함 |
| `READ_COMMITTED` | Dirty Read 방지 (PostgreSQL 기본) |
| `REPEATABLE_READ` | + Non-repeatable Read 방지 |
| `SERIALIZABLE` | (가장 강함) 모든 문제 방지, 성능 비용 큼 |
| `DEFAULT` | DB 기본값 사용 |

> [!TIP]
> 격리 수준은 대부분 **DB 기본값(`DEFAULT`)** 을 그대로 두는 것이 좋습니다. 동시성 문제를 명확히 이해하고 필요할 때만 조정하세요. 섣불리 `SERIALIZABLE`을 쓰면 성능이 크게 떨어집니다.

## 5. 롤백 규칙 — Kotlin은 모두 unchecked

Spring의 기본 롤백 규칙은 Java를 전제로 합니다.

- **unchecked 예외**(`RuntimeException`과 그 하위, `Error`): 롤백 **O**
- **checked 예외**(`Exception`의 하위 중 RuntimeException이 아닌 것): 롤백 **X** (커밋됨!)

그런데 **Kotlin에는 checked 예외라는 개념이 없습니다.** 모든 예외가 사실상 unchecked처럼 동작합니다. 따라서 Kotlin에서는 "예외가 던져지면 일반적으로 롤백된다"고 이해하면 대체로 맞습니다.

특정 예외에 대한 동작을 명시하고 싶으면 옵션으로 지정합니다.

```kotlin
@Transactional(rollbackFor = [Exception::class])   // 모든 예외에 롤백 (명시적으로)
fun doSomething() { /* ... */ }

@Transactional(noRollbackFor = [IllegalStateException::class])  // 이 예외는 롤백 안 함
fun doAnother() { /* ... */ }
```

> [!WARNING]
> 트랜잭션 안에서 예외를 `try-catch`로 삼켜 버리면(다시 던지지 않으면) **롤백이 일어나지 않습니다.** 예외를 잡아 로깅만 하고 정상 흐름으로 돌려보내면, 앞선 DB 변경이 그대로 커밋되어 데이터 정합성이 깨질 수 있습니다.

## 6. 프록시 기반 AOP의 함정

`@Transactional`은 **프록시(proxy) 기반 AOP**로 동작합니다. Spring은 `BookService`를 감싸는 프록시 객체를 만들어, 메서드 호출을 가로채 트랜잭션을 시작·커밋합니다.

```
호출자 → [ 프록시 ] → (트랜잭션 시작) → 실제 BookService.create() → (커밋)
```

여기서 두 가지를 반드시 알아야 합니다.

### (1) 클래스가 open이어야 한다 — kotlin-spring 플러그인

프록시(특히 CGLIB 프록시)는 대상 클래스를 **상속**해서 만듭니다. 그런데 **Kotlin의 클래스와 메서드는 기본적으로 `final`** 이라 상속할 수 없습니다. 그대로 두면 프록시 생성이 실패하거나 트랜잭션이 적용되지 않습니다.

이 문제를 해결해 주는 것이 [Phase 1에서 추가한](../phase-1-project-setup/04-build-gradle-kts.md) **`kotlin("plugin.spring")`** 플러그인입니다. 이 플러그인(내부적으로 all-open 플러그인)은 `@Service`, `@Component`, `@Transactional` 등 Spring 애너테이션이 붙은 클래스를 **자동으로 `open`** 하게 만들어, 프록시가 상속할 수 있게 합니다. 덕분에 우리는 `open` 키워드를 직접 붙이지 않아도 됩니다.

```kotlin
// kotlin-spring 플러그인이 없으면 이렇게 직접 open을 붙여야 한다
open class BookService(/* ... */) {
    @Transactional
    open fun create(book: Book): Book = /* ... */
}
// 플러그인이 있으면 open 없이 위 BookService 그대로 동작
```

### (2) 자기 호출(self-invocation)은 프록시를 타지 않는다

같은 클래스 안에서 메서드가 **다른 메서드를 직접 호출**하면, 그 호출은 프록시를 거치지 않습니다. 호출이 `this`를 통해 실제 객체로 바로 가기 때문입니다. 결과적으로 호출된 메서드의 `@Transactional`이 무시됩니다.

```kotlin
@Service
class BookService(private val bookRepository: BookRepository) {

    fun importBooks(books: List<Book>) {
        books.forEach { saveOne(it) }   // ❌ this.saveOne() → 프록시 우회, 트랜잭션 적용 안 됨!
    }

    @Transactional
    fun saveOne(book: Book): Book = bookRepository.save(book)
}
```

해결책은 트랜잭션이 필요한 메서드를 **다른 빈으로 분리**하거나, 진입점 메서드에 `@Transactional`을 붙이는 것입니다. 자기 자신을 주입받아 프록시로 호출하는 방법도 있지만 권장되지 않습니다.

## 7. LazyInitializationException과 영속성 컨텍스트 경계

[Phase 3-1](01-jpa-concepts.md)에서 영속성 컨텍스트는 **트랜잭션이 살아 있는 동안만** 동작한다고 했습니다. `@Transactional`은 바로 이 경계를 결정합니다.

지연 로딩(`FetchType.LAZY`) 연관 객체는 "접근하는 순간" DB에서 가져옵니다. 그런데 트랜잭션이 이미 끝나 영속성 컨텍스트가 닫힌 뒤에 접근하면, 가져올 방법이 없어 **`LazyInitializationException`** 이 발생합니다.

```
[ 트랜잭션 안 ] book.author 접근 → OK (DB 조회 가능)
─────────────── 트랜잭션 종료, 컨텍스트 닫힘 ───────────────
[ Controller에서 ] book.author 접근 → ❌ LazyInitializationException
```

이를 피하는 방법:

- 트랜잭션 **안에서** 필요한 연관 데이터를 미리 로딩해 둔다(fetch join / `@EntityGraph`).
- 서비스 계층에서 **DTO로 변환**한 뒤 Controller로 반환한다(영속 객체를 웹 계층까지 끌고 가지 않는다).
- 조회 메서드에 `@Transactional(readOnly = true)`를 붙여 경계를 명확히 한다.

> [!TIP]
> "조회 메서드는 `@Transactional(readOnly = true)`, 변경 메서드는 `@Transactional`"을 서비스 계층의 기본 습관으로 삼으세요. 그리고 **Entity 대신 DTO를 반환**하면 LazyInitializationException과 직렬화 문제를 한꺼번에 피할 수 있습니다.

## 다음 단계

이제 실제로 애플리케이션이 붙을 데이터베이스를 설정할 차례입니다. 개발용 H2와 운영용 PostgreSQL을 프로필로 분리하고, `ddl-auto`와 마이그레이션 전략을 정리합니다.

→ [데이터베이스 설정 (H2 / PostgreSQL)](05-database-setup.md)
