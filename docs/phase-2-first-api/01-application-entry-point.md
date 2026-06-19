# 진입점 — @SpringBootApplication

모든 Spring Boot 애플리케이션에는 단 하나의 **진입점(entry point)** 클래스가 있습니다. Phase 1에서 프로젝트를 생성하면 `src/main/kotlin/com/example/bookapi/` 아래에 `BookApiApplication.kt` 파일이 자동으로 만들어집니다. 이 파일이 애플리케이션 전체의 출발점입니다.

## 1. 생성된 진입점 클래스

```kotlin
package com.example.bookapi

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class BookApiApplication

fun main(args: Array<String>) {
    runApplication<BookApiApplication>(*args)
}
```

코드는 단 몇 줄이지만, 이 안에 Spring Boot의 거의 모든 마법이 압축되어 있습니다. 하나씩 풀어 보겠습니다.

## 2. @SpringBootApplication 애너테이션

`@SpringBootApplication`은 사실 세 개의 애너테이션을 합쳐 놓은 **메타 애너테이션(composed annotation)**입니다.

| 포함된 애너테이션 | 역할 |
|---|---|
| `@SpringBootConfiguration` | 이 클래스가 Spring 설정(configuration) 클래스임을 표시 (`@Configuration`의 특수형) |
| `@EnableAutoConfiguration` | **자동 설정(auto-configuration)** 활성화. 클래스패스에 있는 라이브러리를 보고 필요한 빈을 자동 등록 |
| `@ComponentScan` | 현재 패키지(`com.example.bookapi`)와 그 하위 패키지를 스캔하여 `@Component`, `@Service`, `@RestController` 등을 빈으로 등록 |

여기서 가장 중요한 규칙: **진입점 클래스는 프로젝트의 최상위 패키지에 두어야 합니다.** `@ComponentScan`은 이 클래스가 위치한 패키지를 기준(base package)으로 하위를 탐색하기 때문입니다. `com.example.bookapi`에 두면 `com.example.bookapi.controller`, `com.example.bookapi.service` 등이 모두 스캔 대상이 됩니다.

> **자주 하는 실수**: 컨트롤러를 진입점 패키지 바깥(예: `com.example.web`)에 두면 스캔되지 않아 404가 발생합니다. 새 클래스는 항상 `com.example.bookapi` 하위에 만드세요.

### 자동 설정이란?

`@EnableAutoConfiguration`은 "클래스패스에 무엇이 있는가"를 보고 적절한 기본 설정을 알아서 적용합니다. 예를 들어,

- `spring-boot-starter-web`이 있으면 → 내장 **Tomcat** 서버, `DispatcherServlet`, Jackson JSON 변환기 등을 자동 구성
- `jackson-module-kotlin`이 있으면 → Kotlin data class를 위한 JSON 직렬화기를 자동 등록

이 덕분에 우리는 XML 설정 한 줄 없이 곧바로 웹 서버를 띄울 수 있습니다.

## 3. runApplication — Kotlin다운 시작 방식

`runApplication`은 Spring Boot가 Kotlin 사용자를 위해 제공하는 **확장 함수**입니다. Java에서는 보통 이렇게 씁니다.

```java
// Java 스타일
public static void main(String[] args) {
    SpringApplication.run(BookApiApplication.class, args);
}
```

Kotlin에서는 `runApplication`을 쓰면 클래스 참조(`::class.java`)를 명시할 필요 없이 **타입 파라미터**로 깔끔하게 표현됩니다.

```kotlin
runApplication<BookApiApplication>(*args)
```

`*args`는 **스프레드 연산자(spread operator)**로, `Array<String>`을 가변 인자(vararg)로 풀어서 전달합니다. 이 인자는 커맨드라인 옵션(`--server.port=9090` 등)으로 활용됩니다.

## 4. 시작 시 무슨 일이 일어나는가

`main`이 실행되면 다음 순서로 진행됩니다.

```
runApplication<BookApiApplication>(*args)
        │
        ▼
1. SpringApplication 객체 생성, 환경(Environment) 준비
        │
        ▼
2. ApplicationContext(IoC 컨테이너) 생성
        │
        ▼
3. @ComponentScan → 빈 정의 수집 (@Service, @RestController ...)
        │
        ▼
4. @EnableAutoConfiguration → 내장 Tomcat, Jackson 등 자동 구성
        │
        ▼
5. 모든 싱글톤 빈 생성 및 의존성 주입(DI)
        │
        ▼
6. 내장 Tomcat 시작 → 8080 포트에서 요청 대기
```

