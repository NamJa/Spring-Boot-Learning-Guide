# 함정과 내부 동작

AOP는 "분명히 애너테이션을 붙였는데 동작하지 않는" 버그를 만들기로 악명 높습니다. 원인은 거의 항상 **프록시의 동작 방식**에 있습니다. 이 페이지는 가장 흔한 함정들과, `@Transactional`이 AOP로 동작하는 내부 원리를 파헤쳐 "보이지 않는 마법"의 정체를 드러냅니다.

## 1. 자기 호출(self-invocation) — 프록시를 우회한다

가장 악명 높은 함정입니다. **같은 클래스 안의 메서드를 `this`로 호출하면, 프록시를 거치지 않으므로 AOP가 적용되지 않습니다.** [Phase 3-4 트랜잭션](../phase-3-data-jpa/04-transactions.md)에서 예고했던 바로 그 문제입니다.

```kotlin
@Service
class BookService(private val bookRepository: BookRepository) {

    fun createTwo(a: CreateBookRequest, b: CreateBookRequest) {
        create(a)        // ⚠ this.create(a) — 프록시를 우회한다!
        create(b)        // ⚠ @Transactional / @LogExecution 안 먹힘
    }

    @Transactional
    @LogExecution
    fun create(request: CreateBookRequest): BookResponse =
        bookRepository.save(request.toEntity()).toResponse()
}
```

왜 안 될까요? 호출 경로를 그림으로 보면 명확합니다.

```
  컨트롤러 ──► [프록시] ──► BookService.createTwo()
                              │
                              └─ create()   ← 여기서 'this.create()'
                                              프록시가 아니라 원본 객체를
                                              직접 부르므로 어드바이스 미적용!

  올바른 경로:  컨트롤러 ──► [프록시] ──► create()  ← 프록시를 거침 → 적용 O
```

`create()`에 붙은 `@Transactional`·`@LogExecution`은 **프록시를 통해 들어올 때만** 발동합니다. 그런데 `createTwo` 안의 `create()`는 프록시가 아닌 **원본 인스턴스(`this`)** 의 메서드를 직접 호출하므로 어드바이스가 끼어들 틈이 없습니다.

### 해결책

| 방법 | 설명 |
| --- | --- |
| **빈 분리(권장)** | `create()`를 별도 빈(예: `BookCreator`)으로 빼고, 그 빈을 주입받아 호출. 외부 빈 호출이므로 프록시를 거침. |
| **구조 변경** | 자기 호출 자체를 없애도록 메서드 설계를 재구성. |
| 자기 주입 | 자기 자신의 프록시를 주입받아 `self.create()` 호출. 동작하지만 가독성이 나빠 비권장. |
| `AopContext` | `AopContext.currentProxy()`로 프록시 획득. 설정이 필요하고 코드가 지저분해 비권장. |

```kotlin
// 해결: 빈 분리
@Service
class BookCreator(private val bookRepository: BookRepository) {
    @Transactional
    @LogExecution
    fun create(request: CreateBookRequest): BookResponse =
        bookRepository.save(request.toEntity()).toResponse()
}

@Service
class BookService(private val bookCreator: BookCreator) {
    fun createTwo(a: CreateBookRequest, b: CreateBookRequest) {
        bookCreator.create(a)    // 외부 빈 → 프록시를 거침 → AOP 적용 O
        bookCreator.create(b)
    }
}
```

> [!WARNING]
> `@Transactional`이 "왜 롤백이 안 되지?"라며 헤맬 때, 80%는 자기 호출입니다. 트랜잭션 메서드를 같은 클래스의 다른 메서드가 부르고 있지 않은지 가장 먼저 의심하세요.

## 2. `final`/`open` 함정 — 프록시를 못 만든다

[01 페이지](01-proxy-and-decorator.md)에서 본 대로, CGLIB은 대상을 **상속**해 프록시를 만듭니다. 따라서 `final` 클래스나 `final` 메서드는 프록시할 수 없습니다.

