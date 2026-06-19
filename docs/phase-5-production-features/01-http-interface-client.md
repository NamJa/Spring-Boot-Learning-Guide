# 선언적 HTTP 클라이언트

우리의 Book API는 지금까지 자기 데이터베이스 안에서만 살았습니다. 하지만 실무 서비스는 거의 항상 **다른 서비스를 호출**합니다. 예를 들어 도서를 등록할 때 ISBN을 외부 도서 메타데이터 API에 던져 제목·저자·표지 이미지를 가져오고 싶을 수 있습니다. 결제 게이트웨이, 알림 서비스, 내부 마이크로서비스 호출도 모두 마찬가지입니다.

이 문서에서는 Spring Boot 4가 제공하는 **HTTP 클라이언트**들을 정리하고, 가장 현대적이고 Kotlin과 잘 어울리는 **선언적 HTTP 인터페이스**로 외부 도서 메타데이터 API를 호출해 봅니다.

## 1. Spring의 HTTP 클라이언트 지형도

Spring에는 HTTP 클라이언트가 여러 개 있습니다. 새 코드라면 무엇을 골라야 하는지 먼저 정리합시다.

| 클라이언트 | 모델 | 상태 | 권장 여부 |
|-----------|------|------|-----------|
| `RestTemplate` | 동기(blocking) | 유지보수 모드 (deprecated 아님) | **신규 코드에는 쓰지 말 것** |
| `RestClient` | 동기(blocking), fluent API | Spring 6.1+ 도입, 현대적 | **동기 호출의 기본 선택** |
| `WebClient` | 리액티브(non-blocking) | 안정적 | WebFlux/리액티브 스택일 때 |
| **`@HttpExchange` 인터페이스** | 선언적 (위 둘 위에서 동작) | Spring 6+ / Boot 4에서 강화 | **가장 권장** |

핵심 메시지는 두 가지입니다.

- **`RestClient`가 `RestTemplate`을 대체**합니다. 같은 동기 모델이지만 fluent하고 현대적인 API를 제공합니다.
- 그리고 그 위에 **선언적 HTTP 인터페이스**(`@HttpExchange`)를 얹으면, Retrofit이나 Ktor의 타입 안전 클라이언트처럼 **인터페이스만 선언하면 구현(프록시)을 Spring이 만들어** 줍니다.

> [!TIP]
> Ktor를 쓰던 분이라면: `RestClient`는 `HttpClient`의 fluent 호출과 비슷하고, `@HttpExchange` 인터페이스는 Ktor의 Ktorfit이나 Retrofit의 `@GET`/`@POST` 인터페이스와 거의 같은 개념입니다.

## 2. 의존성 — 새 스타터

Spring Boot 4는 HTTP 클라이언트 전용 스타터를 분리했습니다. 동기 클라이언트라면 `restclient`를 추가합니다.

```kotlin
// build.gradle.kts
dependencies {
    // 동기 RestClient + @HttpExchange 인터페이스 지원
    implementation("org.springframework.boot:spring-boot-starter-restclient")

    // 리액티브가 필요할 때만
    // implementation("org.springframework.boot:spring-boot-starter-webclient")
}
```

`spring-boot-starter-web`이 이미 있어도, 명시적으로 `restclient` 스타터를 두면 의도가 분명해지고 자동 구성(`RestClient.Builder` 빈 등)이 깔끔하게 들어옵니다.

## 3. 선언적 HTTP 인터페이스 정의

외부 도서 메타데이터 API가 `GET /books/{isbn}` 으로 도서 정보를 준다고 가정합시다. 먼저 응답 DTO와 클라이언트 인터페이스를 선언합니다.

```kotlin
package com.example.bookapi.client

import org.springframework.web.service.annotation.GetExchange
import org.springframework.web.service.annotation.HttpExchange
import org.springframework.web.bind.annotation.PathVariable

// 외부 API의 응답 형태 (필요한 필드만)
data class BookMetadata(
    val isbn: String,
    val title: String,
    val authors: List<String>,
    val coverImageUrl: String?,
)

// 인터페이스 "선언"만 하면, 구현은 Spring이 프록시로 만들어 준다.
@HttpExchange(url = "/books", accept = ["application/json"])
interface BookMetadataClient {

    @GetExchange("/{isbn}")
    fun findByIsbn(@PathVariable isbn: String): BookMetadata
}
```

