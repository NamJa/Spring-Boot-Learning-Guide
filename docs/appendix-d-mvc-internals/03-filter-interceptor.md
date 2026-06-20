# 서블릿 필터와 스프링 인터셉터

요청 로깅, 인증 확인, 요청마다 추적 ID 부여… 이런 작업은 특정 컨트롤러 하나의 일이 아니라 **수많은 요청에 공통으로 적용되는 횡단 관심사(cross-cutting concern)** 입니다. 컨트롤러마다 같은 코드를 복붙할 수는 없죠. Spring MVC에는 이를 위한 두 장치가 있습니다. **서블릿 필터(Filter)** 와 **스프링 인터셉터(HandlerInterceptor)** 입니다.

둘은 비슷해 보이지만 **동작하는 위치가 다릅니다.** 이 차이가 둘의 용도를 가릅니다.

## 1. 실행 위치 — 필터 vs 인터셉터

[1번 문서](01-dispatcher-servlet.md)에서 본 구조를 떠올려 보세요. 요청은 **서블릿 컨테이너(Tomcat) → DispatcherServlet → 컨트롤러** 순으로 흐릅니다. 필터와 인터셉터는 이 흐름의 **서로 다른 지점**에 끼어듭니다.

```
                          서블릿 컨테이너 (Tomcat) 영역
  ┌───────────────────────────────────────────────────────────────────┐
  │                                                                     │
  │   [필터 A] → [필터 B] →  ┌──── DispatcherServlet (스프링 영역) ────┐ │
  │   (Filter)              │                                         │ │
  │                         │  [인터셉터 preHandle]                    │ │
  │                         │       ↓                                 │ │
  │                         │  [Controller 실행]                       │ │
  │                         │       ↓                                 │ │
  │                         │  [인터셉터 postHandle]                   │ │
  │                         │       ↓ (뷰 렌더링)                       │ │
  │                         │  [인터셉터 afterCompletion]              │ │
  │   [필터 A] ← [필터 B] ←  └─────────────────────────────────────────┘ │
  │                                                                     │
  └───────────────────────────────────────────────────────────────────┘
   요청 ─►                                                       ─► 응답
```

| 구분 | 서블릿 필터 (Filter) | 스프링 인터셉터 (HandlerInterceptor) |
|---|---|---|
| 소속 | **서블릿 컨테이너**(Tomcat) | **Spring MVC**(DispatcherServlet 내부) |
| 실행 시점 | DispatcherServlet **이전/이후** | DispatcherServlet **이후**, 컨트롤러 **전후** |
| 스펙 | `jakarta.servlet.Filter` | `org.springframework.web.servlet.HandlerInterceptor` |
| 어떤 핸들러가 매핑됐는지 | 모름 (서블릿 도달 전) | 앎 (`handler` 객체를 받음) |
| 등록 방법 | `FilterRegistrationBean` | `WebMvcConfigurer` |
| 주 용도 | 인코딩, 요청 로깅, 보안(아주 넓은 범위) | 인증/인가, 요청별 컨텍스트, 핸들러 의존 로직 |

핵심 직관: **필터는 "스프링 바깥에서 모든 요청을 거르는 그물"** 이고, **인터셉터는 "스프링 안에서 컨트롤러를 감싸는 래퍼"** 입니다. 인터셉터는 DispatcherServlet 안에서 동작하므로 어떤 핸들러가 호출될지 알고, `Model`과 뷰 렌더링 사이에도 끼어들 수 있습니다. 필터는 그보다 바깥이라 더 일찍/넓게 작동하지만 스프링의 내부 정보는 모릅니다.

## 2. 서블릿 필터 — 요청 로깅 예제

필터는 `jakarta.servlet.Filter` 인터페이스를 구현합니다. 핵심은 `doFilter` 안에서 **`chain.doFilter(...)`를 호출하기 전이 "요청 진입 시점", 호출한 후가 "응답 반환 시점"** 이라는 점입니다.

```kotlin
package com.example.bookapi.config

import jakarta.servlet.*
import jakarta.servlet.http.HttpServletRequest
import org.slf4j.LoggerFactory

class RequestLoggingFilter : Filter {

    private val log = LoggerFactory.getLogger(javaClass)

    override fun doFilter(
        request: ServletRequest,
        response: ServletResponse,
        chain: FilterChain,           // 다음 필터(또는 서블릿)로 넘기는 통로
    ) {
        val req = request as HttpServletRequest
        val start = System.currentTimeMillis()
        log.info("[REQ] {} {}", req.method, req.requestURI)   // 진입 시점

        try {
            chain.doFilter(request, response)   // ← 다음 단계로 진행 (필수!)
        } finally {
            val took = System.currentTimeMillis() - start
            log.info("[RES] {} {} ({}ms)", req.method, req.requestURI, took)  // 반환 시점
        }
    }
}
```

