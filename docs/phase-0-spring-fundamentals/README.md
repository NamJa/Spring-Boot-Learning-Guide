# Phase 0. Spring 핵심 개념 다지기

Spring Boot로 본격적인 코드를 작성하기 전에, **Spring 생태계가 어떤 철학 위에서 동작하는지** 먼저 이해하는 단계입니다. Spring은 단순한 웹 프레임워크가 아니라 **IoC 컨테이너**라는 강력한 핵심 위에 수많은 모듈이 쌓인 거대한 생태계입니다. 이 핵심을 모른 채 코드를 따라 치기만 하면, 조금만 상황이 달라져도 "왜 이게 동작하는지" 설명할 수 없게 됩니다.

이미 Kotlin과 (자매 가이드의) Ktor에 익숙하다면 더욱 좋습니다. Ktor가 "필요한 것을 직접 명시적으로 조립하는" 미니멀리즘을 추구한다면, Spring은 "관례와 자동화로 빠르게 생산성을 끌어올리는" 정반대 철학을 가집니다. 이 차이를 이해하는 것이 Phase 0의 가장 큰 목표입니다.

## 이 Phase에서 배우는 것

- **Spring과 Spring Boot의 관계** — 무엇이 다르고, Spring Boot가 무엇을 자동화해 주는가
- **IoC 컨테이너와 의존성 주입(DI)** — Spring을 떠받치는 가장 중요한 개념
- **Bean 생명주기와 스코프** — 객체가 언제 만들어지고 언제 사라지는가
- **자동 설정(Auto-configuration)과 스타터** — Spring Boot의 "마법"이 동작하는 원리
- **Spring MVC vs WebFlux** — 두 가지 웹 스택 중 무엇을 선택할 것인가

## 왜 코딩 전에 개념부터 잡아야 하는가

Spring Boot는 **수많은 것을 자동으로 해 줍니다**. 이 자동화는 양날의 검입니다.

- 잘 이해하면: 보일러플레이트 없이 빠르게 실무 수준의 애플리케이션을 만들 수 있습니다.
- 모르면: 에러 메시지 하나를 해석하지 못하고, 자동 설정이 "왜 내가 원하는 Bean을 안 만들어 주는지" 디버깅에 며칠을 쓰게 됩니다.

> **TIP**: Spring의 거의 모든 기능(트랜잭션, 보안, 캐시, AOP)은 결국 **IoC 컨테이너가 Bean을 어떻게 관리하느냐**로 귀결됩니다. 02번 문서의 DI 개념만 확실히 잡아도 이후 Phase가 훨씬 수월해집니다.

## 가이드 전체를 관통하는 예제

이 가이드는 처음부터 끝까지 **도서(Book) 관리 REST API**를 만들며 진행합니다.

- 기본 패키지: `com.example.bookapi`
- 도메인 모델:

```kotlin
data class Book(
    val id: Long,
    val title: String,
    val author: String,
    val isbn: String,
    val price: Int,
    val publishedAt: java.time.LocalDate,
)
```

Phase 0에서는 아직 이 도메인을 본격적으로 다루지 않지만, 개념 설명마다 이 예제를 끌어와 "실제로 어디에 쓰이는지" 감을 잡아 둡니다.

## 사용하는 버전 (2026-06-20 기준)

| 구성요소 | 버전 |
| --- | --- |
| Spring Boot | **4.1.0** (GA 2026-06-10) |
| Spring Framework | **7.0.8+** |
| Kotlin | **2.2.21** (Spring Boot BOM이 관리) |
| JDK | 17 최소 ~ 26 지원 (본 가이드는 **21 LTS** 기준) |
| Gradle | 8.14+ / 9.x |
| Spring Security | 7.0 |

## 페이지 목록

1. [Spring & Spring Boot 입문](01-what-is-spring.md) — Spring Framework와 Spring Boot가 각각 무엇이고 어떻게 다른지, 생태계 전체 지도를 그립니다.
2. [IoC 컨테이너와 의존성 주입](02-ioc-and-di.md) — Spring의 심장인 제어의 역전과 DI를 Kotlin 코드로 익힙니다.
3. [Bean 생명주기와 스코프](03-bean-lifecycle-scope.md) — Bean이 생성-초기화-소멸되는 과정과 스코프를 다룹니다.
4. [자동 설정과 스타터](04-auto-configuration.md) — `@SpringBootApplication`의 분해, 조건부 Bean, 스타터의 원리를 파헤칩니다.
5. [Spring MVC vs WebFlux](05-mvc-vs-webflux.md) — 두 웹 스택을 비교하고, 본 가이드가 MVC를 선택한 이유를 설명합니다.

## 다음 단계

➡️ [01. Spring & Spring Boot 입문](01-what-is-spring.md) — 먼저 "Spring이 도대체 무엇인가"라는 질문에 답하며 출발합니다.
