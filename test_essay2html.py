#!/usr/bin/env python3
"""Tests for essay2html. Zero dependencies: python3 test_essay2html.py

Every test under "regressions" corresponds to a bug that shipped once.
"""
import unittest

from essay2html import build, esc, inline, render, split_cells


def md(s):
    """Inline markdown → HTML, the way render() calls it."""
    return inline(esc(s))


def body(s):
    return render(s)[2]


class Inline(unittest.TestCase):
    def test_bold(self):
        self.assertEqual(md("a **bold** b"), "a <strong>bold</strong> b")

    def test_italic(self):
        self.assertEqual(md("a *soft* b"), "a <em>soft</em> b")

    def test_code(self):
        self.assertEqual(md("a `x=1` b"), "a <code>x=1</code> b")

    def test_link(self):
        self.assertEqual(md("[t](https://x.com)"), '<a href="https://x.com">t</a>')

    def test_emphasis_may_close_before_underscore(self):
        # physics notation: *k*_B
        self.assertEqual(md("the *k*_B constant"), "the <em>k</em>_B constant")

    def test_allowed_inline_html_survives(self):
        self.assertEqual(md("<i>T</i><sub>amb</sub>"), "<i>T</i><sub>amb</sub>")

    def test_other_html_stays_escaped(self):
        self.assertEqual(md("<script>x</script>"),
                         "&lt;script&gt;x&lt;/script&gt;")


class Regressions(unittest.TestCase):
    def test_emphasis_does_not_reach_into_code_spans(self):
        self.assertEqual(md("use `foo * bar * baz` here"),
                         "use <code>foo * bar * baz</code> here")

    def test_bold_does_not_reach_into_code_spans(self):
        self.assertEqual(md("use `a ** b` here"), "use <code>a ** b</code> here")

    def test_arithmetic_is_not_emphasis(self):
        self.assertEqual(md("compute 5 * 4 * 3 now"), "compute 5 * 4 * 3 now")

    def test_unclosed_display_math_does_not_crash(self):
        # used to raise IndexError walking off the end of the line list
        out = body("para\n\n$$ x = y\n")
        self.assertIn("eqfallback", out)

    def test_title_is_not_double_escaped(self):
        page = build("# Tea & Sympathy\n\ntext\n")
        self.assertIn("<title>Tea &amp; Sympathy</title>", page)
        self.assertNotIn("&amp;amp;", page)

    def test_escaped_pipe_stays_in_its_cell(self):
        rows = body("| a | b |\n|---|---|\n| x \\| y | z |\n")
        self.assertIn("<td>x | y</td>", rows)
        self.assertIn("<td>z</td>", rows)

    def test_pipe_inside_code_span_stays_in_its_cell(self):
        rows = body("| a | b |\n|---|---|\n| `x | y` | z |\n")
        self.assertIn("<code>x | y</code>", rows)

    def test_fenced_code_block(self):
        out = body("```python\nif a < b:\n    x = 1\n```\n")
        self.assertIn('<pre><code class="language-python">', out)
        self.assertIn("if a &lt; b:", out)
        self.assertIn("    x = 1", out)

    def test_markdown_inside_fence_is_literal(self):
        out = body("```\n**not bold** and *not em*\n```\n")
        self.assertIn("**not bold**", out)
        self.assertNotIn("<strong>", out)

    def test_unclosed_fence_does_not_hang(self):
        out = body("```\nx = 1\n")
        self.assertIn("x = 1", out)

    def test_javascript_url_is_neutralised(self):
        self.assertEqual(md("[click](javascript:alert(1))"),
                         '<a href="#">click</a>')

    def test_quote_cannot_escape_the_href_attribute(self):
        out = md('[x](https://a.com/"onmouseover="alert(1))')
        self.assertNotIn('onmouseover="alert', out)
        self.assertIn("&quot;", out)

    def test_balanced_parens_in_url(self):
        self.assertEqual(md("[F](https://en.wikipedia.org/wiki/Foo_(bar))"),
                         '<a href="https://en.wikipedia.org/wiki/Foo_(bar)">F</a>')

    def test_asterisk_in_url_is_not_emphasis(self):
        self.assertEqual(md("[t](https://x.com/*y*/z)"),
                         '<a href="https://x.com/*y*/z">t</a>')

    def test_byline_only_matches_the_head(self):
        # a bold sentence deep in the body must not be eaten as the byline
        src = "# T\n\n" + "filler\n\n" * 20 + "**Note.** a · b\n"
        page = build(src)
        self.assertNotIn('class="byline"', page)
        self.assertIn("<strong>Note.</strong>", page)

    def test_byline_at_the_head_is_lifted(self):
        page = build("# T\n\n**Florence** · 2026-08-07 · Rev. 4\n\nbody\n")
        self.assertIn('<p class="byline"><b>Florence</b> · 2026-08-07 · Rev. 4</p>', page)

    def test_ordered_and_bulleted_lists_do_not_merge(self):
        out = body("1. one\n2. two\n\n- alpha\n- beta\n")
        self.assertIn("<ol><li>one</li><li>two</li></ol>", out)
        self.assertIn("<ul><li>alpha</li><li>beta</li></ul>", out)

    def test_front_matter_is_not_prose(self):
        out = body("---\ntitle: x\ntags: [a]\n---\n\nreal text\n")
        self.assertNotIn("tags:", out)
        self.assertIn("<p>real text</p>", out)

    def test_null_bytes_cannot_forge_placeholders(self):
        # \x00c0\x00 is the internal placeholder syntax
        self.assertNotIn("\x00", md("literal \x00c0\x00 marker `real`"))


