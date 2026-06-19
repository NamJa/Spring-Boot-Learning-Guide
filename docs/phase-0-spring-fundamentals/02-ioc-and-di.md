# IoC 컨테이너와 의존성 주입

Spring을 한 문장으로 설명하라면 "거대한 IoC 컨테이너"라고 답해야 합니다. 트랜잭션, 보안, 캐시, 웹 라우팅까지 Spring의 모든 기능은 결국 **컨테이너가 Bean을 만들고 연결하는 방식** 위에 올라가 있기 때문입니다. 이 문서를 제대로 이해하면 이후 모든 Phase가 쉬워집니다.

## 1. 제어의 역전(IoC)이란

**IoC(Inversion of Control, 제어의 역전)** 란, 객체의 생성·조립·생명주기에 대한 **제어권을 개발자에서 프레임워크(컨테이너)로 넘기는 것**입니다. 말로는 추상적이니 코드로 봅시다.

### 1.1 IoC 적용 전 — 직접 제어

```kotlin
// 객체를 내가 직접 만들고(new), 의존성도 내가 직접 연결한다.
class BookService {
    private val repository = JdbcBookRepository(DataSource(...)) // 강한 결합!

    fun findById(id: Long): Book? = repository.findById(id)
}

fun main() {
    val service = BookService() // 내가 직접 생성·제어
    println(service.findById(1L))
}
```

문제점이 보입니다.

- `BookService`가 **구체 구현(`JdbcBookRepository`)에 직접 의존**합니다. 메모리 구현이나 JPA 구현으로 바꾸려면 `BookService` 코드를 고쳐야 합니다.
- `DataSource` 같은 의존성을 누가 만들고 주입할지 일일이 손으로 챙겨야 합니다.
- 테스트할 때 가짜(Mock) Repository로 교체하기가 어렵습니다.

### 1.2 IoC 적용 후 — 컨테이너가 제어

```kotlin
interface BookRepository {
    fun findById(id: Long): Book?
}

@Repository
class JdbcBookRepository(/* DataSource는 컨테이너가 주입 */) : BookRepository {
    override fun findById(id: Long): Book? = TODO()
}

@Service
class BookService(
    private val repository: BookRepository, // 인터페이스에만 의존, 구현은 컨테이너가 결정
) {
    fun findById(id: Long): Book? = repository.findById(id)
}
```

이제 **누가 `BookService`를 만들고, 그 안에 어떤 `BookRepository` 구현을 넣을지를 Spring 컨테이너가 결정**합니다. 개발자는 "무엇이 필요한지"만 선언하고, "어떻게 조립할지"는 컨테이너에 맡깁니다. 이것이 제어의 역전입니다.

```
[전통적 흐름]   내 코드 ──생성·호출──▶ 라이브러리
[IoC 흐름]      컨테이너 ──생성·주입──▶ 내 코드(Bean)
```

> **Ktor와 비교**: Ktor에는 내장 IoC 컨테이너가 없어, 의존성을 직접 만들거나 Koin 같은 외부 DI 라이브러리를 씁니다. Spring은 IoC 컨테이너 자체가 프레임워크의 본체입니다.

## 2. ApplicationContext와 BeanFactory

Spring의 IoC 컨테이너는 **Bean들을 담고 관리하는 객체**입니다. 두 가지 핵심 인터페이스가 있습니다.

| 인터페이스 | 설명 |
| --- | --- |
| **BeanFactory** | 가장 기본적인 컨테이너. Bean의 생성과 DI 등 최소 기능만 제공 (지연 로딩) |
| **ApplicationContext** | `BeanFactory`를 상속한 상위 인터페이스. 메시지 국제화, 이벤트 발행, AOP, 환경(프로퍼티) 등 **엔터프라이즈 기능을 모두 포함**. 실무에서 사용하는 것은 사실상 이것 |

Spring Boot 애플리케이션을 실행하면 `runApplication`이 내부적으로 `ApplicationContext`를 생성하고, **컴포넌트 스캔**으로 발견한 모든 Bean을 등록합니다.

