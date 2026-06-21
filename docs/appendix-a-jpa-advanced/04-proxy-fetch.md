# 프록시와 즉시/지연 로딩, N+1

JPA 성능 문제의 90%는 이 한 장에 모여 있습니다. **프록시**가 무엇인지, **지연 로딩**이 어떻게 동작하는지를 이해하지 못하면, 어느 날 운영 로그에서 SQL 수천 개가 쏟아지는 **N+1 문제**를 마주하게 됩니다. [02장](02-associations.md)에서 만든 `Book ↔ Review`, `Book → Category` 연관을 가지고 직접 재현하고 해결합니다.

## 1. 프록시(Proxy)란

`em.find()`는 실제 엔티티를 DB에서 즉시 조회합니다. 반면 **`em.getReference()`** 는 **프록시(proxy)** 객체를 반환합니다. 프록시는 진짜 엔티티를 상속한 **가짜 객체**로, 껍데기만 있고 실제 데이터는 비어 있습니다.

```kotlin
@Transactional
fun proxyDemo() {
    val ref = em.getReference(Book::class.java, 1L)  // SELECT 안 나감! 프록시만 생성
    println(ref.javaClass)        // class Book$HibernateProxy$xxxx — 진짜가 아님
    println(ref.id)               // id는 알고 있으니 SELECT 없음
    println(ref.title)            // ← 이 순간 실제 데이터 필요 → SELECT 발생 (초기화)
}
```

```
getReference() ─▶ [ 프록시: id만 보유, target=null ]
                          │ title 접근 (초기화 트리거)
                          ▼
                   SELECT … WHERE id=1  ─▶  target(진짜 Book) 채움
                          │
                          ▼
                   이후 접근은 target에 위임
```

> [!WARNING]
> 프록시 초기화는 **영속성 컨텍스트(=트랜잭션)가 살아 있을 때만** 가능합니다. 트랜잭션이 끝난 뒤 프록시의 필드에 접근하면 그 악명 높은 **`LazyInitializationException`** 이 터집니다([01장](01-persistence-context.md)에서 예고한 그 예외입니다). 지연 로딩이 곧 프록시 기반이라는 점이 핵심입니다.

## 2. FetchType — LAZY vs EAGER

연관관계를 "언제 로딩할지"를 결정하는 것이 **`FetchType`** 입니다.

| FetchType | 의미 | 동작 |
|-----------|------|------|
| `LAZY` (지연) | 실제 사용할 때 로딩 | 연관 객체 자리에 **프록시**를 넣어 둠 |
| `EAGER` (즉시) | 조회 즉시 함께 로딩 | JOIN 또는 추가 SELECT로 같이 가져옴 |

```kotlin
@ManyToOne(fetch = FetchType.LAZY)   // book 조회 시 category는 프록시
@JoinColumn(name = "category_id")
var category: Category? = null
```

각 연관의 **기본 FetchType**은 다음과 같습니다. 표를 외워 두세요.

| 애너테이션 | 기본 FetchType |
|-----------|:---:|
| `@ManyToOne` | **EAGER** ⚠️ |
| `@OneToOne` | **EAGER** ⚠️ |
| `@OneToMany` | LAZY |
| `@ManyToMany` | LAZY |

> [!TIP]
> **결론: 모든 연관관계를 `LAZY`로 명시하세요.** `@ManyToOne`/`@OneToOne`은 기본이 EAGER라 위험합니다. EAGER는 어떤 SQL이 언제 나갈지 예측이 어렵고, 특히 JPQL과 만나면 그 자체로 N+1을 유발합니다. 필요한 시점에만 페치 조인으로 함께 가져오는 것이 정석입니다.

## 3. N+1 문제 재현

`Book` 100권을 조회하면서 각 책의 `Category`를 출력한다고 합시다. `category`가 LAZY라면 어떻게 될까요?

