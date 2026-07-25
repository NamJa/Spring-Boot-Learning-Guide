# 02. Kotlin + Gradle 설정

Querydsl을 쓰려면 **두 가지**가 필요합니다. (1) 런타임/컴파일 의존성, 그리고 (2) 엔티티로부터 **Q타입**(예: `QBook`)을 생성하는 **애너테이션 프로세서**. Kotlin에서 애너테이션 프로세서는 `kapt`로 구동합니다. 이 페이지에서는 완전한 `build.gradle.kts` 설정과 Q타입 생성 확인 방법을 다룹니다.

## 1. 좌표와 버전 (2026-07-25 검증)

본 부록은 OpenFeign 포크를 사용합니다. Maven Central의 실제 아티팩트 목록으로 확인한 좌표는 다음과 같습니다(최신 버전 **7.5**, 2026-07-21 릴리스).

| 용도 | 좌표 | 비고 |
|---|---|---|
| JPA 모듈 | `io.github.openfeign.querydsl:querydsl-jpa:7.5` | 런타임/컴파일. **classifier 없음** |
| 애너테이션 프로세서(kapt) | `io.github.openfeign.querydsl:querydsl-apt:7.5:jakarta` | Q타입 생성. **`:jakarta` classifier 필요** |
| (대안) KSP 코드젠 | `io.github.openfeign.querydsl:querydsl-ksp-codegen:7.5` | KSP로 Q타입 생성. classifier 없음 |

> [!WARNING]
> **`querydsl-jpa`에는 `:jakarta` classifier를 붙이지 마세요.** Querydsl 7.x의 `querydsl-jpa` 메인 아티팩트는 이미 `jakarta.persistence-api`에 의존하는 Jakarta 전용이고, `:jakarta` classifier 파일 **자체가 존재하지 않습니다**(`querydsl-jpa-7.5-jakarta.jar` → 404). 옛 안내를 따라 classifier를 붙이면 의존성 해석 단계에서 빌드가 실패합니다.
>
> 반대로 **`querydsl-apt`는 `:jakarta` classifier가 필요합니다.** classifier 없는 기본 `querydsl-apt` jar에는 애너테이션 프로세서 등록 파일(`META-INF/services/javax.annotation.processing.Processor`)이 아예 없어서, 넣어도 **Q타입이 하나도 생성되지 않고 조용히 넘어갑니다.** `:jakarta`(또는 `:jpa`) classifier jar가 `JPAAnnotationProcessor`를 등록합니다. **"jpa는 classifier 없이, apt는 jakarta로"** 라고 기억하세요.

## 2. Q타입 생성기: kapt와 KSP

Kotlin 생태계는 애너테이션 처리에서 `kapt` → **KSP**(Kotlin Symbol Processing)로 이동하는 추세이고, KSP가 더 빠릅니다. Querydsl(OpenFeign 포크)에는 **두 경로가 모두** 있습니다.

| 경로 | 아티팩트 | 생성 결과 | 특징 |
|---|---|---|---|
| **kapt** (본 부록 기준) | `querydsl-apt:7.5:jakarta` | Java Q타입(`QBook.java`) | 오래 검증된 경로, 자료가 가장 많음 |
| **KSP** | `querydsl-ksp-codegen:7.5` | Kotlin Q타입 | 빌드가 빠르고 Kotlin에 자연스러움 |

본문은 자료와 검증 사례가 많은 **kapt**로 설명하고, KSP 설정은 이 페이지 마지막 **7절**에 정리했습니다.

> [!NOTE]
> `kapt`는 **유지보수 모드(maintenance mode)** 입니다. 신규 기능은 추가되지 않으므로, 빌드 속도가 중요하거나 새로 시작하는 프로젝트라면 KSP 경로를 검토할 만합니다. 다만 KSP 코드젠은 생성 결과가 Kotlin 코드라 세부 API가 kapt 결과와 다를 수 있으니, 도입 전 작은 범위에서 검증하세요.

## 3. 완전한 build.gradle.kts 발췌

