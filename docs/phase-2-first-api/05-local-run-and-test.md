# 로컬 실행과 테스트

코드가 모두 준비되었습니다. 이제 애플리케이션을 실행하고, 5개 엔드포인트를 직접 호출하며 정상 동작과 에러 동작을 모두 확인합니다.

## 1. bootRun으로 실행하기

프로젝트 루트에서 Gradle 태스크 `bootRun`을 실행합니다.

```bash
./gradlew bootRun
```

(Windows는 `gradlew.bat bootRun`)

처음 실행 시 의존성을 내려받느라 시간이 걸릴 수 있습니다. 다음과 같은 로그의 **마지막 줄**이 보이면 기동 완료입니다.

```
... INFO ... Tomcat started on port 8080 (http) with context path '/'
... INFO ... Started BookApiApplication in 1.234 seconds (process running for 1.567)
```

- 포트는 기본 **8080**입니다. 바꾸려면 `application.yml`에 `server.port: 9090` 등을 지정합니다.
- 종료는 터미널에서 `Ctrl + C`입니다.

> **빌드 후 실행 (대안)**: `./gradlew build`로 실행 가능한 JAR을 만든 뒤 `java -jar build/libs/book-api-0.0.1-SNAPSHOT.jar`로 띄울 수도 있습니다. 운영 환경은 보통 이 방식을 씁니다.

## 2. 전체 엔드포인트 수동 테스트 (curl)

서버가 떠 있는 다른 터미널에서 아래 순서대로 실행해 보세요. 데이터는 메모리에 있으므로 서버를 재시작하면 초기화됩니다.

### ① 도서 등록 (POST → 201)

```bash
curl -i -X POST http://localhost:8080/api/books \
  -H "Content-Type: application/json" \
  -d '{
    "title": "소년이 온다",
    "author": "한강",
    "isbn": "9788936434120",
    "price": 13500,
    "publishedAt": "2014-05-19"
  }'
```

```
HTTP/1.1 201 Created
Location: /api/books/1
```
```json
{
  "id": 1,
  "title": "소년이 온다",
  "author": "한강",
  "isbn": "9788936434120",
  "price": 13500,
  "publishedAt": "2014-05-19"
}
```

한 번 더 다른 책을 등록하면 `id`는 `2`가 됩니다.

### ② 전체 목록 (GET → 200)

```bash
curl http://localhost:8080/api/books
```
```json
[
  {
    "id": 1,
    "title": "소년이 온다",
    "author": "한강",
    "isbn": "9788936434120",
    "price": 13500,
    "publishedAt": "2014-05-19"
  }
]
```

### ③ 단건 조회 (GET → 200)

```bash
curl http://localhost:8080/api/books/1
```
```json
{
  "id": 1,
  "title": "소년이 온다",
  "author": "한강",
  "isbn": "9788936434120",
  "price": 13500,
  "publishedAt": "2014-05-19"
}
```

### ④ 수정 (PUT → 200)

```bash
curl -X PUT http://localhost:8080/api/books/1 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "소년이 온다 (리커버)",
    "author": "한강",
    "isbn": "9788936434120",
    "price": 14000,
    "publishedAt": "2014-05-19"
  }'
```
```json
{
  "id": 1,
  "title": "소년이 온다 (리커버)",
  "author": "한강",
  "isbn": "9788936434120",
  "price": 14000,
  "publishedAt": "2014-05-19"
}
```

### ⑤ 삭제 (DELETE → 204)

```bash
curl -i -X DELETE http://localhost:8080/api/books/1
```
```
HTTP/1.1 204 No Content
```

삭제 후 다시 조회하면 404가 나옵니다(아래 에러 케이스 참고).

## 3. HTTPie를 쓰는 경우 (대안)

`curl`이 번거롭다면 **HTTPie**(`brew install httpie`)가 더 읽기 쉽습니다.

```bash
# 등록
http POST :8080/api/books \
  title="채식주의자" author="한강" isbn="9788936433598" \
  price:=13500 publishedAt="2007-10-30"

# 조회
http :8080/api/books/1

# 삭제
http DELETE :8080/api/books/1
```

> HTTPie에서 `:=`는 **숫자/불리언** 등 비문자열 값을 의미합니다. `price:=13500`은 `"price": 13500`(숫자)으로 보냅니다. 그냥 `price=13500`이면 문자열이 되어 역직렬화에 실패할 수 있으니 주의하세요.

## 4. 에러 케이스 확인

정상 동작뿐 아니라 실패 동작도 검증해야 합니다.

### 404 Not Found — 없는 도서

```bash
curl -i http://localhost:8080/api/books/9999
```
```
HTTP/1.1 404 Not Found
```

`BookNotFoundException`에 붙인 `@ResponseStatus(HttpStatus.NOT_FOUND)` 덕분에 404가 반환됩니다. (응답 본문의 에러 JSON 형식은 Phase 4에서 다듬습니다.)

