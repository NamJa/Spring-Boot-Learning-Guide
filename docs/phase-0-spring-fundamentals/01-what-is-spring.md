# Spring & Spring Boot 입문

Spring을 처음 접하면 가장 헷갈리는 것이 **"Spring", "Spring Framework", "Spring Boot"가 같은 말인가 다른 말인가**입니다. 결론부터 말하면 셋은 다릅니다. 이 문서에서는 Spring Framework의 본질, Spring Boot가 그 위에 무엇을 더했는지, 그리고 거대한 Spring 생태계의 전체 지도를 그려 보겠습니다.

## 1. Spring Framework란 무엇인가

**Spring Framework**는 2003년 Rod Johnson이 당시 무겁고 복잡했던 Java EE(EJB)에 대한 대안으로 만든 **경량 애플리케이션 프레임워크**입니다. 20년이 넘게 진화하며 Java/Kotlin 진영의 사실상 표준이 되었습니다.

Spring Framework의 핵심은 단 두 가지로 요약할 수 있습니다.

### 1.1 IoC 컨테이너 (Inversion of Control)

Spring의 심장입니다. 객체(Spring에서는 **Bean**이라 부릅니다)의 생성과 생명주기, 그리고 객체 간의 의존 관계 연결을 **개발자가 아니라 컨테이너가 대신 관리**합니다. 이것을 **제어의 역전(IoC)** 이라 부르며, 그 구체적 구현 기법이 **의존성 주입(DI, Dependency Injection)** 입니다. (자세한 내용은 [02번 문서](02-ioc-and-di.md)에서 다룹니다.)

```kotlin
// 개발자가 직접 만들지 않는다. 컨테이너가 BookRepository를 주입해 준다.
@Service
class BookService(private val repository: BookRepository) {
    fun findById(id: Long): Book? = repository.findById(id)
}
```

### 1.2 AOP (Aspect-Oriented Programming, 관점 지향 프로그래밍)

트랜잭션, 로깅, 보안처럼 **여러 곳에 흩어져 반복되는 부가 기능**(횡단 관심사, cross-cutting concern)을 핵심 비즈니스 로직과 분리하는 기법입니다. 예를 들어 `@Transactional` 한 줄이면, 메서드 시작 시 트랜잭션을 열고 끝나면 커밋/롤백하는 코드를 Spring이 **프록시**를 통해 자동으로 감싸 줍니다.

```kotlin
@Service
class BookService(private val repository: BookRepository) {
    @Transactional // 메서드 전후로 트랜잭션 begin/commit이 AOP로 끼워진다
    fun register(book: Book): Book = repository.save(book)
}
```

> **TIP**: AOP가 "프록시"로 동작한다는 사실은 매우 중요합니다. 같은 클래스 내부 메서드끼리 호출하면 프록시를 거치지 않아 `@Transactional`이 동작하지 않는 함정이 있습니다. 이건 Phase 후반의 데이터 액세스 편에서 다시 다룹니다.

이 두 핵심 위에 Spring은 웹(MVC), 데이터 접근, 트랜잭션, 메시징 등 **모듈**을 쌓아 올린 거대한 생태계를 형성합니다.

## 2. Spring Boot가 더한 것

Spring Framework는 강력하지만, 옛날에는 설정이 **악명 높게 번거로웠습니다**. XML 수백 줄, DispatcherServlet 등록, 뷰 리졸버 설정, 데이터소스 빈 구성... 애플리케이션 코드를 한 줄도 쓰기 전에 설정 지옥을 겪어야 했습니다.

**Spring Boot**(2014년 등장)는 이 문제를 해결하기 위한 **Spring Framework 위의 레이어**입니다. 본 가이드에서 사용하는 **Spring Boot 4.1.0**(2026-06-10 GA)은 **Spring Framework 7** 위에서 동작합니다. Spring Boot가 더하는 핵심 가치는 다음과 같습니다.

