# Bean Validation 입력 검증

지금까지의 `BookController`는 사용자가 보낸 데이터를 **무조건 믿었습니다.** 제목이 빈 문자열이든, 가격이 `-9999`든, ISBN이 `"hello"`든 그대로 받아 저장했죠. 실무에서는 절대 그래선 안 됩니다. 입력 검증은 보안과 데이터 무결성의 첫 번째 방어선입니다.

물론 Service 안에서 `if (request.title.isBlank()) throw ...` 식으로 직접 검증할 수도 있습니다. 하지만 이런 코드는 금방 지저분해지고 중복됩니다. Spring은 **선언적(declarative)** 으로 검증 규칙을 애너테이션으로 표현하는 표준 방식 — **Bean Validation (Jakarta Validation)** — 을 제공합니다.

## 1. Bean Validation이란

**Bean Validation**은 객체의 필드에 애너테이션으로 제약 조건(constraint)을 선언하면, 런타임에 그 규칙을 검사해 주는 **Jakarta EE 표준 명세**입니다. JPA가 그랬듯 이것 역시 명세일 뿐이고, 실제 구현체는 **Hibernate Validator**입니다(Hibernate ORM과는 별개의 라이브러리입니다).

- **명세**: `jakarta.validation.*` — `@NotNull`, `@Size`, `@Valid` 등
- **구현체**: Hibernate Validator
- **스타터**: `spring-boot-starter-validation` — 위 둘을 묶어 가져오고 Spring MVC와 통합

> [!NOTE]
> 과거 `javax.validation.*` 패키지는 Jakarta EE 이관으로 **`jakarta.validation.*`** 로 바뀌었습니다. Spring Boot 4.x는 전부 `jakarta` 네임스페이스를 씁니다.

먼저 의존성을 추가합니다. Spring Boot 4.x에서는 web 스타터만으로는 검증이 자동 포함되지 않으므로 명시적으로 추가해야 합니다.

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.springframework.boot:spring-boot-starter-validation") // ← 추가
}
```

## 2. 주요 제약 애너테이션

자주 쓰는 `jakarta.validation.constraints.*` 애너테이션을 정리하면 다음과 같습니다.

| 애너테이션 | 적용 대상 | 의미 |
|-----------|----------|------|
| `@NotNull` | 모든 타입 | `null`이 아니어야 함 (빈 문자열은 통과) |
| `@NotEmpty` | String, Collection, Map, 배열 | `null`도 아니고 비어 있지도 않음 |
| `@NotBlank` | String | `null`/빈 문자열/공백만 있는 문자열 모두 거부 |
| `@Size(min, max)` | String, Collection 등 | 길이/크기 범위 |
| `@Min` / `@Max` | 숫자 | 최소/최대값 (정수) |
| `@Positive` / `@PositiveOrZero` | 숫자 | 양수 / 0 이상 |
| `@Negative` / `@NegativeOrZero` | 숫자 | 음수 / 0 이하 |
| `@DecimalMin` / `@DecimalMax` | 숫자 | 소수 포함 경계값 |
| `@Pattern(regexp)` | String | 정규식 일치 |
| `@Email` | String | 이메일 형식 |
| `@Past` / `@PastOrPresent` | 날짜/시간 | 과거 / 과거·현재 |
| `@Future` / `@FutureOrPresent` | 날짜/시간 | 미래 / 미래·현재 |

> [!TIP]
> 문자열 필수값에는 거의 항상 `@NotBlank`를 쓰세요. `@NotNull`은 `""`(빈 문자열)을 통과시키고, `@NotEmpty`는 `" "`(공백)을 통과시킵니다. `@NotBlank`만이 셋 다 막습니다.

## 3. Kotlin의 함정 — 애너테이션 use-site target

여기는 Kotlin 개발자가 가장 자주 걸려 넘어지던 지점이고, **Kotlin 2.2 / Spring Boot 4에서 규칙이 바뀐** 곳이기도 합니다. 먼저 왜 문제가 생겼는지부터 봅니다.

Kotlin에서 `val title: String`을 생성자 프로퍼티로 선언하면, 컴파일러는 내부적으로 **생성자 파라미터(param)**, **필드(field)**, **getter** 를 함께 만들어 냅니다. 애너테이션을 아무 표시 없이 붙이면 예전 Kotlin은 그것을 **생성자 파라미터에만** 붙였습니다. 반면 Hibernate Validator는 필드/getter의 제약을 읽으므로, 애너테이션이 파라미터에만 남아 **검증이 조용히 통과**되는 사고가 났습니다.

```
@NotBlank val title  ──┐
                       │  Kotlin이 생성하는 요소들
                       ├──▶ constructor param   ← 예전 기본값: 여기에만 붙었다
                       ├──▶ private field        ← @field: 로 지정하면 여기 (검증기가 읽음)
                       └──▶ getter               ← @get: 로 지정
