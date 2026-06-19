# 자동 설정과 스타터

Spring Boot로 프로젝트를 만들면 `@SpringBootApplication` 하나 붙이고 `runApplication`만 호출했는데 웹 서버가 뜨고, DB가 연결되고, JSON 직렬화까지 됩니다. 이 "마법"의 정체가 바로 **자동 설정(auto-configuration)** 과 **스타터(starter)** 입니다. 이 둘을 이해하면 Spring Boot가 더 이상 마법이 아니라 **예측 가능한 도구**가 됩니다.

## 1. @SpringBootApplication 해부

모든 Spring Boot 앱의 출발점인 이 어노테이션은 사실 **세 개의 어노테이션을 합친 것**입니다.

```kotlin
@SpringBootApplication // = 아래 세 개의 합성
class BookApiApplication

// @SpringBootApplication 은 내부적으로:
// @SpringBootConfiguration  (= @Configuration)
// @EnableAutoConfiguration
// @ComponentScan
```

| 구성 어노테이션 | 역할 |
| --- | --- |
| `@SpringBootConfiguration` | 이 클래스 자체가 설정 클래스(`@Configuration`)임을 표시 |
| `@ComponentScan` | **이 클래스가 속한 패키지 이하**를 스캔해 `@Component`/`@Service` 등을 Bean으로 등록 |
| `@EnableAutoConfiguration` | 클래스패스를 보고 **자동 설정을 활성화** — 핵심 |

> **WARNING**: `@ComponentScan`은 메인 클래스가 위치한 패키지부터 하위만 스캔합니다. `com.example.bookapi`에 메인 클래스를 두면 그 하위 패키지(`controller`, `service`, `repository`)는 자동 스캔되지만, **상위나 형제 패키지의 컴포넌트는 발견되지 않습니다.** 그래서 메인 클래스를 최상위 기본 패키지에 두는 것이 관례입니다.

## 2. 자동 설정 메커니즘

`@EnableAutoConfiguration`은 "클래스패스에 X가 있고, 사용자가 직접 Y를 만들지 않았다면, 합리적인 기본 Bean을 대신 등록"하는 일을 합니다. 어떻게 동작하는지 단계별로 봅시다.

### 2.1 AutoConfiguration.imports

각 스타터(또는 라이브러리) jar 안에는 다음 파일이 들어 있습니다.

```
META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
```

이 파일에는 적용 후보가 되는 자동 설정 클래스들의 이름이 나열되어 있습니다. Spring Boot는 기동 시 이 목록을 모두 읽어 후보로 올린 뒤, **조건(condition)을 만족하는 것만 실제로 적용**합니다.

> 참고: 과거(Spring Boot 2.x 이전)에는 `spring.factories` 파일을 썼지만, 현재는 위의 `.imports` 파일이 표준입니다.

### 2.2 조건부 Bean — @Conditional 계열

자동 설정 클래스의 Bean에는 "이런 조건일 때만 만들어라"는 어노테이션이 붙습니다. 대표적인 것들입니다.

| 어노테이션 | 의미 |
| --- | --- |
| `@ConditionalOnClass` | 특정 클래스가 **클래스패스에 있을 때**만 적용 |
| `@ConditionalOnMissingClass` | 특정 클래스가 **없을 때**만 적용 |
| `@ConditionalOnBean` | 특정 Bean이 **이미 등록돼 있을 때**만 적용 |
| `@ConditionalOnMissingBean` | 사용자가 같은 타입 Bean을 **직접 만들지 않았을 때**만 적용 (오버라이딩의 핵심) |
| `@ConditionalOnProperty` | 특정 프로퍼티 값일 때만 적용 |
| `@ConditionalOnWebApplication` | 웹 애플리케이션일 때만 적용 |

자동 설정 클래스를 흉내 낸 예시입니다.

```kotlin
@AutoConfiguration
class BookJsonAutoConfiguration {

    @Bean
    @ConditionalOnClass(name = ["com.fasterxml.jackson.databind.ObjectMapper"])
    @ConditionalOnMissingBean // 사용자가 ObjectMapper Bean을 안 만들었을 때만!
    fun objectMapper(): ObjectMapper = ObjectMapper().findAndRegisterModules()
}
```

핵심은 **`@ConditionalOnMissingBean`** 입니다. "기본값은 우리가 줄게. 하지만 네가 직접 만들면 네 것을 쓸게"라는 철학이 여기서 구현됩니다. 이것이 Spring Boot가 "관례를 따르면 자동, 원하면 언제든 재정의 가능"한 이유입니다.

```
클래스패스 스캔
      │
      ▼
.imports의 자동설정 후보 목록 로드
      │
      ▼
각 후보의 @Conditional 평가
      │
   조건 만족? ──No──▶ 건너뜀
      │ Yes
      ▼
사용자가 같은 Bean 등록했나? (@ConditionalOnMissingBean)
      │
   이미 있음 ──Yes──▶ 사용자 Bean 우선 (자동설정 양보)
      │ No
      ▼
자동설정 Bean 등록
```

## 3. 스타터(Starter)란

