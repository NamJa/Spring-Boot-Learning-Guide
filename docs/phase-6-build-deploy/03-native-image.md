# GraalVM 네이티브 이미지

지금까지 만든 산출물은 모두 **JVM 위에서** 실행됩니다. JVM은 강력하지만, 클래스 로딩과 JIT 워밍업 때문에 시작이 느리고 기본 메모리 사용량이 큽니다. 서버리스나 오토스케일링처럼 **빠른 콜드 스타트**와 **낮은 메모리**가 중요한 환경에서는 이 비용이 부담입니다.

**GraalVM 네이티브 이미지**는 이 문제에 대한 답입니다. 애플리케이션을 **AOT(Ahead-Of-Time) 컴파일**해, JVM 없이 OS에서 바로 실행되는 **단일 네이티브 실행 파일**로 만듭니다.

## AOT / 네이티브 컴파일이란

기존 JVM은 바이트코드를 실행 중에 JIT로 기계어로 번역합니다(런타임 컴파일). 반면 네이티브 이미지는 **빌드 시점에 모든 것을 기계어로 컴파일**하고, 도달 가능한 코드만 골라(closed-world 분석) 하나의 실행 파일에 담습니다.

```
[ 전통적 JVM ]
  jar → JVM 시작 → 클래스 로딩 → JIT 워밍업 → 정상 속도
  (시작 수 초, 메모리 수백 MB)

[ 네이티브 이미지 ]
  소스 → AOT 컴파일(빌드 길다) → 단일 실행 파일 → 즉시 풀 스피드
  (시작 수십 ms, 메모리 수십 MB)
```

Spring Boot는 자체 **AOT 엔진**을 통해 빈 정의, 프록시, 설정을 빌드 시점에 미리 처리해 GraalVM이 분석하기 쉬운 코드를 생성합니다. 그 위에 GraalVM이 네이티브 컴파일을 수행합니다.

### 장점

- **콜드 스타트가 수십 ms** — 함수/컨테이너가 거의 즉시 응답. Cloud Run, AWS Lambda 같은 서버리스에 이상적
- **메모리 사용량이 작음** — JVM 메타데이터·JIT 캐시가 없어 RSS가 수십 MB 수준
- **단일 실행 파일** — JRE조차 필요 없어 컨테이너 이미지가 매우 작아짐

### 트레이드오프 (단점)

- **빌드가 길다** — AOT 컴파일은 수 분이 걸리고 CPU·메모리를 많이 씀
- **closed-world 가정** — 빌드 시점에 도달 가능한 코드만 포함. 런타임에 새 클래스를 동적으로 로드할 수 없음
- **리플렉션 설정 필요** — 리플렉션·프록시·리소스 접근은 빌드 시점에 **힌트**로 알려 줘야 함
- **피크 스루풋** — 장시간 도는 워크로드에서는 JIT가 최적화한 JVM의 최대 처리량을 따라가지 못할 수 있음

## 프로젝트 설정

GraalVM Community **25**를 설치하고, `build.gradle.kts`에 **Native Build Tools 1.1.1** 플러그인을 추가합니다.

```kotlin
// build.gradle.kts
plugins {
    kotlin("jvm") version "2.2.21"
    kotlin("plugin.spring") version "2.2.21"
    id("org.springframework.boot") version "4.1.0"
    id("io.spring.dependency-management") version "1.1.7"
    // GraalVM 네이티브 빌드 도구
    id("org.graalvm.buildtools.native") version "1.1.1"
}
```

Spring Boot 플러그인이 적용되면 AOT 처리(`processAot`)와 네이티브 컴파일 태스크가 자동 구성됩니다. GraalVM JDK가 활성 JDK인지 확인합니다.

```bash
java -version
# openjdk version "25" ... GraalVM CE 25...
```

## 네이티브 이미지 빌드하기

두 가지 방법이 있습니다.

### 1) 로컬 네이티브 실행 파일 (`nativeCompile`)

호스트에 직접 실행 파일을 만듭니다.

```bash
./gradlew nativeCompile

# 산출물 실행
./build/native/nativeCompile/book-api
```

시작 로그에서 기동 시간이 초 단위가 아니라 **밀리초 단위**로 찍히는 것을 볼 수 있습니다.

### 2) 네이티브 컨테이너 이미지 (`bootBuildImage`)

별도 GraalVM 설치 없이, Buildpacks가 네이티브 빌드팩으로 네이티브 이미지를 만들어 컨테이너에 담습니다.

```bash
./gradlew bootBuildImage
# (Spring Boot가 네이티브 빌드팩을 자동 선택하도록 구성된 경우)
```

