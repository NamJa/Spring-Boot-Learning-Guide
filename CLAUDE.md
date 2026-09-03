# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Documentation-only repository — a Korean-language tutorial for Kotlin developers learning the Spring Boot framework, from core concepts (IoC/DI, auto-configuration) through REST APIs, Spring Data JPA, validation/security/observability, and deployment (JAR / Docker / GraalVM native). No application source code or tests.

Served as a **generated static HTML site**. **`src/**/*.html` (content HTML fragments) are the source of truth**; `tools/build_site.py` wraps each one in the page shell and writes it to `docs/**/*.html`, which GitHub Pages serves. Markdown was retired (2026-07) because ASCII-art diagrams limited what could be drawn — diagrams are now hand-authored HTML/CSS components (`dg-*`).

## Structure

- `src/phase-{0..7}-*/`, `src/appendix-{a..f}-*/` — **edit these.** Content HTML fragments: no `<html>`/`<head>`/nav, just the page body (`<h1>` first). 부록: A=JPA 심화, B=Querydsl, C=AOP/프록시 고급, D=Spring MVC 내부 원리 & SSR, E=서비스 규모·도메인별 설계 전략(모듈러 모놀리스 / Spring Modulith 2.1.1 — Boot BOM 관리 대상 아님 / 도메인 성격별 전략), F=운영 현장 인사이트(2026-09 기준 커뮤니티 후기를 CS 배경과 함께: 가상 스레드 실전 / HikariCP·캐시·락 / 아웃박스·멱등성·재시도·속도 제한 / 컨테이너 속 JVM·K8s 프로브·종료 예산 / OTel 스타터·gRPC(4.1)·Spring AI 2.0 MCP·Passkeys·InetAddressFilter). 부록 F 각 페이지 끝의 「더 읽을거리」에 인용 출처(Medium·LinkedIn·velog·spring.io 등)를 남기는 관례를 유지. Querydsl은 OpenFeign 포크(`io.github.openfeign.querydsl`; `querydsl-jpa`는 classifier 없이, `querydsl-apt`는 `:jakarta`) 기준.
- `src/index.html` — home page (→ `docs/index.html`). `src/glossary.html` — 용어집 (nav 「개요」 카테고리).
- `src/_nav.html` — nav tree source; links are **root-relative** and the build rewrites them per page and marks the current one `active`. Update when adding/renaming pages.
- `tools/build_site.py` — generator. `tools/verify_site.py` — link/feature verifier.
- `tools/assets/base.css` (layout·typography·legacy diagram classes), `tools/assets/diagrams.css` (the `dg-*` component library), `tools/assets/app.js` — copied/concatenated into `docs/assets/{style.css,app.js}` at build time. **Edit these, never `docs/assets/*`.**
- **Everything under `docs/` is generated and committed** (Pages serves it directly). Never hand-edit `docs/`.

Page files follow `phase-N-topic/NN-slug.html` with a `README.html` (phase overview) per directory.

## Build & verify (IMPORTANT)

After editing anything in `src/` or `tools/`, rebuild **and** verify:

```bash
python3 -m venv .venv && . .venv/bin/activate   # first time only
pip install pygments                            # first time only (markdown 은 더 이상 필요 없음)
python tools/build_site.py                      # 81 pages + assets → docs/
python tools/verify_site.py                     # 링크·앵커·CSS·JS 훅 검증 (오류 시 exit 1)
```

`tools/build_site.py --check` 는 빌드 없이 소스만 검사하고, `--page <경로>` 는 한 페이지만 다시 만듭니다. Then commit both `src/` and the regenerated `docs/`. Commit messages follow `docs:` / `docs(scope):` / `refactor(site):` prefixes with a Korean subject (see `git log`).

## Source HTML conventions

