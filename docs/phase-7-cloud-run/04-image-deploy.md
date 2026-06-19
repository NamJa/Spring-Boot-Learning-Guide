# 컨테이너 이미지 빌드 후 배포

`--source` 배포는 손쉽지만, 빌드를 Cloud Build에 맡깁니다. 실무에서는 이미지를 **미리 빌드해 두고** 그 이미지를 배포하고 싶을 때가 많습니다. 이 방식의 흐름과 명령을 익혀 봅시다.

## 1. 왜 이미지를 미리 빌드하는가

| 동기 | 설명 |
| --- | --- |
| **빌드 통제** | JDK 버전, 빌드 단계, 캐시를 내가 정확히 제어 |
| **CI 친화적** | GitHub Actions 등에서 빌드 → 테스트 → 푸시 파이프라인 구성([05장](05-cicd-operations.md)) |
| **Cloud Build 비용/시간 회피** | 매 배포마다 클라우드에서 다시 빌드하지 않음 |
| **재현성** | "이 이미지 태그 = 이 코드"가 명확. 롤백·감사에 유리 |

이미지를 만드는 방법은 세 가지입니다.

1. **Spring Boot `bootBuildImage`** (Paketo buildpacks): Dockerfile 없이 Gradle 태스크 한 방.
2. **멀티 스테이지 Dockerfile**: [Phase 6](../phase-6-build-deploy/02-docker.md)에서 만든 것을 그대로 사용.
3. **JIB**: Google이 만든 Gradle/Maven 플러그인. Docker 데몬 없이 이미지를 만들고 레지스트리에 바로 푸시(여기서는 간략히만 언급).

### 방법 A: Spring Boot bootBuildImage

Spring Boot에는 Paketo buildpacks로 이미지를 만드는 태스크가 내장돼 있습니다. Docker 데몬은 필요하지만 Dockerfile은 필요 없습니다.

```bash
./gradlew bootBuildImage
# → 로컬에 docker.io/library/book-api:0.0.1-SNAPSHOT 이미지 생성
```

### 방법 B: 멀티 스테이지 Dockerfile

Phase 6에서 만든 Dockerfile을 그대로 빌드합니다.

```bash
docker build -t book-api:1.0 .
```

> **방법 C: JIB**: `com.google.cloud.tools.jib` 플러그인을 적용하면 `./gradlew jib`만으로 레이어 최적화된 이미지를 Docker 없이 레지스트리에 직접 푸시할 수 있습니다. 여기서는 개념만 짚고 넘어갑니다.

## 2. Artifact Registry: 이미지 보관소 만들기

Cloud Run은 **Artifact Registry**(GCP의 컨테이너 이미지 저장소)에 있는 이미지를 배포합니다. 먼저 저장소(repository)를 만듭니다.

```bash
gcloud artifacts repositories create book-repo \
  --repository-format=docker \
  --location=asia-northeast3 \
  --description="Book API container images"
```

이제 Docker가 이 레지스트리에 푸시할 수 있도록 인증을 설정합니다.

```bash
gcloud auth configure-docker asia-northeast3-docker.pkg.dev
```

이미지 전체 경로(레지스트리 주소)는 다음 형식입니다.

```
asia-northeast3-docker.pkg.dev/<PROJECT_ID>/<REPO>/<IMAGE>:<TAG>
└────────── 리전 호스트 ──────────┘ └─프로젝트─┘ └저장소┘ └이미지┘ └태그┘

예: asia-northeast3-docker.pkg.dev/book-api-12345/book-repo/book-api:1.0
```

## 3. 태그 붙이고 푸시하기

로컬 이미지에 레지스트리 경로로 태그를 달고 푸시합니다.

```bash
# 편의를 위한 변수 (본인 PROJECT_ID로 교체)
PROJECT_ID=book-api-12345
IMAGE=asia-northeast3-docker.pkg.dev/$PROJECT_ID/book-repo/book-api:1.0

# 로컬 이미지에 레지스트리 태그 부여
docker tag book-api:1.0 $IMAGE

# Artifact Registry로 푸시
docker push $IMAGE
```

