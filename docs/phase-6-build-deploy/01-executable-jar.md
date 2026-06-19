# 실행 가능 JAR 빌드

모든 배포는 **하나의 실행 가능한 산출물**에서 출발합니다. Spring Boot의 Gradle 플러그인은 애플리케이션 코드와 모든 의존성을 단일 jar에 담은 **실행 가능 jar**(흔히 *fat jar* 또는 *uber jar*)를 만들어 줍니다. 별도의 톰캣 설치 없이 `java -jar`만으로 내장 톰캣(Tomcat 11.0.x)을 띄우고 8080 포트에서 서비스가 시작됩니다.

이 문서에서는 Book API를 빌드해 산출물을 만들고, 그 내부 구조(특히 **layered jar**)를 이해하고, 실행 시 프로파일·인자·JVM 옵션을 주입하는 방법을 다룹니다.

## bootJar로 빌드하기

Spring Boot Gradle 플러그인을 적용하면 `bootJar` 태스크가 자동으로 등록됩니다. Book API 프로젝트 루트에서 다음을 실행합니다.

```bash
# 실행 가능 jar만 빌드
./gradlew bootJar

# 전체 빌드 (컴파일 + 테스트 + bootJar + plain jar)
./gradlew build
```

산출물은 `build/libs/` 아래에 생성됩니다.

```bash
$ ls -lh build/libs/
book-api-0.0.1-SNAPSHOT.jar        # 실행 가능 boot jar (의존성 포함)
book-api-0.0.1-SNAPSHOT-plain.jar  # plain jar (애플리케이션 클래스만)
```

> [!NOTE]
> 버전 `0.0.1-SNAPSHOT`은 `build.gradle.kts`의 `version` 속성에서 옵니다. 파일명이 다르면 이후 명령의 jar 이름을 자신의 산출물에 맞춰 바꿔 주세요.

빌드된 jar는 다음과 같이 실행합니다.

```bash
java -jar build/libs/book-api-0.0.1-SNAPSHOT.jar
```

JDK 21(최소 17, 최대 26 지원)이 설치되어 있어야 하며, 실행 즉시 내장 톰캣이 기동되어 `http://localhost:8080`에서 Book API가 응답합니다.

## plain jar vs boot jar

`./gradlew build`는 **두 개의 jar**를 만듭니다. 둘의 차이를 이해하는 것이 중요합니다.

| 구분 | plain jar (`-plain.jar`) | boot jar (실행 가능 jar) |
|------|--------------------------|--------------------------|
| 포함 내용 | 우리 애플리케이션 클래스만 | 애플리케이션 + 모든 의존성 + 로더 |
| 실행 | `java -jar` 불가 (의존성 없음) | `java -jar`로 바로 실행 |
| 용도 | 다른 모듈이 라이브러리로 의존할 때 | 배포·실행용 |
| `Main-Class` | 없음 | `org.springframework.boot.loader.launch.JarLauncher` |

라이브러리로 쓸 일이 없다면 plain jar 생성을 끌 수 있습니다.

```kotlin
// build.gradle.kts
tasks.named<Jar>("jar") {
    enabled = false // plain jar 비활성화
}
```

## 실행 가능 jar의 내부 구조 (layered jar)

Spring Boot 4의 실행 가능 jar는 **layered jar**로 만들어집니다. 이는 jar 내부 콘텐츠를 **변경 빈도**에 따라 여러 계층으로 나눈 구조입니다. `jar tf`로 들여다보면 다음과 같은 레이아웃이 보입니다.

```
book-api-0.0.1-SNAPSHOT.jar
├── META-INF/
│   └── MANIFEST.MF              ← Main-Class: ...JarLauncher
├── org/springframework/boot/loader/   ← 스프링 부트 로더 (jar 안의 jar를 푸는 코드)
└── BOOT-INF/
    ├── classes/                 ← 우리가 작성한 com.example.bookapi 코드
    ├── lib/                     ← 모든 의존성 jar (spring, jackson, hibernate ...)
    ├── classpath.idx
    └── layers.idx               ← 레이어 정의 (아래 4개 레이어)
```

`layers.idx`가 정의하는 **4개의 레이어**는 변경 빈도가 낮은 것부터 높은 순서입니다.

```
┌─────────────────────────────────────────────┐
│ dependencies          (가장 안 바뀜, 외부 정식 릴리스 의존성) │
├─────────────────────────────────────────────┤
│ spring-boot-loader    (스프링 부트 버전 올릴 때만 바뀜)        │
├─────────────────────────────────────────────┤
│ snapshot-dependencies (SNAPSHOT 의존성, 가끔 바뀜)         │
├─────────────────────────────────────────────┤
│ application           (우리 코드, 가장 자주 바뀜)            │
└─────────────────────────────────────────────┘
```

### 왜 레이어가 Docker 캐싱에 중요한가

Docker 이미지는 **레이어 단위로 캐싱**됩니다. 만약 jar 전체를 한 덩어리로 이미지에 복사하면, **한 줄만 고쳐도** 수백 MB짜리 의존성까지 통째로 새 레이어가 됩니다. 매 배포마다 이미지 push/pull이 무거워지죠.

