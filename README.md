# essay2html

Render a Markdown essay to **one standalone HTML file**. No dependencies, no
build step, no network — at render time or at read time.

```sh
python3 essay2html.py essay.md          # → essay.html
python3 essay2html.py essay.md -o -     # → stdout
```

That's it. One Python file, standard library only, Python 3.9+. The output is a
single self-contained page: styles inlined, no fonts to fetch, no scripts to
download, no analytics, no CDN. Open it in 2035 on a laptop with no internet and
it looks the same as today.

## What you get

A page designed for reading long prose, not for looking like a webpage:

- A measure of ~41rem, serif, generous leading — the shape of a book page.
- Light and dark themes, following the system by default, with a toggle that
  remembers your choice. No flash on load.
- A print stylesheet that drops the chrome and avoids breaking tables and code
  blocks across pages.
- Structural flourishes for essays: a `### subtitle` right after the title
  becomes a deck, a `**Author** · date` line becomes a byline, a paragraph
  starting `**Abstract.**` becomes a set-off panel, and a closing `*— Name*`
  becomes a signature.

## Markdown supported

Headings (`#`–`####`), paragraphs, `**bold**`, `*italic*`, `` `code` ``,
[links](#), bulleted and numbered lists with indented continuations,
blockquotes, fenced code blocks with a language class, pipe tables with
alignment, horizontal rules, and YAML front matter (skipped).

A small allowlist of inline HTML passes through — `<i> <b> <em> <strong> <sub>
<sup> <br>` — because scientific notation like `<i>T</i><sub>amb</sub><sup>4</sup>`
cannot be written in Markdown, and GitHub renders those tags too, so the source
stays correct in both places. Everything else that looks like a tag is escaped.

Not supported, deliberately: nested lists, reference links, footnotes, inline
HTML beyond the allowlist, images. This renders essays. If you need a full
CommonMark implementation, use one.

## Maths

Display maths between `$$ … $$` is **hand-typeset**, not parsed. Each equation is
looked up in the `EQUATIONS` table by its LaTeX source (whitespace-normalised)
and rendered as HTML and CSS — a `.frac` is a two-line stacked span with a
border for the rule, not a font glyph and not a layout engine.

This is a real trade. MathJax and KaTeX will typeset anything; they also cost a
multi-megabyte payload, a network request or a vendored bundle, and a layout
shift after first paint. An essay usually has five equations, and typing five
equations by hand costs less than all of that. An unknown equation falls back to
monospace LaTeX and prints a warning to stderr, so it never ships ugly and
silent.

Add your own without touching the source:

```sh
python3 essay2html.py essay.md --equations my-equations.json
```

where the file is a JSON object mapping LaTeX to HTML:

```json
{ "E = mc^2": "<i>E</i> = <i>mc</i><sup>2</sup>" }
```

If your essay has more maths than prose, this is the wrong tool.

## Options

| flag | meaning |
| --- | --- |
| `-o`, `--out` | output path; `-` for stdout (default: source with `.html`) |
| `--equations` | JSON file of LaTeX → HTML, added to the built-in table |
| `--footer` | footer HTML; `{src}` interpolates the source filename |
| `--no-footer` | omit the footer |

## Tests

```sh
python3 test_essay2html.py
```

Standard library `unittest`, no runner needed. Everything under the
`Regressions` class is a bug that shipped once — including emphasis leaking
into code spans, `5 * 4 * 3` becoming italics, an unterminated `$$` walking off
the end of the file, and a link URL escaping its `href` attribute.

## As a library

```python
from essay2html import build
html = build(markdown_text, src_name="essay.md")
```

## License

MIT.