```

> [!NOTE]
> `jakarta.validation.constraints.*` 애너테이션은 Java로 정의돼 있어 Kotlin의 `property` 타깃을 허용하지 않습니다. 그래서 아래 옵션이 켜지면 실제로는 **파라미터 + 필드**에 적용되며(Kotlin은 프로퍼티 타깃이 불가능할 때 필드로 내립니다), 그 필드를 Hibernate Validator가 읽어 검증이 동작합니다.

### 해법 ① 컴파일러 옵션 (Spring Boot 4 + Kotlin 2.2+ 기본)

Kotlin 2.2는 이 불편을 없애는 옵션을 도입했고, **Spring Initializr가 Kotlin 프로젝트에 기본으로 넣어 줍니다**([Phase 1-4](../phase-1-project-setup/04-build-gradle-kts.md)).

```kotlin
// build.gradle.kts — Initializr 기본 출력
kotlin {
    compilerOptions {
        freeCompilerArgs.addAll(
            "-Xjsr305=strict",
            "-Xannotation-default-target=param-property",   // ← 이것
        )
    }
}
```

이 옵션이 켜져 있으면 애너테이션이 **생성자 파라미터와 프로퍼티(프로퍼티 타깃을 못 쓰는 Java 정의 애너테이션은 필드)에 함께** 적용되어, Hibernate Validator와 Jackson이 정상적으로 인식합니다. 즉 아래처럼 Java와 똑같이 써도 검증이 동작합니다.

```kotlin
// ✅ -Xannotation-default-target=param-property 가 켜져 있으면 이대로 동작
data class CreateBookRequest(
    @NotBlank val title: String,
    @NotBlank val author: String,
)
```

### 해법 ② `@field:` 명시 (옵션과 무관하게 항상 안전)

use-site target을 직접 적어 주는 방식은 컴파일러 옵션 유무와 무관하게 언제나 동작합니다.

```kotlin
// ✅ 어떤 설정에서도 안전한 방식
data class CreateBookRequest(
    @field:NotBlank val title: String,
    @field:NotBlank val author: String,
)
```

> [!NOTE]
> 이 규칙은 Kotlin **2.4.0부터 언어 기본값으로 안정화**되어, 그때부터는 옵션 없이도 동일하게 동작합니다. 본 가이드의 기준인 Kotlin 2.3.21(Spring Boot 4.1 BOM 관리 버전)에서는 위 옵션이 필요하며, Initializr가 이미 넣어 줍니다.

> [!TIP]
> **본 가이드는 `@field:`를 계속 사용합니다.** 이유는 두 가지입니다. (1) 빌드 설정에 의존하지 않아 코드만 보고 의도가 분명하고, (2) 옵션이 빠진 기존 프로젝트에 코드를 옮겨 붙여도 검증이 조용히 사라지지 않습니다. 팀이 Initializr 기본 설정을 쓰고 있다면 `@field:`를 생략하는 쪽이 더 깔끔하니, 컨벤션을 정해 한 방향으로 통일하세요.
>
> 반대로 **컴파일러 옵션도 없고 `@field:`도 없다면 검증이 아무 경고 없이 통과**됩니다. 검증 테스트를 반드시 한 건 작성해 이 사고를 잡으세요([Phase 5-4](../phase-5-production-features/04-testing.md)의 400 응답 테스트).

## 4. CreateBookRequest에 검증 적용하기

이제 Phase 2에서 만든 DTO에 실제 규칙을 입혀 봅시다.

```kotlin
package com.example.bookapi.dto