```kotlin
// 만약 all-open 플러그인이 없다면, Kotlin 기본값이 final 이라
@Service
class BookService {
    @Transactional
    fun create(...) { ... }    // final 메서드 → 오버라이드 불가 → 프록시 미적용
}
```

Phase 1의 `kotlin("plugin.spring")`(all-open)이 스프링 애너테이션 클래스를 자동으로 `open`으로 바꿔 주므로 평소엔 문제가 없습니다. 하지만 **all-open이 인식하지 못하는 자작 애너테이션 기반 빈**이나, 실수로 `final`을 명시한 메서드에서는 조용히 AOP가 빠질 수 있습니다.

> [!TIP]
> AOP가 안 먹히는데 자기 호출도 아니라면, 대상 클래스/메서드가 `open`인지 확인하세요. 빈의 실제 타입을 로그로 찍어 보면(`bookService.javaClass.name`) `...$$SpringCGLIB$$...`가 보여야 프록시가 적용된 것입니다.

## 3. 프록시 생성 시점

AOP 프록시는 **컴파일 타임이 아니라, 스프링 컨테이너가 빈을 초기화하는 시점**에 만들어집니다.

```
빈 인스턴스 생성 → 의존성 주입 → BeanPostProcessor 동작
                                    │
                                    └─ AnnotationAwareAspectJAutoProxyCreator
                                       : 포인트컷에 매칭되면 원본을 프록시로 교체
                                    │
                                    ▼
                  컨테이너에는 '프록시'가 빈으로 등록됨
```

핵심은 **컨테이너에 등록되는 빈 자체가 프록시로 바꿔치기된다**는 점입니다. 그래서 다른 빈이 `BookService`를 주입받으면 실제로는 프록시를 받습니다. (이 교체를 담당하는 게 `AnnotationAwareAspectJAutoProxyCreator`라는 `BeanPostProcessor`입니다.)

## 4. `@Transactional`이 AOP로 동작하는 원리

이제 부록 개요에서 한 약속을 갚을 차례입니다. `@Transactional`은 사실 **스프링이 미리 등록해 둔 트랜잭션 Aspect**입니다.

- 스프링 부트가 자동 구성으로 **`@EnableTransactionManagement`** 를 켭니다.
- 이때 **`BeanFactoryTransactionAttributeSourceAdvisor`** 라는 어드바이저(포인트컷 + 어드바이스 묶음)가 등록됩니다.
  - **포인트컷**: "`@Transactional`이 붙은 클래스/메서드"
  - **어드바이스**: `TransactionInterceptor` — `@Around`와 동등하게 동작
- `TransactionInterceptor`는 사실상 이런 `@Around`입니다.

```kotlin
// 개념적 의사 코드 — TransactionInterceptor가 하는 일
fun invoke(joinPoint: ProceedingJoinPoint): Any? {
    val tx = transactionManager.getTransaction(...)   // 1) 트랜잭션 시작
    return try {
        val result = joinPoint.proceed()              // 2) 원본 비즈니스 메서드 실행
        transactionManager.commit(tx)                 // 3) 정상 → 커밋
        result
    } catch (e: RuntimeException) {
        transactionManager.rollback(tx)               // 4) 예외 → 롤백
        throw e
    }
}
```

[02 페이지의 실습 ①](02-spring-aop.md) 실행 시간 측정 Aspect와 구조가 똑같습니다. **`@Transactional`은 특별한 언어 기능이 아니라, 스프링이 기본 제공하는 AOP 적용 사례**일 뿐입니다. 그래서 자기 호출(1번)이나 `final`(2번) 함정에 똑같이 걸립니다.

## 5. AOP 적용 순서 — `@Order`

한 메서드에 여러 Aspect가 걸리면 순서가 중요합니다. 로깅이 트랜잭션 바깥에서 도는지 안쪽에서 도는지에 따라 결과가 달라지죠. 순서는 **`@Order`(또는 `Ordered` 인터페이스)** 로 제어합니다. **숫자가 작을수록 바깥쪽(먼저)** 입니다.

