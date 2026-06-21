# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Documentation-only repository — a Korean-language tutorial for Kotlin developers learning the Spring Boot framework, from core concepts (IoC/DI, auto-configuration) through REST APIs, Spring Data JPA, validation/security/observability, and deployment (JAR / Docker / GraalVM native). No application source code or tests.

Served as a **generated static HTML site**. The Markdown files under `docs/` are the **source of truth**; `tools/build_site.py` converts each `*.md` → a sibling `*.html` (with `docs/README.md` → `docs/index.html`). Previously a Docsify runtime site; now pre-rendered to self-contained HTML (build-time Pygments highlighting, ASCII diagrams → styled "diagram cards", `> [!TIP]/[!WARNING]` → callouts, sidebar from `_sidebar.md`).

## Structure

- `docs/phase-{0..7}-*/` — content per-topic pages (Phase 7 = Google Cloud & Cloud Run 배포)
- `docs/appendix-{a..d}-*/` — 심화 부록: A=JPA 심화, B=Querydsl, C=AOP/프록시 고급, D=Spring MVC 내부 원리 & SSR. Querydsl은 OpenFeign 포크(`io.github.openfeign.querydsl`, `:jakarta` classifier, Kotlin kapt) 기준.
- `docs/_sidebar.md` — nav tree **source** (read by the build script; update when adding/renaming pages). Not served as a page.
- `docs/README.md` → built to `docs/index.html` (home / GitHub Pages entry point).
- `docs/assets/style.css` — **generated** shared stylesheet (theme, code blocks, diagram cards, callouts).
- `tools/build_site.py` — the static-site generator.
- **Generated `*.html` and `assets/style.css` are committed** (GitHub Pages serves them directly).

Phase directories follow the pattern `phase-N-topic/NN-slug.md` with a `README.md` per phase.

## Build (IMPORTANT)

After editing ANY `.md` (or `_sidebar.md`, or `tools/build_site.py`), **regenerate the HTML** so the committed site stays in sync:

```bash
python3 -m venv .venv && . .venv/bin/activate   # first time only
pip install markdown pygments                   # first time only
python tools/build_site.py                       # rebuild all 68 pages + style.css
```

Then commit both the `.md` and the regenerated `.html`/`assets/style.css`. Never hand-edit the generated `.html` — edit the `.md` and rebuild.

## Content Conventions

- **One running example across the whole guide.** Every phase and appendix builds the same Book API under the package root `com.example.bookapi` (subpackages: `controller`, `service`, `repository`, `domain`, `dto`, `config`, `exception`, `validation`, `client`). The canonical types are `BookService` / `BookController` / `BookRepository`. Reuse these names and package paths when adding examples — do **not** introduce a new sample domain.
- **Cross-phase continuity is actively maintained.** The git history shows repeated "연속성 검증 / 정합화" passes that keep package names, class names, and service-method contracts identical across pages. When editing one page, check that signatures and package paths still match the phases/appendices that reference the same code, so a reader following along never hits a contradiction.
- Appendix code targets the same example but at intermediate/advanced depth (mirrors 김영한 roadmap: JPA 기본편 / Querydsl / 핵심원리 고급편 / MVC 1·2편).

## Local Preview

The built site is plain static HTML — open `docs/index.html` directly, or serve it:

```bash
python3 -m http.server 3000 --directory docs   # then open http://localhost:3000/
```

## Language & Tech Baseline

- All documentation is written in **Korean (한국어)**. Maintain Korean when editing or adding content.
- All code examples use **Kotlin**.
- Reference versions (verified 2026-06-20): **Spring Boot 4.1.0**, Spring Framework 7.0.8+, Kotlin 2.3.21, JDK 21 (17~26 supported), Gradle 8.14+/9.x, Tomcat 11.0.x. Keep version claims consistent with `docs/README.md`.

## Authoring Conventions

- Sidebar is manually maintained in `docs/_sidebar.md` — the build reads it to render each page's nav.
- Diagrams: write ASCII box/flow art in a **plain fenced block** (no language). The build auto-detects the shape: a single-box numbered-step diagram or linear `│`/`▼` chain → **stepper flowchart** (`try_step_flow`/`try_linear_flow`); a single box with `│`-separated columns → **HTML table** (`try_ascii_table`, text after the right border becomes a sub-note); a single box with full-width `├──┤` dividers → **layer stack** (`try_layer_stack`); an ASCII directory tree (`├──`/`└──` + file/dir names) → **HTML file tree with icons** (`try_file_tree`); everything else (box-pairs, horizontal/free-form) → styled **diagram card**. Single-box detection requires exactly one `┌` (side-by-side box-pairs stay cards). Use ```` ```kotlin/yaml/bash/... ```` for real code (Pygments-highlighted at build time).
- **Branch flowcharts** (decision `──No──▶`/`──Yes──▶` or fan-out `├─ … →`) are too irregular to auto-parse, so they are hand-authored as **inline HTML** directly in the `.md` using the `flowchart branch-flow` / `flowchart decision-flow` classes (see `.fc-fork`/`.fc-branches`/`.fc-decision`/`.fc-exit`/`.fc-status` in the generated `style.css`). Markdown passes the raw HTML through. When adding such a diagram, write the HTML block (no blank lines inside the `<figure>`).
- Callouts: `> [!TIP]`, `> [!WARNING]`, `> [!NOTE]`, `> [!IMPORTANT]` become styled callout boxes.
- Internal links: write them to the `.md` files (e.g. `[x](../phase-3-data-jpa/01-jpa-concepts.md)`); the build rewrites `.md` → `.html` (and root `README.md` → `index.html`).

## Verifying links

The build does not fail on broken links, so after a rebuild verify every internal `.html` link resolves (404s are easy to introduce when renaming pages or editing `_sidebar.md`):

```bash
cd docs && python3 - <<'PY'
import re, os, glob
broken = total = 0
for f in glob.glob("**/*.html", recursive=True):
    d = os.path.dirname(f); txt = open(f, encoding="utf-8").read()
    for m in re.finditer(r'href="([^"]+)"', txt):
        h = m.group(1)
        if h.startswith(("http://","https://","#","mailto:")) or h.startswith("@{"): continue
        total += 1
        if not os.path.isfile(os.path.normpath(os.path.join(d, h.split("#")[0]))):
            broken += 1; print("BROKEN", f, "->", h)
print(f"links {total}  broken {broken}")
PY
```

(`@{...}` is a Thymeleaf URL expression that appears inside code examples — not a real link.)

## Deployment

GitHub Pages serves the site from the **`main` branch `/docs` folder** (repo `NamJa/Spring-Boot-Learning-Guide`, live at https://namja.github.io/Spring-Boot-Learning-Guide/). Pushing to `main` triggers a rebuild automatically — there is no Actions workflow; Pages serves the committed `docs/*.html` directly. `docs/.nojekyll` disables Jekyll so underscore/`assets` paths are served as-is. Commit the regenerated HTML or the live site will be stale.