import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.PastOrPresent
import jakarta.validation.constraints.Pattern
import jakarta.validation.constraints.Positive
import jakarta.validation.constraints.Size
import java.time.LocalDate

data class CreateBookRequest(
    // 제목: 필수, 1~200자
    @field:NotBlank(message = "제목은 필수입니다")
    @field:Size(max = 200, message = "제목은 200자를 넘을 수 없습니다")
    val title: String,

    // 저자: 필수
    @field:NotBlank(message = "저자는 필수입니다")
    val author: String,

    // ISBN-13: 하이픈 포함/미포함 13자리 숫자 패턴
    @field:Pattern(
        regexp = "^(?:\\d[- ]?){12}\\d$",
        message = "ISBN은 13자리 형식이어야 합니다",
    )
    val isbn: String,

    // 가격: 양수만 허용
    @field:Positive(message = "가격은 0보다 커야 합니다")
    val price: Int,

    // 출판일: 미래일 수 없음 (오늘까지 허용)
    @field:PastOrPresent(message = "출판일은 미래일 수 없습니다")
    val publishedAt: LocalDate,
)
```

`UpdateBookRequest`도 같은 방식으로 적용합니다. 부분 수정(PATCH)이라 필드가 nullable이라면 `@field:NotBlank` 대신 nullable 타입에 제약을 거는데, 이때 `null`은 대부분의 제약을 **통과**한다는 점을 기억하세요(`@NotNull`만 막음). 즉 "값이 들어왔다면 검증, 안 들어왔으면 패스"가 자연스럽게 표현됩니다.

## 5. 컨트롤러에서 `@Valid`로 검증 트리거

DTO에 규칙을 선언만 한다고 검증이 자동으로 일어나지는 않습니다. 컨트롤러 메서드에서 **`@Valid`** 를 `@RequestBody` 앞에 붙여 검증을 발동시켜야 합니다.

```kotlin
package com.example.bookapi.controller

import com.example.bookapi.dto.CreateBookRequest
import com.example.bookapi.service.BookService
import jakarta.validation.Valid
import org.springframework.http.HttpStatus
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/api/books")
class BookController(
    private val bookService: BookService,
) {
    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    fun create(
        @Valid @RequestBody request: CreateBookRequest, // ← @Valid 가 검증을 발동
    ): BookResponse = bookService.create(request)
}
```

이제 검증에 실패하면 Spring은 **`MethodArgumentNotValidException`** 을 던집니다. 별도 처리를 하지 않으면 Spring Boot 기본 동작에 따라 **HTTP 400 Bad Request** 가 응답됩니다. 다음 문서([전역 예외 처리](02-exception-handling.md))에서 이 예외를 잡아 깔끔한 에러 JSON으로 바꾸는 법을 다룹니다.

> [!NOTE]
> `@Valid`(`jakarta.validation`)와 `@Validated`(`org.springframework.validation`)는 비슷하지만 다릅니다. `@Valid`는 표준이고 중첩 객체 검증을 지원합니다. `@Validated`는 Spring 전용으로 **검증 그룹(groups)** 과 메서드 파라미터 검증을 지원합니다(아래 6, 7절).

## 6. 경로 변수 · 쿼리 파라미터 검증

`@RequestBody` 객체가 아니라 단일 경로 변수나 쿼리 파라미터에 제약을 걸려면, 컨트롤러 **클래스에 `@Validated`** 를 붙이고 파라미터에 직접 제약 애너테이션을 답니다.

```kotlin
import org.springframework.validation.annotation.Validated
import jakarta.validation.constraints.Min
import jakarta.validation.constraints.Positive

@RestController
@RequestMapping("/api/books")
@Validated // ← 메서드 파라미터 레벨 검증 활성화
class BookController(/* ... */) {

    @GetMapping("/{id}")
    fun findById(
        @PathVariable @Positive id: Long, // id는 양수여야 함
    ): BookResponse = bookService.findById(id)

