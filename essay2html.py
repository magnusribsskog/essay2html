#!/usr/bin/env python3
"""essay2html.py — render a Markdown essay to one standalone HTML page.

    python3 essay2html.py <essay.md> [-o out.html]

Zero dependencies, one file, no network. Handles the Markdown subset essays
actually use: headings, paragraphs, lists, tables, blockquotes, fenced code,
rules, **bold**, *italic*, `code`, links, and $$…$$ display maths rendered as
HTML/CSS — no MathJax, no KaTeX, no fonts to download. The output opens
offline, on anything, forever, and carries light and dark themes with it.

Display equations are hand-typeset via the EQUATIONS table, keyed by their
LaTeX source (whitespace-normalised). An unrecognised equation falls back to
monospace LaTeX and prints a warning — add it to the table, or pass your own
with --equations, rather than letting it ship ugly.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

# --- hand-typeset display equations -----------------------------------------
# Keyed on the LaTeX between $$ … $$, whitespace-normalised. Values are raw
# HTML, styled by the .frac/.paren/.intg/.lim rules in CSS below. These five
# ship as worked examples; --equations FILE adds or overrides entries from a
# JSON object of the same shape.
FRAC = '<span class="frac"><span class="num">{n}</span><span class="den">{d}</span></span>'

EQUATIONS = {
    r"T_{GH} = \frac{\hbar H_\Lambda}{2\pi k_B} \approx 2.2 \times 10^{-30}\ \text{K}":
        '<i>T</i><sub>GH</sub> = ' + FRAC.format(n="ħ<i>H</i><sub>Λ</sub>", d="2π<i>k</i><sub>B</sub>")
        + ' ≈ 2.2 × 10<sup>−30</sup> K',

    r"T_{op} = \left(T_{amb}^4 + \frac{P}{\sigma A}\right)^{1/4}":
        '<i>T</i><sub>op</sub> = <span class="paren">(</span>'
        '<i>T</i><sub>amb</sub><sup>4</sup> + '
        + FRAC.format(n="<i>P</i>", d="σ<i>A</i>")
        + '<span class="paren">)</span><sup>1/4</sup>',

    r"E_{\max} = \int_0^\infty \sigma A T_{amb}^4\,dt = \tfrac{1}{4}\sigma A T_0^4 \tau":
        '<i>E</i><sub>max</sub> = <span class="intg">∫</span><span class="lim">'
        '<span class="hi">∞</span><span class="lo">0</span></span> '
        'σ<i>A T</i><sub>amb</sub><sup>4</sup> d<i>t</i> = '
        + FRAC.format(n="1", d="4")
        + ' σ<i>A T</i><sub>0</sub><sup>4</sup> τ',

    r"N(T, T_R) = \frac{C}{k \ln 2}\left(\frac{T_R}{T} - 1 - \ln\frac{T_R}{T}\right)":
        '<i>N</i>(<i>T</i>, <i>T</i><sub>R</sub>) = '
        + FRAC.format(n="<i>C</i>", d="<i>k</i> ln 2")
        + '<span class="paren">(</span>'
        + FRAC.format(n="<i>T</i><sub>R</sub>", d="<i>T</i>")
        + ' − 1 − ln '
        + FRAC.format(n="<i>T</i><sub>R</sub>", d="<i>T</i>")
        + '<span class="paren">)</span>',

    r"N = \frac{\left(E^3\,\sigma A\,t\right)^{1/4}}{k_B \ln 2}":
        '<i>N</i> = ' + FRAC.format(
            n="(<i>E</i><sup>3</sup> σ<i>A t</i>)<sup>1/4</sup>",
            d="<i>k</i><sub>B</sub> ln 2"),
}

# Lookup is on whitespace-normalised LaTeX, so the table must be too.
EQUATIONS = {re.sub(r"\s+", " ", k).strip(): v for k, v in EQUATIONS.items()}

PALETTE_LIGHT = """--bg:#fbfaf7; --fg:#1c1a17; --muted:#6b6459; --rule:#ddd7cc;
  --accent:#7a4a2b; --panel:#f3f0e9; --link:#8a4f2a;"""
PALETTE_DARK = """--bg:#14161a; --fg:#dfe3e8; --muted:#8e9aa6; --rule:#2b3038;
  --accent:#d9a679; --panel:#1b1f25; --link:#e0b083;"""

