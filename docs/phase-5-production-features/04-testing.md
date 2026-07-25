# 테스트 전략

테스트 없는 코드는 **배포할 때마다 도박**입니다. 하지만 모든 테스트를 매번 전체 애플리케이션을 띄워서 돌리면 느리고 깨지기 쉽습니다. Spring Boot의 핵심 테스트 전략은 **필요한 만큼만 컨텍스트를 띄우는 "테스트 슬라이스(test slice)"** 입니다.

이 문서에서는 슬라이스별 도구를 정리하고, Book API에 대한 Kotlin + JUnit 5 테스트를 실제로 작성합니다.

## 1. 테스트 슬라이스 한눈에 보기

| 애너테이션 | 띄우는 범위 | 용도 | 속도 |
|-----------|------------|------|------|
| `@SpringBootTest` | **전체** 애플리케이션 컨텍스트 | 통합 테스트, E2E | 느림 |
| `@WebMvcTest` | 웹 계층(컨트롤러)만, 서비스는 목 | 컨트롤러 + `MockMvc`/`MockMvcTester` | 빠름 |
| `@DataJpaTest` | JPA 계층(리포지토리 + 내장 DB) | 쿼리·매핑 검증 | 빠름 |
| `@RestClientTest` | HTTP 클라이언트 + `MockRestServiceServer` | 외부 호출 클라이언트(Phase 5-1) | 빠름 |

원칙: **가능한 한 좁은 슬라이스로** 테스트하고, 전체 통합 테스트는 핵심 시나리오에만 사용합니다. 슬라이스 테스트가 빠르므로 많이, 통합 테스트는 적게 — 흔히 말하는 테스트 피라미드입니다.

### 의존성 — Boot 4의 모듈형 테스트 스타터

Spring Boot 4부터 테스트 의존성이 **기술별 스타터**로 쪼개졌습니다. 필요한 슬라이스만 골라 넣으면 되고, 각 스타터가 `spring-boot-starter-test`(JUnit 6 · AssertJ 3.27 · Mockito 5.23 · Hamcrest · JSONassert)를 전이 의존성으로 가져옵니다.

```kotlin
// build.gradle.kts
testImplementation("org.springframework.boot:spring-boot-starter-webmvc-test")    // MockMvc, RestTestClient
testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")  // @DataJpaTest
testImplementation("org.springframework.boot:spring-boot-starter-restclient-test") // @RestClientTest
testImplementation("org.jetbrains.kotlin:kotlin-test-junit5")
testRuntimeOnly("org.junit.platform:junit-platform-launcher")
```

> [!NOTE]
> `spring-boot-starter-test` 하나만 넣는 Boot 3 방식도 여전히 동작하지만, 그러면 슬라이스별 자동 구성(예: `RestTestClient`)이 빠질 수 있습니다. Initializr도 이제 기술별 `-test` 스타터를 생성합니다. 또한 Spring Boot 4.1의 `spring-boot-starter-test`가 가져오는 JUnit은 **JUnit 6(Jupiter 6.0.3)** 입니다 — 임포트(`org.junit.jupiter.api.*`)는 그대로라 대부분의 테스트 코드는 수정 없이 동작합니다.

> [!WARNING]
> **테스트 슬라이스 애너테이션의 패키지도 함께 이동했습니다.** 기술별 모듈로 쪼개지면서 임포트 경로가 바뀌었으니, Boot 3 예제를 복사하면 컴파일되지 않습니다.
>
> | 애너테이션 | Boot 3 | **Boot 4** |
> |---|---|---|
> | `@WebMvcTest` | `org.springframework.boot.test.autoconfigure.web.servlet` | **`org.springframework.boot.webmvc.test.autoconfigure`** |
> | `@DataJpaTest` | `org.springframework.boot.test.autoconfigure.orm.jpa` | **`org.springframework.boot.data.jpa.test.autoconfigure`** |
> | `@RestClientTest` | `org.springframework.boot.test.autoconfigure.web.client` | **`org.springframework.boot.restclient.test.autoconfigure`** |
>
> `@SpringBootTest`(`org.springframework.boot.test.context`)는 그대로입니다.

