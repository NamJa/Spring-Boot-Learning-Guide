# Spring MVC vs WebFlux

Spring으로 웹 애플리케이션을 만들 때 가장 먼저 마주치는 갈림길이 **두 개의 웹 스택** 중 무엇을 쓸 것인가입니다. 전통적인 **Spring MVC**(서블릿 기반, 동기/블로킹)와 비교적 새로운 **Spring WebFlux**(Reactor 기반, 비동기/논블로킹). 둘은 같은 어노테이션(`@RestController`, `@GetMapping`)을 쓰지만 **내부 실행 모델이 근본적으로 다릅니다.** 이 문서는 둘을 비교하고, 본 가이드의 선택을 분명히 합니다.

## 1. Spring MVC — 서블릿 기반 블로킹 모델

**Spring MVC**는 Java **서블릿(Servlet)** 위에서 동작하는 전통적인 동기 웹 스택입니다.

- 기반: 서블릿 컨테이너 — 본 가이드 기준 **Tomcat 11.0.x (Servlet 6.1)**
- 실행 모델: **요청 1건당 스레드 1개(thread-per-request)**. 스레드가 요청을 받아 처리가 끝날 때까지 점유하며, DB 호출이나 외부 API 응답을 **기다리는 동안 그 스레드는 블로킹**됩니다.
- 프로그래밍 모델: 명령형(imperative). 위에서 아래로 읽히는 평범한 순차 코드.

```kotlin
@RestController
@RequestMapping("/api/v1/books")
class BookController(private val service: BookService) {

    @GetMapping("/{id}")
    fun getBook(@PathVariable id: Long): Book {
        // 평범한 동기 코드. 반환 타입이 그냥 Book
        return service.findById(id) ?: throw BookNotFoundException(id)
    }
}
```

```
[Spring MVC — thread-per-request]

요청 A ──▶ [Thread-1] ──DB 대기(블로킹)──▶ 응답 A
요청 B ──▶ [Thread-2] ──DB 대기(블로킹)──▶ 응답 B
요청 C ──▶ [Thread-3] ── ...

스레드 풀이 가득 차면 이후 요청은 대기
```

## 2. Spring WebFlux — 리액티브 논블로킹 모델

**Spring WebFlux**는 **Reactor**(본 가이드 기준 Reactor 2025.0)를 기반으로 한 리액티브 스택입니다.

- 기반: 보통 **Netty**(논블로킹 서버). 서블릿 컨테이너 위에서도 동작 가능.
- 실행 모델: **이벤트 루프 + 논블로킹 I/O**. 적은 수의 스레드가 많은 요청을 처리. I/O를 기다리는 동안 스레드를 놓아주고 다른 요청을 처리한 뒤, 결과가 준비되면 콜백으로 이어 갑니다.
- 프로그래밍 모델: 반환 타입이 **`Mono<T>`(0~1개)** 또는 **`Flux<T>`(0~N개)** 라는 리액티브 스트림. 데이터가 "흘러가는" 선언적 파이프라인.

```kotlin
@RestController
@RequestMapping("/api/v1/books")
class ReactiveBookController(private val service: ReactiveBookService) {

    @GetMapping("/{id}")
    fun getBook(@PathVariable id: Long): Mono<Book> {
        // 반환 타입이 Mono<Book> — 값이 아니라 "미래에 올 값의 스트림"
        return service.findById(id)
    }
}
```

```
[WebFlux — event loop]

요청 A,B,C... ──▶ [적은 수의 이벤트 루프 스레드]
                        │
              I/O 대기 시 스레드를 놓아줌(논블로킹)
                        │
              결과 준비되면 콜백으로 재개

적은 스레드로 매우 많은 동시 연결 처리 가능
```

### 2.1 WebFlux에서의 Kotlin 코루틴

`Mono`/`Flux`는 처음 보면 낯설지만, **Kotlin을 쓰면 코루틴(suspend 함수)으로 훨씬 자연스럽게** 작성할 수 있습니다. Spring은 `suspend` 함수와 `Flow`를 1급으로 지원해, `Mono`를 `suspend`로, `Flux`를 `Flow<T>`로 대체할 수 있습니다.

```kotlin
@RestController
class CoroutineBookController(private val service: BookService) {

    @GetMapping("/api/v1/books/{id}")
    suspend fun getBook(@PathVariable id: Long): Book? {
        // 코루틴 덕분에 논블로킹이지만 동기 코드처럼 읽힌다
        return service.findById(id)
    }

    @GetMapping("/api/v1/books")
    fun listBooks(): Flow<Book> = service.findAll() // Flux 대신 Flow
}
```

> **TIP**: WebFlux를 쓰더라도 Kotlin 코루틴을 쓰면 콜백 지옥 없이 명령형처럼 읽히는 논블로킹 코드를 얻을 수 있습니다. Ktor가 처음부터 코루틴 기반인 것과 닮은 경험이지만, 위아래(컨트롤러부터 DB 드라이버까지) **모든 계층이 논블로킹이어야** 진가가 나옵니다.

