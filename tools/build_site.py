#!/usr/bin/env python3
"""Static-site builder: docs/*.md -> docs/*.html
- Build-time syntax highlighting (Pygments) -> self-contained, no CDN/JS.
- ASCII box/flow diagrams (fenced blocks w/ box-drawing) -> styled "diagram cards".
- GitHub-style > [!TIP]/[!WARNING]/[!NOTE] -> styled callouts.
- Sidebar nav from _sidebar.md, re-relativized per page; current page highlighted.
Usage:
  build_site.py                 # build every .md under docs/
  build_site.py --page REL.md   # build a single page, CSS inlined (for preview)
"""
import os, re, sys, html, posixpath
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.lexers.special import TextLexer
from pygments.formatters import HtmlFormatter

# tools/build_site.py  ->  repo root is parent of tools/  ->  docs/ is repo/docs
_HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.environ.get("DOCS_DIR", os.path.join(os.path.dirname(_HERE), "docs"))

BOX = set("┌┐└┘│─├┤┬┴┼╔╗╚╝║═╠╣╦╩╬▼▲◀▶→←↑↓↔►◄┃━┏┓┗┛┣┫┳┻╋")
KNOWN = {"kotlin","kt","kts","java","yaml","yml","bash","sh","shell","console","zsh",
         "groovy","json","sql","http","properties","ini","html","xml","dockerfile",
         "docker","gradle","toml","js","javascript","css","text","plaintext","txt","diff"}
LEXER_ALIAS = {"kt":"kotlin","kts":"kotlin","yml":"yaml","sh":"bash","shell":"bash",
               "console":"console","zsh":"bash","docker":"docker","gradle":"groovy",
               "txt":"text","plaintext":"text","js":"javascript"}
PLAIN = {"text","plaintext","txt",""}

FENCE_RE = re.compile(r"^([ \t]{0,3})(```+|~~~+)[ \t]*([\w+-]*)[ \t]*$")
fmt = HtmlFormatter(style="dracula", nowrap=False, cssclass="hl")

def is_diagram(lang, code):
    if lang.lower() in (KNOWN - PLAIN):
        return False
    return any(ch in BOX for ch in code)

def _strip_borders(line):
    s = line
    if s[:1] in "│┃":
        s = s[1:]
    s = re.sub(r"[│┃]\s*$", "", s)
    return s

def try_step_flow(code):
    """Convert a single-outer-box vertical step diagram into an HTML stepper
    flowchart. Returns HTML or None (None => caller falls back to diagram card)."""
    raw = [l.rstrip() for l in code.split("\n")]
    lines = [l for l in raw if l.strip() != ""]
    if len(lines) < 4:
        return None
    if not re.match(r"^[┌╔]", lines[0]) or not re.search(r"[┐╗]$", lines[0]):
        return None
    if not re.match(r"^[└╚]", lines[-1]):
        return None
    inner = lines[1:-1]
    # a reopened box (┌ / └ inside) means this is a box-CHAIN, not a single box
    if any(re.match(r"^\s*[┌└]", l) for l in inner):
        return None
    title, body_start = None, 0
    for i, l in enumerate(inner):
        if re.match(r"^\s*[├╠][─═]+[┤╣]\s*$", l):
            title = " ".join(_strip_borders(x).strip() for x in inner[:i]).strip()
            body_start = i + 1
            break
    body = inner[body_start:]

    def inner_text(l):
        return _strip_borders(l).strip()

    def is_conn(l):
        c = inner_text(l)
        return c == "" or re.fullmatch(r"[│┃▼|]+", c) is not None
    # require at least one *drawn* connector (│ or ▼), not just blank lines
    if not any(re.fullmatch(r"[│┃▼|]+", inner_text(l)) for l in body):
        return None

    nodes, buf = [], []
    def flush():
        tl = [b for b in buf if b.strip() != ""]
        buf.clear()
        if not tl:
            return
        first = tl[0].strip()
        mm = re.match(r"^=+\s*(.*?)\s*=+$", first)
        if mm and len(tl) == 1:
            nodes.append({"type": "milestone", "text": mm.group(1)}); return
        m = re.match(r"^(\d+)\.\s*(.*)$", first)
        num = m.group(1) if m else None
        head = m.group(2) if m else first
        note = None
        if "★" in head:
            head, note = [p.strip() for p in head.split("★", 1)]
        desc = " ".join(t.strip() for t in tl[1:]).strip()
        if note is None and "★" in desc:
            desc, note = [p.strip() for p in desc.split("★", 1)]
        nodes.append({"type": "step", "num": num, "head": head, "desc": desc, "note": note})

    for l in body:
        if is_conn(l):
            flush()
        else:
            buf.append(_strip_borders(l))
    flush()

    if len([n for n in nodes if n["type"] != "milestone"]) < 2:
        return None
    return _render_flow(title, nodes)