class Blocks(unittest.TestCase):
    def test_headings(self):
        self.assertIn("<h2>Section</h2>", body("# T\n\n## Section\n"))

    def test_deck(self):
        title, deck, _ = render("# Title\n\n### A subtitle\n\nbody\n")
        self.assertEqual(title, "Title")
        self.assertEqual(deck, "A subtitle")

    def test_blockquote(self):
        self.assertIn("<blockquote><p>quoted</p></blockquote>", body("> quoted\n"))

    def test_table_alignment(self):
        out = body("| a | b |\n|:--|--:|\n| 1 | 2 |\n")
        self.assertIn('<th style="text-align:left">a</th>', out)
        self.assertIn('<td style="text-align:right">2</td>', out)

    def test_abstract_panel(self):
        out = body("**Abstract.** The claim.\n")
        self.assertIn('<div class="abstract">', out)

    def test_known_equation_is_typeset(self):
        out = body(r"$$N = \frac{\left(E^3\,\sigma A\,t\right)^{1/4}}{k_B \ln 2}$$")
        self.assertIn('<div class="eq">', out)
        self.assertNotIn("eqfallback", out)

    def test_equation_lookup_ignores_line_breaks(self):
        out = body("$$\nN = \\frac{\\left(E^3\\,\\sigma A\\,t\\right)^{1/4}}{k_B \\ln 2}\n$$")
        self.assertIn('<div class="eq">', out)
        self.assertNotIn("eqfallback", out)


class Document(unittest.TestCase):
    def test_self_contained(self):
        page = build("# T\n\nbody\n", "t.md")
        for probe in ("http://", "https://", "src=", "@import"):
            self.assertNotIn(probe, page, f"page reaches outside for {probe!r}")

    def test_footer_is_overridable(self):
        self.assertIn("mine", build("# T\n\nx\n", footer="mine"))
        self.assertNotIn("<footer>", build("# T\n\nx\n", footer=""))

    def test_custom_equations(self):
        page = build("$$a+b$$", equations={"a+b": "<i>sum</i>"})
        self.assertIn("<i>sum</i>", page)

    def test_empty_input(self):
        self.assertIn("</html>", build(""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
