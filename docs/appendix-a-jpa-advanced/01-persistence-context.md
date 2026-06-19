# 영속성 컨텍스트 (Persistence Context)

JPA를 한 문장으로 요약하면 **"영속성 컨텍스트라는 중간 캐시를 통해 객체와 DB를 동기화하는 기술"** 입니다. Phase 3에서 우리는 `BookRepository.save()`를 호출하면 데이터가 저장된다는 사실만 알고 넘어갔습니다. 하지만 그 `save()`가 실제로 `INSERT`를 즉시 날리는지, 변경된 엔티티는 어떻게 `UPDATE`로 이어지는지 — 이 모든 것의 중심에 **영속성 컨텍스트(Persistence Context)** 가 있습니다.

## 1. EntityManager와 영속성 컨텍스트

**영속성 컨텍스트**는 "엔티티를 보관하는 논리적인 작업 공간"입니다. 눈에 보이는 객체가 아니라, `EntityManager` 내부에 존재하는 관리 영역입니다. 우리가 `EntityManager`를 통해 엔티티를 저장하거나 조회하면, 그 엔티티는 영속성 컨텍스트에 담겨 관리됩니다.

```
   애플리케이션 코드
        │  persist(book) / find(...)
        ▼
 ┌──────────────────────────────┐
 │       EntityManager          │
 │  ┌────────────────────────┐  │
 │  │   영속성 컨텍스트        │  │   ← 1차 캐시, 쓰기 지연 SQL 저장소
 │  │   [ Book@1, Book@2 ]   │  │
 │  └────────────────────────┘  │
 └──────────────────────────────┘
        │  flush (SQL 전송)
        ▼
       Database
```

Spring Data JPA를 쓰면 `EntityManager`를 직접 만질 일이 거의 없습니다. `JpaRepository`가 내부적으로 `EntityManager`를 위임받아 사용하기 때문입니다. 하지만 원리를 익히려면 `EntityManager`의 메서드를 직접 보는 편이 명확합니다.

```kotlin
import jakarta.persistence.EntityManager
import jakarta.persistence.PersistenceContext
import org.springframework.stereotype.Repository
import org.springframework.transaction.annotation.Transactional

@Repository
class BookEntityManagerDemo(
    @PersistenceContext private val em: EntityManager  // 컨테이너가 주입
) {
    @Transactional
    fun demo() {
        val book = Book(title = "JPA 기본편", author = "김영한", isbn = "111", price = 30000, publishedAt = LocalDate.now())
        em.persist(book)              // (1) 영속 상태로 만든다 — 아직 INSERT 안 나감
        val found = em.find(Book::class.java, book.id) // (2) 1차 캐시에서 반환 — SELECT 안 나감
        println(book === found)       // true — 동일성 보장
    }
}
```

> [!TIP]
> `@PersistenceContext`로 주입받는 `EntityManager`는 사실 **실제 EntityManager가 아니라 프록시**입니다. 호출 시점의 트랜잭션에 묶인 진짜 `EntityManager`로 매번 위임합니다. 덕분에 싱글턴 빈에 주입해도 스레드별 트랜잭션마다 다른 영속성 컨텍스트를 쓸 수 있습니다.

## 2. 엔티티의 생명주기 (네 가지 상태)

엔티티 인스턴스는 영속성 컨텍스트와의 관계에 따라 **네 가지 상태**를 가집니다. 이 상태를 구분하는 것이 JPA 디버깅의 절반입니다.

```
            new Book(...)
                │
                ▼
        ┌───────────────┐   persist()    ┌───────────────┐
        │ 비영속 (new)   │ ─────────────▶ │  영속 (managed) │ ◀── find() 결과
        │ transient      │                │  managed        │
        └───────────────┘                └───────┬────────┘
                                                  │ detach() / clear() / close()
                                                  ▼
                                          ┌───────────────┐
                                          │ 준영속(detached)│
                                          └───────────────┘
                                                  ▲ merge()
                              remove()            │
        ┌───────────────┐                         │
        │  삭제 (removed) │ ◀───────────────────────┘
        └───────────────┘
```

| 상태 | 설명 | 컨텍스트 관리 | 변경 감지 |
|------|------|:---:|:---:|
| **비영속 (transient)** | `new`로 막 만든, 컨텍스트와 무관한 순수 객체 | X | X |
| **영속 (managed)** | `persist()` 또는 `find()`로 컨텍스트가 관리 중 | O | O |
| **준영속 (detached)** | 한때 영속이었으나 컨텍스트에서 분리됨 | X | X |
| **삭제 (removed)** | `remove()`로 삭제 예약됨 | O | - |

핵심은 **영속 상태일 때만 변경 감지·1차 캐시·쓰기 지연이 작동한다**는 것입니다. 준영속 객체의 필드를 아무리 바꿔도 `UPDATE`는 나가지 않습니다.