CSS = """
:root{ %(light)s }
:root[data-theme="dark"]{ %(dark)s }
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){ %(dark)s }
}
html{ -webkit-text-size-adjust:100%%; }
body{
  background:var(--bg); color:var(--fg);
  font-family:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  font-size:19px; line-height:1.62; margin:0;
  padding:4rem 1.5rem 6rem; -moz-osx-font-smoothing:grayscale;
}
.wrap{ max-width:41rem; margin:0 auto; }
h1{
  font-size:2.35rem; line-height:1.12; letter-spacing:-.015em;
  margin:0 0 .6rem; font-weight:600;
}
.deck{
  font-size:1.12rem; line-height:1.4; color:var(--muted);
  font-style:italic; margin:0 0 1.6rem;
}
.byline{
  font-size:.82rem; letter-spacing:.13em; text-transform:uppercase;
  color:var(--muted); margin:0 0 2.6rem;
  padding-bottom:2.6rem; border-bottom:1px solid var(--rule);
}
.byline b{ color:var(--accent); font-weight:600; }
h2{
  font-size:1.42rem; line-height:1.25; margin:3.2rem 0 1rem;
  font-weight:600; letter-spacing:-.01em;
}
h3{
  font-size:1.06rem; margin:2.2rem 0 .7rem; font-weight:600;
  color:var(--accent); letter-spacing:.005em;
}
h4{ font-size:1rem; margin:1.8rem 0 .6rem; font-weight:600; }
p{ margin:0 0 1.15rem; }
a{ color:var(--link); }
strong{ font-weight:600; }
em{ font-style:italic; }
code{
  font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  font-size:.86em; background:var(--panel); padding:.1em .32em; border-radius:3px;
}
pre{
  background:var(--panel); border:1px solid var(--rule); border-radius:5px;
  padding:.9rem 1.1rem; overflow-x:auto; margin:1.5rem 0; line-height:1.45;
}
pre code{ background:none; padding:0; border-radius:0; font-size:.8rem; }
hr{ border:0; border-top:1px solid var(--rule); margin:3rem 0; }
ul,ol{ margin:0 0 1.15rem; padding-left:1.4rem; }
li{ margin:.34rem 0; }
blockquote{
  margin:1.6rem 0; padding:.9rem 1.2rem; background:var(--panel);
  border-left:3px solid var(--accent); border-radius:0 4px 4px 0;
}
blockquote p:last-child{ margin-bottom:0; }
.abstract{
  background:var(--panel); border:1px solid var(--rule); border-radius:6px;
  padding:1.3rem 1.4rem; margin:0 0 2.4rem; font-size:.94rem; line-height:1.55;
}
.abstract p{ margin:0; }
.tablewrap{ overflow-x:auto; margin:1.6rem 0; }
table{ border-collapse:collapse; width:100%%; font-size:.87rem; line-height:1.4; }
th,td{ padding:.5rem .7rem; text-align:left; border-bottom:1px solid var(--rule); }
th{
  font-size:.74rem; letter-spacing:.09em; text-transform:uppercase;
  color:var(--muted); font-weight:600; border-bottom:1.5px solid var(--rule);
}
tbody tr:last-child td{ border-bottom:none; }
/* display maths */
.eq{
  margin:1.7rem 0; text-align:center; font-size:1.12rem;
  font-family:"Iowan Old Style",Palatino,Georgia,serif;
  overflow-x:auto; padding:.3rem 0;
}
.frac{
  display:inline-block; vertical-align:-0.62em; text-align:center;
  margin:0 .22em; line-height:1.15;
}
.frac .num{ display:block; padding:0 .3em .06em; }
.frac .den{ display:block; padding:.06em .3em 0; border-top:1.1px solid currentColor; }
.paren{ font-size:1.7em; vertical-align:-.22em; line-height:0; }
.intg{ font-size:1.9em; vertical-align:-.30em; line-height:0; margin-left:.15em; }
.lim{
  display:inline-block; font-size:.56em; line-height:1.15;
  vertical-align:-.15em; margin:0 .3em 0 .1em; text-align:left;
}
.lim .hi{ display:block; margin-bottom:.35em; }
.lim .lo{ display:block; }
.eqfallback{ font-family:ui-monospace,monospace; font-size:.85rem; }
.sig{ text-align:right; color:var(--muted); font-style:italic; margin:2.2rem 0; }
footer{
  margin-top:3.5rem; padding-top:1.6rem; border-top:1px solid var(--rule);
  font-size:.8rem; color:var(--muted); line-height:1.5;
}
.theme{
  position:fixed; top:1rem; right:1rem; background:var(--panel);
  color:var(--muted); border:1px solid var(--rule); border-radius:20px;
  padding:.35rem .8rem; font-family:system-ui,sans-serif; font-size:.72rem;
  cursor:pointer; letter-spacing:.06em;
}
@media (max-width:640px){
  body{ font-size:17.5px; padding:2.5rem 1.1rem 4rem; }
  h1{ font-size:1.85rem; }
  h2{ font-size:1.25rem; }
}
@media print{
  body{ background:#fff; color:#000; font-size:11pt; padding:0; }
  .theme{ display:none; }
  h2{ page-break-after:avoid; }
  pre,blockquote,table{ page-break-inside:avoid; }
}
""" % {"light": PALETTE_LIGHT, "dark": PALETTE_DARK}