> [!TIP]
> 로컬에 GraalVM을 깔기 번거롭다면 `bootBuildImage` 방식이 편리합니다. 빌드 환경이 컨테이너 안에 격리되므로 CI에서도 재현이 쉽습니다.

## 런타임 힌트: 리플렉션과 closed-world

대부분의 Spring/Jackson 사용 패턴은 Spring과 GraalVM의 메타데이터로 **자동 처리**됩니다. 하지만 우리가 직접 리플렉션·프록시·리소스에 접근하거나, 힌트가 없는 라이브러리를 쓰면 **명시적 힌트**가 필요합니다.

가장 흔한 두 가지 방법입니다.

```kotlin
// 1) 특정 타입을 직렬화/역직렬화 대상으로 등록 (Jackson 등)
@Configuration
@RegisterReflectionForBinding(BookResponse::class, BookRequest::class)
class NativeHintsConfig
```

```kotlin
// 2) 더 세밀한 제어가 필요하면 RuntimeHintsRegistrar 구현
class BookRuntimeHints : RuntimeHintsRegistrar {
    override fun registerHints(hints: RuntimeHints, classLoader: ClassLoader?) {
        // 리플렉션 힌트
        hints.reflection().registerType(Book::class.java) { it.withMembers(*MemberCategory.values()) }
        // 리소스 힌트 (네이티브 이미지에 포함시킬 리소스)
        hints.resources().registerPattern("db/migration/*.sql")
    }
}

// 등록
@Configuration
@ImportRuntimeHints(BookRuntimeHints::class)
class HintsConfig
```

> [!WARNING]
> 네이티브에서 `ClassNotFoundException`이나 `Jackson`/리플렉션 관련 오류가 난다면 거의 항상 **힌트 누락**이 원인입니다. 동일한 코드가 JVM jar에서는 잘 돌아가더라도 네이티브에서는 closed-world 분석에 걸리지 않은 타입이 빠질 수 있습니다.

## 네이티브 테스트 (`nativeTest`)

네이티브 이미지에서만 드러나는 힌트 누락을 잡으려면, 테스트도 네이티브로 돌려 봐야 합니다.

```bash
./gradlew nativeTest
```

이 태스크는 테스트 스위트를 네이티브로 컴파일해 실행하므로, JVM 테스트는 통과하지만 네이티브에서 깨지는 케이스를 CI에서 조기에 발견할 수 있습니다.

## 언제 네이티브를 쓰지 말아야 하나

네이티브는 만능이 아닙니다. 다음 상황에서는 **JVM jar가 더 낫습니다.**

- **장시간 도는 고스루풋 서비스** — JIT가 충분히 워밍업되면 JVM의 피크 처리량이 더 높음
- **빈번한 배포 + 긴 빌드가 부담** — 네이티브 빌드는 수 분이 걸려 개발 피드백 루프를 늦춤
- **동적 클래스 로딩·바이트코드 생성에 크게 의존** — closed-world와 충돌
- **힌트가 정비되지 않은 외부 라이브러리** 다수 사용

반대로 **콜드 스타트와 메모리가 비용을 좌우하는** 서버리스(Cloud Run, Lambda), 짧게 떴다 사라지는 배치/CLI에는 네이티브가 강력합니다.

## JVM jar vs 네이티브 이미지 비교

| 항목 | JVM 실행 가능 jar | 네이티브 이미지 |
|------|-------------------|------------------|
| 시작 시간 | 1~3초 (워밍업 별도) | 수십 ms |
| 메모리 사용량 | 수백 MB | 수십 MB |
| 빌드 시간 | 빠름 (초 단위) | 느림 (분 단위, CPU 多) |
| 피크 스루풋 | 높음 (JIT 최적화) | 약간 낮을 수 있음 |
| 이미지 크기 | JRE 포함, 큼 | 작음 (JRE 불필요) |
| 동적 기능 | 자유로움 | 힌트 필요, 제약 있음 |
| 적합한 워크로드 | 장시간 고부하 서비스 | 서버리스, 콜드 스타트 민감 |

> [!TIP]
> "일단 JVM jar로 배포해 보고, 콜드 스타트나 메모리가 실제 병목으로 측정될 때 네이티브를 검토한다"가 안전한 순서입니다. 측정 없이 네이티브로 직행하면 빌드·힌트 관리 비용만 떠안을 수 있습니다.

## 다음 단계

빌드 산출물(jar·컨테이너·네이티브)을 모두 준비했습니다. 마지막으로 이를 **프로파일별로 실제 운영 환경에 배포**하고, 프로덕션 체크리스트와 운영·트러블슈팅을 정리합니다.

→ [프로파일별 배포 & 운영](04-deploy-operations.md)