```kotlin
@Transactional(readOnly = true)
fun nPlusOne() {
    val books = bookRepository.findAll()    // (1) SELECT * FROM book  → 100건
    books.forEach { book ->
        println(book.category?.name)         // (N) 각 book 마다 category SELECT!
    }
}
```

SQL 로그를 보면 다음과 같습니다.

```sql
-- (1) 책 목록: 쿼리 1번
select b.* from book b;
-- (N) 첫 book의 category 프록시 초기화
select c.* from category c where c.id = 10;
-- 두 번째 book
select c.* from category c where c.id = 11;
-- ... 책마다 한 번씩, 최악의 경우 100번 ...
```

즉, **쿼리 1번(목록) + N번(연관 초기화) = N+1번**의 쿼리가 나갑니다. 이것이 **N+1 문제**입니다.

<figure class="flowchart branch-flow">
<ol class="fc-steps">
<li class="fc-step fc-fork"><span class="fc-num">1</span><div class="fc-body"><div class="fc-head"><code>findAll()</code> → 1 쿼리</div><div class="fc-desc">Book 100건 조회</div></div></li>
</ol>
<ul class="fc-branches">
<li class="fc-branch"><code>book[0].category</code><span class="fc-arrow">→</span><span class="fc-status fc-cost">+1 쿼리</span></li>
<li class="fc-branch"><code>book[1].category</code><span class="fc-arrow">→</span><span class="fc-status fc-cost">+1 쿼리</span></li>
<li class="fc-branch"><span class="fc-seg">… book[2] ~ book[99]</span><span class="fc-arrow">→</span><span class="fc-status fc-cost">+1 × 100</span></li>
</ul>
<div class="fc-sum">합계 = 1 + 100 = <strong>101 쿼리</strong><span class="fc-badge-warn">N+1 문제</span></div>
</figure>

> [!WARNING]
> N+1은 **EAGER로 바꿔도 해결되지 않습니다.** EAGER로 바꾸면 단지 N개의 SELECT가 `findAll` "직후"에 나갈 뿐, 횟수는 그대로입니다(오히려 JPQL에서는 즉시 N+1을 유발). N+1의 본질은 fetch 시점이 아니라 **"한 번에 가져오지 않는 것"** 입니다.

## 4. 해결책 비교

### 4-1. 페치 조인 (fetch join) — 가장 근본적

JPQL에서 `join fetch`로 연관을 **한 방의 JOIN**으로 함께 가져옵니다.

```kotlin
@Query("select b from Book b join fetch b.category")
fun findAllWithCategory(): List<Book>
```

```sql
-- 단 1쿼리로 끝
select b.*, c.* from book b inner join category c on b.category_id = c.id;
```

> [!WARNING]
> 페치 조인에는 함정이 있습니다. **`@OneToMany`(컬렉션) 페치 조인은 결과 행이 뻥튀기**됩니다(책 1권 × 리뷰 3개 = 3행). 중복 제거가 필요하고, 무엇보다 **컬렉션 페치 조인과 페이징을 함께 쓰면** Hibernate가 모든 데이터를 메모리에 올려 페이징하는 위험한 경고(`HHH000104`)를 냅니다. 컬렉션은 페치 조인 대신 아래 `@BatchSize`/`default_batch_fetch_size`로 푸는 것이 안전합니다.

### 4-2. @EntityGraph — 어노테이션으로 페치 조인

Spring Data JPA에서 JPQL 없이 페치 조인 효과를 냅니다.

```kotlin
@EntityGraph(attributePaths = ["category"])
@Query("select b from Book b")
fun findAllWithCategoryGraph(): List<Book>

// 메서드 이름 쿼리에도 적용 가능
@EntityGraph(attributePaths = ["category"])
override fun findAll(): List<Book>
```

### 4-3. @BatchSize — IN 절로 묶어 조회

연관 초기화를 **N번이 아니라 `IN` 쿼리 몇 번**으로 줄입니다. 컬렉션 N+1에 특히 유효합니다.

