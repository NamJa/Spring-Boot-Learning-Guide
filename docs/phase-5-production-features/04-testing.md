# 테스트 전략

테스트 없는 코드는 **배포할 때마다 도박**입니다. 하지만 모든 테스트를 매번 전체 애플리케이션을 띄워서 돌리면 느리고 깨지기 쉽습니다. Spring Boot의 핵심 테스트 전략은 **필요한 만큼만 컨텍스트를 띄우는 "테스트 슬라이스(test slice)"** 입니다.

이 문서에서는 슬라이스별 도구를 정리하고, Book API에 대한 Kotlin + JUnit 5 테스트를 실제로 작성합니다.

## 1. 테스트 슬라이스 한눈에 보기

| 애너테이션 | 띄우는 범위 | 용도 | 속도 |
|-----------|------------|------|------|
| `@SpringBootTest` | **전체** 애플리케이션 컨텍스트 | 통합 테스트, E2E | 느림 |
| `@WebMvcTest` | 웹 계층(컨트롤러)만, 서비스는 목 | 컨트롤러 + `MockMvc` | 빠름 |
| `@DataJpaTest` | JPA 계층(리포지토리 + 내장 DB) | 쿼리·매핑 검증 | 빠름 |
| `@RestClientTest` | HTTP 클라이언트 + `MockRestServiceServer` | 외부 호출 클라이언트(Phase 5-1) | 빠름 |

원칙: **가능한 한 좁은 슬라이스로** 테스트하고, 전체 통합 테스트는 핵심 시나리오에만 사용합니다. 슬라이스 테스트가 빠르므로 많이, 통합 테스트는 적게 — 흔히 말하는 테스트 피라미드입니다.

```kotlin
// build.gradle.kts — spring-boot-starter-test 에 JUnit5, AssertJ, Mockito 등이 모두 포함
testImplementation("org.springframework.boot:spring-boot-starter-test")
```

## 2. `@WebMvcTest` — 컨트롤러 테스트

컨트롤러의 요청 매핑·직렬화·검증·상태 코드만 검증하고 싶을 때 씁니다. 서비스 계층은 **목(mock)** 으로 대체합니다. 여기서 Spring Boot가 제공하는 **`@MockitoBean`** 을 씁니다.

> [!TIP]
> `@MockitoBean`은 과거의 **`@MockBean`을 대체**합니다(`@MockBean`은 deprecated). 동작은 같습니다: 목 객체를 만들어 스프링 컨텍스트의 해당 빈을 교체합니다.

```kotlin
package com.example.bookapi.web

import com.example.bookapi.service.BookService
import org.junit.jupiter.api.Test
import org.mockito.kotlin.given
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest
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
            .willReturn(listOf(Book(1, "코틀린 인 액션", 35000)))

        mockMvc.get("/books")
            .andExpect {
                status { isOk() }
                jsonPath("$[0].title") { value("코틀린 인 액션") }
            }
    }

    @Test
    fun `POST with blank title returns 400`() {
        mockMvc.post("/books") {
            contentType = org.springframework.http.MediaType.APPLICATION_JSON
            content = """{"title":"","price":1000}"""
        }.andExpect {
            status { isBadRequest() }   // Bean Validation 실패 (Phase 4)
        }
    }
}
```

Spring Boot 4에서는 fluent한 **`MockMvcTester`** (AssertJ 기반)도 자동 주입됩니다. 더 읽기 좋은 단언을 원하면 이렇게 쓸 수 있습니다.

```kotlin
import org.springframework.test.web.servlet.assertj.MockMvcTester
import org.assertj.core.api.Assertions.assertThat

@WebMvcTest(BookController::class)
class BookControllerTesterTest(@Autowired val mvc: MockMvcTester) {

    @MockitoBean lateinit var bookService: BookService

    @Test
    fun `GET books is ok`() {
        given(bookService.findAll()).willReturn(emptyList())

        assertThat(mvc.get().uri("/books"))
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
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest

@DataJpaTest
class BookRepositoryTest(
    @Autowired val repository: BookRepository,
) {
    @Test
    fun `findByTitleContaining returns matching books`() {
        repository.save(Book(title = "코틀린 인 액션", price = 35000))
        repository.save(Book(title = "이펙티브 코틀린", price = 30000))
        repository.save(Book(title = "자바 최강의 기술", price = 28000))

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

실제 서버를 띄워 HTTP 호출부터 DB 저장까지 **전 계층을 관통**하는 테스트입니다. `webEnvironment = RANDOM_PORT` 로 실제 포트에 톰캣을 띄우고, **`TestRestClient`** (Spring Boot 4, `RestClient` 기반)로 호출합니다.

```kotlin
package com.example.bookapi