def _render_flow(title, nodes):
    out = ['<figure class="flowchart">']
    if title:
        out.append('<div class="fc-title">%s</div>' % html.escape(title))
    out.append('<ol class="fc-steps">')
    for n in nodes:
        if n["type"] == "milestone":
            out.append('<li class="fc-milestone"><span>%s</span></li>' % html.escape(n["text"]))
            continue
        cls = "fc-step" + (" fc-hot" if n.get("note") else "")
        badge = ('<span class="fc-num">%s</span>' % html.escape(n["num"])) if n.get("num") \
                else '<span class="fc-num fc-dot"></span>'
        b = '<div class="fc-head">%s</div>' % html.escape(n["head"])
        if n.get("desc"):
            b += '<div class="fc-desc">%s</div>' % html.escape(n["desc"])
        if n.get("note"):
            b += '<div class="fc-note">%s</div>' % html.escape(n["note"])
        out.append('<li class="%s">%s<div class="fc-body">%s</div></li>' % (cls, badge, b))
    out.append("</ol></figure>")
    return "\n".join(out)

_BORDERONLY = re.compile(r"^[┌┐└┘├┤┬┴┼─═╔╗╚╝║│\s]+$")
def try_linear_flow(code):
    """Vertical chains WITHOUT an outer box: plain-text step chains and simple
    box-chains connected by │/▼. Rejects branches/trees/horizontal arrows."""
    raw = [l.rstrip() for l in code.split("\n")]
    lines = [l for l in raw if l.strip() != ""]
    if len(lines) < 3:
        return None
    joined = "\n".join(lines)
    if "▼" not in joined:
        return None
    # reject trees/branches/section dividers and horizontal arrows
    if any(ch in joined for ch in "├┤┬┴┼►▶◀◄"):
        return None

    def is_conn(l):
        return re.fullmatch(r"[│┃▼|]+", l.strip()) is not None

    def node_text(grp):
        parts = []
        for l in grp:
            if _BORDERONLY.match(l) and l.strip():   # pure box border line -> skip
                continue
            parts.append(_strip_borders(l).strip())
        return " ".join(p for p in parts if p).strip()

    groups, buf = [], []
    for l in lines:
        if is_conn(l):
            if buf:
                groups.append(buf); buf = []
        else:
            buf.append(l)
    if buf:
        groups.append(buf)

    nodes = []
    for g in groups:
        t = node_text(g)
        if not t:
            continue
        mm = re.match(r"^=+\s*(.*?)\s*=+$", t)
        if mm:
            nodes.append({"type": "milestone", "text": mm.group(1)}); continue
        m = re.match(r"^(\d+)\.\s*(.*)$", t)
        num = m.group(1) if m else None
        head = m.group(2) if m else t
        note = None
        if "★" in head:
            head, note = [p.strip() for p in head.split("★", 1)]
        nodes.append({"type": "step", "num": num, "head": head, "desc": "", "note": note})
    if len([n for n in nodes if n["type"] != "milestone"]) < 2:
        return None
    return _render_flow(None, nodes)

_BORDER_LINE = re.compile(r"^[\s┌┐└┘├┤┬┴┼─═╔╗╚╝║╠╣╬╦╩]+$")
def _is_border(line):
    return bool(_BORDER_LINE.match(line)) and ("─" in line or "═" in line)

def _cells_and_note(line):
    """Split a box row into (cells, trailing-note). The first │ is the left
    border, the last │ is the right border; text after the right border is an
    out-of-box annotation (e.g. '← 설명'), NOT a real column."""
    parts = re.split(r"[│┃]", line)
    if len(parts) < 2:
        return [], None
    cells = [p.strip() for p in parts[1:-1]]
    note = parts[-1].strip()
    return cells, (note or None)

def _single_box(lines):
    top, bot = lines[0].strip(), lines[-1].strip()
    if not (re.match(r"^[┌╔]", top) and re.search(r"[┐╗]$", top) and re.match(r"^[└╚]", bot)):
        return None
    joined = "\n".join(lines)
    # a real single box has exactly one top-left corner; >1 => side-by-side boxes
    if joined.count("┌") + joined.count("╔") != 1:
        return None
    inner = lines[1:-1]
    if any(re.match(r"^\s*[┌└]", l) for l in inner):  # reopened => box chain
        return None
    return inner

