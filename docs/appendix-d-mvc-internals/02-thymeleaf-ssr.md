# Thymeleaf 서버 사이드 렌더링

[1번 문서](01-dispatcher-servlet.md)의 마지막에서 본 그림 ⑤에는 두 갈래가 있었습니다. `@ResponseBody`로 JSON 본문을 만드는 위쪽(MessageConverter)과, **뷰 이름을 반환해 ViewResolver가 HTML을 그리는 아래쪽**. 이번 문서는 그 아래쪽 갈래, 즉 **서버 사이드 렌더링(SSR)** 을 다룹니다. 서버가 데이터를 채운 완성된 HTML을 브라우저에 내려주는 전통적인 웹 방식입니다.

## 1. SSR vs REST — 언제 무엇을

같은 도서 데이터라도 두 가지 방식으로 전달할 수 있습니다.

```
[REST 방식 — Phase 2]                      [SSR 방식 — 이 부록]
브라우저(JS) ─GET /api/books─► 서버         브라우저 ─GET /books─► 서버
            ◄──── JSON ───────                       ◄── 완성된 HTML ──
브라우저가 JS로 화면을 그림                  서버가 화면을 다 그려서 보냄
```

| 구분 | SSR (`@Controller` + Thymeleaf) | REST (`@RestController` + JSON) |
|---|---|---|
| 응답 | 완성된 HTML | 데이터(JSON) |
| 화면 렌더링 주체 | 서버 | 클라이언트(브라우저 JS, React 등) |
| 적합한 곳 | 관리자 페이지, 사내 도구, 콘텐츠 사이트, 폼 위주 화면 | SPA/모바일 앱 백엔드, 외부 공개 API |
| 초기 로딩/SEO | 유리(HTML이 바로 옴) | 별도 처리 필요 |

> [!TIP]
> 둘은 양자택일이 아닙니다. 한 애플리케이션이 외부에는 `/api/books` REST를, 내부 관리자에게는 `/books` SSR 화면을 동시에 제공하는 구성은 매우 흔합니다. 이 부록이 정확히 그 구조입니다.

## 2. 의존성과 자동 설정

SSR을 위해 필요한 것은 스타터 하나입니다([Phase 1-4](../phase-1-project-setup/04-build-gradle-kts.md)의 의존성 추가 방식 그대로).

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-thymeleaf") // 추가
}
```

이 스타터는 **Thymeleaf 3.1.5**(Boot 4.1 관리 버전)를 끌어오고, 자동 설정([Phase 0-04](../phase-0-spring-fundamentals/04-auto-configuration.md))이 다음을 알아서 구성합니다.

- **`ThymeleafViewResolver`** — 컨트롤러가 반환한 뷰 이름(예: `"books/list"`)을 실제 템플릿 파일로 연결.
- **템플릿 위치** — 기본 prefix `classpath:/templates/`, suffix `.html`. 즉 `"books/list"` → `src/main/resources/templates/books/list.html`.
- **인코딩** UTF-8, 정적 리소스는 `src/main/resources/static/`.

```
src/main/resources/
├── templates/          ← Thymeleaf HTML (서버가 렌더링)
│   └── books/
│       ├── list.html
│       ├── detail.html
│       └── form.html
└── static/             ← CSS/JS/이미지 (그대로 서빙)
```

> [!WARNING]
> 개발 중 템플릿을 고쳤는데 화면이 안 바뀐다면 캐시 때문입니다. 운영에서는 캐시가 켜져 있어야 하지만, 로컬에서는 꺼 두면 편합니다.
> ```yaml
> spring:
>   thymeleaf:
>     cache: false   # 개발용. 운영(prod 프로파일)에서는 true 유지
> ```

## 3. @Controller + Model로 데이터 전달

SSR의 핵심 협업은 **컨트롤러가 `Model`에 데이터를 담고, 뷰 이름을 반환하면, 템플릿이 그 데이터를 꺼내 HTML을 채우는 것** 입니다.

```kotlin
package com.example.bookapi.controller   // SSR 컨트롤러도 REST와 같은 controller 패키지를 씁니다

import org.springframework.stereotype.Controller
import org.springframework.ui.Model
import org.springframework.web.bind.annotation.*

