# @ConfigurationProperties

앞 문서에서 설정값을 YAML로 외부화했습니다. 이제 그 값을 코드에서 **읽어 쓰는** 방법이 필요합니다. 가장 단순한 방법은 `@Value`로 하나씩 주입하는 것입니다.

```kotlin
@Service
class BookService(
    @Value("\${app.book.default-page-size}") private val defaultPageSize: Int,
    @Value("\${app.book.currency}") private val currency: String,
    @Value("\${app.book.recommendation-enabled}") private val recommendationEnabled: Boolean,
) { /* ... */ }
```

값이 한두 개면 괜찮지만, 관련 설정이 늘어나면 금세 지저분해집니다. 키를 문자열로 적으니 오타가 나도 컴파일러가 못 잡고, 타입도 매번 직접 맞춰야 합니다. 더 나은 방법이 **`@ConfigurationProperties`** — 관련 설정을 **타입 안전한 Kotlin 클래스 하나에 통째로 바인딩**하는 것입니다.

## 1. 설정 블록을 클래스에 바인딩

먼저 묶을 설정을 YAML에 정의합니다. `app.book` 접두사 아래 도서 도메인 관련 설정을 모읍니다.

```yaml
# application.yml
app:
  book:
    default-page-size: 20
    currency: KRW
    recommendation-enabled: true
    allowed-categories:
      - 소설
      - 기술
      - 역사
```

이제 이 블록을 받을 Kotlin 클래스를 만듭니다. **권장 방식은 불변(immutable) 생성자 바인딩** — `val`만 가진 `data class`입니다.

```kotlin
package com.example.bookapi.config

import org.springframework.boot.context.properties.ConfigurationProperties

@ConfigurationProperties(prefix = "app.book")
data class BookProperties(
    val defaultPageSize: Int = 20,            // 케밥 케이스 default-page-size 와 자동 매칭
    val currency: String = "KRW",
    val recommendationEnabled: Boolean = false,
    val allowedCategories: List<String> = emptyList(),
)
```

YAML의 케밥 케이스(`default-page-size`)가 클래스의 카멜 케이스(`defaultPageSize`) 프로퍼티로 **느슨한 바인딩**되어 자동 매칭됩니다(앞 문서 4절). `val`에 기본값을 주면 해당 설정이 누락돼도 안전합니다.

> [!TIP]
> 생성자 바인딩은 모든 프로퍼티가 `val`이라 **불변**이고, 객체 생성 시점에 모든 값이 채워져 일관성이 보장됩니다. 가변 `var` + setter 바인딩보다 항상 이쪽을 권장합니다.

## 2. 클래스 활성화하기

`@ConfigurationProperties`를 붙이는 것만으로는 Bean으로 등록되지 않습니다. 활성화 방법이 두 가지 있습니다.

**방식 A — `@EnableConfigurationProperties` (생성자 바인딩에 권장):**

설정 클래스는 순수하게 두고, 별도 위치에서 활성화합니다.

```kotlin
package com.example.bookapi

import com.example.bookapi.config.BookProperties
import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.context.properties.EnableConfigurationProperties

@SpringBootApplication
@EnableConfigurationProperties(BookProperties::class) // ← 여기서 활성화
class BookApiApplication
```

**방식 B — `@ConfigurationPropertiesScan`:**

여러 properties 클래스가 있으면 패키지 스캔으로 한 번에 등록합니다.

```kotlin
@SpringBootApplication
@ConfigurationPropertiesScan // app 패키지 하위의 @ConfigurationProperties 자동 등록
class BookApiApplication
```

> [!NOTE]
> 가변 `var` 클래스라면 클래스에 `@Component`를 직접 붙여 등록할 수도 있지만, 불변 생성자 바인딩 클래스는 `@Component`와 함께 쓸 수 없습니다. 생성자 바인딩에는 **방식 A 또는 B**를 사용하세요.

## 3. 서비스에서 주입해 사용하기

등록된 `BookProperties`는 다른 Bean처럼 생성자로 주입받아 씁니다.

```kotlin
package com.example.bookapi.service

import com.example.bookapi.config.BookProperties
import org.springframework.data.domain.PageRequest
import org.springframework.stereotype.Service

@Service
class BookService(
    private val bookRepository: BookRepository,
    private val bookProperties: BookProperties, // ← 설정 묶음을 통째로 주입
) {
    fun findAll(page: Int): List<BookResponse> {
        // 설정에서 가져온 기본 페이지 크기 사용
        val pageable = PageRequest.of(page, bookProperties.defaultPageSize)
        return bookRepository.findAll(pageable).map { it.toResponse() }
    }

    fun validateCategory(category: String) {
        if (bookProperties.allowedCategories.isNotEmpty() &&
            category !in bookProperties.allowedCategories
        ) {
            throw IllegalArgumentException("허용되지 않은 카테고리: $category")
        }
    }
}
```