**스타터**는 특정 기능에 필요한 의존성들을 미리 묶어 둔 **편의용 의존성 패키지**입니다. 버전 충돌 걱정 없이 한 줄로 필요한 라이브러리 묶음을 가져옵니다. 예를 들어 `spring-boot-starter-web` 하나를 추가하면 Spring MVC, 내장 Tomcat, Jackson(JSON), 검증 기본기 등이 함께 따라옵니다.

```groovy
// build.gradle.kts (Gradle Kotlin DSL)
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}
```

> **TIP**: 버전 번호를 적지 않은 것에 주목하세요. Spring Boot **BOM(Bill of Materials)** 이 검증된 버전 조합을 관리하므로, 스타터를 추가할 때 버전을 신경 쓸 필요가 없습니다. 이것이 "의견이 반영된(opinionated)" 기본값의 한 예입니다.

### 3.1 자주 쓰는 스타터

| 스타터 | 제공 기능 |
| --- | --- |
| `spring-boot-starter-web` | Spring MVC, 내장 Tomcat, Jackson — 가장 기본 |
| `spring-boot-starter-data-jpa` | Spring Data JPA, Hibernate, 트랜잭션 |
| `spring-boot-starter-security` | Spring Security 7.0 기반 인증/인가 |
| `spring-boot-starter-validation` | Bean Validation(Jakarta Validation) |
| `spring-boot-starter-actuator` | 헬스 체크·메트릭 등 운영 엔드포인트 |
| `spring-boot-starter-test` | JUnit 5, Mockito, AssertJ, Spring Test |
| `spring-boot-starter-restclient` | 동기 HTTP 클라이언트(`RestClient`) — 4.x 신규 |
| `spring-boot-starter-webclient` | 리액티브 HTTP 클라이언트(`WebClient`) — 4.x 신규 |

> 본 가이드의 도서 API는 `web`, `data-jpa`, `validation`, `security`, `actuator`, `test` 정도를 사용하게 됩니다. 외부 API 연동이 필요해지면 `restclient`를 추가합니다.

## 4. 자동 설정 들여다보기

"왜 이 Bean이 만들어졌지? / 왜 안 만들어졌지?"를 알고 싶을 때, Spring Boot는 **조건 평가 보고서(Condition Evaluation Report)** 를 제공합니다. `--debug` 플래그로 켭니다.

```bash
java -jar build/libs/bookapi.jar --debug
```

또는 `application.yml`에서:

```yaml
debug: true
```

기동 로그에 다음과 같은 보고서가 출력됩니다.

```
============================
CONDITIONS EVALUATION REPORT
============================

Positive matches:   (조건을 만족해 적용된 자동설정)
-----------------
   DataSourceAutoConfiguration matched:
      - @ConditionalOnClass found 'javax.sql.DataSource' (OnClassCondition)

Negative matches:   (조건 불충족으로 적용 안 된 자동설정)
-----------------
   MongoAutoConfiguration:
      Did not match:
      - @ConditionalOnClass did not find required class 'com.mongodb.client.MongoClient'
```

이 보고서를 읽으면 "어떤 자동 설정이 왜 켜졌고 왜 꺼졌는지"를 정확히 파악할 수 있어, 설정 디버깅의 강력한 무기가 됩니다.

> **TIP**: Actuator를 쓰면 `/actuator/conditions` 엔드포인트로 같은 정보를 런타임에 JSON으로 조회할 수도 있습니다.

## 5. 자동 설정 재정의(오버라이딩)

자동 설정이 만든 기본 Bean이 마음에 들지 않으면, 방법은 간단합니다. **같은 타입의 Bean을 직접 등록**하면 됩니다. `@ConditionalOnMissingBean` 덕분에 자동 설정이 알아서 양보합니다.

```kotlin
@Configuration
class JacksonConfig {
    // 이 Bean을 직접 등록하면 자동설정의 기본 ObjectMapper는 적용되지 않는다
    @Bean
    fun objectMapper(): ObjectMapper =
        ObjectMapper()
            .registerModule(JavaTimeModule()) // LocalDate 직렬화를 위한 커스터마이징
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)
}
```

또는 프로퍼티로 동작을 바꾸거나, 특정 자동 설정을 통째로 제외할 수도 있습니다.

```kotlin
@SpringBootApplication(exclude = [DataSourceAutoConfiguration::class])
class BookApiApplication
```

> **Ktor와 비교**: Ktor에서는 `install(ContentNegotiation) { jackson { ... } }`처럼 **무엇을 켰는지 코드에 다 드러납니다.** Spring Boot는 기본을 자동으로 깔아 주는 대신, 위처럼 "재정의 가능 지점"을 약속해 둡니다. 자동화의 편의와 명시성의 트레이드오프를 잘 보여주는 대목입니다.

## 다음 단계

➡️ [05. Spring MVC vs WebFlux](05-mvc-vs-webflux.md) — 자동 설정이 깔아 주는 두 가지 웹 스택을 비교하고, 본 가이드가 어떤 스택을 선택했는지와 그 이유를 설명합니다.