@Controller                      // @RestController 아님! (1번 문서 3절)
@RequestMapping("/books")
class BookViewController(
    private val bookService: BookService,   // Phase 2의 서비스 그대로 재사용
) {

    // 목록 화면: GET /books
    @GetMapping
    fun list(model: Model): String {
        model.addAttribute("books", bookService.findAll())  // 뷰에 넘길 데이터
        return "books/list"      // → templates/books/list.html
    }

    // 상세 화면: GET /books/1
    @GetMapping("/{id}")
    fun detail(@PathVariable id: Long, model: Model): String {
        model.addAttribute("book", bookService.findById(id))
        return "books/detail"
    }
}
```

`Model`은 [1번 문서](01-dispatcher-servlet.md)에서 본 아규먼트 리졸버가 채워 주는 객체로, **컨트롤러 → 뷰로 넘기는 데이터 보관함**입니다. `addAttribute("books", ...)`로 담은 값은 템플릿에서 `${books}`로 꺼냅니다.

## 4. 타임리프 기본 문법

Thymeleaf의 가장 큰 장점은 **순수 HTML로도 열린다**는 점입니다(natural template). 동적 부분을 `th:*` 속성으로 표현하므로, 브라우저로 파일을 직접 열어도 디자인을 확인할 수 있습니다.

| 문법 | 용도 | 예시 |
|---|---|---|
| `th:text` | 태그 내용을 값으로 치환 | `<td th:text="${book.title}">샘플</td>` |
| `th:each` | 반복 | `<tr th:each="book : ${books}">` |
| `th:if` / `th:unless` | 조건부 렌더링 | `<p th:if="${books.isEmpty()}">없음</p>` |
| `th:href` | 링크 속성 | `th:href="@{/books/{id}(id=${book.id})}"` |
| `${...}` | 변수식(모델 값 접근) | `${book.title}` |
| `@{...}` | URL 식(컨텍스트 경로 자동 처리) | `@{/books}` |

- **`${...}` (변수식)**: 모델에 담긴 객체의 값을 읽습니다. `${book.title}`은 `book.getTitle()`(Kotlin이면 프로퍼티 `title`)을 호출합니다.
- **`@{...}` (URL식)**: 애플리케이션 컨텍스트 경로를 자동으로 붙여 안전한 URL을 만듭니다. 경로 변수는 `@{/books/{id}(id=${book.id})}` 처럼 괄호로 전달합니다.

## 5. 목록·상세 페이지 예제

### 목록 — `templates/books/list.html`

```html
<!DOCTYPE html>
<html lang="ko" xmlns:th="http://www.thymeleaf.org">
<head>
    <meta charset="UTF-8">
    <title>도서 목록</title>
</head>
<body>
    <h1>도서 목록</h1>

    <!-- 데이터가 없을 때 -->
    <p th:if="${books.isEmpty()}">등록된 도서가 없습니다.</p>

    <table th:unless="${books.isEmpty()}">
        <thead>
            <tr><th>제목</th><th>저자</th><th>가격</th></tr>
        </thead>
        <tbody>
            <!-- books 리스트를 한 행씩 반복 -->
            <tr th:each="book : ${books}">
                <td>
                    <!-- 상세 페이지로 가는 링크: @{/books/{id}(id=...)} -->
                    <a th:href="@{/books/{id}(id=${book.id})}"
                       th:text="${book.title}">제목</a>
                </td>
                <td th:text="${book.author}">저자</td>
                <td th:text="${book.price}">0</td>
            </tr>
        </tbody>
    </table>

    <a th:href="@{/books/new}">새 도서 등록</a>
</body>
</html>
```

### 상세 — `templates/books/detail.html`

```html
<!DOCTYPE html>
<html lang="ko" xmlns:th="http://www.thymeleaf.org">
<head><meta charset="UTF-8"><title>도서 상세</title></head>
<body>
    <h1 th:text="${book.title}">제목</h1>
    <dl>
        <dt>저자</dt><dd th:text="${book.author}">저자</dd>
        <dt>가격</dt><dd th:text="${book.price}">0</dd>
    </dl>
    <a th:href="@{/books}">목록으로</a>
</body>
</html>
```

## 6. 폼 처리 — th:object / th:field 와 PRG 패턴

SSR이 빛나는 영역이 **폼 입력**입니다. Thymeleaf는 폼 객체를 모델에 바인딩해 입력값을 채우고 검증 오류를 표시하는 기능을 제공합니다.

### 폼 컨트롤러

```kotlin
@Controller
@RequestMapping("/books")
class BookFormController(private val bookService: BookService) {

    // 등록 폼 보여주기: GET /books/new
    @GetMapping("/new")
    fun newForm(model: Model): String {
        // 빈 폼 객체를 모델에 담아 둬야 th:object가 바인딩할 대상이 생긴다
        model.addAttribute("form", BookForm())
        return "books/form"
    }

    // 등록 처리: POST /books
    @PostMapping
    fun create(
        @Valid @ModelAttribute("form") form: BookForm,  // 폼 → 객체 바인딩 + 검증
        bindingResult: BindingResult,                    // 검증 결과 (Phase 4-1 연계)
    ): String {
        if (bindingResult.hasErrors()) {
            return "books/form"          // 오류가 있으면 폼을 다시 보여 줌
        }
        val saved = bookService.create(form.toCommand())
        // PRG: 저장 후 상세 페이지로 리다이렉트 (아래 설명)
        return "redirect:/books/${saved.id}"
    }
}