    @GetMapping
    fun list(
        @RequestParam(defaultValue = "0") @Min(0) page: Int,
        @RequestParam(defaultValue = "20") @Min(1) size: Int,
    ): List<BookResponse> = bookService.findAll(page, size)
}
```

> [!TIP]
> 클래스에 `@Validated`가 없으면 `@PathVariable @Positive id`의 제약은 **조용히 무시**됩니다. 파라미터 레벨 검증 실패 시에는 `MethodArgumentNotValidException`이 아니라 **`HandlerMethodValidationException`** 이 던져집니다(Spring 6.1+). 예외 처리 시 둘 다 고려하세요.

## 7. 커스텀 검증기 만들기

표준 애너테이션으로 표현하기 어려운 규칙은 직접 만들 수 있습니다. 예로, ISBN-13의 **체크섬(checksum)** 까지 검증하는 `@Isbn` 애너테이션을 정의해 봅시다.

먼저 애너테이션을 선언합니다.

```kotlin
package com.example.bookapi.validation

import jakarta.validation.Constraint
import jakarta.validation.Payload
import kotlin.reflect.KClass

@Target(AnnotationTarget.FIELD)
@Retention(AnnotationRetention.RUNTIME)
@Constraint(validatedBy = [IsbnValidator::class]) // ← 실제 검증 로직 연결
annotation class Isbn(
    val message: String = "유효하지 않은 ISBN-13입니다",
    val groups: Array<KClass<*>> = [],
    val payload: Array<KClass<out Payload>> = [],
)
```

`message`, `groups`, `payload` 세 멤버는 Bean Validation 명세가 **요구하는 필수 요소**입니다. 빠뜨리면 안 됩니다.

다음으로 `ConstraintValidator`를 구현합니다.

```kotlin
package com.example.bookapi.validation

import jakarta.validation.ConstraintValidator
import jakarta.validation.ConstraintValidatorContext

class IsbnValidator : ConstraintValidator<Isbn, String> {
    override fun isValid(value: String?, context: ConstraintValidatorContext): Boolean {
        // null은 통과시킨다 (필수 여부는 @NotBlank 가 따로 책임진다)
        if (value == null) return true

        val digits = value.filter { it.isDigit() }
        if (digits.length != 13) return false

        // ISBN-13 체크섬: 가중치 1,3 을 번갈아 곱한 합이 10의 배수
        val sum = digits.mapIndexed { index, ch ->
            val d = ch.digitToInt()
            if (index % 2 == 0) d else d * 3
        }.sum()
        return sum % 10 == 0
    }
}
```

이제 DTO에서 `@field:Pattern` 대신 또는 함께 `@field:Isbn`을 사용할 수 있습니다.

```kotlin
@field:Isbn
val isbn: String,
```

검증기 안에서 다른 Bean(예: DB 중복 체크용 Repository)을 주입받고 싶다면, `ConstraintValidator`도 Spring Bean으로 등록되므로 생성자 주입이 가능합니다.

## 8. 검증 그룹 (간단 소개)

같은 DTO를 상황마다 다르게 검증하고 싶을 때 **검증 그룹**을 씁니다. 예를 들어 "생성 시에는 id가 없어야 하고, 수정 시에는 id가 있어야 한다" 같은 경우입니다.

```kotlin
interface OnCreate
interface OnUpdate

data class BookForm(
    @field:Null(groups = [OnCreate::class])
    @field:NotNull(groups = [OnUpdate::class])
    val id: Long?,

    @field:NotBlank // 그룹 미지정 → 기본 그룹(Default)
    val title: String,
)
```

컨트롤러에서는 `@Validated(OnCreate::class)` 처럼 그룹을 지정해 검증합니다(이때는 `@Valid`가 아니라 `@Validated`를 사용). 그룹은 강력하지만 복잡도를 키우므로, **대부분의 경우 DTO를 생성용/수정용으로 분리하는 편이 더 단순**합니다. 우리 예제처럼 `CreateBookRequest`와 `UpdateBookRequest`를 따로 두는 것이 그 예입니다.

## 다음 단계

검증에 실패하면 예외가 던져진다는 것을 확인했습니다. 이제 그 예외(와 그 밖의 모든 예외)를 한곳에서 잡아 일관된 에러 응답으로 바꾸는 방법을 배웁니다.

→ [전역 예외 처리](02-exception-handling.md)