## 2. `@WebMvcTest` — 컨트롤러 테스트

컨트롤러의 요청 매핑·직렬화·검증·상태 코드만 검증하고 싶을 때 씁니다. 서비스 계층은 **목(mock)** 으로 대체합니다. 여기서 Spring Boot가 제공하는 **`@MockitoBean`** 을 씁니다.

> [!WARNING]
> `@MockitoBean`(`org.springframework.test.context.bean.override.mockito`)은 과거의 `@MockBean`을 대체합니다. Spring Boot 4에서 **`@MockBean`과 `@SpyBean`은 deprecated가 아니라 아예 제거**되었으므로, Boot 3 예제를 복사하면 컴파일되지 않습니다. 동작은 같습니다: 목 객체를 만들어 스프링 컨텍스트의 해당 빈을 교체합니다. 단, `@MockitoBean`은 **테스트 클래스(또는 그 상위 클래스·인터페이스)의 필드나 클래스 자체**에만 붙일 수 있습니다. 클래스 레벨에 붙일 때는 `types` 속성으로 대상 타입을 지정하며(반복 사용 가능), `@Configuration` 클래스에서는 쓸 수 없습니다.

```kotlin
package com.example.bookapi.controller

import com.example.bookapi.dto.BookResponse
import com.example.bookapi.service.BookService
import java.time.LocalDate
import org.junit.jupiter.api.Test
import org.mockito.kotlin.given
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest   // ⚠️ Boot 4에서 패키지 이동
import org.springframework.test.context.bean.override.mockito.MockitoBean
import org.springframework.test.web.servlet.MockMvc
import org.springframework.test.web.servlet.get
import org.springframework.test.web.servlet.post

@WebMvcTest(BookController::class)   // BookController만 로드
class BookControllerTest(
    @Autowired val mockMvc: MockMvc,
) {
    @MockitoBean
    lateinit var bookService: BookService   // 진짜 서비스 대신 목 주입

    @Test
    fun `GET books returns 200 with list`() {
        given(bookService.findAll())
            .willReturn(
                listOf(
                    BookResponse(
                        id = 1,
                        title = "코틀린 인 액션",
                        author = "드미트리 제메로프",
                        isbn = "978-8966262281",
                        price = 35000,
                        publishedAt = LocalDate.of(2017, 6, 1),
                    ),
                ),
            )

        mockMvc.get("/api/books")
            .andExpect {
                status { isOk() }
                jsonPath("$[0].title") { value("코틀린 인 액션") }
            }
    }

    @Test
    fun `POST with blank title returns 400`() {
        mockMvc.post("/api/books") {
            contentType = org.springframework.http.MediaType.APPLICATION_JSON
            content = """{"title":"","author":"홍길동","isbn":"978-8966262281","price":1000,"publishedAt":"2017-06-01"}"""
        }.andExpect {
            status { isBadRequest() }   // Bean Validation 실패 (Phase 4)
        }
    }
}
```

Spring Boot 4에서는 fluent한 **`MockMvcTester`** (Spring Framework의 AssertJ 기반 API)도 `@WebMvcTest`에서 자동 주입됩니다. 더 읽기 좋은 단언을 원하면 이렇게 쓸 수 있습니다.

```kotlin
import org.springframework.test.web.servlet.assertj.MockMvcTester
import org.assertj.core.api.Assertions.assertThat

@WebMvcTest(BookController::class)
class BookControllerTesterTest(@Autowired val mvc: MockMvcTester) {

    @MockitoBean lateinit var bookService: BookService

    @Test
    fun `GET books is ok`() {
        given(bookService.findAll()).willReturn(emptyList())

        assertThat(mvc.get().uri("/api/books"))
            .hasStatusOk()
            .bodyJson().isEqualTo("[]")
    }
}
```

