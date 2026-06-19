# Docker 컨테이너화

실행 가능 jar를 손에 넣었으니, 이제 어디서든 동일하게 실행되는 **컨테이너 이미지**로 패키징할 차례입니다. 컨테이너는 JDK 버전, OS 라이브러리, 환경변수까지 함께 봉인하므로 "내 노트북에선 됐는데" 문제를 없애 줍니다.

Spring Boot에서 컨테이너 이미지를 만드는 길은 크게 두 가지입니다.

1. **Cloud Native Buildpacks** — Dockerfile 없이 `./gradlew bootBuildImage`로 자동 생성
2. **직접 작성한 멀티 스테이지 Dockerfile** — 세밀한 제어가 필요할 때

둘 다 실무에서 쓰이며, 트레이드오프가 다릅니다. 차례로 살펴봅니다.

## 방법 A — Cloud Native Buildpacks (`bootBuildImage`)

Spring Boot Gradle 플러그인에는 **Buildpacks**를 이용해 이미지를 만드는 `bootBuildImage` 태스크가 내장돼 있습니다. **Dockerfile을 한 줄도 작성하지 않고도** OCI 이미지가 만들어집니다.

```bash
# Docker 데몬이 떠 있어야 함
./gradlew bootBuildImage
```

내부적으로는 **Paketo Buildpacks**가 동작합니다. 우리 jar를 분석해 적절한 JRE, 메모리 계산기, layered jar 추출, 시작 스크립트까지 자동으로 구성해 줍니다. 사람이 OS 패치나 JRE 선택을 신경 쓸 필요가 없는 것이 가장 큰 장점입니다.

### 이미지 이름과 레지스트리 push 설정

```kotlin
// build.gradle.kts
tasks.named<org.springframework.boot.gradle.tasks.bundling.BootBuildImage>("bootBuildImage") {
    imageName.set("registry.example.com/book-api:${project.version}")

    // 빌드 후 레지스트리로 바로 push
    publish.set(false) // true면 push (아래 인증 필요)

    // 환경변수로 빌드 시점 옵션 전달 (예: BP_JVM_VERSION)
    environment.set(mapOf("BP_JVM_VERSION" to "21"))

    docker {
        publishRegistry {
            url.set("https://registry.example.com")
            username.set(System.getenv("REGISTRY_USER"))
            password.set(System.getenv("REGISTRY_TOKEN"))
        }
    }
}
```

커맨드라인에서도 옵션을 줄 수 있습니다.

```bash
./gradlew bootBuildImage \
  --imageName=registry.example.com/book-api:1.0.0 \
  --publishImage
```

> [!TIP]
> Buildpacks 방식은 Dockerfile 유지보수 부담이 없고, OS 보안 패치를 buildpack 업데이트로 흡수할 수 있어 **운영팀이 선호**합니다. 단, 빌드에 인터넷(빌더 이미지 pull)이 필요하고 세밀한 커스터마이징은 Dockerfile보다 어렵습니다.

## 방법 B — 직접 작성한 멀티 스테이지 Dockerfile

이미지 구성을 완전히 통제하고 싶거나, 사내 베이스 이미지를 강제해야 할 때는 Dockerfile을 직접 씁니다. 핵심은 두 가지입니다.

- **멀티 스테이지 빌드** — 무거운 JDK·Gradle은 빌드 단계에만 두고, 런타임 이미지는 가벼운 JRE만 포함
- **layered jar 활용** — 의존성 레이어와 애플리케이션 레이어를 분리해 Docker 캐시를 극대화

프로젝트 루트에 다음 `Dockerfile`을 둡니다.

```dockerfile
# ===== 1단계: 빌드 스테이지 =====
# JDK 21 + Gradle 환경에서 layered jar 빌드
FROM eclipse-temurin:21-jdk AS builder
WORKDIR /workspace

# 의존성 정의 파일 먼저 복사 → 의존성 다운로드 레이어 캐싱
COPY gradlew settings.gradle.kts build.gradle.kts ./
COPY gradle ./gradle
RUN ./gradlew dependencies --no-daemon || true

# 소스 복사 후 실행 가능 jar 빌드 (테스트는 CI에서 별도 수행)
COPY src ./src
RUN ./gradlew bootJar --no-daemon

# layered jar를 레이어별 디렉터리로 추출
RUN java -Djarmode=tools -jar build/libs/*.jar extract --layers --destination extracted

# ===== 2단계: 런타임 스테이지 =====
# 가벼운 JRE 21만 포함 (JDK 불필요)
FROM eclipse-temurin:21-jre AS runtime
WORKDIR /app

# 보안: root가 아닌 전용 사용자로 실행
RUN groupadd --system spring && useradd --system --gid spring spring
USER spring:spring

# 변경 빈도가 낮은 레이어부터 복사 → 위쪽 레이어일수록 캐시 재사용 잘 됨
COPY --from=builder /workspace/extracted/dependencies/ ./
COPY --from=builder /workspace/extracted/spring-boot-loader/ ./
COPY --from=builder /workspace/extracted/snapshot-dependencies/ ./
COPY --from=builder /workspace/extracted/application/ ./

EXPOSE 8080

# 컨테이너 메모리에 맞춰 힙 자동 조정
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", \
            "org.springframework.boot.loader.launch.JarLauncher"]
```

