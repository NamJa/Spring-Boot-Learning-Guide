# Bean 생명주기와 스코프

[02번 문서](02-ioc-and-di.md)에서 컨테이너가 Bean을 만들고 연결한다는 것을 배웠습니다. 그렇다면 그 Bean은 **정확히 언제 생성되고, 어떻게 초기화되며, 언제 사라질까요?** 그리고 매번 새 객체가 만들어질까요, 아니면 하나를 공유할까요? 이 문서는 Bean의 생명주기와 스코프를 다룹니다. DB 커넥션 풀을 열고 닫거나, 캐시를 준비하고 비우는 등 **리소스 관리**에 직결되는 중요한 내용입니다.

## 1. Bean 생명주기 한눈에 보기

컨테이너는 Bean을 단순히 `new` 하는 게 아니라, 여러 단계를 거쳐 "쓸 준비가 된" 상태로 만듭니다.

```
┌──────────────────────────────────────────────────────────────┐
│                    Bean 생명주기                                │
├──────────────────────────────────────────────────────────────┤
│ 1. 인스턴스화 (Instantiation)                                  │
│      생성자 호출 → 객체 생성, 의존성 주입(생성자 주입)            │
│                          │                                     │
│ 2. 프로퍼티 주입 (Populate)                                    │
│      세터/필드 주입이 있다면 이 단계에서 채움                     │
│                          │                                     │
│ 3. Aware 콜백                                                  │
│      BeanNameAware, ApplicationContextAware 등으로             │
│      컨테이너 정보 주입                                          │
│                          │                                     │
│ 4. BeanPostProcessor (초기화 前)                               │
│      postProcessBeforeInitialization                          │
│                          │                                     │
│ 5. 초기화 (Initialization)                                     │
│      @PostConstruct → InitializingBean.afterPropertiesSet     │
│      → @Bean(initMethod) 순으로 호출                           │
│                          │                                     │
│ 6. BeanPostProcessor (초기화 後)  ★ AOP 프록시가 여기서 입혀짐  │
│      postProcessAfterInitialization                          │
│                          │                                     │
│ ============  Bean 사용 준비 완료 (Ready) ============         │
│                          │                                     │
│ 7. 소멸 (Destruction) — 컨테이너 종료 시                       │
│      @PreDestroy → DisposableBean.destroy                     │
│      → @Bean(destroyMethod) 순으로 호출                        │
└──────────────────────────────────────────────────────────────┘
```

> **TIP**: `@Transactional`, `@Async` 같은 AOP 기능이 6단계(초기화 후처리)에서 **프록시로 감싸진다**는 점이 핵심입니다. 그래서 [01번 문서](01-what-is-spring.md)에서 말한 "내부 메서드 호출에는 트랜잭션이 안 걸리는 함정"이 생기는 것입니다.

## 2. 초기화 / 소멸 콜백

실무에서 가장 많이 쓰는 것은 **`@PostConstruct`**(초기화)와 **`@PreDestroy`**(소멸) 어노테이션입니다. `jakarta.annotation` 패키지에 있습니다.

```kotlin
import jakarta.annotation.PostConstruct
import jakarta.annotation.PreDestroy

@Service
class BookCacheService(private val repository: BookRepository) {

    private val cache = mutableMapOf<Long, Book>()

    @PostConstruct
    fun warmUp() {
        // 모든 의존성 주입이 끝난 직후 1회 실행. 캐시 예열 등 준비 작업에 적합
        println("도서 캐시 예열 시작")
    }

    @PreDestroy
    fun cleanUp() {
        // 컨테이너 종료 직전 1회 실행. 리소스 정리에 적합
        cache.clear()
        println("도서 캐시 정리 완료")
    }
}
```

> **WARNING**: 생성자에서 무거운 초기화 작업을 하지 마세요. 생성자 시점에는 아직 모든 의존성이 완전히 준비됐다고 보장하기 어렵고, AOP 프록시도 입혀지기 전입니다. 초기화 로직은 `@PostConstruct`에 두는 것이 안전합니다.

`@Bean` 메서드로 등록하는 외부 객체는 어노테이션을 붙일 수 없으니, 다음처럼 메서드 이름을 지정합니다.

```kotlin
@Configuration
class AppConfig {
    @Bean(initMethod = "start", destroyMethod = "stop")
    fun connectionPool(): ConnectionPool = ConnectionPool()
}
```

## 3. Bean 스코프

**스코프(scope)** 는 "이 Bean의 인스턴스를 몇 개 만들고 얼마나 오래 유지할지"를 결정합니다.