## 3. `@DataJpaTest` — 리포지토리 테스트

리포지토리의 쿼리 메서드와 엔티티 매핑을 검증합니다. 기본적으로 **내장 H2 DB**를 띄우고, 각 테스트는 **트랜잭션 후 롤백**되어 서로 격리됩니다.

```kotlin
package com.example.bookapi.repository

import com.example.bookapi.domain.Book
import java.time.LocalDate
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest   // ⚠️ Boot 4에서 패키지 이동

@DataJpaTest
class BookRepositoryTest(
    @Autowired val repository: BookRepository,
) {
    @Test
    fun `findByTitleContaining returns matching books`() {
        repository.save(
            Book(
                title = "코틀린 인 액션",
                author = "드미트리 제메로프",
                isbn = "978-8966262281",
                price = 35000,
                publishedAt = LocalDate.of(2017, 6, 1),
            ),
        )
        repository.save(
            Book(
                title = "이펙티브 코틀린",
                author = "마르친 모스카와",
                isbn = "978-8966263363",
                price = 30000,
                publishedAt = LocalDate.of(2022, 3, 1),
            ),
        )
        repository.save(
            Book(
                title = "자바 최강의 기술",
                author = "조슈아 블로크",
                isbn = "978-8966263158",
                price = 28000,
                publishedAt = LocalDate.of(2018, 10, 1),
            ),
        )

        val result = repository.findByTitleContaining("코틀린")

        // AssertJ — 읽기 좋은 단언
        assertThat(result)
            .hasSize(2)
            .extracting<String> { it.title }
            .containsExactlyInAnyOrder("코틀린 인 액션", "이펙티브 코틀린")
    }
}
```

> [!TIP]
> `@DataJpaTest`는 컨트롤러·서비스 빈을 로드하지 않습니다. 따라서 매우 빠릅니다. 단, 내장 H2와 운영 DB(PostgreSQL) 사이에 방언 차이가 있을 수 있으니, 미묘한 쿼리는 6절의 Testcontainers로 실제 DB에서 검증하세요.

## 4. `@SpringBootTest` — 통합 테스트

실제 서버를 띄워 HTTP 호출부터 DB 저장까지 **전 계층을 관통**하는 테스트입니다. `webEnvironment = RANDOM_PORT` 로 실제 포트에 톰캣을 띄우고, Spring Framework 7이 제공하는 **`RestTestClient`** 로 호출합니다.

Spring Boot 4에서는 테스트용 HTTP 클라이언트가 **더 이상 자동 구성되지 않습니다.** `@AutoConfigureRestTestClient`로 명시적으로 켜 줘야 합니다.

```kotlin
package com.example.bookapi

import com.example.bookapi.dto.CreateBookRequest
import java.time.LocalDate
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.resttestclient.autoconfigure.AutoConfigureRestTestClient
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.test.context.ActiveProfiles
import org.springframework.test.web.servlet.client.RestTestClient

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureRestTestClient   // ← Boot 4: 테스트 HTTP 클라이언트를 명시적으로 활성화
@ActiveProfiles("test")        // application-test.yml 설정 사용 (Phase 4)
class BookApiIntegrationTest(
    @Autowired val client: RestTestClient,
) {
    @Test
    fun `create then fetch book end-to-end`() {
        // 1. 도서 등록 (인증 필요 — Phase 5-2)
        client.post().uri("/api/books")
            .headers { it.setBasicAuth("admin", "admin-secret") }
            .body(
                CreateBookRequest(
                    title = "스프링 부트 4 입문",
                    author = "김종우",
                    isbn = "978-8966262281",
                    price = 42000,
                    publishedAt = LocalDate.of(2026, 1, 1),
                ),
            )
            .exchange()                       // 요청 실행 → ResponseSpec 반환
            .expectStatus().isCreated()       // 201 검증
            .expectBody()
            .jsonPath("$.title").isEqualTo("스프링 부트 4 입문")

        // 2. 조회 (인증 불필요)
        client.get().uri("/api/books")
            .exchange()
            .expectStatus().isOk()
            .expectBody()
            .jsonPath("$[0].title").isEqualTo("스프링 부트 4 입문")
    }
}
```