```kotlin
@OneToMany(mappedBy = "book")
@BatchSize(size = 100)         // reviews를 100개씩 IN 절로 묶어 로딩
var reviews: MutableList<Review> = mutableListOf()
```

```sql
-- N번이 아니라, 부족한 것을 IN 으로 한 번에
select * from review where book_id in (1, 2, 3, ..., 100);
```

### 4-4. default_batch_fetch_size — 전역 설정 (실무 권장)

엔티티마다 `@BatchSize`를 붙이는 대신, **전역 기본값**을 설정합니다. 실무에서 가장 추천하는 기본기입니다.

```yaml
spring:
  jpa:
    properties:
      hibernate:
        default_batch_fetch_size: 100   # 100~1000 권장
```

### 해결책 요약

| 방법 | 적용 | 페이징 | 비고 |
|------|------|:---:|------|
| **페치 조인** | `@ManyToOne` 등 단건 연관 | O | 컬렉션엔 부적합 |
| **`@EntityGraph`** | Spring Data 메서드 | O | 페치 조인의 선언적 버전 |
| **`@BatchSize`** | 특정 컬렉션/연관 | O | `IN` 절로 N→1~몇 회 |
| **`default_batch_fetch_size`** | 전역 | O | **기본으로 켜 두기 권장** |

> [!TIP]
> 실전 전략: **(1) 모든 연관 LAZY → (2) `default_batch_fetch_size`를 전역으로 켠다 → (3) 단건 연관은 필요 시 페치 조인/`@EntityGraph`로 명시 조회 → (4) 컬렉션은 배치 페치에 맡긴다.** 이 조합이면 대부분의 N+1을 예측 가능하게 통제할 수 있습니다.

## 5. OSIV (Open Session In View)

Spring Boot는 기본으로 **OSIV가 켜져 있습니다**(`spring.jpa.open-in-view=true`). OSIV는 영속성 컨텍스트(Hibernate 세션)를 **트랜잭션이 아니라 HTTP 요청 끝까지** 살려 둡니다. 덕분에 컨트롤러나 뷰 렌더링 단계에서 지연 로딩을 해도 `LazyInitializationException`이 나지 않습니다.

```
OSIV ON:  요청 시작 ─[영속성 컨텍스트 ──── 살아있음 ─────]─ 응답 종료
                       └ 트랜잭션 ┘ └ 컨트롤러/뷰에서 지연 로딩 가능 ┘

OSIV OFF: 요청 시작 ─[ ─트랜잭션=영속성 컨텍스트─ ]── 컨트롤러 → 응답 종료
                                                  └ 여기서 지연 로딩하면 예외 ┘
```

| | OSIV ON (기본) | OSIV OFF |
|---|---|---|
| 장점 | 컨트롤러/뷰에서 지연 로딩 편리 | DB 커넥션을 트랜잭션 동안만 점유 |
| 단점 | **DB 커넥션을 요청 끝까지 점유** → 고부하 시 커넥션 고갈 | 서비스 계층에서 필요한 데이터를 **미리 다 로딩**해야 함 |

> [!WARNING]
> 트래픽이 많은 실무 API 서버에서는 **OSIV를 끄는 것을 권장**합니다(`spring.jpa.open-in-view=false`). 커넥션 점유 시간이 길어지면 동시 요청이 몰릴 때 커넥션 풀이 고갈됩니다. 대신 **서비스 계층(`@Transactional`) 안에서** 필요한 연관을 페치 조인/배치로 모두 로딩한 뒤, **DTO로 변환**해 컨트롤러로 넘기는 패턴을 씁니다. [Phase 3-4](../phase-3-data-jpa/04-transactions.md)에서 본 트랜잭션 경계 설계가 여기서 그대로 이어집니다.

## 다음 단계

연관과 로딩 전략을 손에 쥐었으니, 이제 그것들을 직접 조회하는 언어 — **JPQL**로 마무리합니다. 페치 조인도 결국 JPQL 문법의 일부였습니다.

→ [JPQL](05-jpql.md)
