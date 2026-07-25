#!/usr/bin/env python3
"""정적 사이트 생성기 — src/**/*.html (콘텐츠) → docs/**/*.html (배포본)

소스는 마크다운이 아니라 **콘텐츠 HTML 조각**이다. 도식·레이아웃을 HTML/CSS로
자유롭게 조립할 수 있고, 빌드는 다음 세 가지만 담당한다.

  1. 레이아웃 래핑   : <head>, 상단바, 사이드바(src/_nav.html), 우측 목차
  2. 코드 하이라이팅 : <pre class="code" data-lang="kotlin"><code>…</code></pre>
                       → Pygments 로 색칠한 .code-block 마크업
  3. 자산 복사       : tools/assets/{base,diagrams}.css → docs/assets/style.css
                       tools/assets/app.js            → docs/assets/app.js

사용법:
  python tools/build_site.py                # 전체 빌드
  python tools/build_site.py --page phase-3-data-jpa/01-jpa-concepts.html
  python tools/build_site.py --check        # 빌드 없이 소스 정합성만 검사
"""
import html
import os
import posixpath
import re
import sys

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexers.special import TextLexer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "docs")
ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

SITE_TITLE = "Spring Boot 학습 가이드"
fmt = HtmlFormatter(style="dracula", cssclass="hl", nowrap=False)

# 하이라이팅 없이 그대로 보여줄 언어
PLAIN = {"text", "txt", "", "none", "plain", "console", "log"}
LEXER_ALIAS = {
    "kt": "kotlin", "kts": "kotlin", "sh": "bash", "shell": "bash", "zsh": "bash",
    "yml": "yaml", "dockerfile": "docker", "gitignore": "text", "dockerignore": "text",
    "properties": "properties", "http": "http", "sql": "sql", "json": "json",
    "groovy": "groovy", "toml": "toml", "xml": "xml", "html": "html", "css": "css",
    "js": "javascript",
}

# ---------------------------------------------------------------- 코드 블록


def _lexer_for(lang):
    try:
        return get_lexer_by_name(LEXER_ALIAS.get(lang, lang))
    except Exception:
        return TextLexer()


CODE_RE = re.compile(
    r'<pre class="code"(?P<attrs>[^>]*)>\s*<code>(?P<body>.*?)</code>\s*</pre>',
    re.S,
)


def render_code_blocks(content):
    """소스의 <pre class="code" data-lang="…"> 를 하이라이팅된 마크업으로 치환."""
    def one(m):
        attrs = m.group("attrs") or ""
        lang_m = re.search(r'data-lang="([^"]*)"', attrs)
        title_m = re.search(r'data-title="([^"]*)"', attrs)
        lang = (lang_m.group(1) if lang_m else "text").lower()
        code = html.unescape(m.group("body"))
        code = code.rstrip("\n")
        if lang in PLAIN:
            body = '<pre class="hl"><code>%s</code></pre>' % html.escape(code)
            disp = "text"
        else:
            body = highlight(code, _lexer_for(lang), fmt)
            disp = lang
        label = title_m.group(1) if title_m else disp
        return ('<div class="code-block" data-lang="%s">'
                '<span class="code-lang">%s</span>%s</div>'
                % (html.escape(disp), html.escape(label), body))
    return CODE_RE.sub(one, content)


# ------------------------------------------------------------------- 목차

H_RE = re.compile(r'<h([23])(?P<attrs>[^>]*)>(?P<text>.*?)</h\1>', re.S)


def _slug(text, used):
    base = re.sub(r"<[^>]+>", "", text)
    base = html.unescape(base).strip().lower()
    base = re.sub(r"[^0-9a-z가-힣\s._-]", "", base)
    base = re.sub(r"[\s._]+", "-", base).strip("-") or "section"
    slug, n = base, 2
    while slug in used:
        slug = "%s-%d" % (base, n)
        n += 1
    used.add(slug)
    return slug


def add_heading_ids(content):
    """h2/h3 에 id 를 부여하고 (content, toc항목) 반환."""
    used, items = set(), []

    def one(m):
        lvl, attrs, text = m.group(1), m.group("attrs") or "", m.group("text")
        have = re.search(r'id="([^"]+)"', attrs)
        sid = have.group(1) if have else _slug(text, used)
        if not have:
            attrs = attrs + ' id="%s"' % sid
            used.add(sid)
        items.append((int(lvl), sid, re.sub(r"<[^>]+>", "", text).strip()))
        return "<h%s%s>%s</h%s>" % (lvl, attrs, text, lvl)

    return H_RE.sub(one, content), items


def toc_html(items):
    if len([i for i in items if i[0] == 2]) < 2:
        return ""  # 섹션이 하나뿐이면 목차를 만들지 않는다
    out = ['<aside class="toc" aria-label="페이지 목차">', '<div class="toc-title">이 페이지</div>']
    for lvl, sid, text in items:
        cls = "lvl3" if lvl == 3 else "lvl2"
        out.append('<a class="%s" href="#%s">%s</a>' % (cls, sid, html.escape(text)))
    out.append("</aside>")
    return "\n".join(out)


# -------------------------------------------------------------------- 내비

NAV_LINK_RE = re.compile(r'<a href="([^"]+)"')


