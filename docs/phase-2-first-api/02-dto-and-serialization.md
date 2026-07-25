# DTO와 JSON 직렬화

REST API는 결국 **JSON을 주고받는 일**입니다. 클라이언트가 보낸 JSON을 Kotlin 객체로 바꾸고(역직렬화, deserialization), 응답할 Kotlin 객체를 다시 JSON으로 바꾸는(직렬화, serialization) 과정이 매 요청마다 일어납니다. Spring Boot는 이 변환을 **Jackson** 라이브러리로 자동 처리합니다. 이번 페이지에서는 그 변환의 단위가 되는 **DTO**를 정의합니다.

## 1. DTO란 무엇이고 왜 필요한가

**DTO(Data Transfer Object)**는 계층 간 데이터 전달만을 목적으로 하는 객체입니다. 우리는 도메인 엔티티(Phase 3에서 만들 JPA `Book` 엔티티)와 **별도의** 요청/응답 DTO를 둡니다. 이유는 다음과 같습니다.

| 이유 | 설명 |
|---|---|
| **노출 제어** | 엔티티의 모든 필드를 외부에 그대로 드러내면 보안·캡슐화에 취약합니다. DTO로 필요한 필드만 노출합니다. |
| **요청과 응답의 차이** | 생성 요청에는 `id`가 없지만(서버가 생성), 응답에는 `id`가 있습니다. 같은 객체로 표현하기 어렵습니다. |
| **변경 격리** | DB 스키마(엔티티)가 바뀌어도 API 계약(DTO)은 유지할 수 있습니다. |
| **검증 분리** | 입력 검증 규칙(Phase 4의 Bean Validation)을 요청 DTO에만 적용할 수 있습니다. |

그래서 우리는 세 종류의 DTO를 만듭니다.

```
응답용         BookResponse        (id 포함, 클라이언트에게 내보냄)
생성 요청용     CreateBookRequest   (id 없음, 모든 필드 필수)
수정 요청용     UpdateBookRequest   (id 없음, 수정할 필드)
```

## 2. DTO 정의 — data class

Kotlin의 `data class`는 DTO에 완벽하게 들어맞습니다. `equals`, `hashCode`, `toString`, `copy`가 자동 생성되고, 프로퍼티 선언만으로 불변(immutable) 객체를 만들 수 있습니다.

`src/main/kotlin/com/example/bookapi/dto/BookDtos.kt`:

```kotlin
package com.example.bookapi.dto

import java.time.LocalDate

// 응답 DTO — 클라이언트에게 내보내는 형태
data class BookResponse(
    val id: Long,
    val title: String,
    val author: String,
    val isbn: String,
    val price: Int,
    val publishedAt: LocalDate,
)

// 생성 요청 DTO — POST 본문으로 받는 형태 (id 없음)
data class CreateBookRequest(
    val title: String,
    val author: String,
    val isbn: String,
    val price: Int,
    val publishedAt: LocalDate,
)

// 수정 요청 DTO — PUT 본문으로 받는 형태 (id 없음)
data class UpdateBookRequest(
    val title: String,
    val author: String,
    val isbn: String,
    val price: Int,
    val publishedAt: LocalDate,
)
```

> **팁**: 입력값 검증(빈 문자열 금지, 가격은 0 이상 등)은 Phase 4에서 `@field:NotBlank`, `@field:Positive` 같은 Bean Validation 애너테이션으로 추가합니다. 지금은 구조에만 집중합니다.

## 3. Spring Boot 4의 JSON 엔진은 Jackson **3**

여기서 Boot 3 예제와 갈리는 가장 큰 지점을 짚습니다. **Spring Boot 4의 기본 JSON 엔진은 Jackson 3**입니다. Jackson 2와 무엇이 다른지 먼저 표로 봅니다.

| 항목 | Jackson 2 (Boot 3까지) | **Jackson 3 (Boot 4)** |
|---|---|---|
| 패키지 | `com.fasterxml.jackson.*` | **`tools.jackson.*`** |
| Kotlin 모듈 좌표 | `com.fasterxml.jackson.module:jackson-module-kotlin` | **`tools.jackson.module:jackson-module-kotlin`** |
| 매퍼 | 가변 `ObjectMapper` | **불변 `JsonMapper`** (빌더로 생성) |
| 애너테이션 | `com.fasterxml.jackson.annotation.*` | **그대로** (`@JsonProperty` 등은 패키지 유지) |
| 날짜 기본 직렬화 | 타임스탬프(숫자) | **ISO-8601 문자열** |
| 프로퍼티 정렬 | 선언 순서 | **알파벳순**(`SORT_PROPERTIES_ALPHABETICALLY` 기본 true) |
| 커스터마이즈 훅 | `Jackson2ObjectMapperBuilderCustomizer` | **`JsonMapperBuilderCustomizer`** |