```groovy
plugins {
    id("org.springframework.boot") version "4.1.0"
    id("io.spring.dependency-management") version "1.1.7"
    kotlin("jvm") version "2.3.21"
    kotlin("plugin.spring") version "2.3.21"
    kotlin("plugin.jpa") version "2.3.21"
    kotlin("kapt") version "2.3.21"          // ← Querydsl Q타입 생성을 위한 kapt 플러그인
}

group = "com.example"
version = "0.0.1-SNAPSHOT"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)   // JDK 21
    }
}

repositories {
    mavenCentral()
}

// Querydsl 버전을 한 곳에서 관리 (2026-07-25 기준 최신 7.5)
val querydslVersion = "7.5"

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-webmvc")
    implementation("org.jetbrains.kotlin:kotlin-reflect")

    // ── Querydsl (OpenFeign 포크) ──────────────────────────────
    // JPA 모듈: classifier 없음 (7.x 메인 아티팩트가 이미 jakarta 전용)
    implementation("io.github.openfeign.querydsl:querydsl-jpa:$querydslVersion")
    // 애너테이션 프로세서: kapt로 구동, :jakarta classifier 필요
    kapt("io.github.openfeign.querydsl:querydsl-apt:$querydslVersion:jakarta")
    // (선택) jakarta 애너테이션 — @Generated 등 참조용
    kapt("jakarta.annotation:jakarta.annotation-api")
    kapt("jakarta.persistence:jakarta.persistence-api")

    runtimeOnly("com.h2database:h2")

    testImplementation("org.springframework.boot:spring-boot-starter-data-jpa-test")
}

tasks.withType<Test> {
    useJUnitPlatform()
}
```

> [!TIP]
> `querydsl-jpa`는 `implementation`, `querydsl-apt`는 `kapt`로 선언한다는 점을 헷갈리지 마세요. `apt`를 `implementation`에 넣으면 Q타입이 **생성되지 않고**, `jpa`를 `kapt`에만 넣으면 런타임에 클래스를 찾지 못합니다.

## 4. JPAQueryFactory 빈 등록

Querydsl 쿼리는 `JPAQueryFactory`를 통해 실행합니다. 이 객체는 `EntityManager`가 필요하므로, 스프링 빈으로 등록해 어디서든 주입받게 합니다.

```kotlin
package com.example.bookapi.config

import com.querydsl.jpa.impl.JPAQueryFactory
import jakarta.persistence.EntityManager
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

@Configuration
class QuerydslConfig {

    // EntityManager를 주입받아 JPAQueryFactory 빈을 생성한다.
    // 이 팩토리가 모든 Querydsl 쿼리의 진입점이 된다.
    @Bean
    fun jpaQueryFactory(entityManager: EntityManager): JPAQueryFactory {
        return JPAQueryFactory(entityManager)
    }
}
```

> [!TIP]
> 패키지 이름은 `com.querydsl.jpa.impl.JPAQueryFactory`로 **그대로** 유지됩니다. group id는 `io.github.openfeign.querydsl`로 바뀌었지만, **클래스의 패키지명(`com.querydsl.*`)은 호환성을 위해 그대로**입니다. import 문에서 `io.github.openfeign`을 찾지 마세요.

이렇게 등록하면 리포지토리나 서비스에서 생성자 주입으로 사용할 수 있습니다.

```kotlin
@Repository
class BookQueryRepository(
    private val queryFactory: JPAQueryFactory,   // 빈 주입
) {
    // ... 쿼리 메서드들
}
```

## 5. Q타입 생성 확인

설정이 끝나면 엔티티(`Book`)로부터 `QBook`이 생성되는지 확인해야 합니다.

```bash
# kapt를 실행해 Q타입만 생성
./gradlew kaptKotlin

# 또는 전체 빌드
./gradlew build
```

생성된 Q타입은 다음 경로에 위치합니다.

```
build/
└── generated/
    └── source/
        └── kapt/
            └── main/
                └── com/example/bookapi/
                    └── QBook.java     ← 생성된 Q타입
```

```
[프로젝트]
   src/main/kotlin/.../Book.kt   (작성)
            │  kapt + querydsl-apt
            ▼
   build/generated/source/kapt/main/.../QBook.java   (자동 생성)
            │  컴파일
            ▼
   QBook.book  ← 코드에서 사용
```

`QBook`이 보이면 성공입니다. 코드에서는 보통 미리 만들어진 정적 인스턴스를 씁니다.

```kotlin
val book = QBook.book          // 권장: 기본 인스턴스 사용
// val book = QBook("b")       // 별칭이 필요할 때(자기 조인 등)만 직접 생성
```

## 6. Kotlin + kapt 주의점