| 기능 | 설명 |
| --- | --- |
| **자동 설정 (Auto-configuration)** | 클래스패스에 무엇이 있는지 보고 합리적인 기본 Bean들을 자동 등록. JPA가 있으면 DataSource·EntityManager를 알아서 구성 |
| **스타터 (Starters)** | `spring-boot-starter-web` 한 줄로 웹 개발에 필요한 의존성 묶음을 한꺼번에 가져옴 |
| **내장 서버 (Embedded server)** | Tomcat/Jetty/Netty를 jar 안에 내장. 별도 WAS 설치·배포 없이 `java -jar`로 실행 |
| **No XML** | 모든 설정을 어노테이션과 `application.yml`로. XML 설정 파일 불필요 |
| **Production-ready** | Actuator로 헬스 체크, 메트릭, 모니터링 엔드포인트를 즉시 제공 |
| **의견이 반영된(opinionated) 기본값** | 검증된 버전 조합, 합리적 기본 설정을 BOM(Bill of Materials)으로 제공 |

핵심 한 문장: **Spring Boot는 새로운 프레임워크가 아니라, Spring Framework를 "관례에 따라 자동으로 설정해 주는" 도구**입니다.

```
┌─────────────────────────────────────────┐
│        내 애플리케이션 (BookApi)          │
├─────────────────────────────────────────┤
│   Spring Boot 4.1                        │
│   (자동 설정 · 스타터 · 내장 서버)         │
├─────────────────────────────────────────┤
│   Spring Framework 7                     │
│   (IoC 컨테이너 · AOP · MVC · TX ...)     │
├─────────────────────────────────────────┤
│   JVM (JDK 21)                           │
└─────────────────────────────────────────┘
```

### 2.1 Spring Boot 4.1의 주요 신규 기능

본 가이드 시점의 Spring Boot 4.1 / Spring Framework 7에서 주목할 변화들입니다. 지금은 "이런 게 있구나" 정도만 알아 두고, 해당 Phase에서 자세히 다룹니다.

- **JSpecify 기반 널 안전성 어노테이션** — Kotlin의 nullable 타입과 더 잘 맞물리도록 표준화된 `@Nullable`/`@NonNull` 메타데이터를 도입.
- **선언적 HTTP 클라이언트** — 인터페이스에 `@HttpExchange`만 붙이고 `RestClient` 위에 `@ImportHttpServices`로 등록하면 구현 없이 HTTP 호출 가능 (Feign과 유사).
- **새 스타터** — `spring-boot-starter-restclient`, `spring-boot-starter-webclient`로 HTTP 클라이언트 의존성을 명확히 분리.
- **회복탄력성(resilience)** — `@Retryable`(재시도), `@ConcurrencyLimit`(동시성 제한)을 코어에 내장.
- **API 버저닝** — `/api/v1` 같은 버전 라우팅을 프레임워크 차원에서 지원.

## 3. Spring 생태계 지도

"Spring을 배운다"는 것은 Framework 하나가 아니라 그 위의 여러 프로젝트를 함께 익히는 것입니다. 자주 마주칠 주요 프로젝트들입니다.

| 프로젝트 | 역할 |
| --- | --- |
| **Spring Framework** | IoC/AOP/MVC 등 핵심. 모든 것의 기반 |
| **Spring Boot** | 자동 설정·스타터로 빠른 부트스트랩 |
| **Spring Data** | JPA/JDBC/MongoDB/Redis 등 데이터 접근 추상화. Repository 인터페이스만 선언하면 구현 생성 |
| **Spring Security** | 인증·인가, OAuth2, JWT 등 보안 (본 가이드 기준 7.0) |
| **Spring Web (MVC)** | 서블릿 기반 동기 웹 스택 |
| **Spring WebFlux** | Reactor 기반 리액티브(비동기) 웹 스택 |
| **Spring Cloud** | 마이크로서비스(설정 서버, 서비스 디스커버리, 게이트웨이) |
| **Spring Batch** | 대용량 배치 처리 |
| **Spring Integration / Kafka / AMQP** | 메시징·이벤트 기반 통합 |