> [!WARNING]
> **`TestRestClient`라는 클래스는 존재하지 않습니다.** Boot 4의 통합 테스트 클라이언트는 Spring Framework 7의 **`RestTestClient`**(`org.springframework.test.web.servlet.client`)이고, 활성화 애너테이션은 `org.springframework.boot.resttestclient.autoconfigure.AutoConfigureRestTestClient`입니다. 기존 **`TestRestTemplate`** 도 남아 있지만 패키지가 `org.springframework.boot.resttestclient`로 옮겨졌고 `@AutoConfigureTestRestTemplate`을 붙여야 주입됩니다. 새 코드는 `RestTestClient`를 권장합니다.
>
> `RestTestClient`는 서버 없이 MockMvc에 바인딩해서(`RestTestClient.bindToApplicationContext(...)`) 쓸 수도 있어, 슬라이스/통합 테스트에서 같은 API를 유지할 수 있습니다.

## 5. `@RestClientTest` — 외부 클라이언트 테스트

Phase 5-1에서 만든 `BookMetadataClient`처럼 **외부 API를 호출하는 클라이언트**는, 실제 외부 서버에 의존하지 않고 `MockRestServiceServer`로 응답을 흉내 내 테스트합니다. Boot 4에서 이 애너테이션의 패키지는 **`org.springframework.boot.restclient.test.autoconfigure.RestClientTest`** 이고, `spring-boot-starter-restclient-test` 스타터가 제공합니다.

```kotlin
@RestClientTest(BookEnrichmentService::class)
class BookEnrichmentServiceTest(
    @Autowired val service: BookEnrichmentService,
    @Autowired val server: MockRestServiceServer,
) {
    @Test
    fun `enrich returns title from external api`() {
        server.expect(requestTo("/books/978-1617293290"))
            .andRespond(withSuccess("""{"isbn":"978-1617293290","title":"코틀린 인 액션","authors":["드미트리"]}""",
                MediaType.APPLICATION_JSON))

        val result = service.enrich("978-1617293290")

        assertThat(result).contains("코틀린 인 액션")
    }
}
```

> [!WARNING]
> `@RestClientTest` 슬라이스는 **`RestClient.Builder`/`RestTemplateBuilder`를 사용하는 빈만** 로드하고 그 빌더에 `MockRestServiceServer`를 끼워 넣습니다. 그런데 [Phase 5-1](01-http-interface-client.md)의 `BookMetadataClient`는 `@ImportHttpServices`가 만들어 주는 프록시 빈이고, 그 등록기는 이 슬라이스의 자동 구성에 포함되지 않습니다. 따라서 위 예제를 그대로 돌리면 `BookMetadataClient` 빈을 찾지 못할 수 있습니다.
>
> 실무에서는 (1) 테스트에 `@ImportHttpServices` 설정 클래스를 명시적으로 `@Import`하거나, (2) 5-1의 "수동 `HttpServiceProxyFactory`" 방식처럼 주입받은 `RestClient.Builder`로 클라이언트를 만들어 두면(그 빌더가 목 서버에 연결됩니다) 이 슬라이스로 깔끔하게 테스트할 수 있습니다.

## 6. 실제 DB 통합 테스트 — Testcontainers

H2로는 PostgreSQL 고유 기능(JSONB, 특정 함수 등)을 검증할 수 없습니다. **Testcontainers**는 테스트 중 **실제 PostgreSQL을 도커 컨테이너로** 띄워 줍니다.

```kotlin
// build.gradle.kts — Testcontainers 2.x 기준 (Spring Boot 4.1 관리 버전 2.0.5)
testImplementation("org.springframework.boot:spring-boot-testcontainers")
testImplementation("org.testcontainers:testcontainers-postgresql")
testImplementation("org.testcontainers:testcontainers-junit-jupiter")
```