> [!WARNING]
> `chain.doFilter(...)`를 호출하지 않으면 **요청이 다음 단계로 전달되지 않고 거기서 끝납니다.** 인증 실패 시 차단하는 용도로는 의도적으로 쓰지만, 무심코 빠뜨리면 모든 요청이 멈춥니다.

### FilterRegistrationBean으로 등록

Spring Boot에서 필터를 등록하는 권장 방법은 **`FilterRegistrationBean`** 을 빈으로 노출하는 것입니다. URL 패턴과 순서를 명시적으로 제어할 수 있습니다.

```kotlin
import org.springframework.boot.web.servlet.FilterRegistrationBean
import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration

@Configuration
class FilterConfig {

    @Bean
    fun requestLoggingFilter(): FilterRegistrationBean<RequestLoggingFilter> =
        FilterRegistrationBean(RequestLoggingFilter()).apply {
            addUrlPatterns("/*")      // 적용 URL 패턴
            order = 1                 // 여러 필터 간 실행 순서(작을수록 먼저)
            setName("requestLoggingFilter")
        }
}
```

> [!TIP]
> 간단한 경우 필터 클래스에 `@Component`만 붙여도 자동 등록되지만, **URL 패턴 제한이나 순서 제어가 필요하면 `FilterRegistrationBean`을 쓰세요.** `@Component`로 등록한 필터는 기본적으로 모든 요청(`/*`)에 적용됩니다.

## 3. 스프링 인터셉터 — HandlerInterceptor

인터셉터는 `HandlerInterceptor` 인터페이스의 세 메서드로 컨트롤러 호출 전후에 개입합니다.

| 메서드 | 호출 시점 | 반환/특징 |
|---|---|---|
| `preHandle` | 컨트롤러 호출 **직전** | `false` 반환 시 **요청 중단**(컨트롤러 미실행) |
| `postHandle` | 컨트롤러 실행 **후, 뷰 렌더링 전** | `ModelAndView` 조작 가능. 예외 발생 시 호출 안 됨 |
| `afterCompletion` | 뷰 렌더링까지 **완료 후** | 예외가 나도 항상 호출 → 리소스 정리/로깅에 적합 |

### 예제 — 요청 ID 부여 + 처리 시간 측정

```kotlin
package com.example.bookapi.config

import jakarta.servlet.http.HttpServletRequest
import jakarta.servlet.http.HttpServletResponse
import org.slf4j.LoggerFactory
import org.springframework.web.servlet.HandlerInterceptor
import org.springframework.web.servlet.ModelAndView
import java.util.UUID

class RequestContextInterceptor : HandlerInterceptor {

    private val log = LoggerFactory.getLogger(javaClass)

    override fun preHandle(
        request: HttpServletRequest,
        response: HttpServletResponse,
        handler: Any,            // ★ 어떤 핸들러가 실행될지 안다 (필터와의 차이!)
    ): Boolean {
        val requestId = UUID.randomUUID().toString().take(8)
        request.setAttribute("requestId", requestId)
        request.setAttribute("startTime", System.currentTimeMillis())
        log.info("[{}] preHandle → {}", requestId, handler)
        return true              // false면 여기서 중단 (인증 거부 등에 활용)
    }

    override fun postHandle(
        request: HttpServletRequest, response: HttpServletResponse,
        handler: Any, modelAndView: ModelAndView?,
    ) {
        val requestId = request.getAttribute("requestId")
        log.info("[{}] postHandle (뷰 렌더링 직전)", requestId)
    }

    override fun afterCompletion(
        request: HttpServletRequest, response: HttpServletResponse,
        handler: Any, ex: Exception?,
    ) {
        val requestId = request.getAttribute("requestId")
        val took = System.currentTimeMillis() - (request.getAttribute("startTime") as Long)
        log.info("[{}] afterCompletion ({}ms){}", requestId, took,
            ex?.let { " ex=${it.message}" } ?: "")
    }
}
```

