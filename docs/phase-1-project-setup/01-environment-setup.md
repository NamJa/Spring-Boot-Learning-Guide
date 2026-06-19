# 개발 환경 설정

Spring Boot 프로젝트를 시작하기 전에 필요한 도구를 갖춰야 합니다. 다행히 Kotlin 개발자라면 이미 대부분 익숙한 도구들입니다. 이 페이지에서는 **JDK, IDE, 빌드 도구, 보조 도구**를 차례대로 설정합니다.

## 1. JDK 21 LTS 설치

Spring Boot 4.1.0은 **JDK 17 이상 ~ 26**까지 지원합니다. 이 가이드는 **JDK 21 LTS** 를 표준으로 사용합니다.

### 왜 JDK 21인가?

| 항목 | 설명 |
| --- | --- |
| **LTS (장기 지원)** | 21은 LTS 버전이라 장기간 보안/버그 패치를 받습니다. 17 다음 LTS입니다. |
| **가상 스레드(Virtual Threads)** | JDK 21에서 정식 도입(JEP 444). Spring Boot 4와 결합 시 높은 동시성 처리를 손쉽게 얻습니다. |
| **레코드 패턴 / 패턴 매칭** | 최신 언어 기능을 안정적으로 사용할 수 있습니다. |
| **생태계 호환성** | 대부분의 라이브러리와 클라우드 런타임이 21을 안정적으로 지원합니다. |

> 💡 17도 동작하지만, 가상 스레드 같은 핵심 기능과 향후 호환성을 위해 21을 권장합니다. 너무 최신(예: 25/26)은 일부 도구 체인이 따라오지 못할 수 있어 LTS인 21이 가장 안전한 선택입니다.

### SDKMAN!으로 설치 (macOS / Linux 권장)

여러 JDK 버전을 관리하기엔 [SDKMAN!](https://sdkman.io/)이 가장 편합니다.

```bash
# 1. SDKMAN! 설치
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"

# 2. 설치 가능한 JDK 21 목록 확인
sdk list java | grep '21\.'

# 3. Temurin(Eclipse Adoptium) 21 설치 — 식별자는 목록에서 확인 후 사용
sdk install java 21.0.7-tem

# 4. 기본 JDK로 지정
sdk default java 21.0.7-tem
```

### 설치 확인

```bash
java -version
```

다음과 비슷한 출력이 나오면 성공입니다.

```
openjdk version "21.0.7" 2025-04-15 LTS
OpenJDK Runtime Environment Temurin-21.0.7+6 (build 21.0.7+6-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.7+6 (build 21.0.7+6-LTS, mixed mode, sharing)
```

> ⚠️ Windows에서는 SDKMAN! 대신 [Adoptium](https://adoptium.net/)에서 MSI 인스톨러를 받거나, WSL2에서 위 명령을 그대로 사용하면 됩니다.

## 2. IntelliJ IDEA 설치

Spring Boot + Kotlin 조합에서 가장 생산성이 높은 IDE는 **IntelliJ IDEA** 입니다.

- **Community Edition으로 충분합니다.** Spring 전용 지원(예: `application.yml` 자동완성, Bean 그래프)은 Ultimate 전용이지만, 학습과 일반 개발에는 Community로도 무리가 없습니다.
- **Kotlin 플러그인이 기본 내장**되어 있어 별도 설치가 필요 없습니다.
- Gradle 통합, 코드 네비게이션, 디버거가 기본 제공됩니다.

> 💡 JetBrains Toolbox App을 사용하면 IDE 버전 관리와 업데이트가 편리합니다.

설치 후 첫 실행 시, 위에서 설치한 JDK 21을 프로젝트 SDK로 지정할 수 있습니다. (`File > Project Structure > SDKs`)

## 3. Gradle Wrapper — 전역 설치가 필요 없는 이유

Spring Initializr가 생성한 프로젝트에는 **Gradle Wrapper**가 포함됩니다. 따라서 **Gradle을 시스템에 전역으로 설치할 필요가 없습니다.**

```
book-api/
├── gradlew              # macOS/Linux 실행 스크립트
├── gradlew.bat          # Windows 실행 스크립트
└── gradle/wrapper/
    ├── gradle-wrapper.jar
    └── gradle-wrapper.properties   # 사용할 Gradle 버전을 고정
```

`gradle-wrapper.properties`에 명시된 버전을 래퍼가 자동으로 내려받아 실행합니다. 덕분에 **팀원 모두가 동일한 Gradle 버전**을 사용하게 됩니다.

```bash
# 전역 gradle 대신 항상 ./gradlew 사용
./gradlew --version      # 사용 중인 Gradle 버전 확인
./gradlew build          # 빌드
./gradlew bootRun        # 애플리케이션 실행
```

> 💡 이 가이드는 **Gradle 8.14+ / 9.x** 를 기준으로 합니다. Initializr가 생성하는 래퍼 버전을 그대로 사용하면 됩니다. Maven(3.6.3+)도 가능하지만 이 가이드는 Gradle - Kotlin DSL을 사용합니다.

## 4. 보조 도구 (선택)

당장은 필요 없지만 이후 단계에서 유용한 도구들입니다.

### Docker

뒤쪽 단계에서 PostgreSQL 같은 외부 데이터베이스나 컨테이너 배포를 다룰 때 사용합니다. 지금은 H2 인메모리 DB를 쓰므로 필수는 아닙니다.

```bash
docker --version
```

### HTTPie 또는 curl

REST API를 테스트할 때 사용합니다. `curl`은 대부분의 시스템에 기본 설치되어 있고, [HTTPie](https://httpie.io/)는 더 읽기 좋은 출력을 제공합니다.

```bash
# curl
curl -i http://localhost:8080/api/books

# HTTPie (설치 시)
http GET :8080/api/books
```

## 환경 점검 체크리스트

| 도구 | 확인 명령 | 기대 결과 |
| --- | --- | --- |
| JDK 21 | `java -version` | `21.x` LTS |
| IntelliJ IDEA | 실행 | Kotlin 내장 |
| Gradle Wrapper | `./gradlew --version` | 8.14+ / 9.x (프로젝트 생성 후) |
| curl/HTTPie | `curl --version` | 임의 버전 |

## 다음 단계

환경이 준비되었으니, [Spring Initializr로 프로젝트 생성](02-create-project.md)에서 실제 `book-api` 프로젝트를 만들어 봅니다.