def load_nav():
    path = os.path.join(SRC, "_nav.html")
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def nav_for(nav_src, page_rel):
    """루트 기준 nav 링크를 현재 페이지 기준 상대경로로 바꾸고 active 를 표시."""
    page_dir = posixpath.dirname(page_rel)

    def one(m):
        target = m.group(1)
        base, _, frag = target.partition("#")
        rel = posixpath.relpath(posixpath.normpath(base), page_dir if page_dir else ".")
        active = ' class="active"' if posixpath.normpath(base) == page_rel else ""
        return '<a href="%s%s"%s' % (rel, "#" + frag if frag else "", active)

    return NAV_LINK_RE.sub(one, nav_src)


# ---------------------------------------------------------------- 페이지 셸

TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {site}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="{root}/assets/style.css">
</head>
<body>
<input id="navtoggle" type="checkbox" hidden>
<header class="topbar">
  <label for="navtoggle" class="hamburger" aria-label="메뉴">☰</label>
  <a class="brand" href="{home}">🍃 {site} <span>(Kotlin)</span></a>
</header>
<div class="layout">
  <aside class="sidebar">{nav}</aside>
  <main class="content">
{content}
  </main>
{toc}
</div>
<label for="navtoggle" class="scrim"></label>
<script src="{root}/assets/app.js" defer></script>
</body>
</html>
"""


def page_title(content):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", content, re.S)
    if not m:
        return SITE_TITLE
    return re.sub(r"<[^>]+>", "", m.group(1)).strip()


def page_desc(content):
    m = re.search(r"<p>(.*?)</p>", content, re.S)
    if not m:
        return "Kotlin 개발자를 위한 Spring Boot 학습 가이드"
    text = re.sub(r"<[^>]+>", "", m.group(1))
    text = html.unescape(text).replace("\n", " ").strip()
    return html.escape(text[:150])


# ------------------------------------------------------------------- 빌드

def all_pages():
    res = []
    for root, _, files in os.walk(SRC):
        for fn in sorted(files):
            if not fn.endswith(".html") or fn.startswith("_"):
                continue
            res.append(posixpath.relpath(os.path.join(root, fn), SRC))
    return sorted(res)


def build_one(rel, nav_src):
    with open(os.path.join(SRC, rel), encoding="utf-8") as f:
        content = f.read()

    title = page_title(content)
    desc = page_desc(content)
    content, headings = add_heading_ids(content)
    content = render_code_blocks(content)

    page_dir = posixpath.dirname(rel)
    root = posixpath.relpath(".", page_dir) if page_dir else "."
    home = posixpath.normpath(posixpath.join(root, "index.html"))

    page = TEMPLATE.format(
        title=html.escape(title), site=SITE_TITLE, desc=desc, root=root, home=home,
        nav=nav_for(nav_src, rel), content=content, toc=toc_html(headings),
    )
    dest = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(page)
    return rel


def write_assets():
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    css = []
    for name in ("base.css", "diagrams.css"):
        with open(os.path.join(ASSETS, name), encoding="utf-8") as f:
            css.append("/* ===== %s ===== */\n%s" % (name, f.read().strip()))
    css.append("/* ===== pygments (dracula) ===== */\n" + fmt.get_style_defs(".hl"))
    with open(os.path.join(OUT, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(css) + "\n")
    with open(os.path.join(ASSETS, "app.js"), encoding="utf-8") as f:
        js = f.read()
    with open(os.path.join(OUT, "assets", "app.js"), "w", encoding="utf-8") as f:
        f.write(js)


def check_sources():
    """빌드 전 소스 정합성 검사: 남은 .md 링크, 미완성 도식, 깨진 내부 링크."""
    problems = []
    pages = set(all_pages())
    for rel in sorted(pages):
        text = open(os.path.join(SRC, rel), encoding="utf-8").read()
        page_dir = posixpath.dirname(rel)
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "#", "mailto:")) or href.startswith("@{"):
                continue
            if ".md" in href:
                problems.append("%s: .md 링크가 남아 있음 → %s" % (rel, href))
                continue
            target = posixpath.normpath(posixpath.join(page_dir, href.split("#")[0]))
            if target not in pages:
                problems.append("%s: 대상 없음 → %s" % (rel, href))
        if 'data-todo="rewrite"' in text:
            n = text.count('data-todo="rewrite"')
            problems.append("%s: HTML 도식으로 옮기지 않은 ASCII 블록 %d개" % (rel, n))
        if "<h1" not in text:
            problems.append("%s: <h1> 이 없음" % rel)
    return problems


if __name__ == "__main__":
    if "--check" in sys.argv:
        errs = check_sources()
        for e in errs:
            print("  •", e)
        print("소스 검사: %d개 문제" % len(errs))
        sys.exit(1 if errs else 0)

    nav_src = load_nav()
    if "--page" in sys.argv:
        rel = sys.argv[sys.argv.index("--page") + 1]
        write_assets()
        print("built", build_one(rel, nav_src))
    else:
        write_assets()
        n = 0
        for rel in all_pages():
            build_one(rel, nav_src)
            n += 1
        print("built %d pages + assets/style.css + assets/app.js" % n)
