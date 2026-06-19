# 소스에서 직접 배포 (가장 간단)

이제 진짜 배포입니다. Cloud Run에는 배포 방법이 여러 가지지만, 가장 빠르게 결과를 보는 길은 **소스 디렉터리에서 바로 배포**하는 것입니다. 명령은 단 한 줄입니다.

```bash
gcloud run deploy book-api --source . \
  --region asia-northeast3 \
  --allow-unauthenticated
```

이 한 줄이 내부에서 무슨 일을 하는지부터 보겠습니다.

## 1. 무슨 일이 벌어지는가

```
  로컬 소스 (.)
      │  gcloud가 코드를 업로드
      ▼
  ┌──────────────────────────────────────────────┐
  │ Cloud Build                                    │
  │  ├─ Dockerfile이 있으면? → 그 Dockerfile로 빌드 │
  │  └─ 없으면? → Buildpacks가 Gradle/Java 자동 감지 │
  │              → 이미지를 알아서 만들어 줌          │
  └──────────────────────────────────────────────┘
      │  완성된 이미지 push
      ▼
  Artifact Registry (이미지 저장소)
      │  배포
      ▼
  Cloud Run: 새 Revision 생성
      │
      ▼
  서비스 URL 발급
  https://book-api-abc123-du.a.run.app
```

## 2. Buildpacks: Dockerfile 없이 빌드되는 마법

`--source .`로 배포할 때 디렉터리에 **Dockerfile이 없으면** Cloud Build는 **buildpacks**를 사용합니다. Buildpacks는 소스를 들여다보고 "아, `build.gradle.kts`와 Gradle wrapper가 있네, Spring Boot Java 앱이군" 하고 **자동으로 컨테이너 이미지를 만들어 줍니다**. JDK 선택, 의존성 다운로드, `bootJar` 실행, 실행 명령 설정까지 알아서 합니다.

- **Dockerfile이 없으면**: buildpacks가 Gradle Spring Boot 프로젝트를 자동 감지해 이미지를 생성.
- **Dockerfile이 있으면**(예: [Phase 6](../phase-6-build-deploy/README.md)에서 만든 멀티 스테이지 Dockerfile): buildpacks 대신 **그 Dockerfile**을 사용해 빌드.

즉, 빠르게 띄우고 싶으면 Dockerfile 없이 그냥 배포하고, 빌드 과정을 직접 통제하고 싶으면 Dockerfile을 두면 됩니다.

> **팁**: buildpacks는 JDK 버전을 자동 선택합니다. 특정 버전(JDK 21)을 강제하려면 `gradle.properties`나 buildpacks 환경 변수로 지정할 수 있지만, 보통은 자동으로도 잘 동작합니다.

## 3. PORT: Cloud Run이 포트를 주입한다

Cloud Run은 컨테이너에 **`PORT` 환경 변수**를 주입하고, 컨테이너가 그 포트에서 HTTP를 받기를 기대합니다. 기본값은 `8080`이지만 Cloud Run이 다른 값을 줄 수도 있으므로, **`PORT`를 읽도록** 설정하는 것이 안전합니다.

Spring Boot는 `SERVER_PORT`/`PORT` 환경 변수를 인식하지만, `application.yml`에 명시적으로 박아 두는 것을 강력히 권장합니다.

```yaml
# src/main/resources/application.yml
server:
  port: ${PORT:8080}   # PORT가 있으면 그 값, 없으면 8080
```

이렇게 해 두면 로컬에서는 `8080`으로, Cloud Run에서는 주입된 `PORT`로 자동으로 동작합니다. **이 설정을 빼먹으면** Cloud Run이 "컨테이너가 PORT에서 응답하지 않는다"며 배포에 실패하는, 가장 흔한 함정에 빠집니다.

## 4. 플래그 완전 정복

배포를 세밀하게 제어하는 주요 플래그입니다.

```bash
gcloud run deploy book-api \
  --source . \
  --region asia-northeast3 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 2 \
  --port 8080 \
  --set-env-vars SPRING_PROFILES_ACTIVE=prod \
  --allow-unauthenticated
```

| 플래그 | 의미 |
| --- | --- |
| `--source .` | 현재 디렉터리 소스로 빌드 후 배포 |
| `--region` | 배포 리전(기본 리전 설정했다면 생략 가능) |
| `--memory 512Mi` | 인스턴스 메모리(Spring Boot는 512Mi~1Gi 권장) |
| `--cpu 1` | vCPU 수 |
| `--min-instances 0` | 최소 인스턴스(0이면 scale to zero, 콜드 스타트 발생) |
| `--max-instances 2` | 최대 인스턴스 상한(비용 폭주 방지) |
| `--port 8080` | 컨테이너가 리스닝하는 포트 |
| `--set-env-vars K=V` | 환경 변수 주입(쉼표로 여러 개) |
| `--allow-unauthenticated` | 인증 없이 누구나 접근 허용(공개 API) |
| `--no-allow-unauthenticated` | 인증된 호출만 허용(비공개) |