## 3. 1차 캐시와 동일성 보장

영속성 컨텍스트는 내부에 `@Id` 값을 키로 하는 **1차 캐시(first-level cache)** 를 가집니다. 같은 트랜잭션 안에서 같은 ID를 두 번 조회하면, 두 번째 조회는 DB로 가지 않고 캐시된 인스턴스를 그대로 반환합니다.

```kotlin
@Transactional
fun firstLevelCache() {
    val a = em.find(Book::class.java, 1L)  // SELECT 발생 → 1차 캐시에 적재
    val b = em.find(Book::class.java, 1L)  // SELECT 없음 → 캐시에서 반환
    println(a === b)  // true — 같은 인스턴스 (동일성, identity 보장)
}
```

이로부터 **동일성(identity) 보장**이 따라옵니다. 같은 트랜잭션 안에서 같은 식별자로 조회한 엔티티는 `==`(Kotlin 참조 동등) 비교에서 항상 같은 객체입니다. 마치 컬렉션에서 `Map`을 캐시처럼 쓰는 것과 동작이 같습니다.

> [!WARNING]
> 1차 캐시는 **트랜잭션 범위**에서만 유효합니다. 트랜잭션이 끝나면 영속성 컨텍스트와 함께 사라집니다. 애플리케이션 전역에서 공유되는 **2차 캐시**와 혼동하지 마세요. 1차 캐시는 성능 최적화 도구가 아니라, "한 트랜잭션 안에서 객체 동일성을 보장하기 위한" 부산물에 가깝습니다.

## 4. 쓰기 지연 (Write-behind)

`em.persist()`를 호출해도 `INSERT` SQL은 **즉시 나가지 않습니다.** 영속성 컨텍스트는 SQL을 **쓰기 지연 SQL 저장소(action queue)** 에 모아 두었다가, **flush 시점**에 한꺼번에 전송합니다.

```kotlin
@Transactional
fun writeBehind() {
    em.persist(bookA)   // INSERT를 쓰기 지연 저장소에 보관
    em.persist(bookB)   // INSERT를 쓰기 지연 저장소에 보관
    // 여기까지 DB에는 아무 SQL도 가지 않았다
}   // 트랜잭션 커밋 → flush → INSERT A, INSERT B 한 번에 전송
```

```
persist(A) ─┐
persist(B) ─┤─▶ [ 쓰기 지연 SQL 저장소 ]  ──flush──▶  DB (INSERT A; INSERT B;)
            ┘
```

이 방식은 **JDBC 배치(batch)** 최적화의 토대가 됩니다. 모아 둔 INSERT를 묶어 보낼 수 있기 때문입니다(`hibernate.jdbc.batch_size` 설정).

> [!NOTE]
> 단, `IDENTITY` 전략(우리 `Book`의 `@GeneratedValue(strategy = IDENTITY)`)은 예외입니다. ID를 DB의 auto-increment가 매기므로, `persist()` 시점에 **즉시 INSERT를 날려야** ID를 알 수 있습니다. 즉 IDENTITY 전략에서는 쓰기 지연이 사실상 동작하지 않습니다. 쓰기 지연·배치를 제대로 활용하려면 `SEQUENCE` 전략이 유리합니다.

## 5. 변경 감지 (Dirty Checking)

JPA에서 가장 직관에 반하는 동작입니다. **영속 상태 엔티티의 필드를 바꾸면, `save()`를 부르지 않아도 트랜잭션 종료 시 자동으로 `UPDATE`가 나갑니다.**

```kotlin
@Transactional
fun dirtyChecking() {
    val book = em.find(Book::class.java, 1L)  // 영속 상태
    book.price = 25000                         // 단순히 필드만 변경
    // em.update() 같은 메서드는 존재하지 않는다!
}   // 커밋 시 flush → 스냅샷과 비교 → 변경 감지 → UPDATE 자동 전송
```

원리는 이렇습니다. 영속성 컨텍스트는 엔티티를 처음 보관할 때 **스냅샷(snapshot)** 을 함께 저장합니다. flush 시점에 현재 엔티티 상태와 스냅샷을 비교(diff)해, 달라진 필드가 있으면 `UPDATE` SQL을 생성합니다.

```
적재 시:  Book{price=30000}  ──복사──▶  스냅샷{price=30000}
변경:     Book{price=25000}            스냅샷{price=30000}
flush:    비교 → price 다름 → UPDATE book SET price=25000 WHERE id=1
```

> [!TIP]
> 이것이 Phase 3-3에서 "서비스 메서드에 `@Transactional`만 걸면 조회 후 필드 변경만으로 수정이 된다"고 했던 이유입니다. Spring Data JPA의 `save()`는 사실 **새 엔티티엔 `persist`, 이미 영속이던 엔티티엔 `merge`** 를 호출할 뿐, 변경 감지의 본질은 영속성 컨텍스트에 있습니다.