| 스코프 | 인스턴스 수명 | 사용 맥락 |
| --- | --- | --- |
| **singleton** (기본) | 컨테이너당 단 1개, 앱 전체에서 공유 | 거의 모든 Bean (Service, Repository 등) |
| **prototype** | 요청(주입/조회)할 때마다 새 인스턴스 | 상태를 가지는 일회성 객체 |
| **request** | HTTP 요청 1건마다 1개 | 웹 요청별 데이터 보관 |
| **session** | HTTP 세션마다 1개 | 사용자 세션별 데이터 |
| **application** | ServletContext당 1개 | 웹 앱 전역 공유 |

`request`/`session`/`application`은 웹 환경(MVC/WebFlux)에서만 의미가 있습니다.

### 3.1 singleton — 기본값

별도 지정이 없으면 모든 Bean은 **singleton**입니다. 즉 `BookService`는 앱 전체에서 **단 하나의 인스턴스**가 공유됩니다.

```kotlin
@Service
class BookService(private val repository: BookRepository) // 기본 singleton
```

> **WARNING**: singleton Bean은 여러 스레드가 동시에 공유합니다. 따라서 **가변 상태(mutable field)를 두면 동시성 버그**가 생깁니다. `BookService`에 `var currentUser`처럼 요청별 상태를 두면 안 됩니다. Bean은 무상태(stateless)로 설계하세요.

### 3.2 prototype — 요청마다 새 객체

```kotlin
@Component
@Scope("prototype")
class BookImportJob {
    // 주입/조회할 때마다 매번 새 인스턴스가 생성됨
    private val processedIds = mutableListOf<Long>()
}
```

> **WARNING**: singleton Bean이 prototype Bean을 생성자 주입으로 받으면, **주입은 한 번만 일어나** prototype의 의미가 깨집니다(매번 새로 받지 못함). 매 호출마다 새 인스턴스가 필요하면 `ObjectProvider<BookImportJob>`를 주입받아 `getObject()`로 그때그때 꺼내는 패턴을 씁니다.

```kotlin
@Service
class BatchService(
    private val jobProvider: ObjectProvider<BookImportJob>,
) {
    fun run() {
        val job = jobProvider.getObject() // 호출할 때마다 새 prototype 인스턴스
    }
}
```

### 3.3 request 스코프 예시

```kotlin
@Component
@Scope(value = "request", proxyMode = ScopedProxyMode.TARGET_CLASS)
class RequestContext {
    var requestId: String = java.util.UUID.randomUUID().toString()
}
```

singleton인 Service가 request 스코프 Bean을 주입받아야 할 때, 수명이 더 짧은 Bean을 직접 주입하면 문제가 생깁니다. 그래서 `proxyMode`로 **프록시를 주입**해 두고, 실제 사용 시점에 현재 요청에 맞는 인스턴스로 연결합니다.

## 4. 지연 초기화 — @Lazy

singleton Bean은 기본적으로 **앱 기동 시점에 모두 생성(eager)** 됩니다. 기동 중 설정 오류를 빨리 발견할 수 있어 좋은 기본값입니다. 하지만 생성 비용이 큰데 자주 안 쓰는 Bean이라면 `@Lazy`로 **실제 처음 사용될 때까지 생성을 미룰** 수 있습니다.

```kotlin
@Service
@Lazy
class HeavyReportService {
    init { println("무거운 리포트 서비스 초기화") } // 처음 사용될 때 출력됨
}
```

주입 지점에 붙이면 해당 의존성만 지연시킬 수도 있습니다.

```kotlin
@Service
class BookService(
    @Lazy private val reportService: HeavyReportService, // 프록시로 주입, 실제 호출 때 초기화
)
```

> **TIP**: `application.yml`에 `spring.main.lazy-initialization=true`를 주면 전체 Bean을 지연 초기화할 수 있지만, 기동 시 오류를 늦게 발견하게 되므로 운영 환경에서는 신중히 사용하세요.

## 5. 생성 순서 제어 — @DependsOn

Bean 간 의존 관계가 코드에 드러나지 않지만(예: 정적 초기화, 외부 부수 효과) **특정 Bean을 먼저 만들어야 할 때** `@DependsOn`으로 순서를 강제합니다.

```kotlin
@Service
@DependsOn("schemaInitializer") // schemaInitializer Bean을 먼저 생성한 뒤 이 Bean 생성
class BookService(private val repository: BookRepository)
```

> **TIP**: `@DependsOn`은 최후의 수단입니다. 가능하면 명시적 의존성(생성자 주입)으로 순서가 자연스럽게 결정되도록 설계하는 것이 좋습니다. 의존 관계가 코드에 안 보이면 유지보수가 어려워집니다.

## 다음 단계

➡️ [04. 자동 설정과 스타터](04-auto-configuration.md) — `@SpringBootApplication`의 정체를 해부하고, 클래스패스만 보고 Bean을 알아서 만들어 주는 자동 설정의 원리를 파헤칩니다.
