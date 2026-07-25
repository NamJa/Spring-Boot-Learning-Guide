#!/usr/bin/env python3
"""빌드 결과 검증 — 링크·자산·도식·인터랙션 기능 점검

  python tools/verify_site.py

검사 항목
  1. 내부 링크/자산 경로가 실제 파일로 해석되는가
  2. 페이지 내 앵커(#id)가 존재하는가
  3. 남은 ASCII 도식(data-todo)이나 .md 링크가 없는가
  4. 소스에서 쓴 모든 CSS 클래스가 스타일시트에 정의돼 있는가
  5. app.js 가 기대하는 DOM 훅이 실제로 존재하는가 (코드 복사·탭·도식 포커스·목차)
  6. 페이지 셸 필수 요소(title/사이드바/스크립트/현재 항목 표시)가 있는가
"""
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
OUT = os.path.join(ROOT, "docs")

FAIL = []
WARN = []
STAT = Counter()


def fail(msg):
    FAIL.append(msg)


def warn(msg):
    WARN.append(msg)


def html_files(base):
    res = []
    for root, _, files in os.walk(base):
        for fn in sorted(files):
            if fn.endswith(".html"):
                res.append(os.path.relpath(os.path.join(root, fn), base))
    return sorted(res)


def read(base, rel):
    with open(os.path.join(base, rel), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- 1·2·3·6
def check_pages():
    pages = html_files(OUT)
    STAT["pages"] = len(pages)
    ids = {}
    for rel in pages:
        text = read(OUT, rel)
        ids[rel] = set(re.findall(r'\sid="([^"]+)"', text))
    for rel in pages:
        text = read(OUT, rel)
        d = os.path.dirname(rel)
        # 셸 필수 요소
        for needle, what in ((" · Spring Boot 학습 가이드</title>", "<title>"),
                             ('class="sidebar"', "사이드바"),
                             ("assets/app.js", "app.js 로드"),
                             ('class="content"', "본문 컨테이너")):
            if needle not in text:
                fail("%s: %s 누락" % (rel, what))
        if text.count('class="active"') != 1:
            warn("%s: 사이드바 현재 항목 표시가 %d개" % (rel, text.count('class="active"')))
        if 'data-todo="rewrite"' in text:
            fail("%s: 변환되지 않은 ASCII 도식이 남아 있음" % rel)
        # 링크·자산
        for attr, href in re.findall(r'(href|src)="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:")) or href.startswith("@{"):
                continue
            if href.startswith("#"):
                STAT["anchors"] += 1
                if href[1:] and href[1:] not in ids[rel]:
                    fail("%s: 페이지 내 앵커 대상 없음 → %s" % (rel, href))
                continue
            if ".md" in href:
                fail("%s: .md 링크가 남아 있음 → %s" % (rel, href))
                continue
            STAT["links"] += 1
            base, _, frag = href.partition("#")
            target = os.path.normpath(os.path.join(OUT, d, base))
            if not os.path.isfile(target):
                fail("%s: 대상 파일 없음 → %s" % (rel, href))
                continue
            if frag:
                trel = os.path.relpath(target, OUT)
                if trel.endswith(".html") and frag not in ids.get(trel, set()):
                    warn("%s: 다른 페이지 앵커 없음 → %s" % (rel, href))


# ------------------------------------------------------------------- 4
def check_css():
    css_path = os.path.join(OUT, "assets", "style.css")
    if not os.path.isfile(css_path):
        fail("assets/style.css 없음")
        return
    css = open(css_path, encoding="utf-8").read()
    defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", css))
    used = Counter()
    for rel in html_files(SRC):
        for attr in re.findall(r'class="([^"]+)"', read(SRC, rel)):
            for cls in attr.split():
                used[cls] += 1
    # 빌드가 생성하는 클래스도 정의 대상
    generated = {"code-block", "code-lang", "hl", "toc", "toc-title", "lvl2", "lvl3",
                 "topbar", "brand", "hamburger", "layout", "sidebar", "content", "scrim",
                 "nav", "nav-section", "active", "code-copy", "is-done", "tab-bar",
                 "tab-panel", "is-focus", "has-focus", "is-active",
                 # 소스 전용 마커: 빌드가 .code-block 으로 치환한다
                 "code"}
    missing = sorted(c for c in used if c not in defined and c not in generated)
    STAT["css_classes_used"] = len(used)
    for c in missing:
        fail("CSS 규칙 없는 클래스: .%s (사용 %d회)" % (c, used[c]))


# ------------------------------------------------------------------- 5
def check_js():
    js_path = os.path.join(OUT, "assets", "app.js")
    if not os.path.isfile(js_path):
        fail("assets/app.js 없음")
        return
    js = open(js_path, encoding="utf-8").read()
    for needle, what in (("code-copy", "코드 복사"), (".tabs", "탭"),
                         ("data-focusable", "도식 포커스"), (".toc a", "목차 스크롤스파이"),
                         ("navtoggle", "모바일 드로어")):
        if needle not in js:
            fail("app.js: %s 기능 코드 없음" % what)
    # DOM 훅이 실제 산출물에 존재하는지
    hooks = Counter()
    for rel in html_files(OUT):
        text = read(OUT, rel)
        hooks["code-block"] += text.count('class="code-block"')
        hooks["focusable"] += text.count("data-focusable")
        hooks["toc"] += text.count('class="toc"')
        hooks["tabs"] += text.count('class="tabs"')
    STAT.update({"code_blocks": hooks["code-block"], "focusable_diagrams": hooks["focusable"],
                 "toc_pages": hooks["toc"], "tab_groups": hooks["tabs"]})
    if not hooks["code-block"]:
        fail("코드블록이 하나도 생성되지 않음 (복사 버튼이 붙을 대상 없음)")
    if not hooks["toc"]:
        fail("목차가 생성된 페이지가 없음")
    if not hooks["focusable"]:
        warn("data-focusable 도식이 없음 — 포커스 기능이 쓰이지 않는다")


# ------------------------------------------------------------------- 도식 통계
def diagram_stats():
    kinds = Counter()
    for rel in html_files(SRC):
        text = read(SRC, rel)
        for cls in re.findall(r'<figure class="([^"]+)"', text):
            kinds[cls.split()[0]] += 1
        for cls in ("dg-pipe", "dg-steps", "dg-vs", "dg-layers", "dg-fork", "dg-seq",
                    "dg-grid", "dg-timeline", "dg-states", "dg-box", "dg-http", "dg-tree", "dg-cross"):
            kinds["  └ " + cls] += text.count('class="%s' % cls) + text.count('class="%s"' % cls) * 0
    return kinds


if __name__ == "__main__":
    check_pages()
    check_css()
    check_js()

    print("── 통계 ──")
    for k in ("pages", "links", "anchors", "css_classes_used", "code_blocks",
              "toc_pages", "focusable_diagrams", "tab_groups"):
        print("  %-18s %s" % (k, STAT.get(k, 0)))
    print("── 도식 컴포넌트 사용 ──")
    for k, v in sorted(diagram_stats().items()):
        if v:
            print("  %-22s %d" % (k, v))
    if WARN:
        print("── 경고 %d건 ──" % len(WARN))
        for w in WARN[:20]:
            print("  ·", w)
        if len(WARN) > 20:
            print("  … 외 %d건" % (len(WARN) - 20))
    if FAIL:
        print("── 오류 %d건 ──" % len(FAIL))
        for e in FAIL[:40]:
            print("  ✕", e)
        if len(FAIL) > 40:
            print("  … 외 %d건" % (len(FAIL) - 40))
        sys.exit(1)
    print("\n✅ 검증 통과 (오류 0건)")
