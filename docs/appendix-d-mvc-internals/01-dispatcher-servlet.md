# DispatcherServlet과 요청 처리 흐름

Phase 2에서 우리는 `@RestController`에 `@GetMapping("/api/books")`를 붙이고, 메서드가 `List<BookResponse>`를 반환하면 그것이 JSON으로 바뀌어 클라이언트에게 도착하는 것을 봤습니다. 하지만 **그 사이에 무슨 일이 벌어졌는지**는 묻지 않았습니다. HTTP 요청 바이트가 어떻게 Kotlin 객체가 되고, 반환된 객체가 어떻게 다시 JSON 바이트가 될까요?

이 문서는 그 블랙박스를 엽니다. 핵심에는 **DispatcherServlet** 이라는 단 하나의 서블릿이 있습니다.

## 1. 서블릿과 서블릿 컨테이너

웹 애플리케이션이 HTTP 요청을 받으려면 누군가 80/8080 포트를 열고, TCP 연결을 받고, HTTP 메시지를 파싱해야 합니다. Java 진영에서 이 저수준 작업을 표준화한 것이 **서블릿(Servlet) 스펙** 이고, 그 구현체가 **서블릿 컨테이너** 입니다. Spring Boot가 내장으로 들고 다니는 **Tomcat 11.0.x** 가 바로 그 서블릿 컨테이너이며, **Servlet 6.1 스펙**을 구현합니다.

- **서블릿(Servlet)**: HTTP 요청 하나를 처리하는 Java 객체. `service(request, response)` 메서드가 핵심이며, 컨테이너가 요청마다 이를 호출합니다.
- **서블릿 컨테이너(Tomcat)**: 소켓 연결, 스레드 풀, HTTP 파싱, 서블릿 생명주기를 책임집니다. 요청이 오면 `HttpServletRequest`/`HttpServletResponse` 객체를 만들어 서블릿에 넘깁니다.

```
[브라우저] --HTTP--> [Tomcat: 소켓 + 스레드풀 + HTTP 파싱]
                          │  HttpServletRequest / HttpServletResponse 생성
                          ▼
                     [서블릿.service(req, res)]
```

옛날에는 URL 패턴마다 서블릿을 하나씩 만들고 `web.xml`에 일일이 등록했습니다. Spring MVC는 이 방식을 버리고 **단 하나의 서블릿**으로 모든 요청을 받습니다. 그게 DispatcherServlet입니다.

> [!NOTE]
> 패키지는 `jakarta.servlet.*` 입니다. 예전 `javax.servlet`은 Jakarta EE로 넘어오며 이름이 바뀌었습니다. 예제에서 `javax`가 보이면 구버전입니다.

## 2. DispatcherServlet — 프런트 컨트롤러

DispatcherServlet은 **모든 요청을 가장 먼저 받는 단일 진입점**입니다. 이런 패턴을 **프런트 컨트롤러(Front Controller)** 라고 부릅니다. 요청을 직접 처리하지 않고, **어떤 컨트롤러가 처리할지 찾아서 위임**하고, 그 결과를 응답으로 변환하는 "교통정리" 역할만 합니다.

Spring Boot에서는 자동 설정([Phase 0-04](../phase-0-spring-fundamentals/04-auto-configuration.md))이 `DispatcherServlet`을 만들어 `/` 경로(전체 요청)에 매핑합니다. 우리가 `web.xml`을 쓰지 않아도 되는 이유가 이것입니다.

### 전체 요청 처리 흐름

`GET /api/books` 요청 하나가 들어왔을 때, DispatcherServlet 내부에서 벌어지는 일을 ASCII로 그리면 다음과 같습니다.