def try_ascii_table(code):
    """Single box whose rows have │-separated columns -> real HTML table."""
    lines = [l for l in code.split("\n") if l.strip() != ""]
    if len(lines) < 3:
        return None
    inner = _single_box(lines)
    if inner is None:
        return None
    rows = []
    for l in inner:
        if _is_border(l):
            continue
        cells, _ = _cells_and_note(l)
        if any(c for c in cells):
            rows.append(cells)
    if len(rows) < 2 or max(len(r) for r in rows) < 2:
        return None
    caption, idx = None, 0
    if len(rows[0]) == 1:
        caption, idx = rows[0][0], 1
    if idx >= len(rows):
        return None
    header = rows[idx]
    body = rows[idx + 1:]
    ncol = len(header)
    out = ['<table class="gen-table">']
    if caption:
        out.append("<caption>%s</caption>" % html.escape(caption))
    out.append("<thead><tr>" + "".join("<th>%s</th>" % html.escape(c) for c in header) + "</tr></thead>")
    out.append("<tbody>")
    for r in body:
        cells = r + [""] * (ncol - len(r)) if len(r) < ncol else r[:ncol]
        out.append("<tr>" + "".join("<td>%s</td>" % html.escape(c) for c in cells) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)

def try_layer_stack(code):
    """Single box with ├──┤ dividers and single-column sections -> stacked bands."""
    lines = [l for l in code.split("\n") if l.strip() != ""]
    if len(lines) < 4 or any(c in code for c in "┬┼┴"):
        return None
    inner = _single_box(lines)
    if inner is None:
        return None
    if not any(re.match(r"^\s*[├╠][─═]+[┤╣]\s*$", l) for l in inner):
        return None
    sections, cur = [], []
    for l in inner:
        if re.match(r"^\s*[├╠][─═]+[┤╣]\s*$", l):
            if cur:
                sections.append(cur); cur = []
        elif _is_border(l):
            continue
        else:
            cells, note = _cells_and_note(l)
            if len(cells) > 1:
                return None  # multi-column -> it's a table, not a layer stack
            if cells and cells[0]:
                cur.append(cells[0])
            if note:
                cur.append(note)
    if cur:
        sections.append(cur)
    if len(sections) < 2:
        return None
    n = len(sections)
    out = ['<figure class="layer-stack">']
    for i, sec in enumerate(sections):
        out.append('<div class="layer" style="--i:%d;--n:%d">' % (i, n))
        out.append('<div class="layer-head">%s</div>' % html.escape(sec[0]))
        if len(sec) > 1:
            out.append('<div class="layer-sub">%s</div>' % html.escape(" ".join(sec[1:])))
        out.append("</div>")
    out.append("</figure>")
    return "\n".join(out)

KNOWN_FILES = {"gradlew", "gradlew.bat", "mvnw", "mvnw.cmd", "dockerfile", ".dockerignore",
               ".gitignore", ".gitattributes", "makefile", "procfile", "license", ".env",
               ".nojekyll", ".gcloudignore"}
def _tree_icon(name, is_dir):
    if is_dir:
        return "📁"
    n = name.lower()
    if n in ("gradlew", "mvnw"): return "📜"
    if n == "dockerfile": return "🐳"
    if n.endswith((".gradle.kts", ".gradle", ".kts")): return "🐘"
    if n.endswith((".yml", ".yaml", ".properties", ".conf", ".xml")): return "⚙️"
    if n.endswith(".jar"): return "📦"
    if n.endswith(".md"): return "📝"
    if n.endswith((".kt", ".java")): return "📄"
    if n.endswith(".sql"): return "🗃️"
    if "." not in n.strip("/"): return "📁"
    return "📄"

def _tree_split(text):
    cm = re.search(r"\s*(#|←)\s*", text)
    sp = re.search(r"\s{2,}", text)
    cut = None
    if cm and sp: cut = min(cm.start(), sp.start())
    elif cm: cut = cm.start()
    elif sp: cut = sp.start()
    name = (text[:cut] if cut is not None else text).strip()
    comment = re.sub(r"^[#←\s]+", "", text[cut:]).strip() if cut is not None else ""
    return name, comment

def try_file_tree(code):
    """ASCII directory tree (├──/└── + file/dir names) -> nested HTML tree."""
    raw = [l for l in code.split("\n") if l.strip() != ""]
    if len(raw) < 3 or any(c in code for c in "▶►◀◄"):
        return None
    tree_lines = [l for l in raw if re.search(r"[├└]──", l)]
    if len(tree_lines) < 2:
        return None
    root = raw[0].strip() if not re.search(r"[├└]──", raw[0]) else None
    nodes, names = [], []
    for l in tree_lines:
        m = re.search(r"[├└]──", l)
        depth = m.start() // 4
        name, comment = _tree_split(l[m.start():].lstrip("├└─ ").rstrip())
        bare = name.strip("/").lower()
        is_dir = name.endswith("/") or ("." not in name.strip("/") and bare not in KNOWN_FILES)
        nodes.append((depth, name.rstrip("/"), comment, is_dir))
        names.append(name)
    # must look like real file/dir names (no spaces / <> / parens)
    filelike = sum(1 for n in names if re.fullmatch(r"[\w.\-/@+]+", n))
    if filelike < max(2, int(len(names) * 0.7)):
        return None
    rootnode = {"name": root or "", "dir": True, "comment": "", "children": []}
    last_at = {}
    for (d, name, comment, is_dir) in nodes:
        node = {"name": name, "dir": is_dir, "comment": comment, "children": []}
        parent = last_at.get(d - 1, rootnode)
        parent["children"].append(node)
        last_at[d] = node
        for k in [k for k in last_at if k > d]:
            del last_at[k]
    def render_ul(children):
        if not children:
            return ""
        out = ["<ul>"]
        for c in children:
            cls = "ft-dir" if c["dir"] else "ft-file"
            cmt = '<span class="ft-cmt">%s</span>' % html.escape(c["comment"]) if c["comment"] else ""
            out.append('<li class="%s"><span class="ft-row"><span class="ft-icon">%s</span>'
                       '<span class="ft-name">%s</span>%s</span>%s</li>'
                       % (cls, _tree_icon(c["name"], c["dir"]), html.escape(c["name"]), cmt,
                          render_ul(c["children"])))
        out.append("</ul>")
        return "".join(out)
    head = '<div class="ft-root">📦 %s</div>' % html.escape(rootnode["name"]) if rootnode["name"] else ""
    return '<figure class="filetree">%s%s</figure>' % (head, render_ul(rootnode["children"]))