`@Value`로 흩어졌던 세 개의 주입이 **`bookProperties` 하나**로 정리됐습니다. 오타 위험도 사라지고, IDE 자동완성으로 `bookProperties.` 만 치면 사용 가능한 설정이 다 뜹니다.

## 4. 설정값 검증하기

설정값도 잘못 들어올 수 있습니다(예: 페이지 크기에 음수). properties 클래스에 **`@Validated`** 와 Jakarta 제약 애너테이션을 붙이면, 애플리케이션 **시작 시점에** 설정을 검증할 수 있습니다.

```kotlin
package com.example.bookapi.config

import jakarta.validation.constraints.Min
import jakarta.validation.constraints.NotBlank
import org.springframework.boot.context.properties.ConfigurationProperties
import org.springframework.validation.annotation.Validated

@Validated
@ConfigurationProperties(prefix = "app.book")
data class BookProperties(
    @field:Min(1)
    val defaultPageSize: Int = 20,

    @field:NotBlank
    val currency: String = "KRW",

    val recommendationEnabled: Boolean = false,
    val allowedCategories: List<String> = emptyList(),
)
```

여기서도 Kotlin의 **`@field:`** use-site target이 똑같이 필요합니다(01번 문서 3절 참고). 검증에 실패하면 애플리케이션이 시작되지 못하고 명확한 에러로 멈춥니다 — 잘못된 설정으로 운영에 배포되는 사고를 **부팅 단계에서** 막아 주는 셈입니다.

> [!TIP]
> 잘못된 설정은 런타임 한참 뒤가 아니라 시작 시점에 터지는 게 좋습니다. "빨리 실패하라(fail fast)" 원칙입니다.

## 5. `@Value` vs `@ConfigurationProperties`

둘의 차이를 정리하면 다음과 같습니다.

| 항목 | `@Value` | `@ConfigurationProperties` |
|------|----------|---------------------------|
| 대상 | 단일 값 | 관련 설정 묶음 (계층 구조) |
| 타입 안전 | 약함 (문자열 키 + 수동 변환) | 강함 (클래스 필드 타입) |
| 느슨한 바인딩 | 미지원 (키 정확히 일치해야) | 지원 (케밥/카멜/환경변수) |
| 검증 | 어려움 | `@Validated` + 제약으로 쉬움 |
| 복잡한 타입 (List, Map, 중첩) | 번거로움 | 자연스럽게 바인딩 |
| IDE 자동완성/메타데이터 | 약함 | 강함 (메타데이터 생성 시) |
| SpEL 표현식 | 지원 | 미지원 |

**결론: 그룹화된 설정에는 `@ConfigurationProperties`를 쓰세요.** `@Value`는 정말 단발성인 한 개 값, 또는 SpEL 표현식(`#{...}`)이 필요할 때만 제한적으로 사용합니다.

## 6. IDE 메타데이터 — configuration-processor

`@ConfigurationProperties` 클래스에 대한 메타데이터를 생성하면, IDE가 `application.yml`을 편집할 때 **자동완성과 문서 툴팁**을 띄워 줍니다. 이를 위해 애너테이션 프로세서를 추가합니다.

```kotlin
// build.gradle.kts
dependencies {
    // ...
    kapt("org.springframework.boot:spring-boot-configuration-processor")
    // 또는 KSP 사용 시:
    // ksp("org.springframework.boot:spring-boot-configuration-processor")
}
```

Kotlin에서는 `annotationProcessor` 대신 **`kapt`** 또는 더 빠른 **`ksp`** 로 등록합니다(해당 Gradle 플러그인이 적용돼 있어야 합니다). 빌드하면 `META-INF/spring-configuration-metadata.json`이 생성되어, `app.book.default-page-size`를 타이핑할 때 IDE가 키와 타입, 기본값을 제안해 줍니다.

> [!NOTE]
> configuration-processor는 **선택 사항**입니다. 없어도 바인딩은 정상 동작하며, 오직 IDE 편의를 위한 것입니다. 빌드 속도가 신경 쓰이면 kapt보다 ksp를 권장합니다.

## 다음 단계

이로써 Phase 4를 마칩니다. 입력 검증, 전역 예외 처리, 외부화된 설정과 타입 안전한 설정 바인딩까지 — API를 견고하게 만드는 기반을 모두 갖췄습니다. 다음 Phase 5부터는 Spring Boot 4의 실전 기능을 다룹니다. 첫 주제는 선언적 HTTP 클라이언트입니다.

→ [선언적 HTTP 클라이언트](../phase-5-production-features/01-http-interface-client.md)