import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.Test
import org.springframework.beans.factory.annotation.Autowired
import org.springframework.boot.test.context.SpringBootTest
import org.springframework.boot.test.web.client.TestRestClient
import org.springframework.test.context.ActiveProfiles

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@ActiveProfiles("test")   // application-test.yml 설정 사용 (Phase 4)
class BookApiIntegrationTest(
    @Autowired val restClient: TestRestClient,
) {
    @Test
    fun `create then fetch book end-to-end`() {
        // 1. 도서 등록 (인증 필요 — Phase 5-2)
        val created = restClient.post().uri("/books")
            .headers { it.setBasicAuth("admin", "admin-secret") }
            .body(BookRequest(title = "스프링 부트 4 입문", price = 42000))
            .retrieve()
            .toEntity(BookResponse::class.java)

        assertThat(created.statusCode.value()).isEqualTo(201)
        val id = created.body!!.id

        // 2. 조회 (인증 불필요)
        val fetched = restClient.get().uri("/books/{id}", id)
            .retrieve()
            .body(BookResponse::class.java)

        assertThat(fetched!!.title).isEqualTo("스프링 부트 4 입문")
    }
}
```

> [!TIP]
> 아직 `TestRestClient`가 없는 환경이라면 기존의 **`TestRestTemplate`** 을 같은 방식으로 주입해 쓸 수 있습니다. 새 코드는 `RestClient` 기반인 `TestRestClient`를 권장합니다.

## 5. `@RestClientTest` — 외부 클라이언트 테스트

Phase 5-1에서 만든 `BookMetadataClient`처럼 **외부 API를 호출하는 클라이언트**는, 실제 외부 서버에 의존하지 않고 `MockRestServiceServer`로 응답을 흉내 내 테스트합니다.

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

## 6. 실제 DB 통합 테스트 — Testcontainers

H2로는 PostgreSQL 고유 기능(JSONB, 특정 함수 등)을 검증할 수 없습니다. **Testcontainers**는 테스트 중 **실제 PostgreSQL을 도커 컨테이너로** 띄워 줍니다.

```kotlin
// build.gradle.kts
testImplementation("org.springframework.boot:spring-boot-testcontainers")
testImplementation("org.testcontainers:postgresql")
testImplementation("org.testcontainers:junit-jupiter")
```

```kotlin
@SpringBootTest
@ActiveProfiles("test")
@Testcontainers
class BookRepositoryPostgresTest {

    companion object {
        @Container
        @ServiceConnection   // 컨테이너 접속 정보를 datasource 설정에 자동 연결 (Spring Boot 3.1+)
        val postgres = PostgreSQLContainer("postgres:17")
    }

    @Autowired lateinit var repository: BookRepository

    @Test
    fun `works against real postgres`() {
        val saved = repository.save(Book(title = "테스트 도서", price = 1000))
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
| 전 계층 시나리오 / 보안 / 통합 | `@SpringBootTest(RANDOM_PORT)` + `TestRestClient` |
| 운영 DB 고유 동작 | `@SpringBootTest` + Testcontainers |

> [!TIP]
> 단언은 **AssertJ**(`assertThat(...)`)로 통일하면 가독성과 에러 메시지가 좋아집니다. JUnit `assertEquals`보다 권장됩니다. 그리고 통합 테스트에는 `@ActiveProfiles("test")`로 테스트 전용 설정을 분리하세요.

## 다음 단계

축하합니다. 이제 Book API는 외부와 통신하고, 보안이 적용되고, 관측 가능하며, 테스트로 검증됩니다. 운영에 필요한 기능을 모두 갖췄으니, 마지막 Phase에서 이 애플리케이션을 **실제로 빌드하고 배포**합니다.

→ [실행 가능 JAR 빌드](../phase-6-build-deploy/01-executable-jar.md)
