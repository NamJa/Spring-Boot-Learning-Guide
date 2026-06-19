# application.yml 설정

Spring Boot는 코드 변경 없이 **외부 설정 파일**로 동작을 바꿀 수 있습니다. 서버 포트, 데이터소스, 로깅, JPA 동작 등이 모두 여기서 정해집니다. Initializr는 기본으로 `application.properties`를 만들지만, 이 가이드는 더 읽기 좋은 **`application.yml`** 을 사용합니다.

## 1. properties vs yaml

두 형식은 표현력이 같습니다. 같은 설정을 비교해 보겠습니다.

**application.properties**

```properties
server.port=8080
spring.application.name=book-api
spring.datasource.url=jdbc:h2:mem:bookdb
spring.jpa.hibernate.ddl-auto=update
```

**application.yml**

```yaml
server:
  port: 8080
spring:
  application:
    name: book-api
  datasource:
    url: jdbc:h2:mem:bookdb
  jpa:
    hibernate:
      ddl-auto: update
```

| 형식 | 장점 | 단점 |
| --- | --- | --- |
| `.properties` | 단순, 한 줄 = 한 설정 | 계층이 깊으면 키가 길고 반복적 |
| `.yml` | 계층 구조를 들여쓰기로 표현, 가독성 좋음 | 들여쓰기(공백) 실수에 민감 |

> ⚠️ YAML은 **탭(tab) 들여쓰기를 허용하지 않습니다.** 반드시 공백을 사용하세요. 기존 `application.properties`는 삭제하고 `src/main/resources/application.yml`을 새로 만들면 됩니다.

## 2. book-api의 기본 application.yml

`src/main/resources/application.yml`을 다음과 같이 구성합니다.

```yaml
server:
  # 외부 환경변수 PORT가 있으면 그 값을, 없으면 8080을 사용
  port: ${PORT:8080}

spring:
  application:
    name: book-api

  # --- H2 인메모리 데이터소스 ---
  datasource:
    url: jdbc:h2:mem:bookdb;DB_CLOSE_DELAY=-1
    driver-class-name: org.h2.Driver
    username: sa
    password: ""

  # --- H2 웹 콘솔 (개발용) ---
  h2:
    console:
      enabled: true
      path: /h2-console

  # --- JPA / Hibernate ---
  jpa:
    hibernate:
      ddl-auto: update        # 엔티티 기준으로 스키마 자동 갱신
    show-sql: true            # 실행되는 SQL을 로그로 출력
    properties:
      hibernate:
        format_sql: true      # SQL을 보기 좋게 정렬
    open-in-view: false       # OSIV 비활성화 (권장)

  # --- Jackson(JSON) ---
  jackson:
    serialization:
      indent-output: true     # 응답 JSON 들여쓰기 (개발 가독성)
    default-property-inclusion: non_null   # null 필드는 응답에서 제외

# --- 로깅 레벨 ---
logging:
  level:
    root: INFO
    com.example.bookapi: DEBUG        # 우리 패키지는 더 자세히
    org.hibernate.SQL: DEBUG          # 실행 SQL 로깅
```

### 주요 설정 설명

| 키 | 의미 |
| --- | --- |
| `server.port` | 내장 Tomcat 리스닝 포트 |
| `spring.application.name` | 앱 이름(로그/액추에이터/추적에 사용) |
| `spring.datasource.*` | DB 연결 정보. 여기선 H2 인메모리 |
| `DB_CLOSE_DELAY=-1` | 마지막 연결이 끊겨도 인메모리 DB를 유지 |
| `spring.h2.console` | 브라우저로 DB를 들여다보는 콘솔 (`/h2-console`) |
| `spring.jpa.hibernate.ddl-auto` | 스키마 자동 관리 전략 |
| `spring.jpa.show-sql` | 실행 SQL 콘솔 출력 |
| `spring.jpa.open-in-view` | OSIV. `false`가 성능/예측성 측면에서 권장 |
| `logging.level.*` | 패키지별 로그 레벨 |

