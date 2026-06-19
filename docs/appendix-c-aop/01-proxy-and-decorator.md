# 프록시와 동적 프록시

AOP의 정체를 이해하려면, 먼저 **프록시(proxy)** 를 알아야 합니다. Spring AOP는 결국 "여러분의 빈을 프록시 객체로 감싸 호출을 가로채는" 기술이기 때문입니다. 이 페이지에서는 횡단 관심사 문제에서 출발해, 프록시·데코레이터 패턴, 그리고 Spring이 런타임에 프록시를 자동으로 만들어 내는 두 가지 방식(JDK 동적 프록시 / CGLIB)을 비교합니다.

## 1. 문제 — 횡단 관심사가 비즈니스 코드를 오염시킨다

도서 등록 메서드에 "실행 시간을 로그로 남겨 달라"는 요구가 들어왔다고 합시다. AOP 없이 직접 짜면 이렇게 됩니다.

```kotlin
@Service
class BookService(private val bookRepository: BookRepository) {

    private val log = LoggerFactory.getLogger(javaClass)

    fun create(request: CreateBookRequest): BookResponse {
        val start = System.currentTimeMillis()       // ← 부가 기능
        try {
            // ↓↓↓ 진짜 비즈니스 로직은 이 한 줄
            return bookRepository.save(request.toEntity()).toResponse()
        } finally {
            val took = System.currentTimeMillis() - start   // ← 부가 기능
            log.info("create() 실행 시간 = {}ms", took)        // ← 부가 기능
        }
    }
}
```

비즈니스 로직은 한 줄인데 부가 코드가 메서드를 뒤덮었습니다. 더 큰 문제는 **`findById`, `update`, `delete`에도 똑같은 코드를 복사해야 한다**는 것입니다. 로깅 형식을 바꾸려면 수십 군데를 고쳐야 하죠. 이것이 횡단 관심사가 흩어졌을 때 생기는 전형적인 고통입니다.

## 2. 프록시 패턴 — 대신 받아 주는 대리인

**프록시**는 원본 객체(real subject)와 **같은 인터페이스를 구현한 대리 객체**입니다. 클라이언트는 원본인 줄 알고 프록시를 호출하고, 프록시는 부가 기능을 수행한 뒤 원본에게 일을 넘깁니다.

```
  클라이언트 ──► [ 프록시 ] ──► [ 실제 BookService ]
                  │  부가기능(로깅) 후
                  └─ 원본에 위임(delegate)
```

핵심은 클라이언트가 **프록시인지 원본인지 구별하지 못한다**는 점입니다. 같은 타입(인터페이스)이기 때문입니다.

```kotlin
interface BookService {
    fun create(request: CreateBookRequest): BookResponse
}

// 실제 구현
class BookServiceImpl(private val bookRepository: BookRepository) : BookService {
    override fun create(request: CreateBookRequest): BookResponse =
        bookRepository.save(request.toEntity()).toResponse()
}

// 프록시 — 같은 인터페이스를 구현하고, 부가 기능 후 원본에 위임
class BookServiceLoggingProxy(private val target: BookService) : BookService {
    private val log = LoggerFactory.getLogger(javaClass)

    override fun create(request: CreateBookRequest): BookResponse {
        val start = System.currentTimeMillis()
        try {
            return target.create(request)        // 원본에 위임
        } finally {
            log.info("create() = {}ms", System.currentTimeMillis() - start)
        }
    }
}
```

이제 `BookServiceImpl`은 비즈니스 로직만, 프록시는 로깅만 책임집니다. **관심사가 분리**됐습니다.

## 3. 데코레이터 패턴과의 관계

프록시 패턴과 **데코레이터(decorator) 패턴**은 코드 구조(원본과 같은 인터페이스를 구현하고 위임)가 거의 같아 헷갈립니다. 차이는 **의도**에 있습니다.

| 구분 | 프록시 패턴 | 데코레이터 패턴 |
| --- | --- | --- |
| 의도 | 접근 **제어**(권한, 캐싱, 지연 로딩) | 기능 **추가**(부가 동작 덧붙이기) |
| 클라이언트가 보는 것 | "원본을 그대로 쓴다"고 생각 | "기능이 더해진 것"을 알 수도 있음 |
| Spring AOP에서는 | 두 의도를 모두 포괄해 **프록시**라 부름 | — |

> [!TIP]
> GoF는 둘을 구분하지만, Spring AOP 문맥에서는 의도와 무관하게 "호출을 가로채 부가 기능을 더하는 대리 객체"를 통칭 **프록시**라고 부릅니다. 용어에 너무 매이지 마세요.

## 4. 동적 프록시 — 프록시를 손으로 안 만든다

위 `BookServiceLoggingProxy`는 메서드가 늘어날 때마다 손으로 위임 코드를 써야 합니다. `findById`, `update`, `delete`까지 일일이 오버라이드하는 건 비현실적이죠. 그래서 Spring은 **런타임에 프록시 클래스를 자동 생성**합니다. 이를 **동적 프록시(dynamic proxy)** 라고 하며, 두 가지 방식이 있습니다.

### 4-1. JDK 동적 프록시 — 인터페이스 기반