```kotlin
@SpringBootApplication
class BookApiApplication

fun main(args: Array<String>) {
    val context = runApplication<BookApiApplication>(*args)
    // 이 시점에 ApplicationContext가 완성되어 있고, 모든 Bean이 준비됨
    val service = context.getBean(BookService::class.java)
}
```

> **TIP**: 실무에서 `getBean()`을 직접 호출할 일은 거의 없습니다. 필요한 Bean은 생성자 주입으로 받는 것이 정석입니다. 컨테이너를 직접 만지는 코드는 "DI를 거스르는" 신호일 때가 많습니다.

## 3. 의존성 주입(DI)의 세 가지 방식

DI는 IoC를 구현하는 구체적 방법입니다. Spring에는 세 가지 주입 방식이 있습니다.

### 3.1 생성자 주입 (Constructor Injection) — Kotlin에서 권장

```kotlin
@Service
class BookService(
    private val repository: BookRepository, // 주생성자 파라미터 = 주입 지점
) {
    // ...
}
```

Kotlin의 주생성자가 그대로 주입 지점이 됩니다. 가장 권장되는 방식이며 이유는 다음과 같습니다.

- **불변성**: `val`로 선언 가능 → 주입 후 바뀌지 않음, 스레드 안전.
- **필수 의존성 보장**: 의존성 없이는 객체를 만들 수 없으므로 누락이 컴파일/기동 시점에 드러남.
- **널 안전성**: Kotlin의 non-null 타입과 자연스럽게 결합. `lateinit` 불필요.
- **테스트 용이**: 테스트에서 생성자에 Mock을 그냥 넣으면 됨. Spring 없이도 단위 테스트 가능.

### 3.2 필드 주입 (Field Injection) — 비권장

```kotlin
@Service
class BookService {
    @Autowired
    private lateinit var repository: BookRepository // 권장하지 않음
}
```

코드가 짧아 보이지만 단점이 큽니다.

- `lateinit var`라 **불변이 아니고**, 주입 전 접근 시 예외 위험.
- Spring 컨테이너 없이는 주입할 방법이 없어 **단위 테스트가 어려움**.
- 의존성이 숨겨져 한 클래스가 의존성을 몇 개나 갖는지 드러나지 않음(과도한 의존 발견 곤란).

### 3.3 세터 주입 (Setter Injection)

```kotlin
@Service
class BookService {
    private var repository: BookRepository? = null

    @Autowired
    fun setRepository(repository: BookRepository) {
        this.repository = repository
    }
}
```

선택적(optional) 의존성이나 런타임 재설정이 필요한 드문 경우에만 사용합니다. 일반적으로는 생성자 주입을 쓰세요.

| 방식 | 불변성 | 테스트 용이성 | 권장도 |
| --- | --- | --- | --- |
| **생성자 주입** | `val` 가능 | 매우 높음 | ★ 권장 |
| 세터 주입 | 불가 | 보통 | 선택적 의존성만 |
| 필드 주입 | 불가 | 낮음 | 지양 |

> **결론**: Kotlin + Spring에서는 **생성자 주입을 기본으로** 삼으세요. 주생성자에 적으면 끝입니다.

## 4. Bean을 등록하는 두 가지 방법

컨테이너가 관리하려면 객체가 Bean으로 등록되어야 합니다. 방법은 크게 둘입니다.

### 4.1 스테레오타입 어노테이션 (컴포넌트 스캔)

클래스에 어노테이션을 붙이면 컴포넌트 스캔이 자동으로 Bean으로 등록합니다. 의미에 따라 종류가 나뉘지만 **기능은 사실상 동일**하며(모두 `@Component`의 특수화), 역할을 드러내는 문서적 의미가 큽니다.

| 어노테이션 | 의미하는 계층 |
| --- | --- |
| `@Component` | 범용 컴포넌트 (가장 일반적) |
| `@Service` | 비즈니스 로직 계층 |
| `@Repository` | 데이터 접근 계층 (+ DB 예외를 Spring 표준 예외로 변환하는 부가 기능) |
| `@Controller` / `@RestController` | 웹 요청 처리 계층 |

```kotlin
@Repository
class JdbcBookRepository : BookRepository { /* ... */ }

@Service
class BookService(private val repository: BookRepository) { /* ... */ }

@RestController
class BookController(private val service: BookService) { /* ... */ }
```