def render_code(lang, code):
    label = (lang or "text").lower()
    if is_diagram(lang, code):
        block = (try_step_flow(code) or try_linear_flow(code)
                 or try_ascii_table(code) or try_layer_stack(code)
                 or try_file_tree(code))
        if block:
            return block
        return ('<figure class="diagram"><pre>%s</pre></figure>'
                % html.escape(code))
    if label in PLAIN or lang == "":
        body = '<pre class="hl"><code>%s</code></pre>' % html.escape(code)
        disp = "text"
    else:
        try:
            lexer = get_lexer_by_name(LEXER_ALIAS.get(label, label))
        except Exception:
            lexer = TextLexer()
        body = highlight(code, lexer, fmt)
        disp = label
    return ('<div class="code-block" data-lang="%s">'
            '<span class="code-lang">%s</span>%s</div>' % (html.escape(disp), html.escape(disp), body))

def extract_fences(text):
    lines = text.split("\n")
    out, blocks, i = [], [], 0
    while i < len(lines):
        m = FENCE_RE.match(lines[i])
        if m:
            fence = m.group(2)[0]  # ` or ~
            lang = m.group(3)
            i += 1
            buf = []
            while i < len(lines) and not re.match(r"^[ \t]{0,3}" + re.escape(fence) + r"{3,}[ \t]*$", lines[i]):
                buf.append(lines[i]); i += 1
            i += 1  # skip closing fence
            token = "@@CB-%d-CB@@" % len(blocks)
            blocks.append(render_code(lang, "\n".join(buf)))
            out.append(""); out.append(token); out.append("")
        else:
            out.append(lines[i]); i += 1
    return "\n".join(out), blocks

CALLOUT_META = {
    "TIP": ("callout-tip", "💡 TIP"), "NOTE": ("callout-note", "📝 NOTE"),
    "WARNING": ("callout-warning", "⚠️ WARNING"), "IMPORTANT": ("callout-important", "❗ IMPORTANT"),
    "CAUTION": ("callout-warning", "🔥 CAUTION"),
}
def style_callouts(htmltext):
    def repl(m):
        kind = m.group(1).upper()
        cls, label = CALLOUT_META.get(kind, ("callout-note", kind))
        return ('<blockquote class="callout %s"><p class="callout-label">%s</p><p>'
                % (cls, label))
    # markdown renders: <blockquote>\n<p>[!TIP]\n쩌rest...</p>...
    htmltext = re.sub(r'<blockquote>\s*<p>\[!(\w+)\]\s*(?:<br\s*/?>)?\s*', repl, htmltext)
    return htmltext

def _fix_one(href, page_dir):
    if href.startswith(("http://","https://","#","mailto:")) or ".md" not in href:
        return href
    base, _, frag = href.partition("#")
    resolved = posixpath.normpath(posixpath.join(page_dir, base))
    if resolved == "README.md":
        target = "index.html"
    elif resolved.endswith(".md"):
        target = resolved[:-3] + ".html"
    else:
        return href
    rel = posixpath.relpath(target, page_dir if page_dir else ".")
    return rel + ("#" + frag if frag else "")

def md_convert(text):
    md = markdown.Markdown(extensions=["tables", "sane_lists", "attr_list"])
    return md.convert(text)

def first_h1(text):
    for line in text.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Spring Boot 학습 가이드"

# ---------- sidebar ----------
def parse_sidebar():
    path = os.path.join(DOCS, "_sidebar.md")
    items = []  # (kind, text, target)  kind: section|link
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            m = re.match(r"-\s+\*\*(.+?)\*\*\s*$", s)
            if m:
                items.append(("section", m.group(1), None)); continue
            m = re.match(r"-\s+\[(.+?)\]\((.+?)\)\s*$", s)
            if m:
                items.append(("link", m.group(1), m.group(2))); continue
    return items