- `@HttpExchange`는 인터페이스/메서드 공통 설정(공통 경로, Accept 헤더 등)을 담습니다.
- `@GetExchange`/`@PostExchange`/`@PutExchange`/`@DeleteExchange`가 각 HTTP 메서드에 대응합니다.
- `@PathVariable`, `@RequestParam`, `@RequestBody`, `@RequestHeader` 등 컨트롤러에서 쓰던 애너테이션을 **그대로 클라이언트 쪽에서도** 사용합니다.

POST 예시도 보겠습니다.

```kotlin
import org.springframework.web.service.annotation.PostExchange
import org.springframework.web.bind.annotation.RequestBody

@HttpExchange(url = "/books")
interface BookMetadataClient {

    @GetExchange("/{isbn}")
    fun findByIsbn(@PathVariable isbn: String): BookMetadata

    @PostExchange
    fun register(@RequestBody metadata: BookMetadata): BookMetadata
}
```

## 4. 등록 방법 ① — `@ImportHttpServices` (Spring Boot 4 권장)

Spring Boot 4는 선언적 클라이언트를 가장 쉽게 등록하는 방법으로 **`@ImportHttpServices`** 애너테이션을 도입했습니다. `@Configuration` 클래스에 붙이면 해당 인터페이스의 **프록시 빈을 자동으로 생성**해 주입할 수 있게 됩니다.

```kotlin
package com.example.bookapi.client

import org.springframework.boot.web.client.ImportHttpServices
import org.springframework.context.annotation.Configuration

@Configuration
@ImportHttpServices(group = "book-metadata", types = [BookMetadataClient::class])
class HttpClientConfig
```

그리고 base URL과 타임아웃 등은 `application.yml`의 `spring.http.client` 설정으로 **그룹별로** 지정합니다.

```yaml
spring:
  http:
    client:
      # 모든 클라이언트 공통 기본값
      connect-timeout: 2s
      read-timeout: 5s
      service:
        group:
          book-metadata:
            base-url: https://metadata.example.com/api
```

이제 어디서든 인터페이스를 그냥 주입받아 쓰면 됩니다.

```kotlin
package com.example.bookapi.service

import com.example.bookapi.client.BookMetadataClient
import org.springframework.stereotype.Service

@Service
class BookEnrichmentService(
    private val metadataClient: BookMetadataClient,  // 프록시 빈이 주입된다
) {
    fun enrich(isbn: String): String {
        val meta = metadataClient.findByIsbn(isbn)
        return "${meta.title} / ${meta.authors.joinToString()}"
    }
}
```

> [!TIP]
> `@ImportHttpServices`의 `group` 값과 `spring.http.client.service.group.<group>` 의 키가 연결됩니다. 그룹을 나누면 외부 API마다 다른 base URL·타임아웃·인터셉터를 줄 수 있습니다.

## 5. 등록 방법 ② — 수동 `HttpServiceProxyFactory` (원리 이해용)

`@ImportHttpServices`가 내부적으로 무엇을 하는지 이해하면 디버깅이 쉬워집니다. 핵심은 **`HttpServiceProxyFactory`** 가 `RestClient`를 어댑터로 감싸 인터페이스 프록시를 만든다는 것입니다. 수동으로 하면 이렇게 됩니다.

```kotlin
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.web.client.RestClient
import org.springframework.web.client.support.RestClientAdapter
import org.springframework.web.service.invoker.HttpServiceProxyFactory

@Configuration
class ManualHttpClientConfig {

    @Bean
    fun bookMetadataClient(builder: RestClient.Builder): BookMetadataClient {
        // 1. base URL과 기본 헤더를 가진 RestClient 구성
        val restClient = builder
            .baseUrl("https://metadata.example.com/api")
            .defaultHeader("X-Client", "book-api")
            .build()

        // 2. RestClient를 어댑터로 감싸 프록시 팩토리 생성
        val factory = HttpServiceProxyFactory
            .builderFor(RestClientAdapter.create(restClient))
            .build()

        // 3. 인터페이스의 프록시 구현체 생성
        return factory.createClient(BookMetadataClient::class.java)
    }
}
```