- **Code blocks**: `<pre class="code" data-lang="kotlin"><code>…원본 그대로…</code></pre>`. 빌드가 Pygments 로 하이라이팅하고 복사 버튼을 붙입니다. 소스에는 색칠된 마크업을 넣지 마세요. `data-lang` 은 `kotlin`/`bash`/`yaml`/`json`/`sql`/`http`/`text` 등.
- **Callouts**: `<aside class="callout tip|note|warning|important">…</aside>` — 라벨(💡 TIP 등)은 CSS 가 붙입니다.
- **Diagrams**: `<figure class="dg">` 안에 컴포넌트를 조립합니다(`figcaption` = 제목, `.dg-foot` = 각주). 사용 가능한 컴포넌트: `dg-pipe`(수평 흐름), `dg-steps`(번호 단계), `dg-vs`(좌우 비교), `dg-layers`(레이어 스택), `dg-fork`(분기), `dg-seq`(요청/응답 시퀀스), `dg-grid`(격자), `dg-timeline`, `dg-states`(상태 전이), `dg-box`(중첩 영역), `dg-http`(HTTP 메시지 주석), `dg-tree`(파일/타입 트리), `dg-cross`(횡단 매트릭스). `<figure class="dg" data-focusable>` 를 주면 단계 클릭 강조가 켜집니다. 정의는 `tools/assets/diagrams.css` 상단 주석 참고.
- **Tabs**: `<div class="tabs"><div class="tab-panel" data-title="…">…</div>…</div>` — 탭 버튼은 JS 가 만듭니다. **탭 패널 안에 `<h2>`/`<h3>` 를 넣지 마세요** (목차가 숨겨진 콘텐츠를 가리키게 됩니다).
- **Accordion**: `<details><summary>…</summary>…</details>` (CSS 만으로 동작).
- **Links**: 페이지 간 링크는 현재 파일 기준 상대경로 `.html` 로 씁니다. `.md` 링크가 남아 있으면 검증에서 실패합니다.
- **Headings**: `<h2>`/`<h3>` 에는 id 를 직접 쓰지 않아도 빌드가 슬러그를 부여하고 우측 목차를 만듭니다(h2 가 2개 이상일 때).
- 옛 자동 변환 산물인 `flowchart`/`layer-stack`/`filetree` 클래스도 계속 유효합니다(`base.css`). 새 도식은 `dg-*` 를 쓰세요.

## Content Conventions

- **One running example across the whole guide.** Every phase and appendix builds the same Book API under the package root `com.example.bookapi` (subpackages: `controller`, `service`, `repository`, `domain`, `dto`, `config`, `exception`, `validation`, `client`, plus `aop`, `health`, `mapper` in the appendices). The canonical types are `BookService` / `BookController` / `BookRepository`. Reuse these names and package paths when adding examples — do **not** introduce a new sample domain.
- **Cross-phase continuity is actively maintained.** The git history shows repeated "연속성 검증 / 정합화" passes that keep package names, class names, and service-method contracts identical across pages. When editing one page, check that signatures and package paths still match the phases/appendices that reference the same code, so a reader following along never hits a contradiction.
- Appendix code targets the same example but at intermediate/advanced depth (A~D mirror the 김영한 roadmap: JPA 기본편 / Querydsl / 핵심원리 고급편 / MVC 1·2편). Appendix E is architecture guidance, not a lecture mirror; to discuss modules it assumes the Book API grew into a bookstore with `catalog` / `order` / `member` subpackages under the same `com.example.bookapi` root — that is an extension of the running example, not a new sample domain.

## Language & Tech Baseline

