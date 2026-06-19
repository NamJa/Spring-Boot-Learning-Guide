- [🏠 홈](README.md)

- **Phase 0: Spring 핵심 개념**
  - [서버 사이드 개발 입문](phase-0-spring-fundamentals/00-server-side-intro.md)
  - [Spring & Spring Boot 입문](phase-0-spring-fundamentals/01-what-is-spring.md)
  - [IoC 컨테이너와 의존성 주입](phase-0-spring-fundamentals/02-ioc-and-di.md)
  - [Bean 생명주기와 스코프](phase-0-spring-fundamentals/03-bean-lifecycle-scope.md)
  - [자동 설정과 스타터](phase-0-spring-fundamentals/04-auto-configuration.md)
  - [Spring MVC vs WebFlux](phase-0-spring-fundamentals/05-mvc-vs-webflux.md)

- **Phase 1: 프로젝트 설정**
  - [개발 환경 설정](phase-1-project-setup/01-environment-setup.md)
  - [Spring Initializr로 프로젝트 생성](phase-1-project-setup/02-create-project.md)
  - [프로젝트 구조 해부](phase-1-project-setup/03-project-structure.md)
  - [build.gradle.kts 해부](phase-1-project-setup/04-build-gradle-kts.md)
  - [application.yml 설정](phase-1-project-setup/05-application-yml.md)

- **Phase 2: 첫 번째 REST API**
  - [진입점 — @SpringBootApplication](phase-2-first-api/01-application-entry-point.md)
  - [DTO와 JSON 직렬화](phase-2-first-api/02-dto-and-serialization.md)
  - [@RestController 구현](phase-2-first-api/03-rest-controller.md)
  - [Service 계층과 DI](phase-2-first-api/04-service-layer.md)
  - [로컬 실행과 테스트](phase-2-first-api/05-local-run-and-test.md)

- **Phase 3: 데이터 영속성 (Spring Data JPA)**
  - [Spring Data JPA 개념](phase-3-data-jpa/01-jpa-concepts.md)
  - [Entity 매핑 (Kotlin)](phase-3-data-jpa/02-entity-mapping.md)
  - [Repository 인터페이스](phase-3-data-jpa/03-repository.md)
  - [트랜잭션 관리](phase-3-data-jpa/04-transactions.md)
  - [데이터베이스 설정 (H2 / PostgreSQL)](phase-3-data-jpa/05-database-setup.md)

- **Phase 4: 검증 · 예외 · 설정**
  - [Bean Validation 입력 검증](phase-4-validation-config/01-bean-validation.md)
  - [전역 예외 처리](phase-4-validation-config/02-exception-handling.md)
  - [외부화된 설정과 프로파일](phase-4-validation-config/03-profiles-config.md)
  - [@ConfigurationProperties](phase-4-validation-config/04-configuration-properties.md)

- **Phase 5: 실전 기능 (Spring Boot 4)**
  - [선언적 HTTP 클라이언트](phase-5-production-features/01-http-interface-client.md)
  - [Spring Security 7 기초](phase-5-production-features/02-security-basics.md)
  - [Actuator와 관측성](phase-5-production-features/03-actuator-observability.md)
  - [테스트 전략](phase-5-production-features/04-testing.md)

- **Phase 6: 빌드 & 배포**
  - [실행 가능 JAR 빌드](phase-6-build-deploy/01-executable-jar.md)
  - [Docker 컨테이너화](phase-6-build-deploy/02-docker.md)
  - [GraalVM 네이티브 이미지](phase-6-build-deploy/03-native-image.md)
  - [프로파일별 배포 & 운영](phase-6-build-deploy/04-deploy-operations.md)

- **Phase 7: Google Cloud & Cloud Run 배포**
  - [Cloud Run 핵심 개념](phase-7-cloud-run/01-cloud-run-concepts.md)
  - [gcloud CLI 설치와 프로젝트 설정](phase-7-cloud-run/02-gcloud-setup.md)
  - [소스에서 직접 배포](phase-7-cloud-run/03-source-deploy.md)
  - [컨테이너 이미지 빌드 후 배포](phase-7-cloud-run/04-image-deploy.md)
  - [CI/CD와 운영](phase-7-cloud-run/05-cicd-operations.md)
