# 외부화된 설정과 프로파일

개발할 때는 H2 인메모리 DB를 쓰지만, 운영 환경에서는 PostgreSQL을 씁니다. 로그 레벨도 개발에서는 `DEBUG`, 운영에서는 `WARN`이 적당하죠. 그리고 DB 비밀번호 같은 비밀값은 **절대 소스 코드나 Git에 들어가서는 안 됩니다.**

이런 요구를 만족시키는 것이 Spring Boot의 **외부화된 설정(Externalized Configuration)** 입니다. 핵심 아이디어는 단순합니다 — **설정값을 코드에서 분리해 환경마다 다르게 주입한다.** 이 문서에서는 프로퍼티가 어디서 오고, 충돌 시 누가 이기며, **프로파일**로 환경을 어떻게 나누는지 배웁니다.

## 1. 프로퍼티 소스와 우선순위

Spring Boot는 여러 곳에서 설정값을 읽어들입니다. 같은 키가 여러 곳에 정의되면 **우선순위가 높은 쪽이 이깁니다.** 자주 쓰는 소스만 우선순위 높은 순으로 정리하면 다음과 같습니다.

| 순위 | 프로퍼티 소스 | 예시 |
|------|--------------|------|
| 1 (가장 높음) | 커맨드라인 인자 | `--server.port=9000` |
| 2 | `SPRING_APPLICATION_JSON` | 인라인 JSON 설정 |
| 3 | OS 환경 변수 | `SERVER_PORT=9000` |
| 4 | `application-{profile}.yml` (프로파일별) | `application-prod.yml` |
| 5 | `application.yml` (공통) | `application.yml` |
| 6 (가장 낮음) | `@PropertySource`, 기본값 | 코드 내 기본값 |

```
높은 우선순위 (덮어쓴다)
  ▲   커맨드라인 인자        --server.port=9000
  │   환경 변수             SERVER_PORT=9000
  │   application-prod.yml  (활성 프로파일)
  │   application.yml       (공통)
  ▼   코드 기본값
낮은 우선순위 (덮어쓰인다)
```

이 구조 덕분에 **공통 설정은 `application.yml`에 두고, 환경별 차이만 프로파일 파일이나 환경 변수로 오버라이드**하는 패턴이 자연스럽게 가능합니다. 예를 들어 운영 서버에서 잠깐 포트만 바꾸고 싶으면, 파일을 고칠 필요 없이 `--server.port=9000`만 붙여 실행하면 됩니다.

## 2. 프로파일로 환경 분리하기

**프로파일(Profile)** 은 "이 설정 묶음은 어떤 환경용인가"를 나타내는 이름표입니다. 관례적으로 `dev`, `prod`, `test` 등을 씁니다. Spring Boot는 `application-{프로파일}.yml` 파일을 자동으로 인식합니다.

공통 설정은 `application.yml`에 둡니다.

```yaml
# application.yml — 모든 환경 공통
spring:
  application:
    name: book-api
server:
  port: 8080
```

개발용 설정 (`application-dev.yml`):

```yaml
# application-dev.yml
spring:
  datasource:
    url: jdbc:h2:mem:bookdb     # 인메모리 H2
    username: sa
    password:
  jpa:
    hibernate:
      ddl-auto: create-drop      # 매번 스키마 재생성
    show-sql: true               # SQL 콘솔 출력
logging:
  level:
    com.example.bookapi: DEBUG
```

운영용 설정 (`application-prod.yml`):

```yaml
# application-prod.yml
spring:
  datasource:
    url: jdbc:postgresql://${DB_HOST:localhost}:5432/bookdb
    username: ${DB_USER}              # 환경 변수에서 주입
    password: ${DB_PASSWORD}          # 절대 하드코딩 금지
  jpa:
    hibernate:
      ddl-auto: validate              # 스키마는 마이그레이션 도구가 관리
    show-sql: false
logging:
  level:
    com.example.bookapi: WARN
```