5단계가 끝나면 우리가 만든 `BookService`, `BookController` 같은 객체들이 컨테이너 안에 준비되고, 서로 의존성이 연결됩니다. 6단계에서 서버가 떠 실제로 HTTP 요청을 받을 수 있게 됩니다.

## 5. 시작 로그 읽기

`./gradlew bootRun`으로 실행하면 콘솔에 다음과 비슷한 로그가 출력됩니다.

```
  .   ____          _            __ _ _
 /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
 \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
  '  |____| .__|_| |_|_| |_\__, | / / / /
 =========|_|==============|___/=/_/_/_/

 :: Spring Boot ::                (v4.1.0)

... INFO ... Starting BookApiApplication using Java 21 ...
... INFO ... Tomcat initialized with port 8080 (http)
... INFO ... Starting service [Tomcat]
... INFO ... Starting Servlet engine: [Apache Tomcat/11.0.x]
... INFO ... Initializing Spring embedded WebApplicationContext
... INFO ... Tomcat started on port 8080 (http) with context path '/'
... INFO ... Started BookApiApplication in 1.234 seconds (process running for 1.567)
```

로그에서 확인할 핵심 정보입니다.

- **Spring Boot 버전**: `v4.1.0`
- **JDK 버전**: `Java 21`
- **내장 서버**: `Apache Tomcat/11.0.x` (Servlet 6.1)
- **포트**: `8080`
- **마지막 줄** `Started BookApiApplication in ...`: 정상 기동 완료 신호. 이 줄이 보이면 API를 호출할 준비가 된 것입니다.

## 6. SpringApplication 커스터마이징 (간단히)

대부분 기본값으로 충분하지만, 시작 동작을 바꾸고 싶다면 람다로 설정을 조정할 수 있습니다.

```kotlin
fun main(args: Array<String>) {
    runApplication<BookApiApplication>(*args) {
        // 시작 배너 끄기
        setBannerMode(Banner.Mode.OFF)
        // 추가 프로파일 지정 등도 가능
    }
}
```

포트나 애플리케이션 이름 같은 설정은 코드보다 `src/main/resources/application.yml`에 두는 것이 더 일반적입니다.

```yaml
server:
  port: 8080
spring:
  application:
    name: book-api
```

## 7. Ktor의 embeddedServer와 비교

Ktor 경험이 있다면 이 구조가 낯설 수 있습니다. Ktor에서는 서버 엔진과 라우팅을 코드에서 명시적으로 조립합니다.

```kotlin
// Ktor
fun main() {
    embeddedServer(Netty, port = 8080) {
        routing {
            get("/api/books") { call.respondText("...") }
        }
    }.start(wait = true)
}
```

| 항목 | Ktor | Spring Boot |
|---|---|---|
| 서버 시작 | `embeddedServer(Netty, ...)` 명시적 조립 | `runApplication` 한 줄, 나머지는 자동 |
| 엔진 선택 | 코드에서 직접 지정 (Netty 등) | starter 의존성으로 결정 (기본 Tomcat) |
| 라우팅 | `routing { }` DSL로 코드에 작성 | `@RestController` 애너테이션으로 선언 |
| 설정 방식 | 코드 중심(명시적) | 애너테이션 + 자동 설정(관례 중심) |

핵심 차이는 **명시(explicit) vs 관례(convention)**입니다. Ktor는 모든 것을 코드로 보여 주는 대신 직접 조립해야 하고, Spring Boot는 관례와 자동 설정으로 보일러플레이트를 줄이는 대신 "어떤 마법이 일어나는지"를 이해하는 학습이 필요합니다. 이 가이드는 바로 그 마법을 한 겹씩 벗겨 나가는 과정입니다.

## 다음 단계

진입점을 이해했으니, 이제 API가 주고받을 데이터의 형태를 정의할 차례입니다. [DTO와 JSON 직렬화](02-dto-and-serialization.md)로 이동하세요.