## 6. flush — 동기화의 순간

**flush**는 영속성 컨텍스트의 변경 내용을 DB에 반영(SQL 전송)하는 동작입니다. **flush는 영속성 컨텍스트를 비우지 않습니다.** 단지 "지금까지 쌓인 쓰기 지연 SQL과 변경 감지 결과를 DB로 내보낼" 뿐입니다.

flush가 발생하는 시점은 셋입니다.

1. **트랜잭션 커밋** — 가장 일반적. 커밋 직전 자동 flush.
2. **JPQL 쿼리 실행 직전** — 조회 정합성을 위해 자동 flush(아래 주의).
3. **`em.flush()` 직접 호출** — 수동.

> [!WARNING]
> JPQL 실행 전 자동 flush는 함정의 원천입니다. `persist()`한 엔티티는 1차 캐시엔 있지만 DB엔 아직 없을 수 있는데, JPQL은 **DB에 직접 SQL을 날리므로** 방금 저장한 데이터를 못 볼 수 있습니다. JPA는 이를 막기 위해 JPQL 실행 직전 자동으로 flush해 DB를 동기화합니다(`FlushModeType.AUTO`가 기본). 벌크 연산과 엮이면 더 까다로워지는데, 자세한 내용은 [05-jpql](05-jpql.md)에서 다룹니다.

## 7. detach / clear / merge

영속 상태를 풀거나 다시 붙이는 연산들입니다.

| 메서드 | 효과 |
|--------|------|
| `em.detach(entity)` | 특정 엔티티 하나를 준영속으로 분리. 이후 변경 감지 안 됨 |
| `em.clear()` | 영속성 컨텍스트를 통째로 초기화. 모든 엔티티가 준영속 |
| `em.close()` | 컨텍스트 종료 (트랜잭션 종료 시 자동) |
| `em.merge(entity)` | 준영속/비영속 엔티티를 **복사해** 새 영속 엔티티를 반환 |

`merge`는 특히 오해가 많습니다. **인자로 넘긴 객체가 영속이 되는 게 아니라, 그 값을 복사한 새 인스턴스가 영속이 되어 반환**됩니다.

```kotlin
@Transactional
fun mergeDemo(detachedBook: Book) {
    val managed = em.merge(detachedBook)  // detachedBook은 여전히 준영속
    println(managed === detachedBook)     // false — 반환된 managed만 영속
    managed.price = 19000                 // 이쪽을 변경해야 UPDATE가 나간다
}
```

> [!WARNING]
> `merge`는 준영속 엔티티의 **모든 필드를 통째로 덮어씁니다.** 일부 필드가 `null`이면 그 값으로 `UPDATE`되어 데이터가 날아갈 수 있습니다. 그래서 실무에서는 `merge`보다 **"조회 후 변경 감지"** 패턴을 권장합니다. 즉, 엔티티를 다시 `find`로 영속화한 뒤 필요한 필드만 바꾸는 방식입니다.

## 8. @Transactional 경계와의 관계

영속성 컨텍스트의 생존 범위는 곧 **트랜잭션의 범위**와 같습니다(OSIV를 끈 기본 가정). [Phase 3-4](../phase-3-data-jpa/04-transactions.md)에서 본 `@Transactional`이 정확히 이 경계를 만듭니다.

```
@Transactional fun service() {
   ┌──────────── 트랜잭션 시작 = 영속성 컨텍스트 생성 ────────────┐
   │  find() → 1차 캐시 적재                                      │
   │  엔티티 필드 변경 → (스냅샷과 차이 기록)                      │
   └──────────── 커밋 직전 flush → UPDATE → 컨텍스트 종료 ────────┘
}
```

여기서 그 악명 높은 `LazyInitializationException`이 등장합니다. 트랜잭션(=영속성 컨텍스트)이 끝난 **뒤에** 지연 로딩 필드에 접근하면, 더 이상 엔티티가 영속 상태가 아니라 프록시를 초기화할 수 없어 예외가 터집니다. 이 문제의 본질과 해법(페치 조인, OSIV 등)은 [04-proxy-fetch](04-proxy-fetch.md)에서 본격적으로 다룹니다.

> [!TIP]
> 정리하면 — **영속성 컨텍스트는 트랜잭션 단위로 태어나고 죽으며, 그 안에서만 1차 캐시·동일성·변경 감지·지연 로딩이 동작한다.** 이 한 문장이 JPA 동작의 90%를 설명합니다.

## 다음 단계

영속성 컨텍스트가 엔티티를 어떻게 관리하는지 봤으니, 이제 엔티티 **사이의 관계** — 연관관계 매핑으로 넘어갑니다.

→ [연관관계 매핑](02-associations.md)