- All documentation is written in **Korean (한국어)**. Maintain Korean when editing or adding content.
- All code examples use **Kotlin**.
- Reference versions (verified 2026-08-30 against the Spring Boot 4.1.1 BOM and real Spring Initializr output): **Spring Boot 4.1.1** (2026-08-20, latest GA; 4.0.8 is the maintenance line, 3.5.x OSS support ended 2026-06-30 at 3.5.16; 4.2.0-M1 is the next feature line), Spring Framework 7.0.9, Spring Security 7.1.1, Spring Data 2026.0.1, Hibernate ORM 7.4.5.Final, Hibernate Validator 9.1.3.Final, Kotlin 2.3.21 (standalone latest 2.4.10), JDK 21 (17~26 supported, latest patch 21.0.12; SDKMAN `21.0.12+1.1-tem`), Gradle 9.7.1 (Initializr wrapper and upstream latest), io.spring.dependency-management 1.1.7, Tomcat 11.0.24, Jetty 12.1.12, Jackson **3**.1.5, JUnit 6.0.3, Testcontainers 2.0.5, Micrometer 1.17.1, Flyway 12.4.0, HikariCP 7.0.2, H2 2.4.240, Thymeleaf 3.1.5, Querydsl (OpenFeign) 7.6, GraalVM CE 25 (`25.3.4+1.r25-graalce`) + Native Build Tools 1.1.8 (BOM-managed; upstream latest 1.1.11). Keep version claims consistent with `src/index.html`.
- **Spring Boot 4 conventions to preserve when editing examples** (these differ from every Boot 3 example on the web):
  - Jackson 3: `tools.jackson.*` packages, `tools.jackson.module:jackson-module-kotlin`, immutable `JsonMapper`; annotations stay in `com.fasterxml.jackson.annotation`. `spring.jackson.datatype.datetime.*` holds the date/time features (`WRITE_DATES_AS_TIMESTAMPS` moved to `DateTimeFeature`).
  - Starters: `spring-boot-starter-webmvc` (not `-web`), `spring-boot-starter-aspectj` (not `-aop`), `spring-boot-h2console` for the H2 console, per-technology test starters `spring-boot-starter-<tech>-test`.
  - Testing: `@MockitoBean` (`@MockBean` removed), `RestTestClient` + `@AutoConfigureRestTestClient` (`TestRestTemplate` moved to `org.springframework.boot.resttestclient` and is no longer auto-configured), `MockMvcTester`.
  - Health: `org.springframework.boot.health.contributor.{Health, HealthIndicator}`.
  - Declarative HTTP clients: `@ImportHttpServices` from `org.springframework.web.service.registry`; config keys `spring.http.clients.*` (defaults) and `spring.http.serviceclient.<group>.*` (per group).
  - Resilience: `org.springframework.resilience.annotation.{Retryable, ConcurrencyLimit, EnableResilientMethods}`; `@Retryable` uses `maxRetries`/`delay`(ms)/`multiplier` — there is no `maxAttempts`.
  - API versioning (new in Framework 7): `version` attribute on `@RequestMapping`/`@GetMapping` etc. — `"1.1"` fixed, `"1.1+"` baseline, absent = matches any version at lowest precedence. Config via `spring.mvc.apiversion.*` (`use.header` / `use.query-parameter` / `use.path-segment` / `use.media-type-parameter`, plus `default`, `supported`, `detect-supported`, `required`) or `WebMvcConfigurer.configureApiVersioning(ApiVersionConfigurer)`. Unsupported/unmatched/missing versions → `InvalidApiVersionException` / `NotAcceptableApiVersionException` / `MissingApiVersionException`, all HTTP 400.
  - Startup optimization: CDS (`-XX:ArchiveClassesAtExit` → `-XX:SharedArchiveFile`, JDK 17+) and the AOT cache (`-XX:AOTCacheOutput` → `-XX:AOTCache`, JDK 25+); both need `-Djarmode=tools … extract` plus a training run with `-Dspring.context.exit=onRefresh`. Buildpack env vars `BP_JVM_CDS_ENABLED` / `BP_JVM_AOTCACHE_ENABLED`.
  - Kotlin: Initializr emits `-Xannotation-default-target=param-property` and an `allOpen { … }` block for JPA annotations.

## Verifying links & features

`tools/verify_site.py` 가 다음을 한 번에 검사하고, 문제가 있으면 exit 1 로 실패합니다.

1. 모든 내부 링크·자산 경로가 실제 파일로 해석되는지 (`.md` 링크가 남아 있으면 실패)
2. 페이지 내 앵커(`#id`)가 존재하는지 (다른 페이지 앵커는 경고)
3. 변환되지 않은 ASCII 도식(`data-todo="rewrite"`)이 남아 있지 않은지
4. 소스에서 쓴 모든 CSS 클래스에 규칙이 있는지 (오타 잡기)
5. `app.js` 가 기대하는 DOM 훅(`.code-block`, `.tabs`, `.dg[data-focusable]`, `.toc a`)이 실제로 존재하는지
6. 페이지 셸 필수 요소(`<title>`, 사이드바, `app.js`, 현재 항목 `active` 표시)

```bash
python tools/verify_site.py     # 통계 + 경고/오류
```

로컬에서 눈으로 확인할 때는 서버로 띄웁니다(파일 프로토콜에서도 동작하지만 서버가 실제 배포와 같습니다).

```bash
python3 -m http.server 3000 --directory docs
```

(`@{...}` is a Thymeleaf URL expression that appears inside code examples — not a real link; 검사기가 무시합니다.)

## Deployment

GitHub Pages serves the site from the **`main` branch `/docs` folder** (repo `NamJa/Spring-Boot-Learning-Guide`, live at https://namja.github.io/Spring-Boot-Learning-Guide/). Pushing to `main` triggers a rebuild automatically — there is no Actions workflow; Pages serves the committed `docs/*.html` directly. `docs/.nojekyll` disables Jekyll so underscore/`assets` paths are served as-is. Commit the regenerated HTML or the live site will be stale.
