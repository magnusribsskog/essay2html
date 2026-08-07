---
title: worked example
draft: false
---

# The Cost of a Dependency

### On what a rendered page owes the person reading it

**A. Author** · 2026-08-07 · Rev. 1

**Abstract.** Every dependency a document acquires is a promise that something
else will still exist when the document is read. This example exercises each
construct `essay2html` supports, so that a change to the renderer that breaks
one of them is visible immediately.

## Prose and emphasis

A paragraph is any run of adjacent lines; they are joined. Emphasis comes in
*italic* and **bold**, and inline `code` spans are inert — `a * b * c` keeps its
asterisks, because emphasis is not allowed to reach inside code. Nor is
arithmetic mistaken for it: 5 * 4 * 3 is sixty.

Scientific notation uses the inline HTML allowlist, so *T*<sub>amb</sub><sup>4</sup>
survives here and on GitHub both. A [link](https://example.com/wiki/Foo_(bar))
may carry balanced parentheses.

> A blockquote sets off borrowed words. It is the one place a page admits that
> it is quoting rather than speaking.

## Lists

1. Numbered items keep their order.
2. A continuation line indented beneath an item
   joins that item rather than starting a paragraph.

- Bulleted items do not merge into the numbered list above.
- They stand on their own.

## A table

| Approach | Payload | Works offline | Layout shift |
| --- | ---: | :---: | --- |
| MathJax | ~1.2 MB | after vendoring | yes |
| KaTeX | ~280 KB | after vendoring | slight |
| Hand-typeset | 0 | always | none |

## Code

```python
def build(md: str) -> str:
    """One file in, one file out, nothing fetched."""
    return render(md)
```

## Maths

Display maths is looked up by its LaTeX source. This one is in the built-in
table:

$$N = \frac{\left(E^3\,\sigma A\,t\right)^{1/4}}{k_B \ln 2}$$

An equation with no hand-typeset form falls back to monospace and warns on
stderr, rather than shipping something ugly without telling you:

$$\oint_{\partial \Sigma} \mathbf{B} \cdot d\boldsymbol{\ell} = \mu_0 I_{enc}$$

---

*— A. Author*
