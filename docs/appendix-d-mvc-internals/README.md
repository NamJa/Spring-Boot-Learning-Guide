# 부록 D · Spring MVC 내부와 서버 사이드 렌더링

이 가이드의 본문(Phase 0~7)은 처음부터 끝까지 **REST API**에 집중했습니다. `@RestController`로 JSON을 주고받고, 그것을 JPA로 영속화하고, 클라우드에 배포하는 흐름이었죠. 실용적인 선택이었지만, 그 과정에서 의도적으로 건너뛴 것이 있습니다. 바로 **Spring MVC가 요청을 어떻게 처리하는지에 대한 내부 동작**과, 서버가 직접 HTML을 그려서 내려주는 **서버 사이드 렌더링(SSR, Server-Side Rendering)** 입니다.

REST만 다루면 `@GetMapping`을 붙인 메서드가 "마법처럼" JSON을 반환하는 것처럼 보입니다. 하지만 그 마법의 정체 — **DispatcherServlet**, HandlerMapping, HttpMessageConverter, 아규먼트 리졸버 — 를 알지 못하면, 조금만 비표준적인 요구사항을 만나도 막힙니다. 또한 관리자 페이지, 사내 도구, 간단한 웹사이트처럼 **브라우저에 완성된 화면을 내려주는** 전통적인 웹 애플리케이션은 여전히 널리 쓰입니다.

이 부록은 김영한 님의 *"스프링 MVC 1편 / 2편"* 에서 다루는 핵심 — 서블릿, MVC 내부 구조, SSR, 필터/인터셉터, 세션/로그인 — 을 Kotlin과 Spring Boot 4.1 맥락으로 재구성했습니다. **본문이 REST-only였기 때문에 비어 있던 "웹 계층의 기초"를 메우는 것**이 목표입니다.

## 1. 이 부록이 다루는 것

본문이 "REST API를 만드는 법"이었다면, 이 부록은 **"Spring MVC가 동작하는 원리"** 와 **"HTML을 직접 그리는 법"** 입니다. 본문에서 쓰던 도서 API(`com.example.bookapi`)를 그대로 이어받되, JSON을 내려주던 `/api/books`와 별개로 **HTML 화면을 내려주는 `/books`** 를 새로 추가하며 진행합니다.

| # | 문서 | 핵심 주제 |
|---|------|-----------|
| 1 | [DispatcherServlet과 요청 처리 흐름](01-dispatcher-servlet.md) | 서블릿/Tomcat, DispatcherServlet, HandlerMapping/Adapter, HttpMessageConverter, 아규먼트 리졸버 |
| 2 | [Thymeleaf 서버 사이드 렌더링](02-thymeleaf-ssr.md) | SSR vs REST, `starter-thymeleaf` 자동설정, `Model`, 타임리프 문법, 폼 처리와 PRG |
| 3 | [서블릿 필터와 스프링 인터셉터](03-filter-interceptor.md) | 필터 vs 인터셉터, `FilterRegistrationBean`, `HandlerInterceptor`, `WebMvcConfigurer` |
| 4 | [쿠키·세션과 로그인](04-session-login.md) | HTTP 무상태성, 쿠키 vs 세션, `HttpSession`, 세션 로그인, 세션 vs JWT 비교 |

## 2. 선수 지식

이 부록은 본 가이드의 **Phase 0~5** 를 어느 정도 따라왔다고 가정합니다. 구체적으로 다음을 알고 있어야 합니다.

- **[Phase 0-05 · Spring MVC vs WebFlux](../phase-0-spring-fundamentals/05-mvc-vs-webflux.md)** — 이 부록은 그중 **MVC(서블릿 스택)** 만 깊게 파고듭니다. WebFlux는 다루지 않습니다.
- **[Phase 2 · 첫 번째 REST API](../phase-2-first-api/README.md)** — `@RestController`, `@RequestMapping`, DTO와 JSON 직렬화의 기초.
- **[Phase 4 · 검증 · 예외](../phase-4-validation-config/README.md)** — Bean Validation과 전역 예외 처리. SSR 폼 검증에서 다시 등장합니다.
- **[Phase 5 · Spring Security 7 기초](../phase-5-production-features/02-security-basics.md)** — 필터 체인과 인증. 이 부록의 필터/세션 내용이 그 기반을 설명합니다.

> [!NOTE]
> 이 부록의 SSR 페이지는 본문의 `/api/books` JSON API와 **공존**합니다. 같은 애플리케이션 안에서 `@RestController`(JSON)와 `@Controller`(HTML)가 나란히 동작하는 구조를 직접 보게 됩니다. 둘이 충돌하지 않도록, JSON은 `/api/books`, 화면은 `/books`로 URL을 분리합니다.

## 3. 기준 스택

이 부록의 모든 코드는 다음 버전에서 검증되었습니다(2026-06-20 기준).

| 항목 | 버전 |
|------|------|
| Spring Boot | 4.1.0 |
| Spring Framework | 7.0.8+ |
| Kotlin | 2.3.21 |
| JDK | 21 |
| Tomcat (내장) | 11.0.x (Servlet 6.1) |
| Thymeleaf | 3.1.5 (`spring-boot-starter-thymeleaf`) |

> [!WARNING]
> 화면 템플릿 기술로 **JSP는 다루지 않습니다.** JSP는 실행 가능한 jar([Phase 6-1](../phase-6-build-deploy/01-executable-jar.md))와 궁합이 나쁘고(내장 Tomcat에서 제약이 많음), 현대 Spring SSR에서는 권장되지 않는 레거시입니다. 이 부록은 그 대안이자 사실상 표준인 **Thymeleaf**를 사용합니다.

## 다음 단계

➡️ **[1. DispatcherServlet과 요청 처리 흐름](01-dispatcher-servlet.md)** — `@GetMapping` 메서드 하나가 호출되기까지, 요청이 거치는 모든 단계를 해부합니다.
