# 쿠키·세션과 로그인

[3번 문서](03-filter-interceptor.md)의 인증 인터셉터에서 `session.getAttribute("loginMember")`를 사용하며 "세션"을 미뤄 뒀습니다. 이제 그 정체를 밝힙니다. 그런데 그러려면 먼저 한 가지 근본적인 사실부터 짚어야 합니다. **HTTP는 상태가 없다(stateless)** 는 것입니다.

## 1. HTTP의 무상태성 복습

[Phase 0](../phase-0-spring-fundamentals/00-server-side-intro.md)에서 봤듯, HTTP는 **요청-응답이 끝나면 연결을 잊는** 무상태 프로토콜입니다. 서버 입장에서 방금 로그인한 사용자가 보낸 다음 요청과, 처음 보는 사용자의 요청은 **구별할 방법이 없습니다.**

```
요청 1: POST /login (id=kim) → 응답: "로그인 성공"   ← 서버: 이 사람 누구지? 기억함
요청 2: GET  /books            → 응답: ???           ← 서버: ...누구세요?
```

요청 2에 "나 아까 로그인한 kim이야"라는 증거가 없으면 서버는 알 수 없습니다. 이 단절을 메우는 장치가 **쿠키와 세션** 입니다.

## 2. 쿠키 vs 세션

### 쿠키(Cookie)

서버가 응답에 `Set-Cookie` 헤더를 실어 보내면, 브라우저는 그 값을 저장해 두고 **이후 같은 서버로 가는 모든 요청에 `Cookie` 헤더로 자동 첨부**합니다. 이렇게 요청 간 연속성이 생깁니다.

```
응답:  Set-Cookie: SESSIONID=abc123
이후 요청:  Cookie: SESSIONID=abc123   ← 브라우저가 자동으로 붙임
```

> [!WARNING]
> 쿠키에 사용자 ID나 권한을 **직접** 담으면 안 됩니다. 쿠키는 클라이언트에 저장되므로 사용자가 위·변조할 수 있습니다(`Cookie: role=admin`으로 바꿔치기). 그래서 의미 없는 **세션 ID만** 쿠키에 담고, 실제 데이터는 서버에 두는 방식 — 세션 — 을 씁니다.

### 세션(Session)

**세션은 서버 메모리(또는 저장소)에 사용자별 데이터를 보관하고, 그 보관함을 가리키는 열쇠(세션 ID)만 쿠키로 주고받는 방식** 입니다.

```
[로그인 시]
  서버 메모리:  { "abc123" → {loginMember: kim, role: USER} }   ← 실제 데이터는 서버에
  응답:        Set-Cookie: JSESSIONID=abc123                    ← 열쇠만 클라이언트로

[이후 요청]
  요청:        Cookie: JSESSIONID=abc123
  서버:        abc123 → 보관함 조회 → "아, kim이구나"
```

| 구분 | 쿠키 | 세션 |
|---|---|---|
| 저장 위치 | 클라이언트(브라우저) | 서버 |
| 보안 | 위·변조 가능 | 세션 ID만 노출, 데이터는 서버 |
| 용량 | 작음(수 KB) | 서버 자원 한도 내 |
| 비고 | 세션 동작에 필수(세션 ID 운반) | 내부적으로 쿠키를 사용 |

Servlet 스펙에서 세션 ID 쿠키의 이름은 관례적으로 **`JSESSIONID`** 입니다. Tomcat이 자동으로 발급·관리합니다.

## 3. HttpSession — 생성·조회·만료

Servlet은 세션을 `jakarta.servlet.http.HttpSession`으로 추상화합니다. 우리는 `JSESSIONID` 쿠키를 직접 다룰 필요 없이 이 객체만 쓰면 됩니다.

```kotlin
// 생성/조회
val session = request.getSession()        // 없으면 새로 생성 (기본값 create=true)
val session2 = request.getSession(false)  // 있으면 반환, 없으면 null (조회 전용)

// 저장 / 읽기 / 삭제
session.setAttribute("loginMember", member)
val member = session.getAttribute("loginMember") as Member?
session.removeAttribute("loginMember")

// 세션 전체 만료 (로그아웃)
session.invalidate()
```

