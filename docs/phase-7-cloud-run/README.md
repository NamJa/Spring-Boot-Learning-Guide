# Phase 7: Google Cloud & Cloud Run 배포

Phase 6에서 우리는 Spring Boot 애플리케이션을 **실행 가능한 JAR**, **Docker 이미지**, 그리고 **GraalVM 네이티브 이미지**로 패키징하는 법을 배웠습니다. 이제 그 산출물을 **실제로 인터넷에 올려** 누구나 접근할 수 있는 서비스로 만들 차례입니다.

## 왜 매니지드/서버리스 플랫폼인가?

직접 서버를 운영하려면 생각보다 할 일이 많습니다.

- 리눅스 VM을 빌리고 OS를 설치·패치하고 방화벽을 설정한다.
- JDK를 깔고, JAR을 올리고, `systemd` 서비스로 등록한다.
- HTTPS 인증서(Let's Encrypt 등)를 발급하고 90일마다 갱신한다.
- 트래픽이 몰리면 서버를 늘리고(스케일 아웃), 한가하면 줄여야 한다.
- 24시간 켜둔 서버 비용을 트래픽이 없는 새벽에도 그대로 낸다.

**서버리스(serverless)** 플랫폼은 이 모든 일을 플랫폼이 대신 해 줍니다. 여러분은 "이 컨테이너를 실행해 줘"라고 말하기만 하면, 나머지(HTTPS, 오토스케일링, 로드밸런싱, 인프라 패치)는 클라우드가 책임집니다. 트래픽이 없으면 인스턴스를 **0개로 줄여** 비용도 0에 수렴합니다.

## Cloud Run 한 줄 요약

> **Cloud Run**은 "컨테이너 이미지를 던져주면 구글이 알아서 실행하고, HTTPS URL을 붙이고, 요청량에 따라 0에서 N개까지 자동으로 늘렸다 줄였다 하고, 쓴 만큼만 과금하는" 컨테이너 기반 서버리스 플랫폼입니다.

Spring Boot 팀과 Google 양쪽 모두 Cloud Run 배포를 공식 문서로 안내할 만큼, JVM 웹 애플리케이션의 배포처로 잘 검증되어 있습니다.

## 이 Phase에서 배우는 것

| 페이지 | 내용 |
| --- | --- |
| [1. Cloud Run 핵심 개념](01-cloud-run-concepts.md) | 서비스/리비전/인스턴스/동시성/콜드 스타트, 제약 조건, 무료 티어, 다른 컴퓨팅 옵션과의 비교 |
| [2. gcloud CLI 설치와 프로젝트 설정](02-gcloud-setup.md) | gcloud 설치, 프로젝트 생성, 결제 연결, 예산 알림, API 활성화 |
| [3. 소스에서 직접 배포](03-source-deploy.md) | `gcloud run deploy --source .` 한 방으로 배포하는 가장 쉬운 길 |
| [4. 컨테이너 이미지 빌드 후 배포](04-image-deploy.md) | 이미지를 직접 빌드해 Artifact Registry에 올리고 배포 |
| [5. CI/CD와 운영](05-cicd-operations.md) | GitHub Actions 자동 배포, Secret Manager, Cloud SQL, 프로브, 로그·모니터링 |

> **선수 지식**: 이 Phase는 [Phase 6](../phase-6-build-deploy/README.md)에서 만든 JAR/Docker/네이티브 이미지 산출물 위에서 진행됩니다. 또한 [Phase 5](../phase-5-production-features/README.md)의 Actuator 헬스 체크, [Phase 3](../phase-3-data-jpa/README.md)의 JPA prod 프로파일 설정을 활용합니다. 아직 보지 않았다면 먼저 훑어보길 권합니다.

## 다음 단계

이제 Cloud Run이 무엇인지, 어떤 개념들로 이루어져 있는지부터 차근차근 살펴봅시다.

➡️ **[1. Cloud Run 핵심 개념](01-cloud-run-concepts.md)**
