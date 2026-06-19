# Spring Initializr로 프로젝트 생성

Spring 프로젝트는 보통 **Spring Initializr**(https://start.spring.io/)로 시작합니다. 필요한 의존성을 고르면 빌드 스크립트, 디렉터리 구조, 진입점 클래스가 미리 구성된 압축 파일을 만들어 줍니다. Kotlin의 Gradle 프로젝트 생성과 비슷하지만, **Spring의 스타터(starter) 의존성**을 한 번에 묶어준다는 점이 다릅니다.

## 1. 웹 Initializr에서 설정

https://start.spring.io/ 에 접속해 다음과 같이 설정합니다.

| 항목 | 선택 값 | 비고 |
| --- | --- | --- |
| **Project** | Gradle - Kotlin | Kotlin DSL 빌드 스크립트(`build.gradle.kts`) |
| **Language** | Kotlin | |
| **Spring Boot** | 4.1.0 | 2026-06-10 GA |
| **Packaging** | Jar | 내장 Tomcat 포함 실행 가능 Jar |
| **Java** | 21 | JDK 21 LTS |
| **Group** | `com.example` | |
| **Artifact** | `book-api` | |
| **Name** | `book-api` | |
| **Package name** | `com.example.bookapi` | |

> 💡 "Project"에서 **Gradle - Kotlin**과 **Gradle - Groovy**를 혼동하지 마세요. 전자는 `build.gradle.kts`(Kotlin DSL), 후자는 `build.gradle`(Groovy DSL)입니다. Kotlin 개발자라면 Kotlin DSL이 자연스럽습니다.

## 2. 의존성(Dependencies) 추가

오른쪽 **ADD DEPENDENCIES** 버튼으로 다음을 추가합니다.

| 의존성 | 스타터 아티팩트 | 역할 |
| --- | --- | --- |
| **Spring Web** | `spring-boot-starter-web` | REST API, 내장 Tomcat, Jackson |
| **Spring Data JPA** | `spring-boot-starter-data-jpa` | JPA/Hibernate ORM |
| **Validation** | `spring-boot-starter-validation` | Bean Validation(`@Valid` 등) |
| **H2 Database** | `h2` | 인메모리 DB (학습용) |
| **Spring Boot Actuator** | `spring-boot-starter-actuator` | 헬스 체크, 메트릭 등 운영 엔드포인트 |

> 💡 **Spring Security**는 인증/인가를 다루는 뒤쪽 단계에서 추가합니다. 지금 넣으면 모든 엔드포인트에 기본 인증이 걸려 학습 흐름이 복잡해지므로 일단 제외합니다.

설정을 마치면 하단의 **GENERATE** 버튼을 눌러 `book-api.zip`을 내려받고 압축을 풉니다.

## 3. curl로 동일하게 생성하기

Initializr는 REST API를 제공하므로, 브라우저 없이 `curl`로 동일한 프로젝트를 생성할 수 있습니다.

```bash
curl https://start.spring.io/starter.zip \
  -d type=gradle-project-kotlin \
  -d language=kotlin \
  -d bootVersion=4.1.0 \
  -d javaVersion=21 \
  -d packaging=jar \
  -d groupId=com.example \
  -d artifactId=book-api \
  -d name=book-api \
  -d packageName=com.example.bookapi \
  -d dependencies=web,data-jpa,validation,h2,actuator \
  -o book-api.zip

unzip book-api.zip -d book-api
cd book-api
```

각 파라미터의 의미는 다음과 같습니다.

| 파라미터 | 값 | 설명 |
| --- | --- | --- |
| `type` | `gradle-project-kotlin` | Gradle + Kotlin DSL |
| `language` | `kotlin` | 소스 언어 |
| `bootVersion` | `4.1.0` | Spring Boot 버전 |
| `javaVersion` | `21` | 툴체인 JDK |
| `dependencies` | `web,data-jpa,validation,h2,actuator` | 쉼표로 구분한 스타터 ID |

> 💡 사용 가능한 모든 옵션은 `curl https://start.spring.io` (브라우저가 아닌 터미널에서)로 텍스트 메타데이터를 확인할 수 있습니다.

## 4. IntelliJ 내장 마법사 사용

IntelliJ IDEA에도 Initializr가 내장되어 있어, 브라우저를 거치지 않고 바로 프로젝트를 만들 수 있습니다.

1. `File > New > Project...`
2. 왼쪽 목록에서 **Spring Boot**(또는 **Spring Initializr**) 선택
3. Name `book-api`, Language `Kotlin`, Type `Gradle - Kotlin`, JDK `21`, Java `21`, Packaging `Jar`, Group `com.example`, Artifact `book-api`, Package `com.example.bookapi` 입력
4. **Next** → 위 표의 의존성(Web, Spring Data JPA, Validation, H2, Actuator) 선택
5. **Create**

> ⚠️ 내장 마법사는 내부적으로 start.spring.io API를 호출하므로 인터넷 연결이 필요합니다. 또한 IntelliJ가 제안하는 기본 Spring Boot 버전이 4.1.0이 아닐 수 있으니, 목록에서 **4.1.0**을 직접 선택하세요.

## 5. 생성된 파일 트리

압축을 풀면 다음과 같은 구조가 나옵니다.

```
book-api/
├── build.gradle.kts                # 빌드 스크립트 (Kotlin DSL)
├── settings.gradle.kts             # 프로젝트 이름/모듈 정의
├── gradlew                         # Gradle Wrapper (Unix)
├── gradlew.bat                     # Gradle Wrapper (Windows)
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.jar
│       └── gradle-wrapper.properties
├── .gitignore
├── src/
│   ├── main/
│   │   ├── kotlin/
│   │   │   └── com/example/bookapi/
│   │   │       └── BookApiApplication.kt   # 애플리케이션 진입점
│   │   └── resources/
│   │       ├── application.properties      # 기본 설정 파일
│   │       ├── static/                     # 정적 리소스
│   │       └── templates/                  # 템플릿 (사용 시)
│   └── test/
│       └── kotlin/
│           └── com/example/bookapi/
│               └── BookApiApplicationTests.kt
```

## 6. 첫 실행 확인

프로젝트 루트에서 다음을 실행하면 내장 Tomcat(11.0.x, Servlet 6.1)에서 애플리케이션이 뜹니다.

```bash
./gradlew bootRun
```

콘솔에 다음과 같은 로그와 함께 8080 포트에서 기동되면 정상입니다. (아직 엔드포인트가 없으므로 404가 정상입니다.)

```
 :: Spring Boot ::                (v4.1.0)
...
Tomcat started on port 8080 (http) with context path '/'
Started BookApiApplicationKt in 1.2 seconds
```

## 다음 단계

프로젝트를 만들었으니, [프로젝트 구조 해부](03-project-structure.md)에서 각 파일과 폴더가 무슨 역할을 하는지 살펴봅니다.
