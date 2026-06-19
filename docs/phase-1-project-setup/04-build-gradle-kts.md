# build.gradle.kts 해부

`build.gradle.kts`는 Gradle의 **Kotlin DSL** 빌드 스크립트입니다. Kotlin 개발자라면 문법 자체는 친숙할 것입니다. 다만 Spring Boot 프로젝트에는 **kotlin-spring 플러그인, 스타터 의존성, JSR-305 엄격 모드** 같은 Spring/Kotlin 특화 설정이 들어갑니다. 이 페이지에서 한 줄씩 해부합니다.

## 1. 전체 build.gradle.kts

Initializr가 생성한 것을 가이드 기준으로 정리한 전체 파일입니다.

```kotlin
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    // Kotlin JVM 컴파일 지원
    kotlin("jvm") version "2.3.21"
    // kotlin-spring: @Component/@Configuration 등 Spring 어노테이션이 붙은 클래스를 자동 open
    kotlin("plugin.spring") version "2.3.21"
    // Spring Boot Gradle 플러그인: bootJar/bootRun, BOM 버전 관리 연동
    id("org.springframework.boot") version "4.1.0"
    // 의존성 버전을 Spring Boot BOM에 맞춰 자동 관리 (Initializr 기본 출력)
    id("io.spring.dependency-management") version "1.1.7"
}

group = "com.example"
version = "0.0.1-SNAPSHOT"

// JDK 21 툴체인: 빌드/실행에 사용할 JDK를 고정
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

repositories {
    mavenCentral()
}

dependencies {
    // --- 웹/REST: 내장 Tomcat, Spring MVC, Jackson 포함 ---
    implementation("org.springframework.boot:spring-boot-starter-web")
    // --- JPA/Hibernate ---
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    // --- Bean Validation (@Valid, @NotNull 등) ---
    implementation("org.springframework.boot:spring-boot-starter-validation")
    // --- Actuator: /actuator/health 등 운영 엔드포인트 ---
    implementation("org.springframework.boot:spring-boot-starter-actuator")

    // --- Kotlin 지원 ---
    // Jackson이 Kotlin data class를 (기본 생성자 없이) 직렬화/역직렬화하도록
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")
    // Spring이 런타임 리플렉션을 사용하므로 필수
    implementation("org.jetbrains.kotlin:kotlin-reflect")

    // --- 런타임 전용: H2 인메모리 DB ---
    runtimeOnly("com.h2database:h2")

    // --- 테스트 ---
    // JUnit5, AssertJ, Mockito, MockMvc 등을 한 번에 제공
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    // JUnit Platform 런처 (테스트 실행에 필요)
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}

kotlin {
    compilerOptions {
        // JSR-305 어노테이션(@Nullable 등)을 엄격하게 해석 → 플랫폼 타입을 null 안전 타입으로
        freeCompilerArgs.addAll("-Xjsr305=strict")
        jvmTarget = JvmTarget.JVM_21
    }
}

tasks.withType<Test> {
    // JUnit 5(JUnit Platform)로 테스트 실행
    useJUnitPlatform()
}
```

## 2. plugins 블록

| 플러그인 | 역할 |
| --- | --- |
| `kotlin("jvm")` | Kotlin 소스를 JVM 바이트코드로 컴파일 |
| `kotlin("plugin.spring")` | **kotlin-spring** — Spring 어노테이션 클래스를 자동으로 `open` 처리 |
| `org.springframework.boot` | `bootJar`, `bootRun` 태스크 제공, 실행 가능 Jar 패키징 |
| `io.spring.dependency-management` | 의존성 버전을 Spring Boot BOM에 맞춰 자동 정렬 |

> 💡 Kotlin 버전 `2.3.21`은 Spring Boot 4.1.0 BOM이 관리하는 버전과 일치시킨 값입니다. 임의의 다른 버전으로 바꾸지 마세요.

### kotlin-spring(allOpen) 플러그인이 필요한 이유

Kotlin 클래스는 **기본이 `final`** 입니다. 그런데 Spring은 `@Configuration`, `@Service`, `@Transactional` 등에서 **CGLIB 프록시**를 만들기 위해 클래스를 상속(서브클래싱)해야 합니다. `final` 클래스는 상속할 수 없으므로 문제가 됩니다.

`kotlin("plugin.spring")`은 내부적으로 **allOpen** 플러그인을 적용해, 아래 Spring 어노테이션이 붙은 클래스/멤버를 컴파일 시 자동으로 `open`으로 만들어 줍니다.

```
@Component @Async @Transactional @Cacheable @SpringBootTest
(@Configuration, @Service, @Repository, @Controller 등은 @Component 메타 어노테이션)
```

덕분에 개발자가 일일이 `open class`를 붙이지 않아도 됩니다.