> [!TIP]
> 여러 프로파일을 한 파일에 담고 싶으면 YAML 문서 구분자 `---` 와 `spring.config.activate.on-profile` 을 쓸 수도 있습니다. 하지만 환경별로 파일을 나누는 편이 보통 더 읽기 좋습니다.

흔히 쓰는 세 번째 프로파일이 **`test`** 입니다. 자동화 테스트 전용 설정(`src/test/resources/application-test.yml`)을 두고, 테스트 클래스에 `@ActiveProfiles("test")`를 붙여 활성화합니다. 보통 인메모리 H2와 `ddl-auto: create-drop`을 써서 테스트마다 깨끗한 스키마로 시작합니다. (실제 테스트 작성은 [Phase 5의 테스트 전략](../phase-5-production-features/04-testing.md)에서 다룹니다.)

```yaml
# src/test/resources/application-test.yml
spring:
  datasource:
    url: jdbc:h2:mem:bookdb-test
  jpa:
    hibernate:
      ddl-auto: create-drop
```

## 3. 프로파일 활성화

작성한 프로파일은 **활성화(activate)** 해야 적용됩니다. 활성화 방법은 여러 가지이고, 1절의 우선순위 규칙이 그대로 적용됩니다.

```yaml
# application.yml 에서 기본 활성 프로파일 지정 (가장 약함)
spring:
  profiles:
    active: dev
```

```bash
# 환경 변수로 (운영 서버에서 흔히 사용)
export SPRING_PROFILES_ACTIVE=prod
java -jar book-api.jar

# 커맨드라인 인자로 (가장 강함, 일시적 오버라이드에 유용)
java -jar book-api.jar --spring.profiles.active=prod

# Gradle 로 로컬 실행 시
./gradlew bootRun --args='--spring.profiles.active=dev'
```

> [!NOTE]
> `SPRING_PROFILES_ACTIVE`는 `spring.profiles.active`의 **환경 변수 표기**입니다. 점(`.`)은 언더스코어(`_`)로, 소문자는 대문자로 바뀝니다. 이를 **느슨한 바인딩(relaxed binding)** 이라 합니다(4절).

## 4. 느슨한 바인딩(Relaxed Binding)

Spring Boot는 프로퍼티 키를 **여러 표기법으로 유연하게 매칭**합니다. 같은 설정을 환경에 맞는 표기로 쓸 수 있습니다.

| 표기법 | 예시 | 주 사용처 |
|--------|------|----------|
| 케밥 케이스 | `app.book.default-page-size` | YAML/properties (권장) |
| 카멜 케이스 | `app.book.defaultPageSize` | 코드 |
| 환경 변수 | `APP_BOOK_DEFAULTPAGESIZE` | OS 환경 변수, 컨테이너 |

즉 YAML에 `default-page-size: 20`이라고 써도, 운영 환경에서는 `APP_BOOK_DEFAULTPAGESIZE=50` 환경 변수로 오버라이드할 수 있습니다. 컨테이너/쿠버네티스 환경에서 환경 변수로 설정을 주입하는 패턴의 기반이 바로 이것입니다.

## 5. 플레이스홀더와 기본값

YAML 안에서 `${...}` 문법으로 **다른 프로퍼티나 환경 변수를 참조**할 수 있고, 콜론 뒤에 **기본값**을 줄 수 있습니다.

```yaml
spring:
  datasource:
    url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/bookdb
    #                       └ 환경변수 없으면 'localhost'  └ 없으면 5432
    password: ${DB_PASSWORD}   # 기본값 없음 → 없으면 시작 실패 (의도된 안전장치)
```

`${DB_HOST:localhost}`는 "`DB_HOST` 환경 변수가 있으면 그 값을, 없으면 `localhost`를 쓴다"는 뜻입니다. 비밀번호처럼 기본값을 두면 위험한 값은 일부러 기본값을 비워, 환경 변수가 없으면 애플리케이션이 **시작 단계에서 즉시 실패**하도록 하는 것이 좋습니다.