> [!NOTE]
> 추출된 레이어는 `JarLauncher`가 인식하는 디렉터리 구조(`BOOT-INF/` 등)로 풀립니다. 따라서 ENTRYPOINT는 jar가 아니라 **`JarLauncher` 클래스**를 직접 실행합니다. 각 `COPY`가 별도 Docker 레이어가 되고, 코드만 바뀌면 마지막 `application` 레이어만 다시 만들어집니다.

### .dockerignore

빌드 컨텍스트에서 불필요하거나 민감한 파일을 제외해 빌드를 빠르고 안전하게 만듭니다.

```dockerignore
# 빌드 산출물 (이미지 안에서 새로 빌드함)
build/
.gradle/

# IDE / VCS
.idea/
.git/
*.iml

# 로컬 환경 / 시크릿
.env
*.local.yml
src/main/resources/application-local.yml
```

## 이미지 빌드 & 실행

```bash
# 이미지 빌드
docker build -t book-api:1.0.0 .

# 컨테이너 실행 (8080 포트 매핑)
docker run --rm -p 8080:8080 book-api:1.0.0
```

### 환경변수로 설정 주입

[이전 문서](01-executable-jar.md)에서 본 relaxed binding 덕분에, 모든 설정을 `docker run -e`로 주입할 수 있습니다. 이미지는 그대로 두고 **환경변수만 바꿔** 여러 환경에 배포하는 것이 핵심입니다.

```bash
docker run --rm -p 8080:8080 \
  -e SPRING_PROFILES_ACTIVE=prod \
  -e SERVER_PORT=8080 \
  -e SPRING_DATASOURCE_URL=jdbc:postgresql://db.internal:5432/books \
  -e SPRING_DATASOURCE_USERNAME=book_app \
  -e SPRING_DATASOURCE_PASSWORD="$DB_PASSWORD" \
  book-api:1.0.0
```

> [!WARNING]
> 일부 플랫폼(예: Cloud Run, Heroku)은 리스닝 포트를 **`PORT`** 환경변수로 주입합니다. 이를 받기 위해 `application.yml`에 `server.port: ${PORT:8080}`처럼 기본값과 함께 바인딩해 두면 어떤 플랫폼에서도 동작합니다.

### 헬스 체크

Phase 5에서 노출한 Actuator 헬스 엔드포인트를 컨테이너 헬스 체크에 연결합니다.

```dockerfile
# Dockerfile에 추가 (런타임 스테이지)
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD ["sh", "-c", "wget -qO- http://localhost:8080/actuator/health | grep -q UP"]
```

`docker compose` 환경에서는 다음처럼 선언할 수도 있습니다.

```yaml
# compose.yaml (발췌)
services:
  book-api:
    image: book-api:1.0.0
    ports:
      - "8080:8080"
    environment:
      SPRING_PROFILES_ACTIVE: prod
      SPRING_DATASOURCE_URL: jdbc:postgresql://db:5432/books
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/actuator/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 40s
    depends_on:
      - db
  db:
    image: postgres:17
    environment:
      POSTGRES_DB: books
      POSTGRES_USER: book_app
      POSTGRES_PASSWORD: secret
```

## 두 방법 비교

| 기준 | Buildpacks (`bootBuildImage`) | 직접 Dockerfile |
|------|-------------------------------|-----------------|
| Dockerfile 필요 | ❌ 없음 | ✅ 직접 작성·유지보수 |
| OS 패치 | buildpack 업데이트로 자동 흡수 | 베이스 이미지 직접 관리 |
| 커스터마이징 | 환경변수/빌드팩 한정 | 완전 자유 |
| 빌드 속도 | 첫 빌드는 빌더 pull로 느릴 수 있음 | 캐시 잘 타면 빠름 |
| 적합한 상황 | 표준화·운영 편의 우선 | 사내 베이스 이미지 강제, 세밀한 제어 |

> [!TIP]
> 처음에는 `bootBuildImage`로 빠르게 시작하고, 사내 보안 정책이나 특수 요구사항이 생기면 Dockerfile로 전환하는 흐름을 권합니다.

## 다음 단계

지금까지는 모두 **JVM 위에서** 도는 컨테이너였습니다. 다음은 시작 시간을 수십 밀리초로 줄이는 **GraalVM 네이티브 이미지**를 살펴봅니다.

→ [GraalVM 네이티브 이미지](03-native-image.md)