# Runs in <head>, before first paint, so a stored choice does not flash.
HEAD_JS = """
try{var t=localStorage.getItem('essay-theme');
if(t)document.documentElement.dataset.theme=t;}catch(e){}
"""

JS = """
(function(){
  var b=document.createElement('button');
  b.className='theme'; b.textContent='theme';
  b.onclick=function(){
    var r=document.documentElement;
    var dark=(r.dataset.theme==='dark')||(!r.dataset.theme&&
      matchMedia('(prefers-color-scheme:dark)').matches);
    r.dataset.theme=dark?'light':'dark';
    try{localStorage.setItem('essay-theme',r.dataset.theme);}catch(e){}
  };
  document.body.appendChild(b);
})();
"""

DEFAULT_FOOTER = ("Rendered from <code>{src}</code>. Self-contained: one file, "
                  "no external requests, no tracking.")

# Inline HTML the source is allowed to use directly, for notation markdown
# emphasis cannot express (<i>T</i><sub>amb</sub><sup>4</sup>). GitHub renders
# these too, so the .md stays correct in both places. Everything else that
# looks like a tag stays escaped.
INLINE_TAGS = re.compile(r"&lt;(/?(?:i|b|em|strong|sub|sup|br\s*/?))&gt;")

# Placeholders park a span of text where no regex can reach it. \x00 cannot
# survive esc(), so these can never collide with document content.
PH_CODE = "\x00c%d\x00"
PH_URL = "\x00u%d\x00"
PH_ANY = re.compile(r"\x00([cu])(\d+)\x00")

SAFE_SCHEME = re.compile(r"^\s*(https?:|mailto:|tel:)", re.I)
HAS_SCHEME = re.compile(r"^\s*[a-z][a-z0-9+.\-]*:", re.I)


def safe_href(url: str) -> str:
    """Keep relative and known-good absolute URLs; neutralise the rest.

    Input has already been through esc(), so & is encoded but " and ' are not
    — those are what would break out of the attribute.
    """
    url = url.strip()
    if HAS_SCHEME.match(url) and not SAFE_SCHEME.match(url):
        return "#"  # javascript:, data:, vbscript: and friends
    return url.replace('"', "&quot;").replace("'", "&#39;")


def inline(s: str) -> str:
    """Inline markdown → HTML, on already-escaped text."""
    s = INLINE_TAGS.sub(r"<\1>", s)

    stash: list[str] = []

    def keep_code(m):
        stash.append("<code>" + m.group(1) + "</code>")
        return PH_CODE % (len(stash) - 1)

    def keep_link(m):
        stash.append(safe_href(m.group(2)))
        return '<a href="' + (PH_URL % (len(stash) - 1)) + '">' + m.group(1) + "</a>"

    # Code spans and link targets go behind placeholders first: emphasis must
    # not reach inside `a * b` or inside http://x/*y*.
    s = re.sub(r"`([^`]+)`", keep_code, s)
    # the URL may contain one level of balanced parens: .../Foo_(disambiguation)
    s = re.sub(r"\[([^\]]+)\]\(((?:[^()\s]|\([^()\s]*\))+)\)", keep_link, s)

    s = re.sub(r"\*\*(\S(?:[^*]|\*(?!\*))*?\S|\S)\*\*", r"<strong>\1</strong>", s, flags=re.S)
    # Emphasis markers must hug non-space (so 5 * 4 * 3 stays arithmetic) and
    # may close before `_` (so *k*_B works), but never mid-word.
    s = re.sub(r"(?<![\w*])\*(\S[^*\n]*?\S|\S)\*(?![*A-Za-z0-9])", r"<em>\1</em>", s, flags=re.S)

    return PH_ANY.sub(lambda m: stash[int(m.group(2))], s)