```
                              ① 요청 GET /api/books
   [브라우저] ─────────────────────────────────────────►
                                                         │
                                                         ▼
   ┌──────────────────────── DispatcherServlet ────────────────────────┐
   │                                                                    │
   │   ② HandlerMapping 에게 묻는다: "이 요청을 처리할 핸들러는?"        │
   │        └─► 반환: BookController.list() + 적용할 인터셉터들          │
   │                                                                    │
   │   ③ 그 핸들러를 실행할 수 있는 HandlerAdapter 를 찾는다             │
   │        └─► RequestMappingHandlerAdapter                            │
   │                                                                    │
   │   ④ HandlerAdapter 가 컨트롤러 메서드를 호출                        │
   │        ├─ (아규먼트 리졸버) @PathVariable/@RequestBody → 파라미터    │
   │        ├─► [Controller] BookController.list() 실행                  │
   │        └─ (리턴값 핸들러) 반환값 처리                                │
   │                                                                    │
   │   ⑤ 분기:                                                          │
   │      • @ResponseBody → HttpMessageConverter 가 객체→JSON 직렬화      │
   │      • View 이름 반환 → ViewResolver 가 View 를 찾아 HTML 렌더링     │
   │                                                                    │
   └────────────────────────────────────────────────────────────────────┘
                                                         │
                                                         ▼  ⑥ HTTP 응답
   [브라우저] ◄─────────────────────────────────────────
```

이 흐름에서 ②③④⑤ 단계의 주인공들을 하나씩 살펴봅니다.

## 3. @Controller vs @RestController

먼저 우리가 매일 쓰던 두 애너테이션의 정체부터 짚고 갑니다.

- **`@Controller`**: 이 클래스가 웹 요청을 처리하는 핸들러임을 표시합니다. 메서드가 **String을 반환하면 그것을 "뷰 이름"으로 해석**해 ViewResolver가 HTML을 렌더링합니다(위 그림의 ⑤ 아래쪽 경로).
- **`@ResponseBody`**: 메서드 반환값을 **뷰 이름이 아니라 응답 본문 자체**로 취급하라는 표시입니다. 이때 HttpMessageConverter가 객체를 JSON 등으로 변환합니다(⑤ 위쪽 경로).
- **`@RestController`** = **`@Controller` + `@ResponseBody`**. 즉 클래스의 모든 메서드에 `@ResponseBody`가 자동으로 붙은 것과 같습니다. 그래서 Phase 2의 REST 컨트롤러는 String을 반환해도 뷰 이름이 아니라 "그 문자열 자체"가 응답 본문이 됩니다.

```kotlin
// Phase 2에서 쓰던 JSON API (이 부록 전체에서 그대로 유지)
@RestController                         // = @Controller + @ResponseBody
@RequestMapping("/api/books")
class BookController(private val bookService: BookService) {

    @GetMapping
    fun list(): List<BookResponse> =     // 반환값이 곧 JSON 본문
        bookService.findAll()
}
```

```kotlin
// 부록 D에서 새로 추가하는 HTML 화면 컨트롤러 (다음 문서에서 본격 사용)
@Controller                             // @ResponseBody 없음 → 반환 String = 뷰 이름
@RequestMapping("/books")
class BookViewController(private val bookService: BookService) {

    @GetMapping
    fun list(model: Model): String {
        model.addAttribute("books", bookService.findAll())
        return "books/list"             // → templates/books/list.html 을 렌더링
    }
}
```

> [!TIP]
> 같은 메서드에서 둘을 구별하는 핵심 질문은 **"반환된 String을 본문으로 쓸 것인가(@ResponseBody), 뷰 이름으로 쓸 것인가(@Controller)"** 입니다. `/api/books`(JSON)와 `/books`(HTML)를 URL로 분리해 두면 한 애플리케이션에서 두 스타일이 깔끔하게 공존합니다.

## 4. HandlerMapping과 HandlerAdapter

DispatcherServlet은 어떤 컨트롤러도 직접 알지 못합니다. 대신 **두 개의 확장 지점**에 위임합니다.

### HandlerMapping — "누가 처리할지"