| 증상 | 원인 | 해결 |
|---|---|---|
| `QBook`을 못 찾음 (IDE 빨간 줄) | 빌드를 안 돌려 Q타입 미생성 | `./gradlew kaptKotlin` 후 IDE의 Gradle 새로고침 |
| 빌드가 느려짐 | kapt는 Java stub을 거쳐 처리 → 오버헤드 | 개발 중엔 변경된 모듈만 빌드, CI에서 캐시 활용 |
| 엔티티 수정 후 옛 필드가 남음 | 이전 Q타입이 캐시됨 | `./gradlew clean kaptKotlin`으로 재생성 |
| IDE가 생성 경로를 소스로 인식 못 함 | 생성 디렉터리 미등록 | IntelliJ는 보통 자동 인식. 안 되면 Gradle 프로젝트 재import |

> [!TIP]
> **IDE 인식 문제는 신규 도입 시 가장 흔한 막힘 지점입니다.** `QBook`이 빨갛게 떠도 당황하지 말고, 먼저 빌드를 돌려 `build/generated/...`에 파일이 실제로 생겼는지 확인한 뒤 IDE를 새로고침하세요. 파일이 있는데 IDE만 못 보는 경우가 대부분입니다.

## 7. (대안) KSP로 Q타입 생성하기

kapt가 유지보수 모드라는 점이 신경 쓰이거나 빌드 속도를 개선하고 싶다면, OpenFeign 포크가 제공하는 **KSP 코드젠**(`querydsl-ksp-codegen`)을 쓸 수 있습니다. kapt 대신 KSP 플러그인을 적용하고, 프로세서 의존성을 `ksp(...)`로 선언합니다.

```kotlin
plugins {
    id("org.springframework.boot") version "4.1.0"
    id("io.spring.dependency-management") version "1.1.7"
    kotlin("jvm") version "2.3.21"
    kotlin("plugin.spring") version "2.3.21"
    kotlin("plugin.jpa") version "2.3.21"
    id("com.google.devtools.ksp") version "2.3.10"   // kapt 대신 KSP
}

val querydslVersion = "7.5"

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("io.github.openfeign.querydsl:querydsl-jpa:$querydslVersion")
    // Kotlin Q타입을 생성하는 KSP 프로세서 (classifier 없음)
    ksp("io.github.openfeign.querydsl:querydsl-ksp-codegen:$querydslVersion")
}

// (선택) 생성 경로를 소스셋에 명시 — KSP 플러그인이 보통 자동으로 엮어 주므로
// 컴파일에는 필요 없고, IDE가 생성 코드를 못 볼 때만 넣으면 됩니다.
kotlin {
    sourceSets.main {
        kotlin.srcDir("build/generated/ksp/main/kotlin")
    }
}
```

```bash
./gradlew kspKotlin      # Q타입 생성
# 결과: build/generated/ksp/main/kotlin/com/example/bookapi/QBook.kt
```

| 항목 | kapt | KSP |
|---|---|---|
| 생성 파일 | `build/generated/source/kapt/main/**/QBook.java` | `build/generated/ksp/main/kotlin/**/QBook.kt` |
| 빌드 속도 | 느림(Java stub 생성 단계) | 빠름 |
| 태스크 | `kaptKotlin` | `kspKotlin` |
| 성숙도 | 사실상 표준, 자료 풍부 | 비교적 새로움 |

> [!NOTE]
> **KSP 버전 표기 주의**: KSP는 **2.3.0부터 Kotlin 버전과 분리된 독립 버전 체계**를 씁니다(예전 `2.2.21-2.0.5` 형식 → 지금은 `2.3.10`). 따라서 플러그인 버전이 내 Kotlin 버전과 숫자가 달라도 정상이며, 2026-07-25 기준 최신인 **2.3.10**이 Kotlin 2.3.21에서 문제없이 동작합니다.
>
> KSP 코드젠은 Kotlin Q타입을 생성하지만 `@QueryProjection`을 지원하고 `QBook.book` 같은 기본 인스턴스도 함께 만들어 주므로, 본 부록 이후의 예제 코드는 kapt/KSP 어느 쪽에서도 대부분 그대로 동작합니다. 도입 시 `./gradlew kspKotlin`으로 Q타입이 기대대로 생성되는지 한 번 확인하세요.

## 다음 단계

설정이 끝났습니다. 이제 `QBook`으로 실제 쿼리를 작성해 봅시다.

→ [03. 기본 쿼리](03-basic-queries.md)