- `getSession(true)`(기본): 세션이 없으면 **새로 만들고** `Set-Cookie`로 `JSESSIONID`를 내려보냅니다.
- `getSession(false)`: **조회만** 하고 없으면 `null` — 인증 체크에서 "로그인 안 했으면 만들지도 말라"는 의도에 적합합니다([3번 문서](03-filter-interceptor.md)의 인터셉터가 이걸 썼습니다).

## 4. 세션 기반 로그인 구현

이제 `@Controller`와 세션, 그리고 [3번 문서](03-filter-interceptor.md)의 인터셉터를 합쳐 로그인을 완성합니다. 도서 화면(`/books`)은 로그인해야 볼 수 있도록 보호합니다.

### 로그인 컨트롤러

```kotlin
package com.example.bookapi.controller

import jakarta.servlet.http.HttpServletRequest
import org.springframework.stereotype.Controller
import org.springframework.ui.Model
import org.springframework.web.bind.annotation.*

@Controller
class LoginController(private val memberService: MemberService) {

    // 로그인 폼
    @GetMapping("/login")
    fun loginForm(): String = "login/form"   // templates/login/form.html

    // 로그인 처리
    @PostMapping("/login")
    fun login(
        @RequestParam loginId: String,
        @RequestParam password: String,
        @RequestParam(required = false) redirect: String?,
        request: HttpServletRequest,
    ): String {
        val member = memberService.authenticate(loginId, password)
            ?: return "redirect:/login?error"      // 인증 실패 → 폼으로

        // 인증 성공: 세션을 만들고 회원 정보를 저장
        val session = request.getSession()         // 여기서 JSESSIONID 발급
        session.setAttribute("loginMember", member)

        // 원래 가려던 곳이 있으면 거기로, 없으면 목록으로 (3번 문서 인터셉터와 연동)
        return "redirect:${redirect ?: "/books"}"
    }

    // 로그아웃
    @PostMapping("/logout")
    fun logout(request: HttpServletRequest): String {
        request.getSession(false)?.invalidate()    // 세션 폐기 (없으면 무시)
        return "redirect:/login"
    }
}
```

### 인증 가드 — 인터셉터 재사용

로그인 여부 확인은 [3번 문서](03-filter-interceptor.md)에서 만든 `LoginCheckInterceptor`가 그대로 담당합니다. `WebMvcConfigurer`에서 `/books/**`에 적용하고 `/login`·`/logout`은 제외했던 그 설정입니다. **세션이 없거나 `loginMember`가 비어 있으면 `/login`으로 리다이렉트** 됩니다.

### 컨트롤러에서 로그인 사용자 꺼내기

매번 `session.getAttribute(...)`를 캐스팅하는 대신, `@SessionAttribute`를 쓰면 아규먼트 리졸버([1번 문서](01-dispatcher-servlet.md))가 세션에서 값을 꺼내 줍니다.

```kotlin
@Controller
@RequestMapping("/books")
class BookViewController(private val bookService: BookService) {

    @GetMapping
    fun list(
        @SessionAttribute("loginMember") member: Member,  // 세션에서 자동 주입
        model: Model,
    ): String {
        model.addAttribute("loginName", member.name)      // 화면에 "kim님 환영"
        model.addAttribute("books", bookService.findAll())
        return "books/list"
    }
}
```

## 5. 세션 설정

세션의 수명과 쿠키 보안은 `application.yml`로 조정합니다([Phase 1-5](../phase-1-project-setup/05-application-yml.md)).

```yaml
server:
  servlet:
    session:
      timeout: 30m            # 마지막 요청 후 30분간 활동 없으면 만료 (기본 30분)
      cookie:
        http-only: true       # JS의 document.cookie 접근 차단 (XSS 방어)
        secure: true          # HTTPS 연결에서만 쿠키 전송 (운영 권장)
        same-site: lax        # CSRF 완화
```

> [!TIP]
> `timeout`은 **고정 만료가 아니라 비활동 기준** 입니다. 요청이 올 때마다 30분이 갱신됩니다. `http-only`·`secure`·`same-site`는 세션 탈취 공격을 줄이는 기본 방어선이니 운영에서는 꼭 켜세요.

