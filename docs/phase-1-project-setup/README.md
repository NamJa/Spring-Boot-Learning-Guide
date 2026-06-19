# Phase 1: 프로젝트 설정

이 단계에서는 Spring Boot 프로젝트를 시작하기 위한 모든 기반을 다집니다. Kotlin은 이미 익숙하지만 Spring 생태계는 처음인 개발자를 위해, **개발 환경 구성부터 프로젝트 생성, 빌드 스크립트와 설정 파일까지** 하나씩 해부합니다.

우리가 이 가이드 전반에 걸쳐 만들 예제는 **도서(Book) 관리 REST API** 입니다. 기본 패키지는 `com.example.bookapi`, 아티팩트 이름은 `book-api`로 통일합니다.

## 이 단계에서 다루는 내용

Phase 1을 마치면 다음을 할 수 있습니다.

- JDK 21 LTS와 IntelliJ IDEA 기반의 Spring Boot 4 개발 환경을 구성한다.
- Spring Initializr로 Kotlin + Gradle 기반 프로젝트를 생성한다.
- 생성된 프로젝트의 디렉터리 구조와 각 파일의 역할을 이해한다.
- `build.gradle.kts`의 모든 블록을 읽고 수정할 수 있다.
- `application.yml`로 서버/데이터소스/로깅/프로파일을 설정할 수 있다.

## 페이지 목록

| 순서 | 페이지 | 내용 |
| --- | --- | --- |
| 1 | [개발 환경 설정](01-environment-setup.md) | JDK 21, IntelliJ, Gradle Wrapper, 보조 도구 |
| 2 | [Spring Initializr로 프로젝트 생성](02-create-project.md) | start.spring.io, 의존성 선택, curl 생성 |
| 3 | [프로젝트 구조 해부](03-project-structure.md) | 디렉터리 트리, 패키지 구성 전략 |
| 4 | [build.gradle.kts 해부](04-build-gradle-kts.md) | 플러그인, 의존성, 컴파일러 옵션 |
| 5 | [application.yml 설정](05-application-yml.md) | properties vs yaml, 데이터소스, 프로파일 |

> 💡 이 가이드는 2026-06-20 기준 최신 GA 버전인 **Spring Boot 4.1.0** (2026-06-10 출시), **Spring Framework 7.0.8+**, **Kotlin 2.2.21** (Spring Boot BOM 관리)을 기준으로 합니다. JDK는 LTS인 **21**로 표준화합니다.

## 다음 단계

이제 첫 번째 페이지인 [개발 환경 설정](01-environment-setup.md)부터 시작합니다.
