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

def render_code(lang, code):
    label = (lang or "text").lower()
    if is_diagram(lang, code):
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