> ⚠️ `ddl-auto`의 값 중 `update`는 학습용으로 편리하지만, **운영에서는 `validate` 또는 마이그레이션 도구(Flyway/Liquibase)** 를 사용해야 합니다. `create`/`create-drop`은 데이터를 날리므로 운영 금지입니다.

## 3. 프로파일(Profiles)

환경마다 다른 설정이 필요할 때 **프로파일**을 사용합니다. `application-{프로파일}.yml` 파일을 만들면, 해당 프로파일이 활성일 때 기본 `application.yml` 위에 **덮어쓰기(override)** 됩니다.

```
src/main/resources/
├── application.yml          # 공통 설정 (항상 적용)
├── application-dev.yml      # dev 프로파일
└── application-prod.yml     # prod 프로파일
```

**application-dev.yml** 예시:

```yaml
logging:
  level:
    com.example.bookapi: DEBUG
spring:
  jpa:
    show-sql: true
```

**application-prod.yml** 예시:

```yaml
logging:
  level:
    root: WARN
    com.example.bookapi: INFO
spring:
  jpa:
    show-sql: false
    hibernate:
      ddl-auto: validate
```

### 프로파일 활성화 방법

```bash
# 1) 실행 인자
./gradlew bootRun --args='--spring.profiles.active=dev'

# 2) 환경 변수
SPRING_PROFILES_ACTIVE=prod java -jar build/libs/book-api-0.0.1-SNAPSHOT.jar

# 3) JVM 시스템 프로퍼티
java -Dspring.profiles.active=prod -jar build/libs/book-api-0.0.1-SNAPSHOT.jar
```

기본 `application.yml`에 기본 프로파일을 지정할 수도 있습니다.

```yaml
spring:
  profiles:
    active: dev
```

## 4. 환경 변수 오버라이드와 `${...}`

Spring Boot 설정은 **우선순위(외부 > 내부)** 가 있어, 코드/파일을 고치지 않고도 외부에서 값을 덮어쓸 수 있습니다. 대략적인 우선순위는 다음과 같습니다.

```
명령행 인자(--key=val)  >  OS 환경 변수  >  application-{profile}.yml  >  application.yml
```

### 플레이스홀더 기본값

`${VAR:기본값}` 문법으로 "환경 변수가 있으면 그 값, 없으면 기본값"을 표현합니다.

```yaml
server:
  port: ${PORT:8080}          # PORT 없으면 8080
spring:
  datasource:
    url: ${DB_URL:jdbc:h2:mem:bookdb}
    username: ${DB_USER:sa}
```

### 완화된 바인딩(Relaxed Binding)

환경 변수는 보통 대문자와 언더스코어를 쓰는데, Spring Boot는 이를 점/캐멀케이스 키와 **유연하게 매칭**해 줍니다.

| 설정 키 | 대응하는 환경 변수 |
| --- | --- |
| `spring.application.name` | `SPRING_APPLICATION_NAME` |
| `server.port` | `SERVER_PORT` |
| `spring.datasource.url` | `SPRING_DATASOURCE_URL` |

즉, 점(`.`)은 언더스코어(`_`)로, 카멜케이스 경계도 언더스코어로 바꾸고 대문자로 쓰면 됩니다. 컨테이너/클라우드 배포에서 매우 유용합니다.

```bash
SERVER_PORT=9090 SPRING_DATASOURCE_URL=jdbc:h2:mem:other \
  java -jar build/libs/book-api-0.0.1-SNAPSHOT.jar
```

> 💡 민감 정보(DB 비밀번호, API 키)는 yml 파일에 하드코딩하지 말고 **환경 변수**로 주입하세요. `application.yml`에는 `${DB_PASSWORD}`만 두고 값은 배포 환경에서 채우는 것이 안전합니다.

## 다음 단계

이제 프로젝트 설정이 모두 끝났습니다. 다음 Phase에서는 실제 코드를 작성합니다. [애플리케이션 진입점](../phase-2-first-api/01-application-entry-point.md)에서 `BookApiApplication.kt`와 첫 API를 만들어 봅니다.
