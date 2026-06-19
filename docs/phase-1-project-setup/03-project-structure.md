# 프로젝트 구조 해부

Initializr가 만들어 준 프로젝트는 표준 Gradle 레이아웃을 따릅니다. Kotlin/Gradle에 익숙하다면 대부분 눈에 익겠지만, Spring 특유의 파일도 있습니다. 이 페이지에서는 **각 파일과 디렉터리의 역할**을 짚고, 앞으로 가이드에서 사용할 **패키지 구성 전략**을 정합니다.

## 1. 전체 디렉터리 트리

```
book-api/
├── build.gradle.kts                # 빌드 스크립트: 플러그인, 의존성, 컴파일러 옵션
├── settings.gradle.kts             # 루트 프로젝트 이름과 포함 모듈 정의
├── gradlew                         # Gradle Wrapper 실행 스크립트 (macOS/Linux)
├── gradlew.bat                     # Gradle Wrapper 실행 스크립트 (Windows)
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.jar          # 래퍼 실행 코드
│       └── gradle-wrapper.properties   # 사용할 Gradle 버전 고정
├── .gitignore
└── src/
    ├── main/
    │   ├── kotlin/
    │   │   └── com/example/bookapi/
    │   │       └── BookApiApplication.kt   # @SpringBootApplication 진입점
    │   └── resources/
    │       ├── application.properties      # 외부 설정
    │       ├── static/                     # JS/CSS/이미지 등 정적 파일
    │       └── templates/                  # 서버 사이드 템플릿 (Thymeleaf 등)
    └── test/
        └── kotlin/
            └── com/example/bookapi/
                └── BookApiApplicationTests.kt   # 통합 테스트 골격
```

## 2. 핵심 파일/폴더 설명

| 경로 | 역할 |
| --- | --- |
| `src/main/kotlin` | 프로덕션 Kotlin 소스. 패키지 구조가 곧 컴포넌트 스캔 범위가 됩니다. |
| `src/main/resources` | 컴파일되지 않는 리소스. 설정 파일, 정적 파일, 템플릿, 메시지 번들 등. |
| `src/test/kotlin` | 테스트 소스. 메인과 동일한 패키지 구조를 따릅니다. |
| `BookApiApplication.kt` | 애플리케이션 진입점. `@SpringBootApplication`이 붙은 클래스와 `main` 함수. |
| `application.properties` | 기본 외부 설정 파일. (다음 페이지에서 `application.yml`로 전환) |
| `static/` | 별도 처리 없이 그대로 제공되는 정적 리소스. |
| `templates/` | Thymeleaf 같은 템플릿 엔진이 렌더링하는 뷰. REST API만 만든다면 거의 쓰지 않습니다. |
| `build.gradle.kts` | 의존성/플러그인/태스크 정의. (4번 페이지에서 상세히) |
| `settings.gradle.kts` | `rootProject.name = "book-api"` 등 빌드 전반 설정. |
| `gradlew` / `gradle/wrapper` | 전역 Gradle 없이 고정 버전으로 빌드하게 해주는 래퍼. |

### BookApiApplication.kt 미리 보기

진입점 클래스는 매우 단순합니다. (다음 Phase에서 자세히 다룹니다.)

```kotlin
package com.example.bookapi

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

// @SpringBootApplication = @Configuration + @EnableAutoConfiguration + @ComponentScan
@SpringBootApplication
class BookApiApplication

fun main(args: Array<String>) {
    runApplication<BookApiApplication>(*args)
}
```

> 💡 `@ComponentScan`은 **이 클래스가 위치한 패키지(`com.example.bookapi`)와 그 하위 패키지**를 스캔합니다. 따라서 모든 컴포넌트는 이 기본 패키지 아래에 두는 것이 원칙입니다. 바깥에 두면 Bean으로 등록되지 않습니다.

## 3. 패키지 구성 전략: 계층형 vs 기능형

소스가 늘어나면 패키지를 어떻게 나눌지 정해야 합니다. 두 가지 대표 전략이 있습니다.

### 계층형 (Package-by-Layer)

기술적 역할(controller/service/repository)로 나눕니다.

```
com.example.bookapi
├── controller     # 모든 컨트롤러
├── service        # 모든 서비스
├── repository     # 모든 리포지토리
├── domain         # 모든 엔티티
└── dto            # 모든 DTO
```

- **장점**: 직관적이고 작은 프로젝트에서 익히기 쉽습니다.
- **단점**: 하나의 기능을 고치려면 여러 패키지를 오가야 합니다. 규모가 커질수록 응집도가 떨어집니다.

### 기능형 (Package-by-Feature)

도메인 기능(book, member ...)으로 먼저 나누고, 그 안에서 계층을 둡니다.

```
com.example.bookapi
├── book
│   ├── BookController.kt
│   ├── BookService.kt
│   ├── BookRepository.kt
│   ├── Book.kt
│   └── dto/
└── member
    ├── MemberController.kt
    └── ...
```

- **장점**: 기능 단위로 응집되어 변경/삭제가 쉽고, 모듈화·마이크로서비스 분리에 유리합니다.
- **단점**: 초보자에게는 계층 위치가 한눈에 안 들어올 수 있습니다.

| 기준 | 계층형 | 기능형 |
| --- | --- | --- |
| 학습 난이도 | 낮음 | 중간 |
| 작은 프로젝트 | 적합 | 무난 |
| 큰 프로젝트 | 응집도 저하 | 유리 |
| 기능별 변경 | 분산됨 | 집중됨 |

## 4. 이 가이드가 사용할 구조

학습 흐름을 명확히 보여주기 위해, 이 가이드는 **계층형을 기본**으로 하되 계층별 패키지를 명시적으로 둡니다. 도서(book) 한 도메인에 집중하므로 계층형이 따라가기 쉽습니다.

```
com.example.bookapi
├── BookApiApplication.kt        # 진입점
├── controller                   # REST 컨트롤러
│   └── BookController.kt
├── service                      # 비즈니스 로직
│   └── BookService.kt
├── repository                   # 데이터 접근(JPA Repository)
│   └── BookRepository.kt
├── domain                       # JPA 엔티티
│   └── Book.kt
├── dto                          # 요청/응답 DTO
│   ├── BookRequest.kt
│   └── BookResponse.kt
└── config                       # 설정 클래스(@Configuration)
    └── ...
```

각 계층의 책임은 다음과 같습니다.

| 계층 | 책임 | 어노테이션(예고) |
| --- | --- | --- |
| `controller` | HTTP 요청/응답 처리, 검증 | `@RestController` |
| `service` | 비즈니스 로직, 트랜잭션 경계 | `@Service`, `@Transactional` |
| `repository` | DB 접근 | `@Repository` / `JpaRepository` |
| `domain` | 영속 엔티티 | `@Entity` |
| `dto` | 외부에 노출하는 데이터 형태 | (POJO/`data class`) |
| `config` | Bean 정의, 설정 | `@Configuration` |

> 💡 도메인이 여러 개로 늘어나면 위 계층형을 그대로 두기보다 **기능형으로 리팩터링**하는 것을 권장합니다. 구조는 프로젝트 규모에 맞춰 진화시키면 됩니다.

## 다음 단계

구조를 이해했으니, [build.gradle.kts 해부](04-build-gradle-kts.md)에서 빌드 스크립트의 모든 줄을 분석합니다.
