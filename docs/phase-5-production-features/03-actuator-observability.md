# Actuator와 관측성

운영 중인 서비스에 대해 가장 무서운 상황은 **"잘 도는지 모르겠다"** 입니다. 메모리는 괜찮은가? DB 연결은 살아 있나? 어제보다 요청이 느려졌나? 이런 질문에 답하지 못하는 서비스는 사실상 눈을 감고 운전하는 것과 같습니다.

**Spring Boot Actuator**는 이 문제를 위한 표준 도구입니다. 헬스 체크, 메트릭, 환경 정보 등을 **즉시 사용 가능한 엔드포인트**로 노출해 주고, **Micrometer**와 **OpenTelemetry**를 통해 메트릭·추적을 표준 관측 백엔드로 보냅니다.

## 1. Actuator 시작하기

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-actuator")
}
```

추가 후 앱을 띄우면 `/actuator` 경로에 엔드포인트들이 생깁니다. 단, **보안상 기본 노출은 `health`뿐**입니다. 나머지는 명시적으로 열어야 합니다.

| 엔드포인트 | 내용 |
|-----------|------|
| `/actuator/health` | 애플리케이션 및 의존성(DB, 디스크 등) 상태 |
| `/actuator/info` | 빌드·버전 등 사용자 정의 정보 |
| `/actuator/metrics` | JVM·HTTP·DB 등 메트릭 목록과 값 |
| `/actuator/env` | 환경 프로퍼티 (민감 정보 주의) |
| `/actuator/loggers` | 런타임 로그 레벨 조회/변경 |
| `/actuator/prometheus` | Prometheus 포맷 메트릭 (스크레이프용) |

## 2. 엔드포인트 노출 설정

무엇을 열지는 `application.yml`로 제어합니다. 운영에서는 **꼭 필요한 것만** 여는 것이 원칙입니다.

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, info, metrics, prometheus   # 필요한 것만 노출
        # exclude: env                                # 민감한 건 명시적 제외
  endpoint:
    health:
      show-details: when-authorized   # 헬스 상세는 인증 사용자에게만
```

> [!TIP]
> Phase 5-2에서 `/actuator/health/**` 를 `permitAll`로 열어 둔 이유가 여기 있습니다. 쿠버네티스/Cloud Run의 프로브는 인증 없이 헬스를 찔러야 하기 때문입니다. 반대로 `env`, `loggers` 같은 민감 엔드포인트는 절대 공개하면 안 됩니다.

## 3. 헬스 체크 — 프로브와 커스텀 인디케이터

`/actuator/health`는 단순 `{"status":"UP"}` 이 아니라, 등록된 **HealthIndicator**들을 종합한 결과입니다. DB가 죽으면 자동으로 `DOWN`이 됩니다.

### Liveness / Readiness 프로브

쿠버네티스·Cloud Run은 두 종류의 프로브를 구분합니다. Spring Boot는 이를 그룹으로 지원합니다.

```yaml
management:
  endpoint:
    health:
      probes:
        enabled: true   # liveness/readiness 그룹 활성화
```

- `/actuator/health/liveness` → 프로세스가 살아 있는가? (실패 시 **재시작**)
- `/actuator/health/readiness` → 트래픽을 받을 준비가 됐는가? (실패 시 **트래픽 차단**)

```yaml
# 쿠버네티스 매니페스트 예시
livenessProbe:
  httpGet: { path: /actuator/health/liveness, port: 8080 }
readinessProbe:
  httpGet: { path: /actuator/health/readiness, port: 8080 }
```

### 커스텀 헬스 인디케이터

외부 도서 메타데이터 API(Phase 5-1)가 우리 서비스의 핵심 의존성이라면, 그 상태도 헬스에 반영하고 싶을 수 있습니다.

```kotlin
package com.example.bookapi.health

import org.springframework.boot.actuate.health.Health
import org.springframework.boot.actuate.health.HealthIndicator
import org.springframework.stereotype.Component

@Component
class MetadataApiHealthIndicator(
    private val metadataClient: BookMetadataClient,
) : HealthIndicator {

    override fun health(): Health {
        return try {
            metadataClient.findByIsbn("PING")   // 가벼운 핑 호출
            Health.up().withDetail("metadata-api", "reachable").build()
        } catch (ex: Exception) {
            // DOWN을 반환하면 전체 health도 DOWN이 된다
            Health.down(ex).withDetail("metadata-api", "unreachable").build()
        }
    }
}
```

빈 이름(`metadataApi`)이 헬스 응답의 컴포넌트 키가 됩니다.

## 4. Micrometer — 메트릭의 표준 추상화