layered jar를 이용하면 변경 빈도가 다른 콘텐츠를 **별도의 Docker 레이어**로 분리할 수 있습니다.

```
코드 한 줄 수정 후 재빌드 시:
  dependencies          → 캐시 히트 ✅ (안 바뀜, 재사용)
  spring-boot-loader    → 캐시 히트 ✅
  snapshot-dependencies → 캐시 히트 ✅
  application           → 이 레이어만 새로 빌드 (수십 KB)
```

결과적으로 **자주 바뀌는 우리 코드 레이어만** 새로 만들어지고, 무거운 의존성 레이어는 캐시에서 재사용됩니다. 이 구조를 실제 Dockerfile에서 활용하는 방법은 [다음 문서](02-docker.md)에서 다룹니다.

레이어를 직접 추출해 볼 수도 있습니다.

```bash
# jar에 어떤 레이어가 있는지 나열
java -Djarmode=tools -jar build/libs/book-api-0.0.1-SNAPSHOT.jar list-layers

# 레이어별로 디렉터리에 추출
java -Djarmode=tools -jar build/libs/book-api-0.0.1-SNAPSHOT.jar extract --layers --destination extracted
```

> [!TIP]
> Spring Boot 3.3+부터 레이어 추출 도구가 `-Djarmode=layertools`에서 **`-Djarmode=tools`** 로 통합되었습니다. Spring Boot 4에서도 동일하게 `tools` jarmode를 사용합니다.

## bootRun vs bootJar

개발 중에는 jar를 만들지 않고 Gradle에서 바로 실행하는 것이 편합니다.

| 태스크 | 용도 | 특징 |
|--------|------|------|
| `./gradlew bootRun` | **로컬 개발** | 빌드 후 곧바로 실행, 소스 클래스 디렉터리에서 구동, jar 생성 안 함 |
| `./gradlew bootJar` | **배포 산출물 생성** | `build/libs/`에 실행 가능 jar 생성, 실행은 별도 |

`bootRun`에 인자나 프로파일을 넘길 때는 `--args`를 사용합니다.

```bash
./gradlew bootRun --args='--spring.profiles.active=local --server.port=9090'
```

## 실행 시 설정 주입: 인자 · 프로파일 · JVM 옵션

같은 jar를 환경마다 다르게 동작시키는 핵심은 **실행 시점 설정 주입**입니다. Spring Boot는 여러 소스에서 설정을 읽으며, 우선순위가 높은 순서대로 정리하면 다음과 같습니다.

```
커맨드라인 인자 (--key=value)
  > OS 환경변수 (SPRING_PROFILES_ACTIVE 등)
    > application-{profile}.yml
      > application.yml
```

### 프로파일 활성화

Phase 3에서 도입한 `prod` 프로파일을 켜는 방법은 세 가지입니다.

```bash
# 1) 커맨드라인 인자
java -jar app.jar --spring.profiles.active=prod

# 2) 환경변수 (컨테이너 배포에서 가장 흔함)
SPRING_PROFILES_ACTIVE=prod java -jar app.jar

# 3) JVM 시스템 프로퍼티
java -Dspring.profiles.active=prod -jar app.jar
```

### 임의의 설정 값 덮어쓰기

`application.yml`의 어떤 값이든 커맨드라인 인자나 환경변수로 덮어쓸 수 있습니다. **점(.) 표기**를 환경변수로 쓸 때는 **대문자 + 언더스코어**로 변환합니다(relaxed binding).

```bash
# 커맨드라인 인자
java -jar app.jar --server.port=8081 --spring.datasource.url=jdbc:postgresql://db:5432/books

# 동일한 의미의 환경변수
SERVER_PORT=8081 \
SPRING_DATASOURCE_URL=jdbc:postgresql://db:5432/books \
java -jar app.jar
```

### JVM 옵션 (`JAVA_OPTS`)

힙 크기, GC, 시스템 프로퍼티 같은 **JVM 수준 옵션**은 `java` 명령 앞에 둡니다. 컨테이너에서는 관례적으로 `JAVA_OPTS` 환경변수에 모아 둡니다.

```bash
# 힙 최대 512MB, 컨테이너 메모리 인식 활성화
java -Xmx512m -XX:+UseContainerSupport -jar app.jar

# JAVA_OPTS 패턴 (쉘에서 펼쳐서 전달)
export JAVA_OPTS="-Xmx512m -XX:MaxRAMPercentage=75.0"
java $JAVA_OPTS -jar app.jar --spring.profiles.active=prod
```

> [!TIP]
> 컨테이너 환경에서는 고정 `-Xmx`보다 **`-XX:MaxRAMPercentage`** 로 컨테이너에 할당된 메모리의 비율을 지정하는 편이 안전합니다. JDK 21은 cgroup 메모리 한도를 자동 인식합니다.

## 다음 단계

이제 실행 가능 jar를 손에 넣었습니다. 다음은 이 jar(특히 layered 구조)를 활용해 **Docker 컨테이너 이미지**로 패키징하는 두 가지 방법을 배웁니다.

→ [Docker 컨테이너화](02-docker.md)
