# Spring AOP 실전

[앞 페이지](01-proxy-and-decorator.md)에서 본 프록시를 손으로 짜는 건 고통스럽습니다. Spring AOP는 **`@Aspect` 한 곳에 부가 기능을 모아 두고, 포인트컷으로 "어디에 끼울지"만 선언**하면 프록시를 알아서 만들어 줍니다. 이 페이지에서는 의존성 설정부터 포인트컷 표현식, 어드바이스 5종을 다루고, 도서 API에 실습 2개를 적용합니다.

## 1. 의존성 추가

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-aop")
}
```

이 스타터는 AspectJ의 **애너테이션(`@Aspect`, `@Around` 등)** 과 위빙(weaving) 도구를 가져옵니다. 다만 Spring AOP는 컴파일/로드 타임 위빙이 아니라, [앞에서 본] **런타임 프록시 기반**으로 동작한다는 점을 기억하세요. (AspectJ는 문법만 빌려 쓰는 것)

## 2. AOP 핵심 용어

```
  ┌──────────────────── Aspect (관점) ────────────────────┐
  │   Pointcut(어디에)  +  Advice(무엇을 언제)               │
  └────────────────────────────────────────────────────────┘
                          │ 적용
                          ▼
   BookService.create(...)   ← Join Point(적용 가능 지점)
```

| 용어 | 뜻 |
| --- | --- |
| **Aspect** | 횡단 관심사를 모듈화한 단위 (`@Aspect` 클래스) |
| **Join Point** | 어드바이스가 끼어들 수 있는 지점. Spring AOP에서는 **메서드 실행** 시점만 가능 |
| **Pointcut** | 수많은 Join Point 중 "실제로 적용할 곳"을 고르는 표현식 |
| **Advice** | 그 지점에서 실행할 부가 기능 (전/후/예외 등) |
| **Target** | 프록시가 감싸는 원본 빈 |

## 3. 첫 Aspect

`@Aspect`와 `@Component`를 함께 붙여 **스프링 빈으로 등록**해야 동작합니다. (Spring Boot는 `@EnableAspectJAutoProxy`를 자동 구성하므로 별도 설정 불필요)

```kotlin
import org.aspectj.lang.ProceedingJoinPoint
import org.aspectj.lang.annotation.Around
import org.aspectj.lang.annotation.Aspect
import org.springframework.stereotype.Component

@Aspect
@Component
class HelloAspect {

    @Around("execution(* com.example.bookapi.service..*(..))")
    fun around(joinPoint: ProceedingJoinPoint): Any? {
        println("[AOP] ${joinPoint.signature.name} 호출 전")
        val result = joinPoint.proceed()        // 원본 메서드 실행
        println("[AOP] ${joinPoint.signature.name} 호출 후")
        return result
    }
}
```

> [!TIP]
> `@Aspect`도 all-open 플러그인이 열어 주는 대상이지만, AOP가 동작하려면 **반드시 `@Component`(또는 `@Bean`)로 빈 등록**이 추가로 필요합니다. `@Aspect`만 붙이면 메타데이터일 뿐, 빈이 아니면 프록시가 만들어지지 않습니다.

## 4. 포인트컷 표현식

"어디에 적용할지"를 고르는 핵심 문법입니다. 자주 쓰는 세 가지를 봅니다.

### 4-1. `execution` — 메서드 시그니처로 매칭

가장 많이 쓰는 지정자입니다.

```
execution( [접근제어자] 반환타입 [선언타입.]메서드명(파라미터) )
```

```kotlin
// service 패키지 및 하위 패키지의 모든 메서드
"execution(* com.example.bookapi.service..*(..))"

// BookService의 모든 메서드
"execution(* com.example.bookapi.service.BookService.*(..))"

// 이름이 find 로 시작하는 메서드, 파라미터 무관
"execution(* com.example.bookapi.service..find*(..))"
```

- `*` : 아무 값 하나 (반환타입/메서드명 등)
- `..` : 패키지에서는 "0개 이상의 하위 패키지", 파라미터에서는 "0개 이상의 파라미터"

### 4-2. `@annotation` — 특정 애너테이션이 붙은 메서드

```kotlin
// @LogExecution 이 붙은 메서드에만 적용 (실습 2에서 사용)
"@annotation(com.example.bookapi.aop.LogExecution)"
```

### 4-3. `bean` — 빈 이름으로 매칭

```kotlin
// 이름이 bookService 인 빈의 모든 메서드
"bean(bookService)"

// Service 로 끝나는 모든 빈
"bean(*Service)"
```

여러 표현식은 `&&`, `||`, `!`로 조합할 수 있습니다.

```kotlin
"execution(* com.example.bookapi.service..*(..)) && !execution(* *..find*(..))"
```

## 5. 어드바이스 5종

`ProceedingJoinPoint`로 원본 실행을 직접 제어하는 `@Around`가 가장 강력하고, 나머지는 특정 시점에만 끼어듭니다.

| 어드바이스 | 시점 | 파라미터 | `proceed()` 호출 |
| --- | --- | --- | --- |
| `@Around` | 전·후 전체를 감쌈 | `ProceedingJoinPoint` | **직접 호출** |
| `@Before` | 메서드 실행 전 | `JoinPoint` | 자동 |
| `@AfterReturning` | 정상 반환 후 | `JoinPoint`, `returning` | 자동 |
| `@AfterThrowing` | 예외 발생 시 | `JoinPoint`, `throwing` | 자동 |
| `@After` | 정상/예외 무관 항상 (finally) | `JoinPoint` | 자동 |

```kotlin
@Aspect
@Component
class AllAdviceDemoAspect {

