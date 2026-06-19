# 02. Kotlin + Gradle 설정

Querydsl을 쓰려면 **두 가지**가 필요합니다. (1) 런타임/컴파일 의존성, 그리고 (2) 엔티티로부터 **Q타입**(예: `QBook`)을 생성하는 **애너테이션 프로세서**. Kotlin에서 애너테이션 프로세서는 `kapt`로 구동합니다. 이 페이지에서는 완전한 `build.gradle.kts` 설정과 Q타입 생성 확인 방법을 다룹니다.

## 1. 좌표와 버전 (2026-06-20 검증)

본 부록은 OpenFeign 포크를 사용합니다. 검증한 좌표는 다음과 같습니다.

| 용도 | 좌표 | 비고 |
|---|---|---|
| JPA 모듈 | `io.github.openfeign.querydsl:querydsl-jpa:7.4.0:jakarta` | 런타임/컴파일, **`:jakarta` classifier 필수** |
| 애너테이션 프로세서 | `io.github.openfeign.querydsl:querydsl-apt:7.4.0:jakarta` | Q타입 생성, **`:jakarta` classifier 필수** |

> [!WARNING]
> **`:jakarta` classifier를 반드시 붙여야 합니다.** Spring Boot 3/4는 `javax.persistence`가 아니라 **`jakarta.persistence`** 패키지를 씁니다. classifier 없는 기본 artifact는 옛 `javax`용이라, Q타입이 잘못 생성되거나 컴파일이 깨집니다.

## 2. 왜 KSP가 아니라 kapt인가

Kotlin 생태계는 애너테이션 처리에서 `kapt` → **KSP**(Kotlin Symbol Processing)로 이동하는 추세이고, KSP가 더 빠릅니다. 하지만 **Querydsl은 KSP를 지원하지 않습니다.** Q타입 생성은 Java 애너테이션 프로세서로 작성되어 있어, Kotlin에서는 **반드시 `kapt`** 로 구동해야 합니다.

> [!WARNING]
> `kapt`는 현재 **유지보수 모드(maintenance mode)** 입니다. 신규 기능은 추가되지 않지만, Querydsl을 Kotlin에서 쓰는 **유일하게 지원되는 경로**이므로 그대로 사용합니다. "kapt가 deprecated 아니냐"는 걱정 때문에 KSP로 바꾸려 하지 마세요 — Querydsl에서는 동작하지 않습니다.

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

// Querydsl 버전을 한 곳에서 관리 (2026-06-20 기준 최신 7.4.0)
val querydslVersion = "7.4.0"

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.jetbrains.kotlin:kotlin-reflect")

    // ── Querydsl (OpenFeign 포크) ──────────────────────────────
    // JPA 모듈: :jakarta classifier 필수
    implementation("io.github.openfeign.querydsl:querydsl-jpa:$querydslVersion:jakarta")
    // 애너테이션 프로세서: kapt로 구동, :jakarta classifier 필수
    kapt("io.github.openfeign.querydsl:querydsl-apt:$querydslVersion:jakarta")
    // (선택) jakarta 애너테이션 — @Generated 등 참조용
    kapt("jakarta.annotation:jakarta.annotation-api")
    kapt("jakarta.persistence:jakarta.persistence-api")

    runtimeOnly("com.h2database:h2")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
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

## 다음 단계

설정이 끝났습니다. 이제 `QBook`으로 실제 쿼리를 작성해 봅시다.

→ [03. 기본 쿼리](03-basic-queries.md)