> [!WARNING]
> 세션은 기본적으로 **서버 메모리**에 저장됩니다. 서버를 여러 대로 늘리면(스케일 아웃, [Phase 7](../phase-7-cloud-run/01-cloud-run-concepts.md)) A 서버에 만든 세션을 B 서버가 모릅니다. Cloud Run처럼 인스턴스가 늘었다 줄었다 하는 환경에서는 더 심각하죠. 해결책은 **Redis 등 외부 세션 저장소(`spring-session-data-redis`)** 로 세션을 외부화하거나, 아예 세션을 안 쓰는 **토큰 방식**으로 가는 것입니다.

## 6. 세션 방식 vs 토큰(JWT) 방식

위 경고가 자연스럽게 다음 질문으로 이어집니다. **상태를 서버에 둘 것인가, 클라이언트에 둘 것인가?**

```
[세션 방식 — 상태가 서버에]            [토큰(JWT) 방식 — 상태가 토큰에]
쿠키(JSESSIONID) → 서버 보관함 조회     Authorization: Bearer <JWT>
                                       서버는 토큰 서명만 검증, 저장소 불필요
```

| 구분 | 세션 방식 | 토큰(JWT) 방식 |
|---|---|---|
| 상태 저장 위치 | 서버(stateful) | 토큰 자체(stateless) |
| 확장성(스케일 아웃) | 외부 세션 저장소 필요 | 서버 간 공유 불필요(유리) |
| 무효화(로그아웃) | `invalidate()` 즉시 | 어려움(만료까지 유효, 블랙리스트 필요) |
| 저장/전달 | 쿠키(`JSESSIONID`) | 헤더(`Authorization: Bearer`) 흔함 |
| 적합한 곳 | 전통 SSR 웹, 동일 도메인 | SPA·모바일, 마이크로서비스, 공개 REST API |
| 본 가이드 연계 | 이 부록(SSR) | [Phase 2 REST](../phase-2-first-api/README.md) + [Phase 5 보안](../phase-5-production-features/02-security-basics.md) |

> [!NOTE]
> **무엇이 더 좋다기보다 맥락의 문제** 입니다. 이 부록의 SSR 도서 화면처럼 브라우저가 쿠키를 자동으로 운반하는 동일 도메인 웹앱은 세션이 자연스럽습니다. 반면 Phase 2처럼 모바일 앱이나 외부 클라이언트가 호출하는 **스테이트리스 REST API** 에서는 매 요청에 토큰을 실어 보내는 방식이 서버 확장에 유리합니다.

**[Phase 5-2 · Spring Security 7](../phase-5-production-features/02-security-basics.md)** 는 이 두 방식을 모두 지원합니다. 폼 로그인 + 세션(전통 웹), 또는 `SessionCreationPolicy.STATELESS`로 세션을 끄고 토큰 기반으로 동작하는 REST 보안 모두 구성할 수 있습니다. 이 부록에서 손으로 만든 인터셉터 인증은 그 내부 원리를 이해하기 위한 학습용이며, 실무에서는 Spring Security의 검증된 필터 체인([3번 문서 6절](03-filter-interceptor.md))에 맡기는 것이 정석입니다.

## 다음 단계

🎉 **축하합니다 — 부록 D를 끝으로 모든 부록을 완주하셨습니다!**

본 가이드 본문에서 REST API로 시작해, 부록 A·B에서 JPA와 Querydsl의 깊은 원리를 파고들었고, 이 부록 D에서는 그동안 비어 있던 **웹 계층의 기초** 를 메웠습니다. 이제 여러분은 다음을 자신 있게 설명할 수 있습니다.

- 요청이 **DispatcherServlet → HandlerMapping/Adapter → 컨트롤러 → 컨버터/뷰리졸버** 를 거치는 전체 흐름
- `@Controller`로 **Thymeleaf SSR** 화면과 폼(PRG)을 만드는 법
- **필터와 인터셉터** 로 횡단 관심사를 처리하는 위치와 방법
- **쿠키·세션 기반 로그인** 과 세션 vs 토큰 방식의 트레이드오프

여기서 익힌 MVC 내부 동작은 Spring Security, Spring Data, Actuator 등 거의 모든 Spring 웹 기술의 토대입니다. 더 깊이 들어가고 싶다면 공식 레퍼런스를 권합니다.

- 🏠 **[가이드 홈으로 돌아가기](../README.md)**
- 📖 **[Spring Framework — Web MVC 공식 문서](https://docs.spring.io/spring-framework/reference/web/webmvc.html)**

수고하셨습니다. 이제 만들고, 배포하고, 디버깅할 차례입니다. 🚀