`HandlerMapping`은 요청(URL, HTTP 메서드, 헤더 등)을 보고 **이 요청을 처리할 핸들러를 찾아 줍니다.** 우리가 쓰는 `@GetMapping`/`@PostMapping` 방식은 `RequestMappingHandlerMapping`이 담당합니다. 애플리케이션이 뜰 때 모든 `@RequestMapping` 메서드를 스캔해 **`{URL+메서드 → 핸들러 메서드}` 매핑 테이블**을 만들어 두고, 요청이 오면 그 테이블을 조회합니다.

반환값에는 핸들러뿐 아니라 **적용할 인터셉터 목록**도 포함됩니다(이게 `HandlerExecutionChain`이며, [3번 문서](03-filter-interceptor.md)의 인터셉터와 직결됩니다).

### HandlerAdapter — "어떻게 호출할지"

찾아낸 핸들러는 형태가 다양할 수 있습니다(애너테이션 방식 메서드, 함수형 핸들러 등). DispatcherServlet은 이 다양성을 직접 다루지 않고, **그 핸들러를 실행하는 방법을 아는 `HandlerAdapter`** 에게 다시 위임합니다. 애너테이션 컨트롤러는 `RequestMappingHandlerAdapter`가 담당하며, 바로 이 어댑터가 **아규먼트 리졸버와 리턴값 핸들러를 호출**합니다.

<figure class="flowchart branch-flow">
<ol class="fc-steps">
<li class="fc-step"><span class="fc-num fc-dot"></span><div class="fc-body"><div class="fc-head">DispatcherServlet</div><div class="fc-desc">"이 핸들러 실행 좀"</div></div></li>
<li class="fc-step fc-fork"><span class="fc-num fc-dot"></span><div class="fc-body"><div class="fc-head"><code>HandlerAdapter.handle(req, res, handler)</code></div></div></li>
</ol>
<ul class="fc-branches">
<li class="fc-branch"><span class="fc-seg"><strong>아규먼트 리졸버</strong> — HTTP 요청 → 메서드 파라미터로 변환</span></li>
<li class="fc-branch"><span class="fc-seg"><strong>실제 컨트롤러 메서드</strong> 호출</span></li>
<li class="fc-branch"><span class="fc-seg"><strong>리턴값 핸들러</strong> — 반환값 → 응답으로 변환</span></li>
</ul>
</figure>

이 **"인터페이스로 확장 지점을 열어 두고 구현을 바꿔 끼운다"** 는 설계가 Spring MVC의 유연함의 원천입니다. WebFlux로 가도 흐름의 골격은 똑같습니다([Phase 0-05](../phase-0-spring-fundamentals/05-mvc-vs-webflux.md)).

## 5. HttpMessageConverter — JSON 변환의 정체

Phase 2에서 객체가 "그냥" JSON이 되던 그 마법의 정체가 바로 **`HttpMessageConverter`** 입니다. `@ResponseBody`(또는 `@RestController`)가 붙은 메서드의 반환값을 처리하는 리턴값 핸들러가, 등록된 컨버터 중 적절한 것을 골라 **객체 ↔ HTTP 본문 바이트** 변환을 수행합니다.

- 요청: `@RequestBody Book` ← 요청 본문 JSON을 컨버터가 `Book` 객체로 **역직렬화**.
- 응답: `return book` → 컨버터가 `Book`을 JSON 바이트로 **직렬화**.

```
@RequestBody  : [요청 본문 JSON 바이트] ──(MessageConverter 읽기)──► Kotlin 객체
@ResponseBody : Kotlin 객체 ──(MessageConverter 쓰기)──► [응답 본문 JSON 바이트]
```

JSON의 경우 Spring Boot는 기본적으로 **Jackson** 기반 컨버터(`MappingJackson2HttpMessageConverter`)를 자동 등록합니다. 어떤 컨버터를 쓸지는 요청의 `Content-Type`/`Accept` 헤더와 반환 타입을 보고 결정합니다. Kotlin 데이터 클래스를 매끄럽게 다루기 위해 Jackson Kotlin 모듈도 함께 등록됩니다.