> **TIP**: 도서 관리 API를 만드는 동안 우리는 **Spring Framework(코어) + Spring Boot + Spring Web(MVC) + Spring Data JPA + Spring Security** 정도를 사용하게 됩니다. 나머지는 존재만 알아 두면 충분합니다.

## 4. Spring Boot vs 순수 Spring vs Ktor

자매 가이드의 Ktor 경험이 있다면, 세 가지 접근법의 철학 차이를 비교하는 것이 빠른 이해에 도움이 됩니다.

| 항목 | 순수 Spring Framework | Spring Boot | Ktor |
| --- | --- | --- | --- |
| **설정 철학** | 모든 것을 명시적으로 직접 설정 | 관례 기반 자동 설정 | 명시적·미니멀, 필요한 것만 플러그인 |
| **초기 설정 비용** | 높음 (XML/Java Config 대량) | 매우 낮음 (스타터 추가만) | 낮음 |
| **서버** | 외부 WAS 배포 또는 직접 임베딩 | 내장 서버 기본 제공 | 내장 엔진(Netty/CIO) |
| **DI** | Spring IoC 컨테이너 (강력) | 동일 (Spring IoC) | 별도 DI 없음 (Koin 등 외부 사용) |
| **러닝 커브** | 가파름 | 완만 (자동화 덕분) | 완만 |
| **"마법" 정도** | 적음 (직접 다 씀) | 많음 (자동 설정) | 거의 없음 (명시적) |
| **생태계 규모** | 거대 | 거대 | 작지만 Kotlin 친화적 |

Ktor는 "내가 무엇을 켰는지 코드에 다 보인다"는 투명성이 장점입니다. Spring Boot는 "관례를 따르면 거의 안 짜도 된다"는 생산성이 장점입니다. 본 가이드는 후자의 생산성을 누리되, **그 자동화가 내부에서 무엇을 하는지** 끝까지 설명하는 것을 목표로 합니다.

## 5. 왜 Spring + Kotlin인가

Spring은 Java 진영에서 출발했지만, **Kotlin을 1급 언어로 공식 지원**합니다. Spring Boot 4.1은 Kotlin **2.2.21**을 BOM으로 관리합니다. Kotlin과 Spring의 궁합이 좋은 이유는 다음과 같습니다.

- **널 안전성** — Kotlin의 `?` 타입과 Spring 7의 JSpecify 어노테이션이 맞물려, 컴파일 시점에 NPE 위험을 크게 줄입니다.
- **간결한 데이터 클래스** — DTO/엔티티를 `data class` 한 줄로. Lombok이 필요 없습니다.
- **생성자 주입과의 궁합** — Kotlin의 주생성자(primary constructor)가 곧 DI 지점이 되어, `@Autowired` 없이도 깔끔합니다.

```kotlin
@RestController
@RequestMapping("/api/v1/books")
class BookController(
    private val bookService: BookService, // 주생성자 = 생성자 주입, 어노테이션 불필요
) {
    @GetMapping("/{id}")
    fun getBook(@PathVariable id: Long): Book? = bookService.findById(id)
}
```

- **확장 함수 / DSL** — Spring은 Kotlin 전용 확장(예: `beans { }` DSL, `runApplication`, MockMvc Kotlin DSL)을 제공해 Java보다 더 자연스러운 코드를 쓸 수 있습니다.

> **WARNING**: Kotlin 클래스는 기본이 `final`입니다. Spring AOP(프록시)는 클래스를 상속해 동작하므로, `@Configuration`이나 `@Transactional`이 붙는 클래스에는 `kotlin-spring` 컴파일러 플러그인이 자동으로 `open`을 붙여 줍니다. Spring Boot 프로젝트를 생성하면 이 플러그인이 기본 포함되니 걱정하지 않아도 됩니다. (Phase 1에서 다룹니다.)

## 다음 단계

➡️ [02. IoC 컨테이너와 의존성 주입](02-ioc-and-di.md) — Spring의 심장인 제어의 역전과 DI가 실제 Kotlin 코드에서 어떻게 동작하는지 깊이 들어갑니다.