> [!WARNING]
> Testcontainers **2.0**에서 두 가지가 바뀌었습니다.
> 1. **아티팩트 이름**에 `testcontainers-` 접두사가 붙었습니다(`postgresql` → `testcontainers-postgresql`, `junit-jupiter` → `testcontainers-junit-jupiter`). 코어(`org.testcontainers:testcontainers`)는 그대로입니다.
> 2. **컨테이너 클래스가 모듈별 패키지로 이동**했습니다: `org.testcontainers.containers.PostgreSQLContainer` → **`org.testcontainers.postgresql.PostgreSQLContainer`**. 구 클래스도 아직 들어 있지만 `@Deprecated`이고, 새 클래스는 제네릭 타입 파라미터가 없습니다(`PostgreSQLContainer` 그대로 사용).
>
> `@Testcontainers`/`@Container`(`org.testcontainers.junit.jupiter`)와 Spring Boot의 `@ServiceConnection`(`org.springframework.boot.testcontainers.service.connection`)은 위치가 그대로입니다. JUnit 4 지원은 제거됐습니다.

```kotlin
import org.springframework.boot.testcontainers.service.connection.ServiceConnection
import org.testcontainers.junit.jupiter.Container
import org.testcontainers.junit.jupiter.Testcontainers
import org.testcontainers.postgresql.PostgreSQLContainer   // ⚠️ 2.x에서 이동한 패키지

@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class BookRepositoryPostgresTest {

    companion object {
        @Container
        @ServiceConnection   // 컨테이너 접속 정보를 datasource 설정에 자동 연결 (Spring Boot 3.1+)
        val postgres = PostgreSQLContainer("postgres:18")   // 2026-07 기준 최신 메이저
    }

    @Autowired lateinit var repository: BookRepository

    @Test
    fun `works against real postgres`() {
        val saved = repository.save(
            Book(
                title = "테스트 도서",
                author = "테스트 저자",
                isbn = "978-8966262281",
                price = 1000,
                publishedAt = LocalDate.of(2025, 1, 1),
            ),
        )
        assertThat(repository.findById(saved.id!!)).isPresent
    }
}
```

`@ServiceConnection` 덕분에 컨테이너의 JDBC URL·계정을 수동으로 프로퍼티에 옮길 필요가 없습니다. 운영과 동일한 DB로 검증하므로 신뢰도가 가장 높지만, 도커가 필요하고 느리므로 **핵심 쿼리에만** 적용합니다.

## 7. 정리: 무엇을 언제 쓰나

| 검증하고 싶은 것 | 사용 |
|------------------|------|
| 요청 매핑·검증·상태 코드·직렬화 | `@WebMvcTest` + `@MockitoBean` |
| 쿼리 메서드·엔티티 매핑 (빠르게) | `@DataJpaTest` |
| 외부 API 호출 클라이언트 | `@RestClientTest` |
| 전 계층 시나리오 / 보안 / 통합 | `@SpringBootTest(RANDOM_PORT)` + `@AutoConfigureRestTestClient` + `RestTestClient` |
| 운영 DB 고유 동작 | `@SpringBootTest` + Testcontainers |

> [!TIP]
> 단언은 **AssertJ**(`assertThat(...)`)로 통일하면 가독성과 에러 메시지가 좋아집니다. JUnit `assertEquals`보다 권장됩니다. 그리고 통합 테스트에는 `@ActiveProfiles("test")`로 테스트 전용 설정을 분리하세요.

## 다음 단계

축하합니다. 이제 Book API는 외부와 통신하고, 보안이 적용되고, 관측 가능하며, 테스트로 검증됩니다. 운영에 필요한 기능을 모두 갖췄으니, 마지막 Phase에서 이 애플리케이션을 **실제로 빌드하고 배포**합니다.

→ [실행 가능 JAR 빌드](../phase-6-build-deploy/01-executable-jar.md)
