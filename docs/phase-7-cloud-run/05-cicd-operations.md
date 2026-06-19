# CI/CD와 운영

지금까지는 손으로 배포했습니다. 마지막 장에서는 **GitHub에 푸시하면 자동으로 배포**되는 파이프라인을 만들고, 환경 변수·비밀·데이터베이스·헬스 프로브·로그까지 **실전 운영**에 필요한 것들을 정리합니다.

## 1. GitHub Actions로 자동 배포

목표: `main` 브랜치에 푸시하면 → 테스트·빌드 → Cloud Run 배포까지 자동.

### 인증: Workload Identity Federation (권장)

GitHub Actions가 GCP에 배포하려면 인증이 필요합니다. 예전에는 서비스 계정의 **JSON 키 파일**을 GitHub Secret에 넣었지만, 키 유출 위험이 큽니다. 지금은 **Workload Identity Federation(WIF)** 이 권장됩니다.

> **WIF란?** JSON 키 없이, "이 GitHub 저장소의 워크플로"라는 신원을 GCP가 직접 신뢰하도록 연결하는 방식입니다. 장기 비밀이 없어 훨씬 안전합니다.

설정은 고수준으로 이렇습니다(한 번만).

1. GCP에 **Workload Identity Pool**과 **Provider**를 만들어 GitHub를 신뢰 발급자로 등록.
2. 배포용 **서비스 계정**을 만들고 `roles/run.admin`, `roles/iam.serviceAccountUser`, (이미지 푸시 시) `roles/artifactregistry.writer`를 부여.
3. 그 서비스 계정을 WIF Provider에 바인딩.
4. GitHub 저장소 Secrets에 `WIF_PROVIDER`(Provider 리소스 경로), `WIF_SERVICE_ACCOUNT`(서비스 계정 이메일), `GCP_PROJECT_ID`를 등록.

### 워크플로 파일

`.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

env:
  PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  REGION: asia-northeast3
  SERVICE: book-api

permissions:
  contents: read
  id-token: write   # WIF에 필수: OIDC 토큰 발급 권한

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: 소스 체크아웃
        uses: actions/checkout@v4

      - name: JDK 21 설정
        uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: '21'

      - name: Gradle 빌드 & 테스트
        run: ./gradlew clean build

      # WIF 기반 인증 (JSON 키 없음)
      - name: GCP 인증
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - name: Cloud Run 배포
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: ${{ env.SERVICE }}
          source: .                       # 소스 배포(buildpacks/Dockerfile)
          region: ${{ env.REGION }}
          flags: >-
            --allow-unauthenticated
            --memory 512Mi
            --port 8080
          env_vars: |
            SPRING_PROFILES_ACTIVE=prod
```

> **대안**: `deploy-cloudrun` 액션 대신 인증 후 `run: gcloud run deploy ... --source .`를 직접 호출해도 됩니다. 이미지를 미리 빌드해 `--image`로 배포하려면 빌드·푸시 스텝([4장](04-image-deploy.md))을 추가하면 됩니다.

## 2. 환경 변수와 비밀(Secret Manager)

DB 비밀번호 같은 민감 정보를 환경 변수에 평문으로 넣는 건 위험합니다. **Secret Manager**에 저장하고 Cloud Run에 마운트하세요.

```bash
# 비밀 생성
echo -n "내DB비밀번호" | gcloud secrets create book-db-password --data-file=-

# 배포 시 비밀을 환경 변수로 주입
gcloud run deploy book-api --source . --region asia-northeast3 \
  --set-secrets SPRING_DATASOURCE_PASSWORD=book-db-password:latest \
  --set-env-vars SPRING_PROFILES_ACTIVE=prod
```

- `--set-env-vars`: 민감하지 않은 일반 설정.
- `--set-secrets`: Secret Manager의 비밀을 환경 변수 또는 파일로 주입.

## 3. Cloud SQL(PostgreSQL) 연결

휘발성 파일 시스템 때문에 영구 데이터는 **Cloud SQL**에 둡니다([Phase 3](../phase-3-data-jpa/README.md)의 prod 프로파일과 연결).

```bash
gcloud run deploy book-api --source . --region asia-northeast3 \
  --add-cloudsql-instances book-api-12345:asia-northeast3:book-db \
  --set-secrets SPRING_DATASOURCE_PASSWORD=book-db-password:latest \
  --set-env-vars SPRING_PROFILES_ACTIVE=prod
```

`--add-cloudsql-instances`는 인스턴스로의 안전한 소켓을 컨테이너에 연결해 줍니다. 애플리케이션은 **Unix 소켓** 경로로 접속합니다. `application-prod.yml` 예:

```yaml
# application-prod.yml
spring:
  datasource:
    # Cloud SQL은 /cloudsql/<INSTANCE_CONNECTION_NAME> 소켓으로 접속
    url: jdbc:postgresql:///bookdb?cloudSqlInstance=book-api-12345:asia-northeast3:book-db&socketFactory=com.google.cloud.sql.postgres.SocketFactory
    username: bookuser
    password: ${SPRING_DATASOURCE_PASSWORD}   # Secret Manager에서 주입
  jpa:
    hibernate:
      ddl-auto: validate            # prod에서는 절대 update/create 금지
```