## 4. 이미지로 배포

푸시된 이미지를 Cloud Run에 배포합니다. `--source` 대신 `--image`를 씁니다.

```bash
gcloud run deploy book-api \
  --image asia-northeast3-docker.pkg.dev/$PROJECT_ID/book-repo/book-api:1.0 \
  --region asia-northeast3 \
  --memory 512Mi \
  --port 8080 \
  --set-env-vars SPRING_PROFILES_ACTIVE=prod \
  --allow-unauthenticated
```

빌드 과정이 없으니 `--source` 배포보다 훨씬 빠릅니다. 나머지 플래그(`--memory`, `--min/max-instances`, `--allow-unauthenticated` 등)는 [3장](03-source-deploy.md)과 동일합니다.

## 5. bootBuildImage로 곧바로 Artifact Registry에 푸시

`bootBuildImage`의 `imageName`을 Artifact Registry 경로로 지정하고 `--publishImage`를 주면, **빌드와 동시에 레지스트리로 푸시**됩니다. 중간의 `docker tag`/`docker push`가 사라집니다.

```bash
./gradlew bootBuildImage \
  --imageName=asia-northeast3-docker.pkg.dev/book-api-12345/book-repo/book-api:1.0 \
  --publishImage
```

`build.gradle.kts`에 박아 둘 수도 있습니다.

```kotlin
// build.gradle.kts
tasks.named<org.springframework.boot.gradle.tasks.bundling.BootBuildImage>("bootBuildImage") {
    imageName.set("asia-northeast3-docker.pkg.dev/book-api-12345/book-repo/book-api:1.0")
    publish.set(true)
    // 레지스트리 인증 정보(docker 설정에서 자동으로 읽힘)
}
```

푸시가 끝나면 위 4절의 `gcloud run deploy --image`로 배포하면 됩니다.

> **네이티브 이미지로 더 작고 빠르게**: [Phase 6의 GraalVM 네이티브 이미지](../phase-6-build-deploy/03-native-image.md)를 빌드하면 이미지 크기가 작고 시작이 수십 ms로 빨라집니다. `./gradlew bootBuildImage`에 네이티브 빌드팩 설정을 더하거나 네이티브 Dockerfile을 쓰면, scale-to-zero 환경에서 콜드 스타트 걱정 없이 운영할 수 있습니다.

## 6. 두 방식 비교

| | **소스 배포 (`--source`)** | **이미지 배포 (`--image`)** |
| --- | --- | --- |
| 사전 준비 | 없음(코드만) | 이미지 빌드 + Artifact Registry 푸시 |
| 빌드 위치 | Cloud Build(클라우드) | 내 PC / CI |
| 배포 속도 | 느림(매번 빌드) | 빠름(빌드 생략) |
| 빌드 통제력 | 낮음(buildpacks 자동) | 높음(내가 전부 제어) |
| CI/CD 적합성 | 보통 | 높음 |
| 적합한 상황 | 빠른 실험, 학습 | 실무, 재현성 중요, 파이프라인 |

**정리**: 빠르게 띄워 보려면 `--source`, 빌드를 통제하고 파이프라인에 태우려면 `--image`입니다. 학습 단계에서는 `--source`로 시작해, 실무로 갈수록 이미지 빌드 + CI/CD로 넘어가는 흐름이 자연스럽습니다.

## 다음 단계

이미지 빌드와 배포를 손으로 해 봤으니, 이제 이걸 **자동화**할 차례입니다. GitHub에 푸시하면 알아서 배포되는 CI/CD 파이프라인과 실전 운영 노하우를 마지막 장에서 다룹니다.

➡️ **[5. CI/CD와 운영](05-cicd-operations.md)**
