# 프로파일별 배포 & 운영

산출물은 준비됐습니다. 이제 같은 이미지를 **여러 환경에 안전하게 배포**하고, 배포 후 **운영**하는 단계입니다. 이 문서는 12-factor 원칙에 따른 설정 주입, 실제 컨테이너 플랫폼 배포 예시, 프로덕션 체크리스트, 그리고 운영·트러블슈팅을 다룹니다.

## 12-factor 스타일 설정: 환경변수로 모든 것을 주입

[12-factor app](https://12factor.net) 원칙의 핵심 중 하나는 **"설정은 코드와 분리해 환경에 둔다"**입니다. 즉 DB URL, 비밀번호, 활성 프로파일 같은 **환경마다 달라지는 값**을 이미지에 굽지 않고, **실행 시점 환경변수**로 주입합니다. 이렇게 하면 dev/staging/prod에서 **완전히 동일한 이미지**를 쓰면서 동작만 다르게 할 수 있습니다.

Phase 4에서 만든 `prod` 프로파일을 복습합니다. 운영 값은 모두 `${ENV_VAR:기본값}`으로 외부화돼 있어야 합니다.

```yaml
# application-prod.yml (발췌)
server:
  port: ${PORT:8080}          # 플랫폼이 PORT를 주면 그걸, 없으면 8080
  shutdown: graceful          # 그레이스풀 셧다운

spring:
  datasource:
    url: ${SPRING_DATASOURCE_URL}
    username: ${SPRING_DATASOURCE_USERNAME}
    password: ${SPRING_DATASOURCE_PASSWORD}   # 시크릿은 절대 하드코딩 금지
  jpa:
    hibernate:
      ddl-auto: validate       # 운영에서는 스키마 자동 변경 금지, 검증만
  flyway:
    enabled: true              # 마이그레이션은 Flyway가 담당

management:
  endpoints:
    web:
      exposure:
        include: health, info, prometheus   # 필요한 것만 노출
  endpoint:
    health:
      probes:
        enabled: true          # liveness/readiness 프로브 활성화
```

## 어디서나 컨테이너 실행하기 (일반)

가장 단순하게는, 컨테이너를 돌릴 수 있는 어떤 호스트에서든 환경변수와 함께 실행하면 됩니다.

```bash
docker run -d --name book-api \
  -p 8080:8080 \
  --memory=512m --cpus=1 \
  -e SPRING_PROFILES_ACTIVE=prod \
  -e SPRING_DATASOURCE_URL=jdbc:postgresql://db.internal:5432/books \
  -e SPRING_DATASOURCE_USERNAME=book_app \
  -e SPRING_DATASOURCE_PASSWORD="$DB_PASSWORD" \
  registry.example.com/book-api:1.0.0
```

## 구체적 예시: Google Cloud Run 배포

서버리스 컨테이너 플랫폼인 **Cloud Run**은 콜드 스타트와 환경변수 주입의 좋은 예입니다(같은 패턴이 다른 컨테이너 호스트에도 적용됩니다). Cloud Run은 리스닝 포트를 **`PORT`** 환경변수로 주입하므로, 앞서 `server.port: ${PORT:8080}`로 받아 둔 것이 그대로 동작합니다.

```bash
# 1) 이미지를 레지스트리에 push (예: Artifact Registry)
docker push registry.example.com/book-api:1.0.0

# 2) Cloud Run 배포 (환경변수 + 시크릿 주입)
gcloud run deploy book-api \
  --image=registry.example.com/book-api:1.0.0 \
  --region=asia-northeast3 \
  --port=8080 \
  --memory=512Mi --cpu=1 \
  --min-instances=0 --max-instances=10 \
  --set-env-vars=SPRING_PROFILES_ACTIVE=prod \
  --set-env-vars=SPRING_DATASOURCE_URL=jdbc:postgresql:///books?cloudSqlInstance=... \
  --set-env-vars=SPRING_DATASOURCE_USERNAME=book_app \
  --set-secrets=SPRING_DATASOURCE_PASSWORD=book-db-password:latest
```

> [!TIP]
> 비밀번호 같은 시크릿은 `--set-env-vars`가 아니라 **`--set-secrets`** 로 시크릿 매니저에서 주입합니다. 환경변수 평문에 시크릿을 넣으면 배포 메타데이터·로그에 노출될 위험이 있습니다. 콜드 스타트가 잦은 `min-instances=0` 구성이라면 [네이티브 이미지](03-native-image.md)가 특히 빛을 발합니다.

## 프로덕션 체크리스트

배포 전에 다음을 점검합니다. 하나라도 빠지면 운영 중 사고로 이어지기 쉽습니다.

| 항목 | 무엇을 / 왜 | 설정 |
|------|-------------|------|
| **시크릿 외부화** | DB 비밀번호·API 키를 이미지/코드에 넣지 않음 | 시크릿 매니저 → 환경변수 주입 |
| **헬스 프로브** | 플랫폼이 liveness/readiness로 트래픽 라우팅·재시작 판단 | `management.endpoint.health.probes.enabled=true`, `/actuator/health/{liveness,readiness}` |
| **구조적 JSON 로깅** | 로그 수집기가 파싱 가능하도록 | `logging.structured.format.console=ecs` (Spring Boot 4 내장 구조적 로깅) |
| **그레이스풀 셧다운** | 종료 시 진행 중 요청을 마저 처리 | `server.shutdown=graceful`, `spring.lifecycle.timeout-per-shutdown-phase=30s` |
| **리소스 제한** | OOM·노이지 네이버 방지 | 컨테이너 `--memory`/`--cpu`, JVM `-XX:MaxRAMPercentage` |
| **관측성/메트릭** | 지표 스크랩으로 모니터링·알람 | `/actuator/prometheus` 노출, 스크랩 설정 |
| **DB 마이그레이션** | 배포 전 스키마 정합성 | Flyway가 기동 시 또는 배포 전 단계에서 실행, `ddl-auto=validate` |

### 헬스 프로브 (liveness / readiness)

쿠버네티스나 Cloud Run 같은 플랫폼은 두 종류의 프로브를 구분합니다.

```
liveness  (/actuator/health/liveness)  → 죽었으면 컨테이너 재시작
readiness (/actuator/health/readiness) → 준비됐을 때만 트래픽 라우팅
```

쿠버네티스 예시입니다.

```yaml
# Deployment 발췌
livenessProbe:
  httpGet: { path: /actuator/health/liveness, port: 8080 }
  initialDelaySeconds: 10
  periodSeconds: 10
readinessProbe:
  httpGet: { path: /actuator/health/readiness, port: 8080 }
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 그레이스풀 셧다운

`server.shutdown=graceful`을 켜면, 종료 신호(SIGTERM)를 받았을 때 새 요청 수신을 멈추고 **진행 중인 요청을 정해진 시간까지 마저 처리**한 뒤 종료합니다. 롤링 업데이트 중 사용자가 끊김을 겪지 않게 해 주는 필수 설정입니다.

## 운영 (Operations)

### 로그 읽기

```bash
# Docker
docker logs -f book-api

# Cloud Run
gcloud run services logs read book-api --region=asia-northeast3 --limit=100

# Kubernetes
kubectl logs -f deploy/book-api
```

구조적 JSON 로깅을 켜 두면 로그 수집기에서 필드 단위로 필터링·검색할 수 있습니다.

### 헬스 엔드포인트 확인

```bash
curl http://localhost:8080/actuator/health
# {"status":"UP","components":{"db":{"status":"UP"},...}}

curl http://localhost:8080/actuator/health/readiness
```

### 롤링 업데이트

새 버전을 무중단으로 교체하는 표준 흐름입니다.

```
1. 새 이미지 태그 push (book-api:1.1.0)
2. 플랫폼이 새 인스턴스 기동 → readiness 프로브 통과 대기
3. 준비된 새 인스턴스로 트래픽 전환
4. 구버전 인스턴스에 SIGTERM → 그레이스풀 셧다운으로 진행 중 요청 마무리
5. 구버전 종료
```

readiness 프로브와 그레이스풀 셧다운이 함께 켜져 있어야 이 과정이 **무중단**으로 동작합니다.

### 트러블슈팅

| 증상 | 가능한 원인 | 점검 / 조치 |
|------|-------------|-------------|
| **OOMKilled** | 컨테이너 메모리 < JVM 힙 + 메타스페이스 | `-XX:MaxRAMPercentage=75.0`로 컨테이너 메모리에 맞춤, 컨테이너 메모리 상향 |
| **시작이 느림** | JVM 워밍업, 무거운 빈 초기화 | readiness `initialDelaySeconds` 상향, 또는 [네이티브 이미지](03-native-image.md) 검토 |
| **포트 바인딩 실패** | 플랫폼 `PORT`와 앱 포트 불일치 | `server.port: ${PORT:8080}` 확인, EXPOSE/매핑 포트 일치 |
| **DB 연결 오류** | 잘못된 URL/자격증명, 네트워크/방화벽, 커넥션 풀 고갈 | 환경변수 값 확인, `/actuator/health`의 `db` 컴포넌트 확인, HikariCP 풀 사이즈 점검 |
| **마이그레이션 실패** | Flyway 체크섬 불일치, 권한 부족 | `flyway info`/`validate`, 마이그레이션 파일 변경 이력 확인 |

> [!WARNING]
> 운영에서 `spring.jpa.hibernate.ddl-auto`를 `update`나 `create`로 두면 안 됩니다. 의도치 않은 스키마 변경·데이터 손실의 원인입니다. 운영에서는 **`validate`** 로 두고 스키마 변경은 **Flyway**로만 수행하세요.

## 다음 단계

축하합니다! 🎉 Phase 0의 "Spring이란 무엇인가"에서 출발해, 첫 REST API, 데이터 영속성, 검증·예외·설정, 보안·관측성·테스트를 거쳐, 마침내 이번 Phase에서 Book API를 **빌드하고 컨테이너로 패키징해 운영 환경까지 배포**했습니다. 이제 여러분은 Kotlin으로 Spring Boot 4 애플리케이션을 처음부터 끝까지 만들고 배포할 수 있습니다.

여기서 멈추지 말고, 직접 만든 Book API에 기능을 더하고, 네이티브 빌드를 측정하고, 실제 클라우드에 한 번 올려 보세요. 막히는 부분은 공식 문서가 가장 정확한 길잡이가 되어 줄 것입니다.

- 🏠 [가이드 홈으로 돌아가기](../README.md)
- 📘 [Spring Boot 공식 문서](https://docs.spring.io/spring-boot/index.html)
- 🧭 [Spring Guides (주제별 실습)](https://spring.io/guides)

이 가이드를 완주해 주셔서 감사합니다. 즐거운 Spring 여정 되시길 바랍니다!