Actuator의 메트릭은 **Micrometer**가 수집합니다. Micrometer는 "메트릭계의 SLF4J"로, 코드는 Micrometer API로 작성하고 **백엔드(Prometheus, OTLP 등)는 의존성만 바꿔 끼웁니다.**

JVM 메모리, GC, HTTP 요청 지연(`http.server.requests`), DataSource 커넥션 등 수많은 메트릭이 **자동으로** 수집됩니다.

### 커스텀 메트릭 — Counter와 Timer

도서 등록 횟수와 처리 시간을 직접 측정해 봅시다. `MeterRegistry`를 주입받아 사용합니다.

```kotlin
package com.example.bookapi.service

import io.micrometer.core.instrument.Counter
import io.micrometer.core.instrument.MeterRegistry
import io.micrometer.core.instrument.Timer
import org.springframework.stereotype.Service

@Service
class BookService(
    private val repository: BookRepository,
    registry: MeterRegistry,
) {
    // 도서 등록 누적 횟수
    private val createdCounter: Counter = Counter.builder("books.created")
        .description("등록된 도서 수")
        .register(registry)

    // 등록 처리 시간 분포
    private val createTimer: Timer = Timer.builder("books.create.duration")
        .description("도서 등록 처리 시간")
        .register(registry)

    fun create(request: CreateBookRequest): BookResponse =
        createTimer.recordCallable {
            val saved = repository.save(request.toEntity())
            createdCounter.increment()
            saved.toResponse()
        }!!
}
```

이제 `/actuator/metrics/books.created` 에서 값을 확인할 수 있습니다.

> [!TIP]
> 더 간단하게는 메서드에 `@Timed`(`@Counted`) 애너테이션을 붙여 AOP로 측정할 수도 있습니다. 세밀한 제어가 필요하면 위처럼 직접 등록하세요.

## 5. Prometheus 노출

Prometheus로 메트릭을 수집하려면 레지스트리 의존성을 추가하고 엔드포인트를 엽니다.

```kotlin
// build.gradle.kts
runtimeOnly("io.micrometer:micrometer-registry-prometheus")
```

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health, prometheus
```

그러면 Prometheus 서버가 `GET /actuator/prometheus` 를 스크레이프해 시계열로 저장하고, Grafana로 대시보드를 그릴 수 있습니다.

## 6. 관측성 — OpenTelemetry와 분산 추적

메트릭(무엇이 얼마나)만으로는 부족합니다. "이 느린 요청이 **어디서** 시간을 썼나"를 알려면 **분산 추적(distributed tracing)** 이 필요합니다. Spring Boot 4는 **Micrometer Tracing** + **OpenTelemetry**로 이를 표준 지원합니다.

```kotlin
// build.gradle.kts
implementation("io.micrometer:micrometer-tracing-bridge-otel")     // Micrometer ↔ OTel 연결
implementation("io.opentelemetry:opentelemetry-exporter-otlp")     // OTLP로 추적 전송
```

```yaml
management:
  tracing:
    sampling:
      probability: 1.0          # 개발: 전부 추적 / 운영: 0.1 등으로 낮춤
  otlp:
    tracing:
      endpoint: http://otel-collector:4318/v1/traces
```

이렇게 하면 들어오는 HTTP 요청, DB 호출, 그리고 `RestClient`를 통한 외부 호출(Phase 5-1)에 **자동으로 trace ID / span ID가 부여**되고 OpenTelemetry Collector(→ Jaeger, Tempo, Zipkin 등)로 전송됩니다.

### 구조화 로깅과 trace 연계

Spring Boot 4는 **구조화 로깅(structured logging)** 도 기본 지원합니다. 로그를 JSON으로 출력하고, 위의 trace ID를 자동으로 끼워 넣으면 로그와 추적을 연결해 디버깅할 수 있습니다.

```yaml
logging:
  structured:
    format:
      console: ecs   # ECS(Elastic) 또는 logstash, gelf 등
```

```
관측성 3대 신호
  Metrics  : 무엇이 얼마나? (Micrometer → Prometheus)
  Traces   : 어디서 느린가? (Micrometer Tracing → OpenTelemetry)
  Logs     : 정확히 무슨 일이? (구조화 로깅 + trace ID 연계)
```

> [!TIP]
> 셋을 trace ID 하나로 묶는 것이 핵심입니다. 메트릭에서 지연 급증을 발견 → 해당 trace를 추적에서 확인 → 같은 trace ID로 로그를 조회, 이 흐름이 운영 디버깅의 정석입니다.

## 다음 단계

이제 우리 서비스는 외부와 통신하고, 보안이 적용되고, 관측 가능합니다. 마지막으로 이 모든 것을 **배포 전에 검증**하는 방법 — 테스트 전략을 다룹니다.

→ [테스트 전략](04-testing.md)