def esc(s: str) -> str:
    return html.escape(s.replace("\x00", ""), quote=False)


def split_cells(row: str) -> list[str]:
    """Split a table row on unescaped pipes that are not inside a code span."""
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|") and not row.endswith("\\|"):
        row = row[:-1]
    cells: list[str] = []
    buf: list[str] = []
    in_code = False
    pending = False
    for ch in row:
        if pending:
            # A backslash only escapes punctuation; C:\new keeps its backslash.
            buf.append(ch if not ch.isalnum() else "\\" + ch)
            pending = False
        elif ch == "\\":
            pending = True
        elif ch == "`":
            in_code = not in_code
            buf.append(ch)
        elif ch == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if pending:
        buf.append("\\")
    cells.append("".join(buf).strip())
    return cells


def alignments(sep: str) -> list[str]:
    out = []
    for c in split_cells(sep):
        left, right = c.startswith(":"), c.endswith(":")
        out.append("center" if left and right else "right" if right
                   else "left" if left else "")
    return out


def render(md: str, equations: dict | None = None) -> tuple[str, str, str]:
    """Markdown → (title_html, deck_html, body_html)."""
    eqs = EQUATIONS if equations is None else equations
    lines = md.split("\n")
    out: list[str] = []
    title = deck = ""
    i, n = 0, len(lines)
    unknown_eq: list[str] = []

    # YAML front matter, if any, is metadata and not prose.
    if lines and lines[0].strip() == "---":
        for j in range(1, n):
            if lines[j].strip() in ("---", "..."):
                i = j + 1
                break

    def flush_para(buf):
        if buf:
            out.append("<p>" + inline(esc(" ".join(buf).strip())) + "</p>")
            buf.clear()

    para: list[str] = []

    while i < n:
        st = lines[i].strip()

        # fenced code
        m = re.match(r"^(`{3,}|~{3,})\s*([\w+.\-]*)", st)
        if m:
            flush_para(para)
            fence, lang = m.group(1)[0] * 3, m.group(2)
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith(fence):
                buf.append(lines[i])
                i += 1
            i += 1  # closing fence, or off the end
            cls = f' class="language-{lang}"' if lang else ""
            out.append(f"<pre><code{cls}>" + esc("\n".join(buf)) + "</code></pre>")
            continue

        # display maths
        if st.startswith("$$"):
            flush_para(para)
            body = st
            while body.count("$$") < 2 and i + 1 < n:
                i += 1
                body += " " + lines[i].strip()
            tex = re.sub(r"\s+", " ", body.strip().strip("$").strip())
            if body.count("$$") < 2:
                unknown_eq.append(f"unterminated $$ block: {tex[:60]}")
            if tex in eqs:
                out.append('<div class="eq">' + eqs[tex] + "</div>")
            else:
                unknown_eq.append(tex)
                out.append('<div class="eq eqfallback">' + esc(tex) + "</div>")
            i += 1
            continue

        # headings
        m = re.match(r"^(#{1,4})\s+(.*)$", st)
        if m:
            flush_para(para)
            lvl, txt = len(m.group(1)), inline(esc(m.group(2)))
            if lvl == 1 and not title:
                title = txt
            elif lvl == 3 and not deck and not out:
                deck = txt
            else:
                out.append(f"<h{lvl}>{txt}</h{lvl}>")
            i += 1
            continue

        # horizontal rule
        if re.fullmatch(r"-{3,}|\*{3,}|_{3,}", st):
            flush_para(para)
            if out:
                out.append("<hr>")
            i += 1
            continue

        # table
        if st.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1].strip()):
            flush_para(para)
            head = split_cells(st)
            align = alignments(lines[i + 1].strip())
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(split_cells(lines[i]))
                i += 1

            def sty(c):
                a = align[c] if c < len(align) else ""
                return f' style="text-align:{a}"' if a else ""

            t = ['<div class="tablewrap"><table><thead><tr>']
            t += [f"<th{sty(c)}>{inline(esc(x))}</th>" for c, x in enumerate(head)]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join(f"<td{sty(c)}>{inline(esc(x))}</td>"
                                          for c, x in enumerate(r)) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue

        # blockquote
        if st.startswith(">"):
            flush_para(para)
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip().lstrip(">").strip())
                i += 1
            out.append("<blockquote><p>" + inline(esc(" ".join(buf))) + "</p></blockquote>")
            continue

        # lists
        item = re.compile(r"^([-*+]|\d+\.)\s+(.*)$")
        m = item.match(st)
        if m:
            flush_para(para)
            ordered = m.group(1)[0].isdigit()
            items = []
            while i < n:
                mm = item.match(lines[i].strip())
                if not mm:
                    # an indented continuation line belongs to the item above
                    if lines[i].startswith(("  ", "\t")) and lines[i].strip() and items:
                        items[-1] += " " + lines[i].strip()
                        i += 1
                        continue
                    break
                if mm.group(1)[0].isdigit() != ordered:
                    break  # a bulleted list starting where a numbered one ended
                items.append(mm.group(2))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(esc(x))}</li>" for x in items) + f"</{tag}>")
            continue

        if not st:
            flush_para(para)
            i += 1
            continue

        para.append(st)
        i += 1

    flush_para(para)
    body = "\n".join(out)

    # a first paragraph starting **Abstract.** becomes the abstract panel
    body = re.sub(r"<p>(<strong>Abstract\.</strong>.*?)</p>",
                  r'<div class="abstract"><p>\1</p></div>', body, count=1, flags=re.S)
    # a closing italic — Name line becomes a signature
    body = re.sub(r"<p><em>— ([^<]*)</em></p>", r'<p class="sig">— \1</p>', body, count=1)

    for e in unknown_eq:
        print(f"warning: no hand-typeset form for equation: {e}", file=sys.stderr)
    return title, deck, body