// 폼 전용 객체 (검증 애너테이션은 Phase 4-1 참고)
// 빈 폼 렌더링을 위해 기본값을 둔다(BookForm()). 필드 구성은 본문 CreateBookRequest와 동일.
data class BookForm(
    @field:NotBlank val title: String = "",
    @field:NotBlank val author: String = "",
    @field:Pattern(regexp = "^(?:\\d[- ]?){12}\\d$") val isbn: String = "",
    @field:Positive val price: Int = 0,
    @field:PastOrPresent val publishedAt: LocalDate = LocalDate.now(),
) {
    // 폼 객체 → 서비스 커맨드로 변환. 본문 Phase 2/4의 CreateBookRequest와 필드가 1:1로 맞는다.
    fun toCommand() = CreateBookRequest(title, author, isbn, price, publishedAt)
}
```

`@ModelAttribute`는 폼 필드(`title`, `author`, `isbn`, `price`, `publishedAt`)를 객체로 바인딩하는 아규먼트 리졸버를 동작시키고, `@Valid`는 [Phase 4-1](../phase-4-validation-config/01-bean-validation.md)의 Bean Validation을 그대로 적용합니다. **REST에서는 `@RequestBody`로 받던 것을, SSR 폼에서는 `@ModelAttribute`로 받는다**는 차이만 기억하면 됩니다. `toCommand()`가 폼을 본문의 `CreateBookRequest`로 변환하므로, 서비스 계층은 REST든 SSR이든 **동일한 DTO 계약**을 받습니다.

### 폼 템플릿 — `templates/books/form.html`

```html
<!DOCTYPE html>
<html lang="ko" xmlns:th="http://www.thymeleaf.org">
<head><meta charset="UTF-8"><title>도서 등록</title></head>
<body>
    <h1>도서 등록</h1>

    <!-- th:object: 이 폼이 다룰 모델 객체 지정 -->
    <form th:action="@{/books}" th:object="${form}" method="post">

        <!-- th:field="*{title}" 가 name/id/value 를 한 번에 처리 -->
        <div>
            <label>제목</label>
            <input type="text" th:field="*{title}">
            <!-- 해당 필드의 검증 오류 메시지 -->
            <span th:if="${#fields.hasErrors('title')}"
                  th:errors="*{title}">오류</span>
        </div>
        <div>
            <label>저자</label>
            <input type="text" th:field="*{author}">
            <span th:if="${#fields.hasErrors('author')}" th:errors="*{author}"></span>
        </div>
        <div>
            <label>ISBN</label>
            <input type="text" th:field="*{isbn}">
            <span th:if="${#fields.hasErrors('isbn')}" th:errors="*{isbn}"></span>
        </div>
        <div>
            <label>가격</label>
            <input type="number" th:field="*{price}">
            <span th:if="${#fields.hasErrors('price')}" th:errors="*{price}"></span>
        </div>
        <div>
            <label>출판일</label>
            <input type="date" th:field="*{publishedAt}">
            <span th:if="${#fields.hasErrors('publishedAt')}" th:errors="*{publishedAt}"></span>
        </div>

        <button type="submit">저장</button>
    </form>
</body>
</html>
```

`th:object`로 폼 전체가 다룰 객체를 지정하면, 내부에서 `*{title}`처럼 `*{}`(선택 변수식)로 그 객체의 프로퍼티에 접근합니다. **`th:field="*{title}"`** 한 줄이 `name="title"`, `id="title"`, `value="(현재값)"`을 모두 채워 주므로, 검증 실패로 폼을 다시 그릴 때 사용자가 입력했던 값이 그대로 보존됩니다.

### PRG 패턴 — Post/Redirect/Get

`create()`가 저장 후 `"redirect:/books/${id}"`를 반환한 것에 주목하세요. 이것이 **PRG(Post-Redirect-Get) 패턴** 입니다.

```
[잘못된 방식]                          [PRG 방식]
POST /books → 200 OK + HTML            POST /books → 302 Redirect → /books/1
새로고침(F5) → 폼이 또 전송됨(중복 저장!)   GET /books/1 → 200 OK + HTML
                                       새로고침 → 단순 GET 재요청 (안전)
```

폼 제출 응답을 HTML로 바로 내려주면, 사용자가 새로고침할 때 **POST가 재전송되어 중복 등록**이 발생합니다. 저장 직후 `redirect:`로 GET 페이지로 보내면, 이후 새로고침은 안전한 GET이 됩니다. `redirect:` 접두사는 `ThymeleafViewResolver`가 인식해 302 응답을 만들어 줍니다.

> [!TIP]
> 리다이렉트하면서 일회성 메시지("등록되었습니다")를 전달하려면 `RedirectAttributes.addFlashAttribute(...)`를 사용하세요. 세션에 잠깐 저장됐다가 다음 요청에서 한 번 읽히고 사라지는 **플래시 속성**입니다. 세션은 [4번 문서](04-session-login.md)에서 자세히 다룹니다.

## 다음 단계

이제 같은 도서 데이터를 JSON(`/api/books`)과 HTML(`/books`) 두 가지로 내려줄 수 있게 됐습니다. 다음 문서에서는 이 요청들이 컨트롤러에 닿기 **전후로** 공통 처리를 끼워 넣는 두 장치 — **서블릿 필터와 스프링 인터셉터** — 를 다룹니다. 요청 로깅, 인증 체크 같은 횡단 관심사를 처리하는 방법입니다.

➡️ **[3. 서블릿 필터와 스프링 인터셉터](03-filter-interceptor.md)**
