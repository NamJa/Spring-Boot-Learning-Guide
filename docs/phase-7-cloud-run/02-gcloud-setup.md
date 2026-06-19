# gcloud CLI 설치와 프로젝트 설정

Cloud Run에 배포하려면 GCP를 명령줄에서 조작하는 도구인 **`gcloud` CLI**(Google Cloud SDK)가 필요합니다. 이 장에서는 설치부터 프로젝트 생성, 결제 연결, 예산 알림, API 활성화까지 한 번에 끝냅니다. 한 번만 해 두면 이후 배포는 명령 한 줄로 끝납니다.

## 1. gcloud CLI 설치

macOS에서는 **Homebrew**로 설치하는 것이 가장 깔끔합니다.

```bash
# Google Cloud SDK 설치
brew install --cask google-cloud-sdk

# 설치 확인
gcloud --version
```

`gcloud --version`을 실행했을 때 `Google Cloud SDK 5xx.x.x` 같은 버전 정보가 나오면 성공입니다.

> **Linux/Windows 사용자**: Homebrew가 없다면 공식 설치 스크립트를 사용하세요. 이 가이드는 macOS + zsh 기준으로 설명합니다.

### zsh 보완: PATH와 자동완성

Homebrew cask로 설치하면 보통 PATH가 자동으로 잡히지만, `gcloud` 명령을 못 찾는다면 `~/.zshrc`에 다음을 추가합니다(Homebrew 경로는 환경에 따라 다를 수 있습니다).

```bash
# ~/.zshrc 에 추가
source "$(brew --prefix)/share/google-cloud-sdk/path.zsh.inc"        # PATH 설정
source "$(brew --prefix)/share/google-cloud-sdk/completion.zsh.inc"  # 명령어 자동완성
```

추가 후 새 터미널을 열거나 `source ~/.zshrc`로 적용합니다. 자동완성이 켜지면 `gcloud run dep<Tab>`이 `gcloud run deploy`로 완성됩니다.

## 2. 초기화와 로그인

```bash
# 대화형 초기 설정 마법사: 로그인 + 기본 프로젝트/리전 선택
gcloud init

# 또는 로그인만 따로
gcloud auth login
```

`gcloud auth login`은 브라우저를 열어 구글 계정 인증을 진행합니다. 인증이 끝나면 그 계정으로 GCP 리소스를 조작할 수 있습니다.

## 3. 프로젝트 생성

GCP의 모든 리소스는 **프로젝트(project)** 안에 들어갑니다. 청구·권한·리소스의 경계가 프로젝트 단위입니다.

```bash
# 프로젝트 생성 (PROJECT_ID는 전 세계에서 유일해야 함)
gcloud projects create book-api-12345 --name="Book API"

# 이후 모든 명령의 기본 프로젝트로 지정
gcloud config set project book-api-12345
```

> **프로젝트 ID 명명 규칙**: 프로젝트 ID는 **전 세계에서 유일**해야 하며 한 번 정하면 바꿀 수 없습니다. 소문자·숫자·하이픈만 쓸 수 있고 6~30자입니다. 그래서 `book-api`처럼 흔한 이름은 이미 누군가 썼을 가능성이 큽니다. 뒤에 임의의 숫자나 본인만의 접미사를 붙이세요(예: `book-api-jongwoo-0620`).

## 4. 결제 계정 연결

Cloud Run을 쓰려면(무료 티어를 쓰더라도) 프로젝트에 **결제 계정(billing account)**이 연결돼 있어야 합니다.

```bash
# 내 결제 계정 목록 확인 (ACCOUNT_ID 형태: XXXXXX-XXXXXX-XXXXXX)
gcloud billing accounts list

# 프로젝트에 결제 계정 연결
gcloud billing projects link book-api-12345 \
  --billing-account=0X0X0X-0X0X0X-0X0X0X
```

결제 계정이 아직 없다면 [Google Cloud Console](https://console.cloud.google.com/billing)에서 먼저 만들어야 합니다(신용카드 등록 필요).

### 예산 알림 설정 (강력 권장)

무료 티어가 넉넉하지만, 실수로 `--min-instances`를 크게 잡거나 트래픽이 폭주하면 비용이 나올 수 있습니다. **$5~$10 정도의 예산(budget)**을 걸어 두고, 초과하면 메일을 받도록 설정하세요.

콘솔에서 **Billing → Budgets & alerts → Create budget**으로 만드는 것이 가장 쉽습니다. 예: 월 $5 예산, 50%/90%/100% 도달 시 메일 알림.

> **팁**: 토이 프로젝트라면 예산 알림은 "안전벨트"입니다. 처음부터 꼭 걸어 두세요.

## 5. 필요한 API 활성화

GCP의 각 서비스는 프로젝트에서 **명시적으로 활성화**해야 쓸 수 있습니다. Cloud Run 배포에 필요한 API를 한 번에 켭니다.

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

| API | 용도 |
| --- | --- |
| `run.googleapis.com` | Cloud Run 자체 |
| `cloudbuild.googleapis.com` | `--source` 배포 시 소스를 빌드(Cloud Build) |
| `artifactregistry.googleapis.com` | 빌드된 컨테이너 이미지 저장소 |

> **Cloud SQL을 쓸 예정이라면** `sqladmin.googleapis.com`도 함께 켜 두세요. PostgreSQL 연결은 [05-cicd-operations.md](05-cicd-operations.md)에서 다룹니다.

## 6. 기본 리전 설정

매번 `--region`을 타이핑하기 번거로우니 기본 리전을 지정합니다. 한국 사용자라면 **서울(`asia-northeast3`)**이 지연 시간 면에서 유리합니다.

```bash
gcloud config set run/region asia-northeast3
```

자주 쓰는 리전:

| 리전 코드 | 위치 |
| --- | --- |
| `asia-northeast3` | 서울 |
| `asia-northeast1` | 도쿄 |
| `us-central1` | 아이오와(미국) |

## 7. gcloud 치트시트

자주 쓰는 명령을 모았습니다. 필요할 때 찾아보세요.

| 명령 | 설명 |
| --- | --- |
| `gcloud config list` | 현재 활성 프로젝트·계정·리전 등 설정 확인 |
| `gcloud config set project <ID>` | 기본 프로젝트 변경 |
| `gcloud config set run/region <REGION>` | 기본 Cloud Run 리전 설정 |
| `gcloud auth login` | 사용자 로그인 |
| `gcloud auth list` | 인증된 계정 목록 |
| `gcloud projects list` | 내 프로젝트 목록 |
| `gcloud services enable <API>` | API 활성화 |
| `gcloud services list --enabled` | 활성화된 API 목록 |
| `gcloud billing accounts list` | 결제 계정 목록 |
| `gcloud run services list` | 배포된 Cloud Run 서비스 목록 |
| `gcloud run deploy ...` | 서비스 배포(다음 장) |
| `gcloud run services logs read <SVC>` | 서비스 로그 보기 |
| `gcloud components update` | gcloud SDK 업데이트 |

## 다음 단계

준비가 끝났습니다. 이제 가장 짧고 쉬운 배포 방법, **소스에서 직접 배포**를 해 봅시다. Dockerfile조차 필요 없습니다.

➡️ **[3. 소스에서 직접 배포](03-source-deploy.md)**