### 인증: 공개 vs 비공개

- `--allow-unauthenticated`: URL만 알면 누구나 호출 가능. **공개 REST API**라면 이걸 씁니다.
- `--no-allow-unauthenticated`: IAM으로 인증된 호출만 허용. 내부용·관리용 서비스에 사용.

### prod 프로파일 활성화

Spring Boot의 프로파일을 환경 변수로 켭니다. `SPRING_PROFILES_ACTIVE=prod`를 주입하면 `application-prod.yml`이 적용됩니다([Phase 3](../phase-3-data-jpa/README.md)에서 만든 prod 프로파일과 연결됩니다).

```bash
--set-env-vars SPRING_PROFILES_ACTIVE=prod
```

> **콜드 스타트가 신경 쓰인다면** `--min-instances 1`로 항상 하나를 켜 두거나, `--cpu-boost`로 시작을 가속하세요. 가장 확실한 해법은 [Phase 6의 네이티브 이미지](../phase-6-build-deploy/03-native-image.md)입니다.

## 5. `.gcloudignore`: 불필요한 파일 제외

`--source .`는 디렉터리 전체를 업로드합니다. 빌드 산출물·로컬 설정은 올릴 필요가 없으니 `.gcloudignore`로 제외해 업로드 속도와 빌드 안정성을 높입니다(형식은 `.gitignore`와 같음).

```gitignore
# .gcloudignore
.git
.gitignore
.idea/
*.iml
build/
.gradle/
/out
.env
*.log
```

> `.gitignore`가 있으면 gcloud가 기본적으로 그 규칙도 참고합니다. 하지만 `build/` 같은 무거운 디렉터리는 `.gcloudignore`에 명시적으로 넣는 게 안전합니다.

## 6. 배포 결과 읽고 확인하기

배포가 끝나면 마지막 줄에 **서비스 URL**이 출력됩니다.

```
Building using Buildpacks and deploying container to Cloud Run service [book-api] in project [book-api-12345] region [asia-northeast3]
✓ Building and deploying new service... Done.
Service [book-api] revision [book-api-00001-abc] has been deployed
and is serving 100 percent of traffic.
Service URL: https://book-api-abc123-du.a.run.app
```

URL을 변수에 담아 헬스 체크를 호출해 봅시다([Phase 5](../phase-5-production-features/README.md)의 Actuator와 연결).

```bash
# 배포된 서비스 URL을 가져와 변수에 저장
SERVICE_URL=$(gcloud run services describe book-api \
  --region asia-northeast3 --format='value(status.url)')

# Actuator 헬스 체크 호출
curl "$SERVICE_URL/actuator/health"
# {"status":"UP"}  ← 이렇게 나오면 성공!
```

## 7. 재배포

코드를 고친 뒤 다시 배포할 때도 **똑같은 명령**을 실행하면 됩니다. 새 리비전이 만들어지고 트래픽이 자동으로 그쪽으로 넘어갑니다. URL은 그대로입니다.

```bash
gcloud run deploy book-api --source . --region asia-northeast3 --allow-unauthenticated
```

## 8. 자주 묻는 질문 (FAQ)

**Q. 배포가 "Container failed to start. Failed to listen on PORT"로 실패해요.**
A. 가장 흔한 원인은 PORT 설정입니다. `server.port: ${PORT:8080}`이 `application.yml`에 있는지 확인하세요(3절).

**Q. 빌드는 되는데 OOM(메모리 부족)으로 죽어요.**
A. `--memory 1Gi`로 올려 보세요. JVM은 512Mi에서 빠듯할 수 있습니다.

**Q. 첫 요청이 너무 느려요.**
A. 콜드 스타트입니다. `--min-instances 1` 또는 `--cpu-boost`, 궁극적으로 네이티브 이미지를 고려하세요(4절).

**Q. 매번 빌드가 오래 걸려요. 더 빠른 방법은?**
A. 이미지를 미리 빌드해 올리는 방식이 있습니다. 다음 장에서 다룹니다.

## 다음 단계

`--source` 배포는 편하지만, 빌드를 직접 통제하거나 CI에서 다루려면 **이미지를 미리 빌드**하는 편이 낫습니다. 다음 장에서 살펴봅시다.

➡️ **[4. 컨테이너 이미지 빌드 후 배포](04-image-deploy.md)**
