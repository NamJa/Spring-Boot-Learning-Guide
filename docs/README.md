# Spring Boot 학습 가이드 (Kotlin)

[![Live Site](https://img.shields.io/badge/Live-namja.github.io-6DB33F?style=flat-square&logo=githubpages&logoColor=white)](https://namja.github.io/Spring-Boot-Learning-Guide/)
[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-4.1.0-6DB33F?style=flat-square&logo=springboot&logoColor=white)](https://docs.spring.io/spring-boot/index.html)
[![Kotlin](https://img.shields.io/badge/Kotlin-2.3.21-7F52FF?style=flat-square&logo=kotlin&logoColor=white)](https://kotlinlang.org/)
[![JDK](https://img.shields.io/badge/JDK-21%20LTS-orange?style=flat-square&logo=openjdk&logoColor=white)](https://adoptium.net/)

> **Kotlin으로 배우는 Spring Boot 4 — 핵심 개념부터 REST API · 데이터 · 보안 · 배포까지**

Kotlin은 알지만 Spring 생태계는 처음인 분들을 위한 실습형 입문 가이드입니다. IoC/DI 같은 Spring의 핵심 철학부터 시작해, Kotlin으로 REST API를 만들고, Spring Data JPA로 데이터를 다루며, 검증·예외·보안·관측성을 더한 뒤, JAR·Docker·네이티브 이미지로 배포하는 전 과정을 단계별로 다룹니다.

## 📦 기준 버전 (2026-06-20 기준)

| 구성요소 | 버전 | 비고 |
|---|---|---|
| **Spring Boot** | 4.1.0 | 2026-06-10 GA |
| **Spring Framework** | 7.0.8+ | Spring Boot 4.1의 베이스라인 |
| **Kotlin** | 2.3.21 | Spring Boot 4.1.0 BOM이 관리 (스탠드얼론 최신은 2.4.0) |
| **JDK** | 17 (최소) ~ 26 | 빌드·런타임. 본 가이드는 LTS인 JDK 21 기준 |
| **Gradle** | 8.14+ / 9.x | Kotlin DSL(`build.gradle.kts`) 사용 |
| **Maven** | 3.6.3+ | (가이드는 Gradle 중심) |
| **내장 서버** | Tomcat 11.0.x (Servlet 6.1) | 기본값. Jetty 12.1.x도 지원 |
| **GraalVM** | Community 25 | 네이티브 이미지 |

> Spring Boot 4.1.0은 **Java 17을 최소 버전**으로 요구하며 **Java 26까지** 호환됩니다. 본 가이드는 가장 무난한 LTS인 **JDK 21**을 기준으로 작성했습니다. Spring Boot 3.5.x도 여전히 유지보수되는 안정 버전이지만, 본 가이드는 최신 메이저인 **4.1.0**을 기준으로 합니다.
>
> **Kotlin 버전에 관하여:** 2026-06-20 기준 Kotlin의 스탠드얼론 최신 릴리스는 **2.4.0**(2026-06-03)이지만, Spring Boot 4.1.0의 BOM은 **Kotlin 2.3.21**을 관리합니다. Spring Boot 프로젝트에서는 BOM이 검증한 버전을 그대로 쓰는 것이 안전하므로, 본 가이드는 **2.3.21**을 기준으로 합니다. (Spring Boot 4.0.0은 2.2.21을 관리했습니다.)

## 🗺️ 학습 경로

Spring이 처음이라면 **Phase 0**부터 순서대로 읽어 IoC/DI와 자동 설정의 원리를 먼저 이해하세요. 개념이 익숙하다면 **Phase 1**부터 바로 실습을 시작해도 좋습니다.

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

> 본 문서의 모든 버전·API는 **2026년 6월 20일** 기준 공식 문서로 검증했습니다.