### 400 Bad Request — 잘못된 JSON

본문 JSON 문법이 깨졌거나, non-null 필드(`price`)에 `null`을 보내면 역직렬화에 실패합니다.

```bash
curl -i -X POST http://localhost:8080/api/books \
  -H "Content-Type: application/json" \
  -d '{ "title": "제목만", "price": null }'
```
```
HTTP/1.1 400 Bad Request
```

`jackson-module-kotlin`이 non-null 프로퍼티에 `null`이 들어온 것을 감지해 거부합니다.

### 415 Unsupported Media Type — Content-Type 누락

`@RequestBody`로 JSON을 받는 엔드포인트는 `Content-Type: application/json` 헤더가 필요합니다. 누락하면 415가 납니다.

```bash
# 헤더 없이 POST → 415
curl -i -X POST http://localhost:8080/api/books \
  -d '{ "title": "헤더 없음" }'
```
```
HTTP/1.1 415 Unsupported Media Type
```

## 5. DevTools — 코드 수정 시 자동 재시작

개발 중 매번 수동 재시작은 번거롭습니다. **Spring Boot DevTools**를 추가하면 클래스가 변경될 때 애플리케이션이 **자동 재시작**됩니다.

`build.gradle.kts`:

```kotlin
dependencies {
    developmentOnly("org.springframework.boot:spring-boot-devtools")
}
```

- `developmentOnly` 스코프이므로 운영 빌드(JAR)에는 포함되지 않습니다.
- IDE에서 빌드(컴파일)가 일어나면 자동 재시작됩니다. IntelliJ는 `Build > Build Project`(또는 저장 시 자동 빌드 설정)로 트리거됩니다.
- 전체 재시작이 아니라 애플리케이션 클래스로더만 다시 로드하므로, 콜드 스타트보다 훨씬 빠릅니다.

> **팁**: DevTools 재시작은 **메모리 데이터 초기화**를 의미합니다. 재시작 후에는 등록했던 도서가 사라집니다. 이는 메모리 저장소의 한계이며, Phase 3에서 DB를 붙이면 해결됩니다.

## 6. 시작 오류 트러블슈팅

| 증상(로그) | 원인 | 해결 |
|---|---|---|
| `Port 8080 was already in use` | 8080 포트를 다른 프로세스가 사용 중 | 기존 프로세스 종료(`lsof -i :8080` 후 `kill`) 또는 `server.port` 변경 |
| `Web server failed to start` | 포트 충돌 또는 빈 생성 실패 | 위 포트 확인, 그리고 아래 행들 점검 |
| 404가 계속 발생 | 컨트롤러가 컴포넌트 스캔 밖에 위치 | 클래스를 `com.example.bookapi` 하위 패키지로 이동 |
| `No qualifying bean of type 'BookService'` | `@Service` 누락 또는 패키지 위치 오류 | `BookService`에 `@Service`가 있는지, 패키지가 진입점 하위인지 확인 |
| `LocalDate` 직렬화 오류 | JSR-310 모듈 누락 | `spring-boot-starter-web` 의존성 확인(보통 자동 포함) |
| `Cannot construct instance of CreateBookRequest` | `jackson-module-kotlin` 누락 | 의존성에 `jackson-module-kotlin` 추가 |
| `Whitelabel Error Page` 표시 | 매핑되지 않은 경로 접근 | URL 경로/메서드 확인 (`/api/books` 오타 등) |

8080 포트를 점유한 프로세스를 찾고 종료하는 예시(macOS/Linux):

```bash
lsof -i :8080        # 점유 프로세스 PID 확인
kill -9 <PID>        # 해당 프로세스 종료
```

## 7. 이번 단계 정리

축하합니다. 동작하는 REST API를 완성했습니다. 이번 Phase에서 익힌 것을 돌아보면,

- `@SpringBootApplication`과 `runApplication`으로 애플리케이션을 띄우는 구조
- `data class` DTO와 Jackson 기반 JSON 직렬화/역직렬화
- `@RestController`로 5개 CRUD 엔드포인트 구현, `ResponseEntity`로 상태 코드 제어
- `@Service` + 생성자 주입(DI)으로 비즈니스 로직 분리
- 메모리 저장소(`ConcurrentHashMap`)와 커스텀 예외 처리
- `bootRun` 실행과 `curl`/HTTPie를 이용한 엔드포인트 검증

하지만 데이터가 메모리에만 있어 서버를 끄면 사라집니다. 실무에서는 데이터베이스가 필요합니다.

## 다음 단계

Phase 3에서는 메모리 저장소를 **JPA**로 교체하여 데이터를 실제 데이터베이스에 영속화합니다. JPA의 핵심 개념부터 시작합니다. [Phase 3 — JPA 개념](../phase-3-data-jpa/01-jpa-concepts.md)으로 이동하세요.