## 3. 두 스택 비교

| 항목 | Spring MVC | Spring WebFlux |
| --- | --- | --- |
| **기반** | 서블릿 (Tomcat 11, Servlet 6.1) | Reactor / Netty |
| **실행 모델** | thread-per-request, 블로킹 | 이벤트 루프, 논블로킹 |
| **반환 타입** | `Book`, `List<Book>` 등 일반 타입 | `Mono<T>`, `Flux<T>`, 또는 `suspend`/`Flow` |
| **프로그래밍 스타일** | 명령형(쉬움) | 리액티브/함수형(러닝 커브 가파름) |
| **블로킹 라이브러리 사용** | 자유로움 (JDBC, JPA 등 그대로) | 금지 — 한 곳만 블로킹해도 전체 성능 붕괴 |
| **데이터 접근** | JPA, JDBC (블로킹) | R2DBC, 리액티브 드라이버 필요 |
| **적합한 상황** | 일반적인 CRUD, 대부분의 비즈니스 앱 | 초고동시성 I/O 바운드, 스트리밍, 게이트웨이 |
| **디버깅/스택트레이스** | 직관적 | 비동기라 어려운 편 |

### 3.1 언제 무엇을 선택하는가

- **Spring MVC를 선택**: 대부분의 경우. CRUD 위주 비즈니스 애플리케이션, JPA/JDBC 같은 블로킹 데이터 접근을 쓰는 경우, 팀이 리액티브에 익숙하지 않은 경우. 코드가 단순하고 디버깅이 쉽습니다.
- **WebFlux를 선택**: 수만 개의 동시 연결을 적은 스레드로 처리해야 하거나(API 게이트웨이, 채팅, SSE/스트리밍), 처리 전 구간이 논블로킹으로 정렬돼 있을 때.

> **WARNING**: "WebFlux가 더 빠르다"는 단순한 오해입니다. 처리 파이프라인 **어느 한 곳이라도 블로킹**(예: WebFlux에서 일반 JPA 호출)하면 이벤트 루프 스레드가 막혀 오히려 MVC보다 나빠집니다. 모든 계층이 논블로킹일 때만 이점이 있습니다.

## 4. 가상 스레드(Virtual Threads) — MVC의 게임 체인저

JDK 21(본 가이드 표준)부터 정식 도입된 **가상 스레드(Project Loom)** 는 MVC의 약점을 크게 보완합니다. 가상 스레드는 OS 스레드보다 훨씬 가벼워 수십만 개를 만들 수 있고, 블로킹 호출 시 OS 스레드를 점유하지 않고 양보합니다.

즉 **익숙한 명령형 MVC 코드를 그대로 쓰면서도**, 가상 스레드 덕분에 높은 동시성을 얻을 수 있습니다. Spring Boot에서 한 줄로 켭니다.

```yaml
# application.yml
spring:
  threads:
    virtual:
      enabled: true   # 요청 처리에 가상 스레드 사용 (JDK 21+)
```

> **TIP**: 가상 스레드 덕분에 "고동시성을 위해 반드시 WebFlux로 가야 한다"는 압박이 크게 줄었습니다. 명령형 코드의 단순함을 유지하면서 동시성을 끌어올릴 수 있어, 많은 신규 프로젝트가 **MVC + 가상 스레드** 조합을 선택합니다.

## 5. 본 가이드의 선택: Spring MVC

본 가이드는 처음부터 끝까지 **Spring MVC**를 사용합니다. 이유는 다음과 같습니다.

1. **러닝 커브** — Spring을 처음 배우는 단계에서 리액티브 스트림(`Mono`/`Flux`)의 복잡성까지 동시에 짊어지는 것은 비효율적입니다.
2. **데이터 접근** — 도서 API는 Spring Data **JPA**(블로킹)를 사용하며, 이는 MVC와 자연스럽게 맞물립니다.
3. **현실성** — 실무 비즈니스 애플리케이션의 절대다수가 MVC 기반입니다.
4. **가상 스레드** — JDK 21의 가상 스레드로 동시성 한계도 상당 부분 해소됩니다.

WebFlux는 "이런 선택지가 있고 코루틴으로 우아하게 쓸 수 있다"는 것을 알아 두는 정도로 충분합니다. 필요해지면 그때 깊이 학습하면 됩니다.

> **Ktor와 비교**: Ktor는 코루틴 기반 논블로킹이 기본이라 WebFlux의 코루틴 경험과 가깝습니다. 반면 본 가이드의 MVC 선택은 "동기 코드의 단순함 + 가상 스레드"라는, 최근 JVM 진영에서 다시 주목받는 실용적 방향입니다.

## 다음 단계

➡️ [Phase 1로 이동](../phase-1-project-setup/01-environment-setup.md) — 이제 개념 무장을 마쳤으니, 실제로 Spring Boot 4.1 프로젝트를 생성하고 도서 관리 API의 첫 코드를 작성합니다.
