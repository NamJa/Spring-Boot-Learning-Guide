# Phase 6 · 빌드 & 배포

Phase 5까지 우리는 도서(Book) 관리 REST API에 데이터베이스, 검증, 예외 처리, 보안, 관측성, 테스트까지 갖췄습니다. 이제 남은 것은 이 애플리케이션을 **내 노트북 밖**으로 내보내는 일입니다. Phase 6에서는 완성된 Book API를 **실행 가능한 산출물**로 빌드하고, **컨테이너**로 패키징하고, **운영 환경**에 배포하는 전체 흐름을 다룹니다.

Kotlin 개발자라면 `java -jar`로 단일 jar를 실행해 본 경험이 있을 것입니다. Spring Boot는 이 모델을 한 단계 더 발전시켜 **실행 가능한 layered jar**, **Cloud Native Buildpacks**, **GraalVM 네이티브 이미지**라는 세 가지 패키징 전략을 제공합니다. 각 전략의 장단점을 이해하고, 12-factor 원칙에 따라 환경변수로 설정을 주입하며, 프로덕션 체크리스트를 점검하는 것이 이 마지막 Phase의 목표입니다.

## 이 Phase에서 다루는 내용

| # | 문서 | 핵심 주제 |
|---|------|-----------|
| 1 | [실행 가능 JAR 빌드](01-executable-jar.md) | `bootJar`, layered jar 구조, `bootRun` vs `bootJar`, 실행 옵션 |
| 2 | [Docker 컨테이너화](02-docker.md) | Buildpacks(`bootBuildImage`), 멀티 스테이지 Dockerfile, `.dockerignore`, 환경변수 |
| 3 | [GraalVM 네이티브 이미지](03-native-image.md) | AOT/네이티브 컴파일, `nativeCompile`, 런타임 힌트, JVM vs 네이티브 비교 |
| 4 | [프로파일별 배포 & 운영](04-deploy-operations.md) | 12-factor 설정, 컨테이너 플랫폼 배포, 프로덕션 체크리스트, 운영/트러블슈팅 |

## 학습 목표

이 Phase를 마치면 다음을 할 수 있습니다.

- `./gradlew bootJar`로 **실행 가능한 layered jar**를 빌드하고 `java -jar`로 실행할 수 있다.
- **Buildpacks**와 **직접 작성한 Dockerfile** 두 방식으로 컨테이너 이미지를 만들 수 있다.
- **GraalVM 네이티브 이미지**가 무엇이고 언제 쓰며, 언제 쓰지 말아야 하는지 판단할 수 있다.
- **환경변수 기반 설정**으로 같은 이미지를 여러 환경에 배포할 수 있다.
- **프로덕션 체크리스트**(시크릿, 헬스 프로브, 그레이스풀 셧다운, 마이그레이션)를 점검할 수 있다.

> [!TIP]
> Phase 4에서 만든 `prod` 프로파일과 Phase 5의 Actuator 헬스 엔드포인트가 이번 Phase에서 본격적으로 활용됩니다. 두 문서를 한 번 복습하고 시작하면 흐름이 매끄럽습니다.

## 다음 단계

먼저 모든 배포의 출발점인 **실행 가능 JAR** 빌드부터 시작합니다.

→ [실행 가능 JAR 빌드](01-executable-jar.md)