    private val log = LoggerFactory.getLogger(javaClass)
    private val pc = "execution(* com.example.bookapi.service..*(..))"

    @Before(pc)
    fun before(jp: JoinPoint) =
        log.info("[Before] {} args={}", jp.signature.name, jp.args.toList())

    @AfterReturning(pointcut = pc, returning = "result")
    fun afterReturning(jp: JoinPoint, result: Any?) =
        log.info("[AfterReturning] {} -> {}", jp.signature.name, result)

    @AfterThrowing(pointcut = pc, throwing = "ex")
    fun afterThrowing(jp: JoinPoint, ex: Throwable) =
        log.warn("[AfterThrowing] {} 예외: {}", jp.signature.name, ex.message)

    @After(pc)
    fun after(jp: JoinPoint) =
        log.info("[After] {} 종료(finally)", jp.signature.name)
}
```

- **`JoinPoint`**: 호출 대상 정보(메서드명 `signature`, 인자 `args`)를 읽기만 함.
- **`ProceedingJoinPoint`**: `JoinPoint`를 상속하며, `proceed()`로 **원본 실행 여부·시점·결과까지 제어**. `@Around`에서만 받을 수 있음.

> [!WARNING]
> `@Around`에서 `proceed()`를 호출하지 않으면 **원본 메서드가 아예 실행되지 않습니다.** 또한 `proceed()`의 반환값을 그대로 `return`해야 호출자가 정상적인 결과를 받습니다.

## 6. 실습 ① — 실행 시간 측정 Aspect

서비스 계층 전체 메서드의 실행 시간을 측정하는 Aspect입니다. `@Around` 하나로 끝납니다.

```kotlin
package com.example.bookapi.aop

import org.aspectj.lang.ProceedingJoinPoint
import org.aspectj.lang.annotation.Around
import org.aspectj.lang.annotation.Aspect
import org.slf4j.LoggerFactory
import org.springframework.stereotype.Component

@Aspect
@Component
class ExecutionTimeAspect {

    private val log = LoggerFactory.getLogger(javaClass)

    // 서비스 계층 전체에 적용
    @Around("execution(* com.example.bookapi.service..*(..))")
    fun measure(joinPoint: ProceedingJoinPoint): Any? {
        val start = System.currentTimeMillis()
        try {
            return joinPoint.proceed()                       // 원본 실행
        } finally {
            val took = System.currentTimeMillis() - start
            log.info("⏱ {} 실행 시간 = {}ms", joinPoint.signature.toShortString(), took)
        }
    }
}
```

`BookService.create()`를 호출하면, **비즈니스 코드는 손도 안 댔는데** 로그가 찍힙니다.

```
⏱ BookService.create(..) 실행 시간 = 12ms
```

[01 페이지의 1번 예제](01-proxy-and-decorator.md)에서 `BookService`를 오염시켰던 측정 코드가 깔끔히 사라졌습니다.

## 7. 실습 ② — 커스텀 `@LogExecution` 애너테이션 로깅

전체가 아니라 **원하는 메서드에만** 로깅을 켜고 싶다면, 마커 애너테이션을 만들고 `@annotation` 포인트컷으로 잡습니다.

```kotlin
package com.example.bookapi.aop

// 1) 마커 애너테이션 정의
@Target(AnnotationTarget.FUNCTION)         // 메서드에 부착
@Retention(AnnotationRetention.RUNTIME)    // 런타임까지 유지되어야 AOP가 읽음
annotation class LogExecution
```

```kotlin
// 2) @LogExecution 이 붙은 메서드만 가로채는 Aspect
@Aspect
@Component
class LogExecutionAspect {

    private val log = LoggerFactory.getLogger(javaClass)

    @Around("@annotation(com.example.bookapi.aop.LogExecution)")
    fun log(joinPoint: ProceedingJoinPoint): Any? {
        val name = joinPoint.signature.toShortString()
        log.info("▶ {} 시작, args={}", name, joinPoint.args.toList())
        return try {
            joinPoint.proceed().also { log.info("◀ {} 정상 종료", name) }
        } catch (e: Throwable) {
            log.warn("✖ {} 예외: {}", name, e.message)
            throw e                                  // 예외는 반드시 다시 던진다
        }
    }
}
```

```kotlin
// 3) 적용 — 원하는 메서드에만 애너테이션을 붙인다
@Service
@Transactional(readOnly = true)
class BookService(private val bookRepository: BookRepository) {

    @LogExecution                                    // ← 이 메서드만 로깅됨
    @Transactional
    fun create(request: CreateBookRequest): BookResponse =
        bookRepository.save(request.toEntity()).toResponse()

    fun findById(id: Long): BookResponse =           // 애너테이션 없음 → 로깅 안 됨
        bookRepository.findById(id).orElseThrow().toResponse()
}
```

`@RestController`의 핸들러에도 붙일 수 있어, 컨트롤러·서비스 어디든 **선언적으로 로깅을 켜고 끌 수** 있습니다.

> [!TIP]
> 실무에서는 `@LogExecution`에 `level`이나 `message` 같은 속성을 두고, 어드바이스에서 `MethodSignature`로 애너테이션 인스턴스를 꺼내 읽는 패턴을 자주 씁니다. 마커에서 시작해 점진적으로 확장하세요.

## 다음 단계

Aspect를 만드는 법을 익혔습니다. 하지만 AOP에는 **"분명히 붙였는데 안 먹는"** 함정이 많습니다. → **[03. 함정과 내부 동작](03-pitfalls-and-internals.md)** 에서 자기 호출 문제와 `@Transactional`의 내부 동작을 파헤칩니다.