> 💡 나중에 JPA 엔티티를 만들 때는 `kotlin("plugin.jpa")`도 추가합니다. 이는 **noArg** 플러그인을 적용해 `@Entity` 클래스에 JPA가 요구하는 **매개변수 없는 기본 생성자**를 만들어 줍니다. (Phase에서 JPA를 다룰 때 추가 예정)

## 3. group / version / java 툴체인

```kotlin
group = "com.example"
version = "0.0.1-SNAPSHOT"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}
```

- `group`, `version`은 산출물 좌표입니다. (`com.example:book-api:0.0.1-SNAPSHOT`)
- **툴체인(toolchain)** 은 빌드 머신의 기본 JDK와 무관하게, Gradle이 **JDK 21을 찾아(없으면 자동 다운로드)** 컴파일/실행에 사용하도록 고정합니다. 팀원 간 JDK 불일치를 방지합니다.

## 4. dependencies 블록

스타터(starter)는 **관련 라이브러리를 한 번에 묶은 의존성**입니다. 버전은 `dependency-management` 플러그인이 BOM에 맞춰 채워주므로 대부분 **버전을 적지 않습니다.**

| 구성 | 의미 |
| --- | --- |
| `implementation` | 컴파일·런타임 모두 필요 |
| `runtimeOnly` | 런타임에만 필요 (예: H2 드라이버) |
| `testImplementation` | 테스트 컴파일·런타임에 필요 |
| `testRuntimeOnly` | 테스트 런타임에만 필요 (예: JUnit 런처) |

핵심 의존성 요약:

- `spring-boot-starter-web`: REST 컨트롤러, 내장 **Tomcat 11.0.x(Servlet 6.1)**, Jackson.
- `spring-boot-starter-data-jpa`: Hibernate 기반 JPA.
- `spring-boot-starter-validation`: Bean Validation 구현체.
- `spring-boot-starter-actuator`: 헬스/메트릭 엔드포인트.
- `jackson-module-kotlin`: Kotlin `data class`를 기본 생성자 없이도 직렬화. **Kotlin + REST에서 사실상 필수.**
- `kotlin-reflect`: Spring의 런타임 리플렉션에 필요.
- `h2`: 인메모리 DB. `runtimeOnly`로 충분.

## 5. 컴파일러 옵션 — `-Xjsr305=strict`

```kotlin
kotlin {
    compilerOptions {
        freeCompilerArgs.addAll("-Xjsr305=strict")
        jvmTarget = JvmTarget.JVM_21
    }
}
```

Spring은 자바 코드에 JSR-305 nullability 어노테이션(`@NonNull`, `@Nullable`)을 광범위하게 붙여 두었습니다. `-Xjsr305=strict`를 켜면 Kotlin 컴파일러가 이 어노테이션을 **엄격하게** 해석합니다. 즉, 자바 API에서 넘어오는 값을 모호한 **플랫폼 타입**이 아니라 **정확한 null 가능/불가능 타입**으로 다뤄, Kotlin의 null 안전성 이점을 Spring API에서도 온전히 누릴 수 있습니다.

`jvmTarget = JVM_21`은 생성 바이트코드 타깃을 21로 맞춥니다.

## 6. tasks 블록

```kotlin
tasks.withType<Test> {
    useJUnitPlatform()
}
```

`useJUnitPlatform()`은 테스트를 **JUnit 5(JUnit Platform)** 로 실행하라는 지시입니다. `spring-boot-starter-test`가 JUnit 5를 가져오므로 짝을 맞춰야 합니다.

## 7. settings.gradle.kts

```kotlin
rootProject.name = "book-api"
```

루트 프로젝트 이름을 정합니다. 멀티 모듈로 확장하면 여기서 `include("module-a")` 식으로 하위 모듈을 추가합니다.

## 8. (대안) 버전 카탈로그

의존성 좌표/버전을 한곳에서 관리하고 싶다면 **버전 카탈로그**(`gradle/libs.versions.toml`)를 쓸 수 있습니다. 규모가 커지거나 멀티 모듈일 때 유용합니다.

```toml
# gradle/libs.versions.toml
[versions]
kotlin = "2.3.21"
springBoot = "4.1.0"

[plugins]
kotlin-jvm = { id = "org.jetbrains.kotlin.jvm", version.ref = "kotlin" }
spring-boot = { id = "org.springframework.boot", version.ref = "springBoot" }
```

```kotlin
// build.gradle.kts
plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.spring.boot)
}
```

> 💡 학습 단계에서는 Initializr 기본 출력(직접 명시) 그대로가 더 읽기 쉽습니다. 버전 카탈로그는 프로젝트가 커진 뒤 도입해도 늦지 않습니다.

## 다음 단계

빌드 스크립트를 이해했으니, [application.yml 설정](05-application-yml.md)에서 애플리케이션 외부 설정을 다룹니다.