```kotlin
@Aspect
@Component
@Order(1)                 // 가장 바깥 — 트랜잭션보다 먼저 진입
class LogExecutionAspect { ... }

@Aspect
@Component
@Order(2)                 // 안쪽
class ExecutionTimeAspect { ... }
```

```
요청 ─► @Order(1) 로깅 진입
        └─► @Order(2) 시간측정 진입
              └─► @Transactional 진입
                    └─► [ 비즈니스 로직 ]
                    ◄─ 커밋
              ◄─ 시간측정 종료
        ◄─ 로깅 종료
```

> [!WARNING]
> `@Order`를 지정하지 않으면 적용 순서가 보장되지 않습니다. 트랜잭션과 다른 Aspect의 선후 관계가 결과에 영향을 준다면 반드시 명시하세요. 참고로 트랜잭션 어드바이저의 기본 순서는 `Ordered.LOWEST_PRECEDENCE`(가장 안쪽)에 가깝습니다.

## 6. ThreadLocal과 요청 스코프 빈

트랜잭션 같은 부가 기능은 "현재 진행 중인 작업의 상태"를 어딘가 저장해야 합니다. 스프링은 이를 **`ThreadLocal`** 에 담습니다.

- **`ThreadLocal`**: 스레드마다 독립된 저장소. 같은 코드라도 스레드 A와 B가 서로 다른 값을 봅니다. 스프링은 현재 트랜잭션·영속성 컨텍스트(`EntityManager`)·보안 컨텍스트를 ThreadLocal에 보관해, 요청을 처리하는 한 스레드 안에서 일관되게 공유합니다.
- **요청 스코프 빈(`@Scope("request")`)**: HTTP 요청 1건당 빈 하나가 생성됐다가 요청이 끝나면 사라집니다. 요청별 로그 추적 ID(traceId) 같은 걸 담기에 좋습니다.

```kotlin
@Component
@Scope(value = "request", proxyMode = ScopedProxyMode.TARGET_CLASS)
class RequestLogContext {
    var traceId: String = UUID.randomUUID().toString()
}
```

> [!WARNING]
> ThreadLocal은 **`@Async`나 별도 스레드로 작업을 넘기면 전파되지 않습니다.** 트랜잭션·보안 컨텍스트가 새 스레드에서 사라지는 사고의 원인이 되니, 비동기 경계에서는 컨텍스트 전파(`TaskDecorator` 등)를 따로 챙겨야 합니다.

## 7. 마무리 — 마법의 정체

`@Transactional` 하나로 트랜잭션이 열리고 닫히는 것, `@Cacheable` 하나로 결과가 캐시되는 것 — 모두 **"스프링이 여러분의 빈을 프록시로 한 겹 감싸, 정해진 포인트컷에서 어드바이스를 실행한다"** 는 단 하나의 원리에서 나옵니다.

이 정체를 알면 디버깅이 쉬워집니다.

- 트랜잭션이 안 먹는다 → **자기 호출**을 의심한다 (1번)
- AOP가 통째로 안 먹는다 → **`open` 여부**와 **빈 등록**을 확인한다 (2·3번)
- Aspect 순서가 이상하다 → **`@Order`** 를 점검한다 (5번)
- 비동기에서 컨텍스트가 사라진다 → **ThreadLocal 전파**를 챙긴다 (6번)

> [!TIP]
> "보이지 않는 마법의 정체를 이해하면, 마법이 풀렸을 때 어디를 봐야 할지 안다." AOP를 두려워하지 말고, 프록시라는 한 겹을 항상 머릿속에 그리세요.

## 다음 단계

AOP와 프록시의 원리를 마쳤습니다. 다음 부록에서는 이 프록시 위에서 동작하는 웹 계층 — 디스패처 서블릿과 요청 처리 파이프라인의 내부를 들여다봅니다. → **[부록 D. Spring MVC 내부 동작](../appendix-d-mvc-internals/README.md)**