## 6. 설정 가져오기 — `spring.config.import`

별도 파일이나 외부 소스의 설정을 끌어오려면 `spring.config.import`를 씁니다.

```yaml
spring:
  config:
    import:
      - optional:file:./local.yml        # 있으면 읽고 없으면 무시(optional:)
      - configtree:/etc/secrets/          # 디렉터리의 각 파일을 키-값으로 (k8s Secret 마운트)
```

`optional:` 접두사를 붙이면 파일이 없어도 오류 없이 넘어갑니다. 쿠버네티스에서는 Secret을 디렉터리로 마운트한 뒤 `configtree:`로 읽는 패턴이 흔합니다.

## 7. 비밀값은 환경 변수로 — Git에 커밋 금지

가장 중요한 원칙입니다. **DB 비밀번호, API 키, 토큰 같은 비밀값은 절대 YAML 파일에 직접 쓰거나 Git에 커밋하지 않습니다.**

```yaml
# ✅ 올바른 방식 — 비밀값은 환경 변수 참조만
spring:
  datasource:
    password: ${DB_PASSWORD}
```

```bash
# 실행 환경에서 환경 변수로 실제 값 주입
export DB_PASSWORD='실제_비밀번호'
```

- 로컬 개발에서는 `.env` 파일이나 IDE 실행 구성에 환경 변수를 설정하되, **`.gitignore`에 등록**합니다.
- 운영 환경에서는 쿠버네티스 Secret, AWS Secrets Manager, HashiCorp Vault 등 **비밀 관리 시스템**에서 환경 변수로 주입합니다.

> [!WARNING]
> 실수로 비밀번호를 커밋했다면 값을 바꾸는 것만으로는 부족합니다. Git 히스토리에 영원히 남으므로, 노출된 자격증명은 **반드시 폐기(rotate)** 하고 새로 발급해야 합니다.

## 8. `@Profile` — 환경별 Bean 등록

설정값뿐 아니라 **Bean 자체를 프로파일에 따라 다르게 등록**할 수도 있습니다. `@Profile` 애너테이션을 쓰면 됩니다.

```kotlin
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.context.annotation.Profile

@Configuration
class NotificationConfig {

    // 개발 환경: 콘솔에 출력만 하는 가짜 구현
    @Bean
    @Profile("dev")
    fun devNotifier(): Notifier = ConsoleNotifier()

    // 운영 환경: 실제 이메일 발송 구현
    @Bean
    @Profile("prod")
    fun prodNotifier(): Notifier = EmailNotifier()
}
```

`@Profile("!prod")`처럼 부정(`!`)도 가능합니다("prod가 아닐 때만"). 활성 프로파일에 맞는 Bean만 컨텍스트에 등록되므로, 환경별로 구현을 깔끔하게 갈아끼울 수 있습니다.

## 9. 프로파일 그룹

여러 프로파일을 하나의 이름으로 묶을 수 있습니다. 예를 들어 운영 환경은 `prod` 설정에 더해 모니터링용 `metrics` 프로파일도 함께 켜고 싶을 때:

```yaml
# application.yml
spring:
  profiles:
    group:
      production: prod, metrics, audit   # production 활성화 시 셋 다 켜짐
```

이제 `--spring.profiles.active=production` 하나로 `prod`, `metrics`, `audit` 세 프로파일이 동시에 활성화됩니다. 운영 환경의 여러 관심사를 한 번에 켜고 끄기 편리합니다.

## 다음 단계

설정값을 외부화하고 환경별로 나누는 법을 배웠습니다. 그런데 `@Value`로 설정값을 하나씩 주입하는 것은 번거롭고 타입 안전하지도 않습니다. 다음은 관련 설정을 **타입 안전한 Kotlin 클래스**로 묶는 `@ConfigurationProperties`를 다룹니다.

→ [@ConfigurationProperties](04-configuration-properties.md)