`@ImportHttpServices`는 위 세 단계를 그룹 설정 기반으로 자동화한 것일 뿐입니다. 특수한 커스터마이징(예: 그룹 설정으로 표현하기 어려운 동적 base URL)이 필요할 때만 수동 방식을 쓰면 됩니다.

## 6. 에러 처리와 타임아웃

선언적 인터페이스도 결국 `RestClient` 위에서 돕니다. HTTP 4xx/5xx 응답은 기본적으로 예외(`RestClientResponseException` 계열)로 던져집니다. base URL을 만드는 `RestClient.Builder`에 **상태 핸들러**를 달아 외부 에러를 우리 도메인 예외로 바꿀 수 있습니다.

```kotlin
val restClient = builder
    .baseUrl("https://metadata.example.com/api")
    .defaultStatusHandler({ status -> status.value() == 404 }) { _, _ ->
        throw BookMetadataNotFoundException()  // 우리 도메인 예외로 변환
    }
    .build()
```

타임아웃은 앞서 본 `spring.http.client.connect-timeout` / `read-timeout` 으로 그룹/전역 지정하는 것을 권장합니다. 외부 호출은 **반드시** 타임아웃을 둬야 합니다. 그렇지 않으면 외부 서비스가 느려질 때 우리 스레드가 무한정 묶여 장애가 전파됩니다.

## 7. 회복 탄력성 — `@Retryable`과 `@ConcurrencyLimit`

외부 호출은 실패할 수 있습니다. Spring Framework 7은 별도 라이브러리 없이 쓸 수 있는 **선언적 회복 탄력성 애너테이션**을 코어에 포함했습니다.

```kotlin
import org.springframework.resilience.annotation.ConcurrencyLimit
import org.springframework.resilience.annotation.Retryable
import kotlin.time.Duration.Companion.seconds

@Service
class BookEnrichmentService(
    private val metadataClient: BookMetadataClient,
) {
    // 일시적 실패 시 최대 3회, 지수 백오프로 재시도
    @Retryable(maxAttempts = 3, delay = 1, multiplier = 2.0)
    fun enrich(isbn: String) = metadataClient.findByIsbn(isbn)

    // 동시에 외부 API를 두드리는 호출 수를 10개로 제한 (과부하 방지)
    @ConcurrencyLimit(10)
    fun bulkEnrich(isbns: List<String>) = isbns.map { metadataClient.findByIsbn(it) }
}
```

이 애너테이션들이 동작하려면 AOP 프록시가 필요하므로, 설정 클래스에 `@EnableResilientMethods`(Spring Framework 7) 를 켜 줍니다. 더 정교한 서킷 브레이커나 레이트 리미터가 필요하면 여전히 **Resilience4j**를 함께 쓸 수 있습니다.

> [!TIP]
> 재시도는 **멱등(idempotent)** 한 연산(GET 등)에만 안전합니다. 결제 같은 비멱등 POST를 무지성 재시도하면 중복 결제가 날 수 있습니다.

## 8. Ktor Client / Retrofit과의 비교

| | Ktor Client | Retrofit | Spring `@HttpExchange` |
|---|-------------|----------|------------------------|
| 정의 방식 | 함수 호출 / Ktorfit 인터페이스 | 인터페이스 + 애너테이션 | **인터페이스 + 애너테이션** |
| 엔진 | CIO/OkHttp 등 교체 가능 | OkHttp 고정 | `RestClient`/`WebClient` 교체 가능 |
| DI 통합 | 수동 | 수동/Hilt | **컨테이너 네이티브** (빈 주입) |
| 코루틴 | 일급 지원 | suspend 지원 | 동기 또는 리액티브(`Mono`/`Flow`) |

개념은 Retrofit과 거의 동일하지만, Spring 버전은 **DI 컨테이너에 녹아들고**, 컨트롤러에서 쓰던 바인딩 애너테이션을 그대로 재사용한다는 점이 큰 장점입니다.

## 다음 단계

이제 외부와 통신할 수 있게 되었으니, 반대로 **우리 API를 아무나 호출하지 못하도록** 보호할 차례입니다. Spring Security 7로 인증과 인가를 적용해 봅니다.

→ [Spring Security 7 기초](02-security-basics.md)