### 인증 체크 인터셉터 예제

`preHandle`이 `false`를 반환하면 컨트롤러가 실행되지 않는 점을 이용해, 간단한 인증 가드를 만들 수 있습니다([4번 문서](04-session-login.md)의 세션 로그인에서 다시 등장합니다).

```kotlin
class LoginCheckInterceptor : HandlerInterceptor {
    override fun preHandle(req: HttpServletRequest, res: HttpServletResponse, handler: Any): Boolean {
        val session = req.getSession(false)          // 기존 세션만 조회(없으면 null)
        if (session?.getAttribute("loginMember") == null) {
            res.sendRedirect("/login?redirect=${req.requestURI}")  // 로그인 페이지로
            return false                              // 요청 중단
        }
        return true
    }
}
```

## 4. WebMvcConfigurer로 인터셉터 등록

인터셉터는 필터와 달리 **`WebMvcConfigurer`의 `addInterceptors`** 로 등록합니다. 여기서 적용 경로(`addPathPatterns`)와 제외 경로(`excludePathPatterns`), 그리고 등록 순서를 지정합니다.

```kotlin
import org.springframework.context.annotation.Configuration
import org.springframework.web.servlet.config.annotation.InterceptorRegistry
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer

@Configuration
class WebMvcConfig : WebMvcConfigurer {

    override fun addInterceptors(registry: InterceptorRegistry) {
        // 모든 요청에 공통 컨텍스트 인터셉터
        registry.addInterceptor(RequestContextInterceptor())
            .order(1)
            .addPathPatterns("/**")

        // 로그인 체크: /books/** 에만 적용, 단 로그인/정적/조회 화면은 제외
        registry.addInterceptor(LoginCheckInterceptor())
            .order(2)
            .addPathPatterns("/books/**")
            .excludePathPatterns("/login", "/logout", "/css/**", "/*.ico", "/error")
    }
}
```

> [!TIP]
> 인터셉터의 경로 패턴(`/**`, `/books/**`)은 **필터의 URL 패턴보다 훨씬 유연**합니다. 특정 컨트롤러군에만, 혹은 일부 경로를 제외하고 적용하는 세밀한 제어가 인터셉터를 인증/인가에 즐겨 쓰는 이유입니다. 필터는 서블릿 도달 전이라 "어떤 핸들러인지"를 모르므로 이런 제어가 어렵습니다.

## 5. 적용 순서 정리

요청 하나가 들어왔을 때 전체 실행 순서를 정리하면 다음과 같습니다.

```
요청
 → [필터들]  order 작은 순서로 doFilter 진입
   → DispatcherServlet
     → [인터셉터들] preHandle  order 작은 순서로
       → Controller
     ← [인터셉터들] postHandle  (역순)
       → 뷰 렌더링
     ← [인터셉터들] afterCompletion (역순)
   ← DispatcherServlet
 ← [필터들]  doFilter 빠져나옴 (진입 역순)
응답
```

- **필터끼리**는 `order` 값이 작을수록 먼저 진입하고, 응답 시엔 역순으로 빠져나옵니다(스택 구조).
- **인터셉터끼리**는 등록/`order` 순서대로 `preHandle`, 그 역순으로 `postHandle`·`afterCompletion`이 호출됩니다.
- 전체로 보면 **필터가 인터셉터를 바깥에서 감쌉니다.**

## 6. Phase 5 보안과의 관계

**[Phase 5-2 · Spring Security 7](../phase-5-production-features/02-security-basics.md)** 의 인증/인가는 사실상 **거대한 서블릿 필터 체인(`FilterChainProxy`)** 으로 구현되어 있습니다 — 즉 이 문서에서 배운 "필터"가 Security의 동작 원리 그 자체입니다. 따라서 직접 만드는 인증 인터셉터는 학습·소규모용으로 충분하지만, 실제 운영 인증/인가는 Spring Security에 맡기는 것이 정석입니다.

## 다음 단계

인증 인터셉터에서 `session.getAttribute("loginMember")`를 슬쩍 사용했는데, **그 "세션"이 정확히 무엇인지** 는 아직 설명하지 않았습니다. 다음 문서에서 HTTP의 무상태성부터 시작해 쿠키와 세션, 그리고 세션 기반 로그인을 완성하고, 세션 방식과 토큰(JWT) 방식을 비교합니다.

➡️ **[4. 쿠키·세션과 로그인](04-session-login.md)**