def build(md: str, src_name: str = "input.md", equations: dict | None = None,
          footer: str | None = None) -> str:
    """Markdown → a complete, standalone HTML document."""
    # The byline (**Author** · date · rev) is chrome, not prose. Only the
    # head of the document is searched, so a bold sentence in the body that
    # happens to contain a middot is not mistaken for it.
    byline_html = ""
    head_end = len("\n".join(md.split("\n")[:15]))
    m = re.compile(r"^\*\*(.+?)\*\*[ \t]*·[ \t]*(.+)$", re.M).search(md, 0, head_end)
    if m:
        byline_html = f"<b>{esc(m.group(1))}</b> · {esc(m.group(2))}"
        md = md[: m.start()] + md[m.end():]

    title_html, deck, body = render(md, equations)
    # title_html is already escaped; strip our own generated tags for <title>
    title_text = re.sub(r"<[^>]+>", "", title_html)
    foot = DEFAULT_FOOTER if footer is None else footer

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>{title_text}</title>
<style>{CSS}</style>
<script>{HEAD_JS}</script>
</head><body>
<div class="wrap">
{f'<h1>{title_html}</h1>' if title_html else ''}
{f'<p class="deck">{deck}</p>' if deck else ''}
{f'<p class="byline">{byline_html}</p>' if byline_html else ''}
{body}
{f'<footer>{foot.format(src=esc(src_name))}</footer>' if foot else ''}
</div>
<script>{JS}</script>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser(
        description="Render a Markdown essay to one standalone HTML page.")
    ap.add_argument("src", type=Path, help="Markdown source file")
    ap.add_argument("-o", "--out", type=Path,
                    help="output path (default: alongside the source; - for stdout)")
    ap.add_argument("--equations", type=Path,
                    help="JSON object of LaTeX → HTML, added to the built-in table")
    ap.add_argument("--footer", help="footer HTML; {src} is the source filename")
    ap.add_argument("--no-footer", action="store_true", help="omit the footer")
    a = ap.parse_args()

    eqs = dict(EQUATIONS)
    if a.equations:
        extra = json.loads(a.equations.read_text(encoding="utf-8"))
        eqs.update({re.sub(r"\s+", " ", k).strip(): v for k, v in extra.items()})

    footer = "" if a.no_footer else a.footer
    page = build(a.src.read_text(encoding="utf-8"), a.src.name, eqs, footer)

    if str(a.out) == "-":
        sys.stdout.write(page)
        return
    out = a.out or a.src.with_suffix(".html")
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out} ({len(page):,} bytes)")


if __name__ == "__main__":
    main()
