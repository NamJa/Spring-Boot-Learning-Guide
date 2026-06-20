# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Documentation-only repository — a Korean-language tutorial for Kotlin developers learning the Spring Boot framework, from core concepts (IoC/DI, auto-configuration) through REST APIs, Spring Data JPA, validation/security/observability, and deployment (JAR / Docker / GraalVM native). No source code, build system, or tests.

Served as a **Docsify** static site (`docs/index.html` is the entry point).

## Structure

- `docs/phase-{0..7}-*/` — content broken into per-topic pages for Docsify navigation (Phase 7 = Google Cloud & Cloud Run 배포)
- `docs/appendix-{a..d}-*/` — 심화 부록: A=JPA 심화, B=Querydsl, C=AOP/프록시 고급, D=Spring MVC 내부 원리 & SSR. Querydsl은 OpenFeign 포크(`io.github.openfeign.querydsl`, `:jakarta` classifier, Kotlin kapt) 기준.
- `docs/_sidebar.md` — defines the sidebar navigation tree (update when adding/renaming pages)
- `docs/README.md` — Docsify landing page (renders as the home page)
- `docs/index.html` — Docsify config and plugins (theme, search, pagination, syntax highlighting)

Phase directories follow the pattern `phase-N-topic/NN-slug.md` with a `README.md` per phase.

## Content Conventions

- **One running example across the whole guide.** Every phase and appendix builds the same Book API under the package root `com.example.bookapi` (subpackages: `controller`, `service`, `repository`, `domain`, `dto`, `config`, `exception`, `validation`, `client`). The canonical types are `BookService` / `BookController` / `BookRepository`. Reuse these names and package paths when adding examples — do **not** introduce a new sample domain.
- **Cross-phase continuity is actively maintained.** The git history shows repeated "연속성 검증 / 정합화" passes that keep package names, class names, and service-method contracts identical across pages. When editing one page, check that signatures and package paths still match the phases/appendices that reference the same code, so a reader following along never hits a contradiction.
- Appendix code targets the same example but at intermediate/advanced depth (mirrors 김영한 roadmap: JPA 기본편 / Querydsl / 핵심원리 고급편 / MVC 1·2편).

## Local Preview

Docsify requires a local HTTP server. Any of these work from the repo root:

```bash
npx docsify-cli serve docs
# or
python3 -m http.server 3000 --directory docs
```

## Language & Tech Baseline

- All documentation is written in **Korean (한국어)**. Maintain Korean when editing or adding content.
- All code examples use **Kotlin**.
- Reference versions (verified 2026-06-20): **Spring Boot 4.1.0**, Spring Framework 7.0.8+, Kotlin 2.3.21, JDK 21 (17~26 supported), Gradle 8.14+/9.x, Tomcat 11.0.x. Keep version claims consistent with `docs/README.md`.

## Docsify Conventions

- Sidebar is manually maintained in `docs/_sidebar.md` — it is **not** auto-generated
- Syntax highlighting languages loaded: Kotlin, Bash, YAML, Docker, Groovy, JSON, SQL, properties, XML, HTTP
- Plugins enabled: search, pagination, copy-code, tabs