### 4.2 `@Configuration` + `@Bean` (자바/코틀린 설정)

내가 직접 만들 수 없는 **외부 라이브러리 객체**(예: `ObjectMapper`, `RestClient`)를 Bean으로 등록할 때 사용합니다.

```kotlin
@Configuration
class AppConfig {

    @Bean
    fun restClient(): RestClient =
        RestClient.builder()
            .baseUrl("https://api.example.com")
            .build()

    @Bean
    fun bookService(repository: BookRepository): BookService =
        // @Bean 메서드의 파라미터도 컨테이너가 자동 주입한다
        BookService(repository)
}
```

> **TIP**: 직접 작성한 컴포넌트는 `@Service` 등 스캔 방식으로, 외부 객체는 `@Bean` 방식으로 — 이 구분이 일반적인 관례입니다.

## 5. @Autowired, @Qualifier, @Primary, @Value

### 5.1 @Autowired — 단일 생성자면 생략 가능

`@Autowired`는 "이 지점에 의존성을 주입하라"는 표시입니다. 그러나 **생성자가 하나뿐인 클래스에서는 생략할 수 있습니다.** Spring이 유일한 생성자를 자동으로 주입 대상으로 인식하기 때문입니다. Kotlin의 주생성자는 거의 항상 단일 생성자이므로, 실무 코드에서 `@Autowired`를 거의 보지 못하게 됩니다.

```kotlin
@Service
class BookService(private val repository: BookRepository) // @Autowired 없이 동작
```

### 5.2 @Qualifier / @Primary — 같은 타입 Bean이 여러 개일 때

`BookRepository` 구현이 둘 이상이면 Spring은 "어느 것을 주입할지" 결정하지 못해 기동에 실패합니다. 이때 충돌을 해소하는 두 방법이 있습니다.

```kotlin
@Repository
@Primary // 동일 타입 중 기본으로 선택될 Bean
class JpaBookRepository : BookRepository

@Repository("memoryBookRepository")
class InMemoryBookRepository : BookRepository

@Service
class BookService(
    @Qualifier("memoryBookRepository") // 특정 Bean을 이름으로 지정
    private val repository: BookRepository,
)
```

- `@Primary`: 여러 후보 중 **기본값**을 지정.
- `@Qualifier("이름")`: 주입 지점에서 **콕 집어** 특정 Bean을 선택. `@Qualifier`가 `@Primary`보다 우선합니다.

### 5.3 @Value — 프로퍼티 값 주입

`application.yml`이나 환경 변수의 값을 Bean에 주입합니다.

```yaml
# application.yml
book:
  default-page-size: 20
```

```kotlin
@Service
class BookService(
    private val repository: BookRepository,
    @Value("\${book.default-page-size}") private val pageSize: Int,
)
```

> **TIP**: 여러 프로퍼티를 묶어 받을 때는 `@Value`보다 타입 안전한 `@ConfigurationProperties`를 쓰는 것이 좋습니다. (Phase 1의 설정 편에서 다룹니다.)

## 6. Spring Framework 7의 Kotlin Bean Registration DSL

Spring Framework 7은 어노테이션 대신 **Kotlin DSL로 Bean을 프로그래밍 방식 등록**하는 길도 제공합니다. 어노테이션 스캔의 리플렉션을 줄여 기동을 빠르게 하거나(특히 GraalVM 네이티브 이미지), 조건에 따라 동적으로 Bean을 구성할 때 유용합니다.

```kotlin
val beans = beans {
    bean<JpaBookRepository>()
    bean {
        BookService(ref()) // ref()로 컨테이너에서 의존성 조회
    }
}
```

지금 단계에서는 "어노테이션 외에 DSL 방식도 있다" 정도만 기억하면 충분합니다. 본 가이드의 본문 예제는 가독성을 위해 어노테이션 방식을 기본으로 사용합니다.

## 다음 단계

➡️ [03. Bean 생명주기와 스코프](03-bean-lifecycle-scope.md) — 컨테이너에 등록된 Bean이 언제 생성되고 초기화되며 소멸하는지, 그리고 singleton/prototype 등 스코프를 살펴봅니다.
