# Spring Boot 학습 가이드 (Kotlin)

[![Live Site](https://img.shields.io/badge/Live-namja.github.io-6DB33F?style=flat-square&logo=githubpages&logoColor=white)](https://namja.github.io/Spring-Boot-Learning-Guide/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.1.0-6DB33F?style=flat-square&logo=springboot&logoColor=white)](https://docs.spring.io/spring-boot/index.html)
[![Kotlin](https://img.shields.io/badge/Kotlin-2.3.21-7F52FF?style=flat-square&logo=kotlin&logoColor=white)](https://kotlinlang.org/)
[![JDK](https://img.shields.io/badge/JDK-21%20LTS-orange?style=flat-square&logo=openjdk&logoColor=white)](https://adoptium.net/)

> **Kotlin으로 배우는 Spring Boot 4 — 핵심 개념부터 REST API · 데이터 · 보안 · 배포까지**

Kotlin은 알지만 Spring 생태계는 처음인 분들을 위한 실습형 입문 가이드입니다. IoC/DI 같은 Spring의 핵심 철학부터 시작해, Kotlin으로 REST API를 만들고, Spring Data JPA로 데이터를 다루며, 검증·예외·보안·관측성을 더한 뒤, JAR·Docker·네이티브 이미지로 배포하는 전 과정을 단계별로 다룹니다.

## 📦 기준 버전 (2026-07-25 기준)

| 구성요소 | 버전 | 비고 |
|---|---|---|
| **Spring Boot** | 4.1.0 | 2026-06-10 GA. 2026-07-25 기준 최신 GA |
| **Spring Framework** | 7.0.8 | Spring Boot 4.1.0 BOM 관리 버전 |
| **Spring Security** | 7.1.0 | Spring Boot 4.1.0 BOM 관리 버전 |
| **Spring Data** | 2026.0.0 | BOM(`spring-data-bom`) 버전 |
| **Kotlin** | 2.3.21 | Spring Boot 4.1.0 BOM이 관리 (스탠드얼론 최신은 2.4.10) |
| **JDK** | 17 (최소) ~ 26 | 빌드·런타임. 본 가이드는 LTS인 JDK 21 기준 (Temurin 최신 태그 21.0.12, SDKMAN 설치본 21.0.11) |
| **Gradle** | 9.x (Initializr 래퍼 9.5.1) | Kotlin DSL(`build.gradle.kts`). 8.14+도 동작 |
| **Maven** | 3.6.3+ | (가이드는 Gradle 중심) |
| **내장 서버** | Tomcat 11.0.22 (Servlet 6.1) | 기본값. Jetty 12.1.10도 지원 |
| **Hibernate ORM** | 7.4.1.Final | Spring Data JPA의 구현체 |
| **Jackson** | 3.1.4 (`tools.jackson`) | **Spring Boot 4의 기본 JSON 엔진** |
| **JUnit** | 6.0.3 (Jupiter) | `spring-boot-starter-test`가 관리 |
| **Testcontainers** | 2.0.5 | 아티팩트 이름이 `testcontainers-*`로 변경됨 |
| **Querydsl (OpenFeign)** | 7.5 | 부록 B 기준 |
| **GraalVM** | Community 25 + Native Build Tools 1.1.1 | 네이티브 이미지 |

> Spring Boot 4.1.0은 **Java 17을 최소 버전**으로 요구하며 **Java 26까지** 호환됩니다. 본 가이드는 가장 무난한 LTS인 **JDK 21**을 기준으로 작성했습니다. 현재 오픈소스 유지보수 라인은 **4.0.7** 하나이며, **3.5.x는 2026-06-30에 오픈소스 지원이 종료**되어(마지막 OSS 릴리스 3.5.16) 이후 패치는 상용 지원 대상입니다. Initializr도 4.1.x / 4.0.x만 제공하므로, 새 프로젝트는 최신 GA인 **4.1.0**으로 시작하세요.
>
> **Kotlin 버전에 관하여:** 2026-07-25 기준 Kotlin의 스탠드얼론 최신 릴리스는 **2.4.10**(2026-07-14)이지만, Spring Boot 4.1.0의 BOM은 **Kotlin 2.3.21**을 관리합니다. Spring Boot 프로젝트에서는 BOM이 검증한 버전을 그대로 쓰는 것이 안전하므로, 본 가이드는 **2.3.21**을 기준으로 합니다. (Spring Boot 4.0.0은 2.2.21을 관리했습니다.)

### ⚠️ Spring Boot 4에서 달라진 것 (Boot 3 예제와 다른 부분)

인터넷의 Spring Boot 3 예제를 그대로 복사하면 컴파일조차 되지 않는 지점들입니다. 각 항목은 해당 Phase에서 자세히 다룹니다.

| 변경 | Boot 3까지 | Boot 4 (본 가이드) | 다루는 곳 |
|---|---|---|---|
| **JSON 엔진** | Jackson 2 (`com.fasterxml.jackson.*`) | **Jackson 3** (`tools.jackson.*`), `JsonMapper` | [Phase 2-2](phase-2-first-api/02-dto-and-serialization.md) |
| **웹 스타터 이름** | `spring-boot-starter-web` | **`spring-boot-starter-webmvc`** (구 이름은 deprecated) | [Phase 1-4](phase-1-project-setup/04-build-gradle-kts.md) |
| **테스트 스타터** | `spring-boot-starter-test` 하나 | 기술별 **`spring-boot-starter-<기술>-test`** | [Phase 5-4](phase-5-production-features/04-testing.md) |
| **목 빈** | `@MockBean` | **`@MockitoBean`** (`@MockBean`은 제거됨) | [Phase 5-4](phase-5-production-features/04-testing.md) |
| **통합 테스트 클라이언트** | `TestRestTemplate` 자동 구성 | **`RestTestClient`** + `@AutoConfigureRestTestClient` | [Phase 5-4](phase-5-production-features/04-testing.md) |
| **헬스 API 패키지** | `org.springframework.boot.actuate.health` | **`org.springframework.boot.health.contributor`** | [Phase 5-3](phase-5-production-features/03-actuator-observability.md) |
| **AOP 스타터** | `spring-boot-starter-aop` | **`spring-boot-starter-aspectj`** | [부록 C-2](appendix-c-aop/02-spring-aop.md) |
| **H2 콘솔** | `h2` 의존성만으로 사용 | **`spring-boot-h2console`** 모듈 추가 필요 | [Phase 3-5](phase-3-data-jpa/05-database-setup.md) |
| **Kotlin 애너테이션 타깃** | `@field:` 수동 지정 | `-Xannotation-default-target=param-property` 기본 | [Phase 4-1](phase-4-validation-config/01-bean-validation.md) |

## 🧭 추천 학습 경로

본 가이드는 **하나의 예제(도서 관리 API)** 를 본문 Phase 0→7로 완성한 뒤, **부록 A~D**로 깊이를 더하는 구성입니다. 모든 페이지는 "다음 단계" 링크로 이어져 있어, 아래 순서대로 따라가면 됩니다.

### ✅ 권장 통합 순서 (본문 + 부록)

처음이라면 이 순서를 권장합니다. **부록은 선택적 심화**이므로, 일단 본문(Phase 0~7)만 완주하고 부록은 나중에 봐도 됩니다.

| 순서 | 단계 | 핵심 학습 | 선행 |
|:---:|---|---|:---:|
| 1 | **Phase 0** 핵심 개념 | 서버 입문, IoC/DI, 자동 설정, MVC vs WebFlux | — |
| 2 | **Phase 1** 프로젝트 설정 | JDK·Initializr·`build.gradle.kts`·`application.yml` | 0 |
| 3 | **Phase 2** 첫 REST API | `@RestController`·DTO·Service (인메모리) | 1 |
| 4 | **Phase 3** 데이터 영속성 | Spring Data JPA·Entity·트랜잭션 | 2 |
| 5 | 📎 **부록 A** JPA 심화 | 영속성 컨텍스트·연관관계·프록시·N+1·JPQL | 3 |
| 6 | 📎 **부록 B** Querydsl | 타입 안전·동적 쿼리·DTO 프로젝션 | A |
| 7 | **Phase 4** 검증·예외·설정 | Bean Validation·`ProblemDetail`·프로파일 | 2~3 |
| 8 | **Phase 5** 실전 기능 | HTTP 클라이언트·Security 7.1·Actuator·테스트 | 4 |
| 9 | 📎 **부록 C** AOP/프록시 고급 | 동적 프록시·`@Aspect`·`@Transactional` 원리 | 3-4(트랜잭션) |
| 10 | **Phase 6** 빌드 & 배포 | JAR·Docker·GraalVM 네이티브 | 5 |
| 11 | **Phase 7** Cloud Run 배포 | gcloud·소스/이미지 배포·CI/CD | 6 |
| 12 | 📎 **부록 D** MVC 내부·SSR | DispatcherServlet·Thymeleaf·필터/인터셉터·세션 | 2(+5) |

> 💡 **부록 선행 관계**: 부록 B는 **부록 A**를, 부록 C는 **Phase 3-4(트랜잭션)** 를, 부록 D는 **Phase 2**를 먼저 보고 오는 것을 권장합니다.

### 🎯 목표별 빠른 트랙

시간이 부족하거나 목적이 분명하다면 아래 축약 경로를 참고하세요.

- **🚀 빠르게 배포까지 (야생형)**: Phase 0(빠르게) → 1 → 2 → 3 → 6 → 7 *(검증·보안은 나중에 4·5로 보강)*
- **📚 탄탄한 백엔드 정석**: 위 **권장 통합 순서 전체**(1→12)
- **🗄️ 데이터/쿼리 집중**: Phase 0 → 1 → 2 → 3 → 부록 A → 부록 B → Phase 4
- **🧠 이론·면접 대비**: Phase 0 → 부록 C(AOP) → 부록 A(JPA) → 부록 D(MVC 내부) *(원리 위주)*
- **🌐 화면(SSR)까지**: 본문 완주 → 부록 D(Thymeleaf·세션 로그인)

---

## 🗺️ 전체 페이지 목록

아래는 모든 페이지의 전체 목차입니다. (추천 순서는 위 **🧭 추천 학습 경로** 절 참고)

### Phase 0 — Spring 핵심 개념
- [서버 사이드 개발 입문](phase-0-spring-fundamentals/00-server-side-intro.md)
- [Spring & Spring Boot 입문](phase-0-spring-fundamentals/01-what-is-spring.md)
- [IoC 컨테이너와 의존성 주입](phase-0-spring-fundamentals/02-ioc-and-di.md)
- [Bean 생명주기와 스코프](phase-0-spring-fundamentals/03-bean-lifecycle-scope.md)
- [자동 설정과 스타터](phase-0-spring-fundamentals/04-auto-configuration.md)
- [Spring MVC vs WebFlux](phase-0-spring-fundamentals/05-mvc-vs-webflux.md)

### Phase 1 — 프로젝트 설정
- [개발 환경 설정](phase-1-project-setup/01-environment-setup.md)
- [Spring Initializr로 프로젝트 생성](phase-1-project-setup/02-create-project.md)
- [프로젝트 구조 해부](phase-1-project-setup/03-project-structure.md)
- [build.gradle.kts 해부](phase-1-project-setup/04-build-gradle-kts.md)
- [application.yml 설정](phase-1-project-setup/05-application-yml.md)

### Phase 2 — 첫 번째 REST API
- [진입점 — @SpringBootApplication](phase-2-first-api/01-application-entry-point.md)
- [DTO와 JSON 직렬화](phase-2-first-api/02-dto-and-serialization.md)
- [@RestController 구현](phase-2-first-api/03-rest-controller.md)
- [Service 계층과 DI](phase-2-first-api/04-service-layer.md)
- [로컬 실행과 테스트](phase-2-first-api/05-local-run-and-test.md)

### Phase 3 — 데이터 영속성 (Spring Data JPA)
- [Spring Data JPA 개념](phase-3-data-jpa/01-jpa-concepts.md)
- [Entity 매핑 (Kotlin)](phase-3-data-jpa/02-entity-mapping.md)
- [Repository 인터페이스](phase-3-data-jpa/03-repository.md)
- [트랜잭션 관리](phase-3-data-jpa/04-transactions.md)
- [데이터베이스 설정 (H2 / PostgreSQL)](phase-3-data-jpa/05-database-setup.md)

### Phase 4 — 검증 · 예외 · 설정
- [Bean Validation 입력 검증](phase-4-validation-config/01-bean-validation.md)
- [전역 예외 처리](phase-4-validation-config/02-exception-handling.md)
- [외부화된 설정과 프로파일](phase-4-validation-config/03-profiles-config.md)
- [@ConfigurationProperties](phase-4-validation-config/04-configuration-properties.md)

### Phase 5 — 실전 기능 (Spring Boot 4)
- [선언적 HTTP 클라이언트](phase-5-production-features/01-http-interface-client.md)
- [Spring Security 7 기초](phase-5-production-features/02-security-basics.md)
- [Actuator와 관측성](phase-5-production-features/03-actuator-observability.md)
- [테스트 전략](phase-5-production-features/04-testing.md)

### Phase 6 — 빌드 & 배포
- [실행 가능 JAR 빌드](phase-6-build-deploy/01-executable-jar.md)
- [Docker 컨테이너화](phase-6-build-deploy/02-docker.md)
- [GraalVM 네이티브 이미지](phase-6-build-deploy/03-native-image.md)
- [프로파일별 배포 & 운영](phase-6-build-deploy/04-deploy-operations.md)

### Phase 7 — Google Cloud & Cloud Run 배포
- [Cloud Run 핵심 개념](phase-7-cloud-run/01-cloud-run-concepts.md)
- [gcloud CLI 설치와 프로젝트 설정](phase-7-cloud-run/02-gcloud-setup.md)
- [소스에서 직접 배포](phase-7-cloud-run/03-source-deploy.md)
- [컨테이너 이미지 빌드 후 배포](phase-7-cloud-run/04-image-deploy.md)
- [CI/CD와 운영](phase-7-cloud-run/05-cicd-operations.md)

---

## 📎 부록 (심화)

본문이 "넓고 빠르게" 한 바퀴 도는 입문 과정이라면, 부록은 실무·중급으로 들어가는 **심화 과정**입니다. (인프런 김영한 강사 로드맵의 *JPA 기본편 / Querydsl / 핵심원리 고급편 / MVC 1·2편* 영역을 Kotlin·Spring Boot 4 기준으로 보강)

### 부록 A — JPA 심화
- [영속성 컨텍스트](appendix-a-jpa-advanced/01-persistence-context.md)
- [연관관계 매핑](appendix-a-jpa-advanced/02-associations.md)
- [상속 매핑과 값 타입](appendix-a-jpa-advanced/03-inheritance-embedded.md)
- [프록시와 N+1](appendix-a-jpa-advanced/04-proxy-fetch.md)
- [JPQL](appendix-a-jpa-advanced/05-jpql.md)

### 부록 B — Querydsl
- [왜 Querydsl인가](appendix-b-querydsl/01-why-querydsl.md)
- [Kotlin + Gradle 설정](appendix-b-querydsl/02-setup-kotlin.md)
- [기본 쿼리](appendix-b-querydsl/03-basic-queries.md)
- [동적 쿼리와 조인](appendix-b-querydsl/04-dynamic-and-join.md)
- [DTO 프로젝션 & 리포지토리 통합](appendix-b-querydsl/05-dto-and-repository.md)

### 부록 C — AOP / 프록시 고급
- [프록시와 동적 프록시](appendix-c-aop/01-proxy-and-decorator.md)
- [Spring AOP 실전](appendix-c-aop/02-spring-aop.md)
- [함정과 내부 동작](appendix-c-aop/03-pitfalls-and-internals.md)

### 부록 D — Spring MVC 내부 원리 & SSR
- [DispatcherServlet과 요청 흐름](appendix-d-mvc-internals/01-dispatcher-servlet.md)
- [Thymeleaf 서버 사이드 렌더링](appendix-d-mvc-internals/02-thymeleaf-ssr.md)
- [필터와 인터셉터](appendix-d-mvc-internals/03-filter-interceptor.md)
- [쿠키·세션과 로그인](appendix-d-mvc-internals/04-session-login.md)

---

## 📚 공식 문서

- [Spring Framework Reference](https://docs.spring.io/spring-framework/reference/overview.html)
- [Spring Boot Reference](https://docs.spring.io/spring-boot/index.html)
- [Spring 공식 사이트](https://spring.io/)
- [Spring Initializr](https://start.spring.io/)

> 본 문서의 모든 버전·API는 **2026년 7월 25일** 기준 공식 문서·Spring Boot 4.1.0 BOM·Spring Initializr 실제 출력으로 검증했습니다.