> [!NOTE]
> 여기서 한 가지가 명확해집니다. **`@Controller`의 뷰 렌더링과 `@ResponseBody`의 메시지 컨버터는 서로 배타적인 두 갈래** 입니다(그림 ⑤). 전자는 ViewResolver+View로 HTML을 만들고([2번 문서](02-thymeleaf-ssr.md)), 후자는 MessageConverter로 본문을 직접 만듭니다. SSR이냐 REST냐의 분기점이 바로 이 지점입니다.

## 6. 아규먼트 리졸버와 리턴값 핸들러

`@PathVariable`, `@RequestParam`, `@RequestBody`, `Model`, `HttpSession`… 컨트롤러 메서드 파라미터에 무엇이든 선언하면 알아서 채워지는 것도 마법처럼 보였을 겁니다. 그 마법의 주인공이 **아규먼트 리졸버(`HandlerMethodArgumentResolver`)** 입니다.

`RequestMappingHandlerAdapter`는 메서드를 호출하기 전에, **각 파라미터마다 "이걸 처리할 수 있는 리졸버"를 찾아** 값을 만들어 채웁니다.

```kotlin
@GetMapping("/{id}")
fun detail(
    @PathVariable id: Long,          // PathVariableMethodArgumentResolver 가 URL에서 추출
    @RequestParam(required = false) // RequestParamMethodArgumentResolver 가 쿼리스트링에서
    sort: String?,
    model: Model,                    // ModelMethodProcessor 가 모델 객체 주입
): String { /* ... */ return "books/detail" }

@PostMapping("/api/books")
fun create(
    @RequestBody req: CreateBookRequest  // RequestResponseBodyMethodProcessor
                                          // → 내부에서 HttpMessageConverter 호출
): BookResponse { /* ... */ }
```

| 애너테이션/타입 | 담당 리졸버 | 값의 출처 |
|---|---|---|
| `@PathVariable` | `PathVariableMethodArgumentResolver` | URL 경로 변수 |
| `@RequestParam` | `RequestParamMethodArgumentResolver` | 쿼리스트링 / 폼 필드 |
| `@RequestBody` | `RequestResponseBodyMethodProcessor` | 요청 본문(컨버터 사용) |
| `Model` | `ModelMethodProcessor` | 뷰에 넘길 모델 |
| `HttpSession` | `ServletRequestMethodArgumentResolver` | 현재 세션([4번 문서](04-session-login.md)) |

반대편에는 **리턴값 핸들러(`HandlerMethodReturnValueHandler`)** 가 있습니다. 반환값이 `@ResponseBody`면 `RequestResponseBodyMethodProcessor`가 컨버터로 본문을 만들고, 일반 String이면 `ViewNameMethodReturnValueHandler`가 뷰 이름으로 처리합니다.

> [!TIP]
> 정리하면, 컨트롤러 메서드 시그니처는 **"아규먼트 리졸버가 채워 줄 입력"** 과 **"리턴값 핸들러가 처리할 출력"** 의 선언일 뿐입니다. 우리는 비즈니스 로직만 쓰고, 변환의 양 끝단은 Spring MVC가 책임집니다. 검증(`@Valid`)도 이 아규먼트 리졸버 단계에서 동작합니다([Phase 4-1](../phase-4-validation-config/01-bean-validation.md)).

## 다음 단계

이제 요청이 컨트롤러까지 도달하는 길을 알았습니다. 그림 ⑤의 두 갈래 중 본문에서 쭉 다룬 것은 위쪽(MessageConverter→JSON)이었죠. 다음 문서에서는 **아래쪽 갈래 — ViewResolver가 Thymeleaf로 HTML을 그려 내려주는 SSR** 을 본격적으로 다룹니다.

➡️ **[2. Thymeleaf 서버 사이드 렌더링](02-thymeleaf-ssr.md)**