> [!WARNING]
> 애너테이션(`@JsonProperty`, `@JsonInclude` 등)만 `com.fasterxml.jackson.annotation`에 남아 있고 **나머지는 전부 `tools.jackson`** 입니다. 그래서 "임포트 일부는 `com.fasterxml`, 일부는 `tools.jackson`"이라는, 처음 보면 어색한 조합이 정상입니다.

> [!NOTE]
> **응답 JSON의 키 순서**: Jackson 3는 프로퍼티를 알파벳순으로 정렬하는 것이 기본이므로, 실제 응답은 `{"author":…,"id":…,"isbn":…,"price":…,"publishedAt":…,"title":…}` 순서로 나옵니다. 본 가이드의 예시 JSON은 읽기 쉽도록 선언 순서(`id` → `title` → …)로 표기했습니다. JSON 객체의 키 순서는 의미가 없으므로 클라이언트 동작에는 영향이 없지만, 응답 문자열을 그대로 비교하는 테스트를 쓴다면 주의하세요. 선언 순서를 유지하고 싶으면 `spring.jackson.mapper.sort-properties-alphabetically: false` 로 끌 수 있습니다.

### jackson-module-kotlin이 하는 일

순수 Jackson은 Java를 전제로 설계되어, **기본 생성자**와 **세터(setter)** 가 있는 클래스를 가정합니다. 하지만 Kotlin data class는 기본 생성자가 없고, `val` 프로퍼티는 불변입니다. 그래서 `jackson-module-kotlin` 모듈이 필요합니다.

이 모듈은 다음을 가능하게 합니다.

- **주 생성자 기반 역직렬화**: 기본 생성자 없이도 JSON → data class 변환
- **기본 인자(default argument) 인식**: JSON에 필드가 없으면 Kotlin 기본값 사용
- **null 안정성 존중**: non-null(`String`) 프로퍼티에 JSON `null`이 들어오면 예외 발생, nullable(`String?`)은 허용

`spring-boot-starter-webmvc`를 쓰는 Spring Boot 프로젝트에 이 모듈이 클래스패스에 있으면 **Spring Boot가 자동으로 등록**합니다. 별도 설정 코드는 필요 없습니다. Phase 1에서 만든 `build.gradle.kts`에 다음이 포함되어 있는지 확인하세요.

```kotlin
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("tools.jackson.module:jackson-module-kotlin")   // ← Jackson 3용
    // ...
}
```

> Spring Initializr로 Kotlin + Spring Boot 4 프로젝트를 생성하면 `tools.jackson.module:jackson-module-kotlin`이 기본 포함됩니다.

### 매퍼를 직접 커스터마이즈할 때

`ObjectMapper`를 빈으로 등록해 설정을 바꾸던 Boot 3 패턴은, 불변 `JsonMapper`와 커스터마이저로 바뀌었습니다.

```kotlin
import org.springframework.boot.jackson.autoconfigure.JsonMapperBuilderCustomizer
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import tools.jackson.databind.SerializationFeature

@Configuration
class JacksonConfig {
    // 자동 구성된 JsonMapper의 빌더에 설정만 얹는다 (매퍼 전체를 대체하지 않는다)
    @Bean
    fun jsonMapperCustomizer() = JsonMapperBuilderCustomizer { builder ->
        builder.enable(SerializationFeature.INDENT_OUTPUT)
    }
}
```

> [!TIP]
> 기존 Jackson 2 코드를 급하게 옮기기 어렵다면 `spring.jackson.use-jackson2-defaults=true`로 **Boot 3 시절의 기본값**(날짜 타임스탬프, 선언 순서 등)을 되살릴 수 있습니다. Jackson 2 자체를 계속 쓰려면 `spring-boot-starter-jackson`을 제외하고 `spring-boot-jackson2` 모듈을 쓰며 `spring.jackson2.*` 프로퍼티로 설정합니다. 다만 신규 프로젝트라면 Jackson 3 기본값을 그대로 받아들이는 편이 낫습니다.

## 4. LocalDate 직렬화 (JSR-310)

`publishedAt: LocalDate`처럼 `java.time` 타입을 쓰면, Jackson의 **JSR-310 모듈**(`jackson-datatype-jsr310`)이 처리합니다. 이 역시 Spring Boot가 자동 등록합니다.

기본 동작은 **ISO-8601 문자열**입니다.

```json
{
  "publishedAt": "2024-03-15"
}
```