JDK가 표준으로 제공하는 `java.lang.reflect.Proxy`를 씁니다. **인터페이스를 구현한** 프록시를 런타임에 만듭니다.

```kotlin
val proxy = Proxy.newProxyInstance(
    BookService::class.java.classLoader,
    arrayOf(BookService::class.java),     // ← 반드시 "인터페이스"가 필요
    InvocationHandler { _, method, args ->
        val start = System.currentTimeMillis()
        try {
            method.invoke(target, *(args ?: emptyArray()))   // 원본에 위임
        } finally {
            log.info("{}() = {}ms", method.name, System.currentTimeMillis() - start)
        }
    }
) as BookService
```

**제약**: 대상이 반드시 **인터페이스를 구현**해야 합니다. 구체 클래스만 있으면 JDK 동적 프록시를 만들 수 없습니다.

### 4-2. CGLIB — 클래스 상속 기반

CGLIB(Code Generation Library)는 대상 클래스를 **상속(extends)한 자식 클래스**를 바이트코드로 생성해 프록시로 씁니다. 메서드를 오버라이드해 가로채므로 **인터페이스가 없어도** 됩니다.

```
JDK 동적 프록시:  프록시  implements  BookService(인터페이스)
CGLIB:           프록시  extends     BookServiceImpl(클래스)
```

### 4-3. 비교표

| 항목 | JDK 동적 프록시 | CGLIB |
| --- | --- | --- |
| 기반 | 인터페이스 구현 | 클래스 상속 |
| 전제 조건 | 대상이 **인터페이스**를 가져야 함 | 인터페이스 불필요 (구체 클래스 OK) |
| 한계 | 인터페이스에 선언된 메서드만 프록시 | **`final` 클래스/메서드는 상속 불가 → 프록시 불가** |
| 제공 주체 | JDK 표준 (`java.lang.reflect.Proxy`) | 라이브러리 (Spring Core에 내장) |
| Spring Boot 기본값 | (예전 Spring 기본) | **현재 기본** |

## 5. Spring Boot는 왜 기본으로 CGLIB을 쓰는가

과거 순수 Spring은 "인터페이스가 있으면 JDK 동적 프록시, 없으면 CGLIB"이었습니다. 하지만 **Spring Boot는 4.x에서도 일관되게 CGLIB을 기본**(`spring.aop.proxy-target-class=true`)으로 씁니다. 이유는:

- **인터페이스 유무에 따라 동작이 달라지지 않아** 혼란이 적다.
- 인터페이스에 선언되지 않은 **구체 클래스의 public 메서드도 프록시**할 수 있다.
- JDK 동적 프록시는 프록시 타입이 인터페이스라, 구현 클래스 타입으로 주입받으려 하면 `ClassCastException`이 난다 — CGLIB은 자식 클래스라 이 문제가 없다.

> [!TIP]
> 굳이 JDK 동적 프록시로 강제하고 싶다면 `spring.aop.proxy-target-class=false`로 바꿀 수 있지만, 특별한 이유가 없다면 기본값(CGLIB)을 권장합니다.

## 6. Kotlin의 `final` 문제와 all-open 플러그인

CGLIB은 대상 클래스를 **상속**해 프록시를 만든다고 했습니다. 그런데 **Kotlin의 클래스와 메서드는 기본이 `final`** 입니다. `final`은 상속·오버라이드가 금지된다는 뜻이므로, 그대로 두면 **CGLIB이 프록시를 만들 수 없습니다.**

```kotlin
@Service
class BookService { ... }   // Kotlin에서 이 클래스는 사실상 final

// → CGLIB이 상속하려다 실패
//   "Cannot subclass final class ..." 같은 에러 또는 프록시 미적용
```

해결책이 **Phase 1에서 이미 적용한** `kotlin("plugin.spring")`(내부적으로 all-open) 플러그인입니다. 이 플러그인은 `@Component`, `@Service`, `@Repository`, `@Configuration`, `@Transactional`, `@Async`, `@Aspect` 등이 붙은 클래스와 그 멤버를 **자동으로 `open`** 으로 바꿔 줍니다. 따라서 우리가 직접 `open`을 붙이지 않아도 프록시가 정상 생성됩니다.

```kotlin
// build.gradle.kts (Phase 1에서 설정 완료)
plugins {
    kotlin("plugin.spring") version "2.3.21"   // all-open: 스프링 애너테이션 클래스를 open 처리
}
```

> [!WARNING]
> all-open이 자동으로 열어 주는 건 **스프링 표준 애너테이션이 붙은 클래스**뿐입니다. 자작 애너테이션이나 일반 클래스를 프록시 대상으로 삼고 싶다면 직접 `open`을 붙이거나 all-open 설정에 애너테이션을 추가해야 합니다. 이 `final`/`open` 함정은 [03. 함정과 내부 동작](03-pitfalls-and-internals.md)에서 다시 다룹니다.

## 다음 단계

프록시의 원리를 이해했으니, 이제 손으로 프록시를 짜는 대신 **Spring AOP가 선언적으로 같은 일을 하게** 만들 차례입니다. → **[02. Spring AOP 실전](02-spring-aop.md)**