def _root_link(target, page_dir):
    """sidebar targets are relative to the docs ROOT (not to page_dir)."""
    base = target.split("#")[0]
    resolved = posixpath.normpath(base)
    if resolved == "README.md":
        tgt = "index.html"
    elif resolved.endswith(".md"):
        tgt = resolved[:-3] + ".html"
    else:
        tgt = resolved
    return posixpath.relpath(tgt, page_dir if page_dir else ".")

def sidebar_html(items, page_dir, current_target):
    out = ['<nav class="nav">']
    for kind, text, target in items:
        if kind == "section":
            out.append('<div class="nav-section">%s</div>' % html.escape(text))
        else:
            resolved = posixpath.normpath(target.split("#")[0])
            is_cur = (resolved == current_target)
            href = _root_link(target, page_dir)
            cls = ' class="active"' if is_cur else ""
            out.append('<a href="%s"%s>%s</a>' % (href, cls, html.escape(text)))
    out.append("</nav>")
    return "\n".join(out)

# ---------- page template ----------
def page_html(title, content, sidebar, rel_root, inline_css):
    if inline_css:
        head_css = "<style>\n%s\n%s\n</style>" % (BASE_CSS, fmt.get_style_defs(".hl"))
    else:
        head_css = '<link rel="stylesheet" href="%s/assets/style.css">' % rel_root
    home = posixpath.normpath(posixpath.join(rel_root, "index.html"))
    return TEMPLATE.format(title=html.escape(title), css=head_css, sidebar=sidebar,
                           content=content, home=home)

TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Spring Boot 학습 가이드</title>
{css}
</head>
<body>
<input id="navtoggle" type="checkbox" hidden>
<header class="topbar">
  <label for="navtoggle" class="hamburger" aria-label="메뉴">☰</label>
  <a class="brand" href="{home}">🍃 Spring Boot 학습 가이드 <span>(Kotlin)</span></a>
</header>
<div class="layout">
  <aside class="sidebar">{sidebar}</aside>
  <main class="content">
{content}
  </main>
</div>
<label for="navtoggle" class="scrim"></label>
</body>
</html>
"""

BASE_CSS = r"""
:root{
  --green:#6DB33F; --green-d:#5a9433; --ink:#1f2329; --muted:#5b6573;
  --line:#e6e8eb; --bg:#ffffff; --bg-soft:#f6f8fa; --sidebar-w:288px;
  --code-bg:#282a36; --radius:12px; --maxw:880px;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans KR",sans-serif;
  --mono:"JetBrains Mono","Fira Code","SF Mono",ui-monospace,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;font-family:var(--font);color:var(--ink);background:var(--bg);
  line-height:1.75;font-size:16px;-webkit-font-smoothing:antialiased}
a{color:var(--green-d);text-decoration:none}
a:hover{text-decoration:underline}
/* top bar */
.topbar{position:sticky;top:0;z-index:30;display:flex;align-items:center;gap:12px;
  height:56px;padding:0 20px;background:rgba(255,255,255,.85);backdrop-filter:saturate(180%) blur(8px);
  border-bottom:1px solid var(--line)}
.brand{font-weight:700;color:var(--ink);font-size:16px}
.brand span{color:var(--muted);font-weight:500}
.hamburger{display:none;font-size:22px;cursor:pointer;color:var(--ink);user-select:none}
/* layout */
.layout{display:flex;align-items:flex-start;max-width:1240px;margin:0 auto}
.sidebar{position:sticky;top:56px;align-self:flex-start;width:var(--sidebar-w);flex:0 0 var(--sidebar-w);
  height:calc(100vh - 56px);overflow-y:auto;padding:22px 14px 60px;border-right:1px solid var(--line)}
.content{flex:1 1 auto;min-width:0;max-width:var(--maxw);margin:0 auto;padding:36px 32px 100px}
/* nav */
.nav-section{margin:18px 0 6px;padding:0 10px;font-size:12.5px;font-weight:800;letter-spacing:.04em;
  color:var(--muted);text-transform:none}
.nav a{display:block;padding:6px 10px;margin:1px 0;border-radius:8px;color:#3a4250;font-size:14px;
  border-left:3px solid transparent}