만약 이 모듈이 없으면 `LocalDate`가 `{"year":2024,"month":3,...}` 같은 숫자 배열로 깨져 나옵니다. Jackson 3는 **날짜를 ISO 문자열로 쓰는 것이 기본값**이라 위와 같은 깔끔한 형태가 그대로 나옵니다. 명시적으로 보장하려면 `application.yml`에 다음을 둡니다.

```yaml
spring:
  jackson:
    datatype:
      datetime:
        write-dates-as-timestamps: false   # 기본값. 날짜를 ISO 문자열로
```

> [!WARNING]
> Boot 3 예제의 **`spring.jackson.serialization.write-dates-as-timestamps`** 는 Boot 4에서 동작하지 않습니다. Jackson 3에서 날짜·시간 관련 기능이 `SerializationFeature`에서 **`DateTimeFeature`** 로 분리되었고, 대응하는 프로퍼티 경로도 `spring.jackson.datatype.datetime.*`으로 바뀌었습니다. (`indent-output` 같은 나머지 직렬화 옵션은 여전히 `spring.jackson.serialization.*` 입니다.)

## 5. 필드 이름 전략 — camelCase vs snake_case

기본적으로 Kotlin 프로퍼티 이름이 그대로 JSON 키가 됩니다. `publishedAt`은 `"publishedAt"`으로 나갑니다. 만약 API 규약이 **snake_case**(`published_at`)라면 두 가지 방법이 있습니다.

### 방법 A — 전역 설정 (권장)

`application.yml`에서 한 번에 적용합니다.

```yaml
spring:
  jackson:
    property-naming-strategy: SNAKE_CASE
```

이러면 모든 DTO의 키가 `published_at`, 입력도 `published_at`으로 통일됩니다.

### 방법 B — 클래스 단위 지정

특정 DTO만 다르게 하려면 `@JsonNaming`을 씁니다.

```kotlin
import tools.jackson.databind.annotation.JsonNaming        // Jackson 3 → tools.jackson
import tools.jackson.databind.PropertyNamingStrategies

@JsonNaming(PropertyNamingStrategies.SnakeCaseStrategy::class)
data class BookResponse(
    val id: Long,
    val publishedAt: LocalDate,   // → "published_at"
    // ...
)
```

### 방법 C — 필드 단위 지정

개별 필드만 이름을 바꾸려면 `@JsonProperty`를 씁니다. **애너테이션은 Jackson 3에서도 `com.fasterxml.jackson.annotation` 패키지 그대로**입니다.

```kotlin
import com.fasterxml.jackson.annotation.JsonProperty   // 애너테이션은 패키지 유지

data class BookResponse(
    @JsonProperty("book_id")
    val id: Long,
    // ...
)
```

> **팁**: 본 가이드는 단순함을 위해 **camelCase 기본값**을 그대로 사용합니다. 팀 규약에 맞춰 위 방법 중 하나를 택하세요.

## 6. null 필드 제어

응답 JSON에 `null` 값을 포함할지 제외할지 정할 수 있습니다. 기본값은 **항상 포함**입니다. (이 프로퍼티는 Jackson 3에서도 이름이 그대로입니다.)

```json
// default-property-inclusion 기본: null도 출력
{ "id": 1, "title": "코틀린", "discount": null }
```

`null` 필드를 응답에서 빼고 싶다면 전역 설정합니다.

```yaml
spring:
  jackson:
    default-property-inclusion: non_null   # null인 프로퍼티는 JSON에서 제외
```

이 설정을 켜면 위 응답에서 `"discount": null` 줄이 사라집니다. 우리 도서 DTO는 nullable 필드가 없으므로 당장 영향은 없지만, 선택적 필드가 생기면 유용합니다.

## 7. 직렬화 흐름 한눈에 보기

```
[POST /api/books 요청]
   JSON 본문
   { "title": "...", "publishedAt": "2024-03-15" }
        │
        ▼  Jackson 3 + jackson-module-kotlin (역직렬화)
   CreateBookRequest(title="...", publishedAt=LocalDate(2024,3,15))
        │
        ▼  Service 처리 → 저장 → BookResponse 생성
   BookResponse(id=1, title="...", publishedAt=...)
        │
        ▼  Jackson (직렬화)
   JSON 응답
   { "id": 1, "title": "...", "publishedAt": "2024-03-15" }
```

이 변환은 컨트롤러의 `@RequestBody`/`@ResponseBody`(또는 `@RestController`)가 트리거합니다. 다음 페이지에서 바로 확인합니다.

## 다음 단계

데이터의 형태(DTO)를 정의했으니, 이제 이 DTO를 주고받는 HTTP 엔드포인트를 만들 차례입니다. [@RestController 구현](03-rest-controller.md)으로 이동하세요.