> Cloud SQL Socket Factory 의존성(`com.google.cloud.sql:postgres-socket-factory`)을 `build.gradle.kts`에 추가해야 합니다.

## 4. 헬스 프로브를 Actuator에 연결

Cloud Run은 컨테이너의 **liveness/readiness 프로브**를 지원합니다. [Phase 5](../phase-5-production-features/README.md)의 Actuator 헬스 그룹과 연결하면 정확한 상태 판정이 가능합니다.

먼저 Spring Boot에서 liveness/readiness 그룹을 노출합니다.

```yaml
# application-prod.yml
management:
  endpoint:
    health:
      probes:
        enabled: true       # /actuator/health/{liveness,readiness} 활성화
  health:
    livenessstate:
      enabled: true
    readinessstate:
      enabled: true
server:
  shutdown: graceful        # 종료 시 진행 중인 요청을 마저 처리
```

- **Liveness 프로브** → `/actuator/health/liveness`: 죽었으면 인스턴스 재시작.
- **Readiness 프로브** → `/actuator/health/readiness`: 준비 안 됐으면 트래픽 제외(예: DB 커넥션 풀 워밍업 전).

Cloud Run 콘솔(또는 YAML 서비스 정의)에서 위 경로로 HTTP 프로브를 지정합니다.

> **Graceful shutdown**: `server.shutdown=graceful`로 두면 Cloud Run이 인스턴스를 줄일 때 진행 중인 요청을 끊지 않고 마무리합니다.

## 5. 스케일링·구조적 로깅·커스텀 도메인

**스케일링 노브**:

```bash
gcloud run services update book-api --region asia-northeast3 \
  --min-instances 1 \      # 콜드 스타트 제거
  --max-instances 5 \      # 상한
  --concurrency 40 \       # 인스턴스당 동시 요청
  --cpu-boost              # 시작 가속
```

**구조적(JSON) 로깅**: Cloud Logging은 JSON 로그를 자동으로 파싱해 필드별 검색·필터를 제공합니다. Spring Boot의 로그를 JSON 포맷(예: `logging.structured.format.console=ecs` 또는 Logback JSON 인코더)으로 내보내면 운영 가시성이 크게 좋아집니다.

**커스텀 도메인**: `*.run.app` 대신 내 도메인을 붙이려면 Cloud Run 도메인 매핑 또는 외부 로드밸런서를 사용합니다(개념만 언급).

## 6. 로그와 모니터링

```bash
# 최근 로그 보기
gcloud run services logs read book-api --region asia-northeast3 --limit 50

# 실시간 추적
gcloud run services logs tail book-api --region asia-northeast3
```

Cloud Console의 Cloud Run 서비스 페이지에서는 **요청 수, 지연 시간(p50/p95/p99), 인스턴스 수, CPU/메모리 사용량, 에러율**을 그래프로 볼 수 있습니다.

## 7. 트러블슈팅

| 증상 | 흔한 원인 | 해결 |
| --- | --- | --- |
| `Container failed to listen on PORT` | PORT 미설정 | `server.port: ${PORT:8080}` 추가([3장](03-source-deploy.md)) |
| OOM으로 인스턴스 강제 종료 | 메모리 부족 | `--memory 1Gi`로 상향, 힙 옵션 점검 |
| 첫 요청 매우 느림 | 콜드 스타트 | `--min-instances 1`, `--cpu-boost`, [네이티브 이미지](../phase-6-build-deploy/03-native-image.md) |
| DB 연결 실패 | Cloud SQL 미연결/URL 오류 | `--add-cloudsql-instances`, 소켓 URL·Secret 확인 |
| 빌드 실패 | Gradle/JDK 문제 | Cloud Build 로그 확인, `.gcloudignore` 점검, JDK 21 명시 |
| 502/503 | readiness 미준비, 타임아웃 | 프로브 경로·`--timeout` 확인 |

## 다음 단계

축하합니다! 🎉 여기까지 왔다면, 여러분은 **IoC/DI와 자동 구성**부터 시작해 **REST API**, **Spring Data JPA**, **검증·보안·관측성**, **JAR/Docker/네이티브 빌드**, 그리고 마침내 **Google Cloud Run으로의 실제 배포와 운영**까지 — Spring Boot 애플리케이션의 한살이(life cycle) 전체를 직접 경험했습니다. Kotlin 개발자로서 Spring 생태계를 자신 있게 다룰 수 있는 토대를 갖춘 셈입니다.

이제 여러분의 코드는 인터넷 어딘가에서 HTTPS URL로 살아 숨 쉬고 있습니다. 다음은 여러분만의 서비스를 만들 차례입니다.

- 🏠 **[가이드 홈으로 돌아가기](../README.md)**
- 📖 Cloud Run 공식 Java 배포 가이드: <https://docs.cloud.google.com/run/docs/quickstarts/build-and-deploy/deploy-java-service>
- 📖 Spring Boot 공식 문서: <https://docs.spring.io/spring-boot/index.html>

수고하셨습니다. Happy shipping! 🚀