.nav a:hover{background:var(--bg-soft);text-decoration:none}
.nav a.active{background:rgba(109,179,63,.12);color:var(--green-d);font-weight:700;border-left-color:var(--green)}
/* typography */
.content h1{font-size:30px;line-height:1.3;margin:.2em 0 .6em;padding-bottom:.3em;border-bottom:2px solid var(--line)}
.content h2{font-size:23px;margin:1.7em 0 .6em;padding-bottom:.25em;border-bottom:1px solid var(--line)}
.content h3{font-size:18.5px;margin:1.4em 0 .5em}
.content h4{font-size:16px;margin:1.2em 0 .4em;color:var(--muted)}
.content p{margin:.7em 0}
.content ul,.content ol{margin:.6em 0;padding-left:1.5em}
.content li{margin:.25em 0}
.content strong{font-weight:700}
.content hr{border:none;border-top:1px solid var(--line);margin:2em 0}
/* inline code */
.content :not(pre)>code{font-family:var(--mono);font-size:.86em;background:var(--bg-soft);
  border:1px solid var(--line);border-radius:6px;padding:.12em .4em;color:#b5295c;white-space:nowrap}
/* code blocks */
.code-block{position:relative;margin:1.1em 0;border-radius:var(--radius);background:var(--code-bg);
  box-shadow:0 1px 2px rgba(0,0,0,.06),0 8px 24px -12px rgba(0,0,0,.35);overflow:hidden}
.code-lang{position:absolute;top:0;right:0;z-index:2;font-family:var(--mono);font-size:11px;
  letter-spacing:.06em;text-transform:uppercase;color:#a8b0c0;background:rgba(255,255,255,.06);
  padding:5px 12px;border-bottom-left-radius:10px}
.code-block pre,.code-block .hl{margin:0;padding:18px 18px 16px;overflow-x:auto}
.code-block pre,.code-block code{font-family:var(--mono);font-size:13.5px;line-height:1.62;tab-size:4}
.code-block code{background:none;border:none;padding:0;color:#f8f8f2;white-space:pre}
/* diagram card */
.diagram{margin:1.3em 0;padding:20px 22px;background:
  linear-gradient(#fbfdfb,#fbfdfb) padding-box,
  repeating-linear-gradient(0deg,#eef2ee,#eef2ee 1px,transparent 1px,transparent 22px) padding-box;
  background-color:#fbfdfb;border:1px solid #dde6dd;border-radius:var(--radius);
  box-shadow:0 1px 2px rgba(0,0,0,.04),0 10px 30px -18px rgba(40,90,30,.5);overflow-x:auto}
.diagram pre{margin:0;font-family:var(--mono);font-size:13px;line-height:1.32;color:#2c3a2a;
  white-space:pre;font-variant-ligatures:none;text-rendering:optimizeLegibility}
/* flowchart (vertical stepper, generated from single-box step diagrams) */
.flowchart{margin:1.5em 0;max-width:680px}
.fc-title{display:block;text-align:center;font-weight:800;color:#fff;font-size:15px;
  background:linear-gradient(135deg,var(--green),var(--green-d));padding:9px 18px;
  border-radius:999px;margin:0 auto 20px;box-shadow:0 6px 16px -6px rgba(90,148,51,.6);width:fit-content}
.fc-steps{list-style:none;margin:0;padding:0;position:relative}
.fc-step,.fc-milestone{position:relative;padding-bottom:26px}
.fc-step{display:grid;grid-template-columns:34px 1fr;gap:16px;align-items:start}
/* vertical spine + arrowhead between nodes */
.fc-steps>li:not(:last-child)::before{content:"";position:absolute;left:16px;top:30px;bottom:-2px;
  width:2px;background:linear-gradient(var(--green),rgba(109,179,63,.35))}
.fc-steps>li:not(:last-child)::after{content:"";position:absolute;left:11px;bottom:8px;
  width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;
  border-top:8px solid var(--green)}
.fc-num{grid-row:1;width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,var(--green),var(--green-d));
  color:#fff;font-weight:800;font-size:15px;display:grid;place-items:center;z-index:1;
  box-shadow:0 3px 8px -2px rgba(90,148,51,.55)}
.fc-num.fc-dot{background:#cdd6cd;width:16px;height:16px;margin:9px}
.fc-body{background:#fff;border:1px solid #dde6dd;border-radius:11px;padding:11px 15px;
  box-shadow:0 1px 2px rgba(0,0,0,.04),0 10px 28px -20px rgba(40,90,30,.55)}
.fc-head{font-weight:700;font-size:15px;color:var(--ink)}
.fc-desc{margin-top:4px;color:var(--muted);font-size:14px;line-height:1.6}
.fc-note{margin-top:9px;font-size:13px;color:#9a6700;background:#fff8e6;border-left:3px solid #e3a008;
  border-radius:6px;padding:5px 10px}
.fc-note::before{content:"★ ";color:#e3a008}
.fc-hot .fc-body{border-color:#f0d48a;box-shadow:0 0 0 3px rgba(227,160,8,.12),0 10px 28px -20px rgba(150,100,0,.5)}
.fc-milestone{text-align:center}
.fc-milestone>span{display:inline-block;background:linear-gradient(135deg,#eafbf0,#d6f5e1);
  color:#1a7f37;font-weight:800;font-size:13.5px;padding:7px 18px;border-radius:999px;
  border:1px solid #b7e6c6;box-shadow:0 4px 12px -6px rgba(26,127,55,.4)}
.fc-milestone>span::before{content:"✓ "}
/* branch flowchart — fan-out */
.branch-flow .fc-steps{margin-bottom:0}
.fc-fork .fc-body{border-color:var(--green);box-shadow:0 0 0 3px rgba(109,179,63,.13),0 10px 28px -20px rgba(40,90,30,.55)}
.fc-branches{list-style:none;margin:0 0 0 16px;padding:16px 0 0 26px;
  border-left:2px solid rgba(109,179,63,.5)}
.fc-branch{position:relative;display:flex;flex-wrap:wrap;align-items:center;gap:8px;
  background:#fff;border:1px solid #dde6dd;border-radius:10px;padding:10px 14px;margin:0 0 12px;
  font-size:14px;box-shadow:0 1px 2px rgba(0,0,0,.04),0 10px 26px -20px rgba(40,90,30,.5)}
.fc-branch:last-child{margin-bottom:0}
.fc-branch::before{content:"";position:absolute;left:-27px;top:50%;width:25px;height:2px;
  background:rgba(109,179,63,.5)}
.fc-branch>code,.fc-branch .fc-seg code{background:var(--bg-soft);border:1px solid var(--line);
  border-radius:6px;padding:.1em .45em;font-family:var(--mono);font-size:.85em;color:#b5295c;white-space:nowrap}
.fc-arrow{color:var(--muted);font-weight:800}
.fc-seg{color:var(--ink)}
.fc-status{margin-left:auto;font-weight:800;font-size:12.5px;padding:3px 11px;border-radius:999px;color:#fff;white-space:nowrap}
.s-200,.s-201,.s-204{background:#2da44e}.s-400{background:#3b82f6}.s-404{background:#e3a008}
.s-409{background:#bf8700}.s-500{background:#cf222e}.fc-cost{background:#cf222e;margin-left:auto}
.fc-sum{margin:14px 0 0 16px;padding:11px 16px;background:#fff5f5;border:1px solid #f3c2c2;
  border-left:4px solid #cf222e;border-radius:9px;font-size:14px}
.fc-badge-warn{background:#cf222e;color:#fff;font-weight:800;font-size:11.5px;padding:2px 10px;border-radius:999px;margin-left:6px}
/* branch flowchart — decision */
.fc-q{background:linear-gradient(135deg,#f0b429,#de911d)!important;color:#fff}
.fc-decision .fc-body{border-color:#f0d48a;background:#fffdf6}
.fc-final .fc-body{border-color:var(--green);background:#f3fbf0}
.fc-exit{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-top:8px;font-size:13.5px;color:#3a4250}
.fc-tag{font-weight:800;font-size:11.5px;padding:2px 10px;border-radius:999px;color:#fff;white-space:nowrap}
.t-yes{background:#2da44e}.t-no{background:#cf222e}
/* layer stack (single box + ├──┤ dividers) */
.layer-stack{margin:1.5em 0;max-width:560px;border-radius:14px;overflow:hidden;
  border:1px solid #cfe0c8;box-shadow:0 10px 30px -18px rgba(40,90,30,.55)}
.layer{padding:15px 18px;text-align:center;border-bottom:1px solid rgba(255,255,255,.7);
  background:hsl(96 38% calc(95% - var(--i) * (42% / var(--n))))}
.layer:last-child{border-bottom:none}
.layer-head{font-weight:800;color:#16320f;font-size:15px}
.layer:nth-child(n+4) .layer-head{color:#16320f}
.layer-sub{margin-top:3px;font-size:13px;color:#3c5733;opacity:.95}
/* generated table (ascii grid -> HTML table) */
.content table.gen-table{margin:1.3em 0}
.content table.gen-table caption{caption-side:top;font-weight:800;color:var(--ink);
  text-align:center;padding:9px 12px;background:linear-gradient(135deg,var(--green),var(--green-d));
  color:#fff;border-radius:10px 10px 0 0;font-size:14.5px}
/* file tree (ASCII directory tree -> nested HTML) */
.filetree{margin:1.4em 0;font-family:var(--mono);font-size:13.5px;background:#fbfdfb;
  border:1px solid #dde6dd;border-radius:12px;padding:15px 18px;overflow-x:auto;
  box-shadow:0 1px 2px rgba(0,0,0,.04),0 10px 28px -20px rgba(40,90,30,.55)}
.ft-root{font-weight:800;color:#16320f;margin-bottom:8px;font-size:14px}
.filetree ul{list-style:none;margin:0;padding-left:18px}
.filetree>ul{padding-left:2px}
.filetree ul ul{border-left:1px dashed #c2d6bb;margin-left:9px;padding-left:14px}
.filetree li{position:relative;padding:2.5px 0;line-height:1.6}
.ft-row{display:inline-flex;align-items:baseline;gap:5px}
.ft-icon{width:1.5em;display:inline-block;text-align:center}
.ft-name{color:#2c3a2a}
.ft-dir>.ft-row .ft-name{font-weight:700;color:#16320f}
.ft-cmt{color:#8a9783;margin-left:10px;font-family:var(--font);font-size:.9em}
.ft-cmt::before{content:"# ";opacity:.45}
/* tables */
.content table{border-collapse:collapse;width:100%;margin:1.2em 0;font-size:14.5px;
  display:block;overflow-x:auto;border:1px solid var(--line);border-radius:10px}
.content thead th{background:var(--bg-soft);font-weight:700;text-align:left}
.content th,.content td{border-bottom:1px solid var(--line);padding:9px 13px;vertical-align:top}
.content tbody tr:nth-child(even){background:#fafbfc}
.content tbody tr:hover{background:rgba(109,179,63,.06)}
.content table code{white-space:normal}
/* blockquote + callouts */
.content blockquote{margin:1.1em 0;padding:.6em 1.1em;border-left:4px solid var(--green);
  background:var(--bg-soft);border-radius:0 10px 10px 0;color:#3a4250}
.content blockquote p{margin:.35em 0}
.callout{border-left-width:4px}
.callout .callout-label{font-weight:800;margin:0 0 .2em;font-size:13.5px;letter-spacing:.02em}
.callout-tip{border-left-color:#2da44e;background:#eafbf0}
.callout-tip .callout-label{color:#1a7f37}
.callout-warning{border-left-color:#e3a008;background:#fff8e6}
.callout-warning .callout-label{color:#9a6700}
.callout-note{border-left-color:#3b82f6;background:#eef4ff}
.callout-note .callout-label{color:#1d4ed8}
.callout-important{border-left-color:#8957e5;background:#f3eefe}
.callout-important .callout-label{color:#6639ba}
/* scrim for mobile drawer */
.scrim{display:none}
@media(max-width:920px){
  .hamburger{display:block}
  .sidebar{position:fixed;left:0;top:56px;z-index:25;background:#fff;transform:translateX(-105%);
    transition:transform .22s ease;box-shadow:0 10px 40px rgba(0,0,0,.18)}
  #navtoggle:checked ~ .layout .sidebar{transform:none}
  #navtoggle:checked ~ .scrim{display:block;position:fixed;inset:56px 0 0;background:rgba(0,0,0,.35);z-index:20}
  .content{padding:24px 18px 80px}
}
"""

def build_one(rel_md, inline_css=False):
    abspath = os.path.join(DOCS, rel_md)
    with open(abspath, encoding="utf-8") as f:
        text = f.read()
    title = first_h1(text)
    page_dir = posixpath.dirname(rel_md)
    # output path: root README.md -> index.html ; else basename.html
    if rel_md == "README.md":
        out_rel = "index.html"
    else:
        out_rel = rel_md[:-3] + ".html"
    cur_target = posixpath.normpath(rel_md)
    rel_root = posixpath.relpath(".", page_dir) if page_dir else "."

    body, blocks = extract_fences(text)
    htmlbody = md_convert(body)
    htmlbody = style_callouts(htmlbody)
    for i, blk in enumerate(blocks):
        tok = "@@CB-%d-CB@@" % i
        htmlbody = htmlbody.replace("<p>%s</p>" % tok, blk).replace(tok, blk)
    htmlbody = re.sub(r'href="([^"]+)"', lambda m: 'href="%s"' % _fix_one(m.group(1), page_dir), htmlbody)

    items = parse_sidebar()
    sb = sidebar_html(items, page_dir, cur_target)
    page = page_html(title, htmlbody, sb, rel_root, inline_css)
    out_abs = os.path.join(DOCS, out_rel)
    with open(out_abs, "w", encoding="utf-8") as f:
        f.write(page)
    return out_rel

def write_css():
    os.makedirs(os.path.join(DOCS, "assets"), exist_ok=True)
    with open(os.path.join(DOCS, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(BASE_CSS + "\n" + fmt.get_style_defs(".hl") + "\n")

def all_md():
    res = []
    for root, _, files in os.walk(DOCS):
        for fn in files:
            if fn.endswith(".md"):
                rel = posixpath.relpath(os.path.join(root, fn), DOCS)
                if rel in ("_sidebar.md", "_coverpage.md", "_navbar.md"):
                    continue
                res.append(rel)
    return sorted(res)

if __name__ == "__main__":
    if "--page" in sys.argv:
        rel = sys.argv[sys.argv.index("--page")+1]
        inline = "--inline" in sys.argv
        if not inline:
            write_css()
        out = build_one(rel, inline_css=inline)
        print("built", out, "(inline)" if inline else "")
    else:
        write_css()
        n = 0
        for rel in all_md():
            build_one(rel, inline_css=False); n += 1
        print("built %d pages + assets/style.css" % n)
