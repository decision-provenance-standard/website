# SPDX-License-Identifier: Apache-2.0
"""Build the six Standard reading pages of one release (dps-v<major>.<minor>-rev<n>-*.html).

One self-contained, document-style page per edition: anchored sections, a generated table of
contents, cross-document navigation, a masthead, embedded figures (base64 data URIs) and
structured data (JSON-LD). Self-contained except the Google Fonts link.

Usage:
  python tools/build_spec_pages.py --edition v1.2-rev10 --editions <editions.json> \\
      --src <joined-dir> --diagrams <spec/diagrams> --outdir <dir>

  --edition   the release id, v<major>.<minor>-rev<n>; it equals the release tag in the
              standard repository and the `tag` of each edition's `releases` entry
  --editions  the standard repository's spec/editions.json as it stands at that tag
              (tools/build_release.py passes `git show <tag>:spec/editions.json`)
  --src       the joined Markdown written by `python tools/check_split.py --write-joined <dir>`
              in the standard repository at that tag; the text is never edited elsewhere
  --diagrams  the standard repository's spec/diagrams folder at that tag

Every version string, page name, source name, page title, meta description and JSON-LD value
comes from the release id and from editions.json. The per-edition navigation label, page title,
description and related-links box are keyed by the edition's `id` (core, companion-A, ...).

This tool writes only the six pages of the release it is given, and only into --outdir.
It never writes any other page of the site: those pages are maintained by hand in docs/.
The pages of v1.0 (reading edition rev. 8) are frozen as published and cannot be rebuilt here.

Byte-for-byte rebuilds depend on the Python-Markdown version: the v1.1 pages were built with
Python-Markdown 3.10.2. The version in use is printed with the report.
"""
import argparse
import base64
import html
import json
import os
import re
import sys

import markdown

DOMAIN = "https://decisionprovenancestandard.org"
EDITION_RE = re.compile(r"^v(\d+)\.(\d+)-rev(\d+)$")
FROZEN_PAGE_RE = re.compile(r"^dps-v1\.0-rev8-")
LAST_FROZEN_REV = 8  # rev. 8 (v1.0) is frozen as published; its pages are never rebuilt

MIME = {".png": "image/png", ".svg": "image/svg+xml", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

_FW = '<a href="firewall.html">The Firewall — what the Standard is not</a>'

# Per edition id, in navigation order: (navigation label, page title, meta description,
# related-links box appended to the body or "").
EDITIONS = {
    "core": (
        "Core", "Decision Provenance Standard",
        "The Decision Provenance Standard™ — an open, CC-BY record format for audit-ready provenance of human–AI decisions. Informs frameworks; not legal advice.",
        ""),
    "companion-A": (
        "A · Regulatory", "Companion A — Regulatory Cross-References",
        "Regulatory Cross-References: how the Standard's records inform the EU AI Act, GDPR, NIST AI RMF, ISO 42001, SOC 2 and more — as input, never satisfying them.",
        f'<div class="related"><strong>Related:</strong> {_FW} · <a href="dps-comparison-frameworks.html">Comparison to frameworks</a></div>'),
    "companion-B": (
        "B · Charters", "Companion B — Worked Charter Library",
        "Worked Charter Library: complete worked Charter examples across Mode 1 and Mode 2 of the Decision Provenance Standard.",
        ""),
    "companion-C": (
        "C · Implementation", "Companion C — Implementation Guidance",
        "Implementation Guidance: the operational pre-conditions and install path for adopting the Decision Provenance Standard.",
        ""),
    "companion-D": (
        "D · Diagrams", "Companion D — Diagrams",
        "Diagrams: the reference figures of the Decision Provenance Standard, with full text alternatives.",
        ""),
    "appendix-G": (
        "G · Governance", "Appendix G — Governance and References",
        "Governance and References: version-stability rules, bibliography, and trademark/licensing for the Decision Provenance Standard.",
        ""),
}

AUTHOR = {"@type": "Person", "name": "Yohay Etsion"}
PUBLISHER = {"@type": "Organization", "name": "Etsion Brands Ltd."}
WEBSITE_ID = f"{DOMAIN}/#website"
CC_BY = "https://creativecommons.org/licenses/by/4.0/"
BREADCRUMB_SECTION = ("Standard", "#read")  # Home -> Standard -> page


class Release:
    """The version strings of one release, derived from its id (v<major>.<minor>-rev<n>)."""

    def __init__(self, edition_id):
        m = EDITION_RE.match(edition_id or "")
        if not m:
            raise SystemExit(f"REFUSED: edition id {edition_id!r} is not of the form v<major>.<minor>-rev<n>")
        self.id = edition_id
        self.major, self.minor, self.rev = (int(x) for x in m.groups())
        if self.rev <= LAST_FROZEN_REV or (self.major, self.minor) <= (1, 0):
            raise SystemExit(f"REFUSED: {edition_id}: the rev. 8 (v1.0) pages are frozen as published "
                             "and are never rebuilt")
        ver = f"{self.major}.{self.minor}"
        self.revision = f"v{ver} rev. {self.rev}"  # as editions.json writes it
        self.nav_edition = f"v{ver} &middot; Reading Edition (rev.&nbsp;{self.rev})"
        self.masthead_version = f"{ver} — Reading Edition (rev.\u00a0{self.rev})"  # no-break space
        self.foot_version = f"v{ver} &mdash; Reading Edition (rev.&nbsp;{self.rev})"


def load_docs(editions_path, rel):
    """The six pages of this release, in navigation order, from editions.json:
    (edition id, joined source file name, page file name, nav label, title, description, related)."""
    with open(editions_path, encoding="utf-8") as fh:
        data = json.load(fh)
    ids = [e["id"] for e in data["editions"]]
    if ids != list(EDITIONS):
        raise SystemExit(f"REFUSED: editions.json lists editions {ids}; this tool knows {list(EDITIONS)}. "
                         "A new or renamed edition needs its label, title and description added here.")
    docs = []
    for e in data["editions"]:
        found = [r for r in e.get("releases", []) if r.get("tag") == rel.id]
        if len(found) != 1:
            raise SystemExit(f"REFUSED: edition {rel.id!r} is not in editions.json for {e['id']} "
                             f"({len(found)} release entries with that tag)")
        r = found[0]
        if r.get("revision") != rel.revision:
            raise SystemExit(f"REFUSED: {e['id']}: editions.json revision {r.get('revision')!r} "
                             f"does not match {rel.revision!r}")
        page = f"dps-{rel.id}-{e['id']}.html"
        if r.get("page_name") != page or FROZEN_PAGE_RE.match(page):
            raise SystemExit(f"REFUSED: {e['id']}: page name {r.get('page_name')!r}, expected {page!r}")
        src = r["published_name"]
        if not (src.startswith(f"decision-provenance-standard-{rel.id}-") and src.endswith(".md")
                and os.path.basename(src) == src):
            raise SystemExit(f"REFUSED: {e['id']}: unexpected published name {src!r}")
        label, title, desc, related = EDITIONS[e["id"]]
        docs.append((e["id"], src, page, label, title, desc, related))
    return docs


def embed_images(html_text, diagrams):
    """Replace <img src="diagrams/NAME.ext"> with a <figure> + base64 data URI + figcaption.

    SVG first: if a PNG is referenced and a sibling .svg exists, embed the SVG instead. SVGs are
    vector (a few KB) and never decode into a large bitmap, which keeps the long pages light."""
    stats = {"embedded": 0, "missing": [], "svg_swapped": 0}
    img_re = re.compile(r'<img\b([^>]*?)\bsrc="(?:\./)?diagrams/([^"]+)"([^>]*)>', re.I)

    def repl(m):
        pre, fname, post = m.group(1), m.group(2), m.group(3)
        alt_m = re.search(r'alt="([^"]*)"', pre + post)
        alt = alt_m.group(1) if alt_m else ""
        base, ext = os.path.splitext(fname)
        svg_sibling = base + ".svg"
        if ext.lower() != ".svg" and os.path.exists(os.path.join(diagrams, svg_sibling)):
            fname, ext = svg_sibling, ".svg"
            stats["svg_swapped"] += 1
        path = os.path.join(diagrams, fname)
        ext = ext.lower()
        if not os.path.exists(path) or ext not in MIME:
            stats["missing"].append(fname)
            return m.group(0)
        with open(path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        stats["embedded"] += 1
        data_uri = f"data:{MIME[ext]};base64,{b64}"
        cap = html.escape(alt) if alt else ""
        figcap = f"<figcaption>{cap}</figcaption>" if cap else ""
        return (f'<figure class="dps-figure">'
                f'<img alt="{html.escape(alt)}" src="{data_uri}" loading="lazy" decoding="async">'
                f'{figcap}</figure>')

    return img_re.sub(repl, html_text), stats


def demote_headings(body_html):
    """If a page has more than one <h1> (the core uses '#' for each 'Section N'), keep the first
    h1 as the page title and demote every other heading by one level (capped at h6), so the
    top-level sections land at h2 and the page has a single h1. Single-h1 pages are unchanged."""
    if len(re.findall(r'<h1\b', body_html)) <= 1:
        return body_html
    token_re = re.compile(r'<(/?)h([1-6])((?:\s[^>]*)?)>')
    seen_first = False
    stack, out, pos = [], [], 0
    for m in token_re.finditer(body_html):
        out.append(body_html[pos:m.start()])
        closing, lvl, attrs = m.group(1) == "/", int(m.group(2)), m.group(3)
        if not closing:
            if lvl == 1 and not seen_first:
                seen_first = True
                stack.append(1)
                out.append(f'<h1{attrs}>')
            else:
                nl = min(lvl + 1, 6)
                stack.append(nl)
                out.append(f'<h{nl}{attrs}>')
        else:
            nl = stack.pop() if stack else min(lvl + 1, 6)
            out.append(f'</h{nl}>')
        pos = m.end()
    out.append(body_html[pos:])
    return "".join(out)


def build_toc(body_html):
    """The table of contents: every h2/h3 with an id in the final (demoted) body."""
    items = []
    for m in re.finditer(r'<h([23])\b[^>]*\bid="([^"]+)"[^>]*>(.*?)</h\1>', body_html, re.S):
        level = int(m.group(1))
        hid = m.group(2)
        name = re.sub(r'<[^>]+>', '', m.group(3)).strip()
        items.append((level, hid, name))
    if not items:
        return ""
    out = ['<details class="toc" open aria-label="Table of contents">'
           '<summary class="toc-summary">Contents</summary>'
           '<div class="toc-body"><ul>']
    for level, hid, name in items:
        cls = "toc-l2" if level == 2 else "toc-l3"
        out.append(f'<li class="{cls}"><a href="#{html.escape(hid)}">{html.escape(name)}</a></li>')
    out.append("</ul></div></details>")
    return "".join(out)


def nav_bar(current_page, docs, rel):
    links = []
    for _id, _src, page, label, _title, _desc, _rel in docs:
        active = ' aria-current="page"' if page == current_page else ""
        cls = "navlink active" if page == current_page else "navlink"
        links.append(f'<a class="{cls}" href="{page}"{active}>{html.escape(label)}</a>')
    return ('<header class="topnav"><div class="topnav-inner">'
            '<a class="brandmark" href="index.html">Decision Provenance Standard<span class="tm">&trade;</span> '
            f'<span class="ed">{rel.nav_edition}</span></a>'
            f'<nav class="docnav" aria-label="{html.escape("Standard documents")}">' + "".join(links) + '</nav>'
            '</div></header>')


def wrap_masthead(body_html, rel):
    """Replace the metadata paragraph right after the first <h1> with a compact masthead:
    Version, Author, Steward and License (the CC-BY attribution). The legal posture is carried
    by the firewall block that follows in the text. Only the core has this paragraph; the
    companions open with a scope note and are returned unchanged."""
    h1_m = re.search(r'(</h1>)', body_html)
    if not h1_m:
        return body_html
    start = h1_m.end()
    m = re.match(r'\s*<p>((?:(?!</p>).)*?)</p>', body_html[start:], re.S)
    if not m:
        return body_html
    inner = m.group(1)
    if inner.count("<strong>") < 3:  # a real masthead has several strong-led fields
        return body_html
    fields = {}
    for fm in re.finditer(r'<strong>(.*?)</strong>\s*:?\s*(.*?)(?=<strong>|$)', inner, re.S):
        key = re.sub(r'<[^>]+>', '', fm.group(1)).strip().rstrip(':').strip()
        val = fm.group(2).strip()
        if key and key not in fields:
            fields[key] = val

    def get(name):
        for k, v in fields.items():
            if k.lower() == name.lower():
                return v
        return None

    parts = [f'<strong>Version:</strong> {rel.masthead_version}']
    for label in ("Author", "Steward", "License"):
        v = get(label)
        if v:
            parts.append(f'<strong>{label}:</strong> {v}')
    masthead = '<div class="masthead"><p>' + ' &middot; '.join(parts) + '</p></div>'
    return body_html[:start] + '\n' + masthead + body_html[start + m.end():]


LONG_CODE = 50  # characters; only identifiers this long get break points


def prepare_tables(body_html):
    """Layout aids for tables; no text changes. Every table can take keyboard focus, so a table
    that scrolls sideways inside its box can be scrolled with the arrow keys in every browser.
    Inside tables, a code identifier of LONG_CODE or more characters may wrap after its
    underscores (<wbr>), so one very long name cannot push its table past the reading column."""
    def table(m):
        def code(c):
            inner = c.group(1)
            if "<" in inner or len(html.unescape(inner)) < LONG_CODE:
                return c.group(0)
            return "<code>" + inner.replace("_", "_<wbr>") + "</code>"
        return re.sub(r"<code>(.*?)</code>", code, m.group(0), flags=re.S)
    body_html = re.sub(r"<table>.*?</table>", table, body_html, flags=re.S)
    return body_html.replace("<table>", '<table tabindex="0">')


def jsonld(page, title, desc):
    canonical = f"{DOMAIN}/{page}"
    article = {"@context": "https://schema.org", "@type": "TechArticle",
               "headline": title, "description": desc,
               "url": canonical, "mainEntityOfPage": canonical,
               "license": CC_BY, "author": AUTHOR, "publisher": PUBLISHER,
               "isPartOf": {"@type": "WebSite", "@id": WEBSITE_ID}}
    section, anchor = BREADCRUMB_SECTION
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList",
              "itemListElement": [
                  {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{DOMAIN}/"},
                  {"@type": "ListItem", "position": 2, "name": section, "item": f"{DOMAIN}/{anchor}"},
                  {"@type": "ListItem", "position": 3, "name": title, "item": f"{DOMAIN}/{page}"}]}
    return "\n".join('<script type="application/ld+json">\n' + json.dumps(b, ensure_ascii=False, indent=2)
                     + '\n</script>' for b in (article, crumbs))


CSS = """
:root{
  --ink:#1A1A1A; --ink-soft:#3F4750; --paper:#F5F5F5; --card:#FFFFFF;
  --accent:#3A5A78; --accent-soft:#8FA8C0; --rule:#E2E5E9; --rule-soft:#EDEFF2;
  --code-bg:#EEF1F4; --callout-bg:#F0F3F6; --warn-bar:#3A5A78;
}
*{box-sizing:border-box;}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
.skip-link{position:absolute;left:-999px;top:0;background:var(--accent);color:#fff;
  padding:.5rem .9rem;border-radius:0 0 6px 0;z-index:200;
  font-family:'Manrope',system-ui,sans-serif;font-weight:700;text-decoration:none;}
.skip-link:focus{left:0;}
@media (prefers-reduced-motion: reduce){*{transition:none!important;scroll-behavior:auto!important;}}
html{scrollbar-width:thin;}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:'Source Serif 4',Georgia,'Times New Roman',serif;
  font-size:18px;line-height:1.72;-webkit-font-smoothing:antialiased;}
.topnav{position:sticky;top:0;z-index:50;background:#F2F4F6;
  border-bottom:1px solid var(--rule);}
.topnav-inner{max-width:1100px;margin:0 auto;padding:.55rem 1.5rem;display:flex;
  align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap;}
.brandmark{font-family:'Manrope',system-ui,sans-serif;font-weight:700;font-size:.95rem;
  color:var(--accent);letter-spacing:.01em;text-decoration:none;}
.brandmark:hover{opacity:.85;}
.brandmark .tm{font-size:.6em;vertical-align:super;font-weight:600;}
.brandmark .ed{font-weight:500;color:var(--ink-soft);font-size:.82em;margin-left:.4rem;}
.docnav{display:flex;gap:.25rem;flex-wrap:wrap;}
.navlink{font-family:'Manrope',system-ui,sans-serif;font-size:.8rem;font-weight:600;
  text-decoration:none;color:var(--ink-soft);padding:.28rem .6rem;border-radius:6px;
  border:1px solid transparent;}
.navlink:hover{background:var(--rule-soft);color:var(--accent);}
.navlink.active{background:var(--accent);color:#fff;}
.wrap{width:100%;max-width:820px;margin:0 auto;padding:2.5rem 1.6rem 6rem;min-width:0;}
.layout{display:grid;grid-template-columns:1fr;gap:0;}
@media(min-width:1180px){
  .layout{grid-template-columns:minmax(0,1fr) 270px;max-width:1240px;margin:0 auto;
    padding:0 1.6rem;column-gap:2.6rem;align-items:start;}
  .wrap{max-width:840px;margin:0;padding:2.5rem 0 6rem;}
  .toc{position:sticky;top:72px;margin-top:2.5rem;}
}
h1,h2,h3,h4,h5,h6{font-family:'Manrope',system-ui,sans-serif;color:var(--ink);
  line-height:1.25;font-weight:700;margin:2.2rem 0 .8rem;scroll-margin-top:72px;}
h1{font-size:2.05rem;font-weight:800;margin-top:.4rem;letter-spacing:-.01em;}
h2{font-size:1.5rem;padding-bottom:.3rem;border-bottom:2px solid var(--accent-soft);}
h3{font-size:1.2rem;color:var(--accent);}
h4{font-size:1.03rem;}
h1+p{color:var(--ink-soft);}
/* masthead: the strong-led metadata lines right after h1 */
.masthead{background:var(--card);border:1px solid var(--rule);border-left:4px solid var(--accent);
  border-radius:8px;padding:1rem 1.25rem;margin:1.2rem 0 2rem;font-size:.92rem;line-height:1.6;}
.masthead strong{font-family:'Manrope',system-ui,sans-serif;}
p,li{overflow-wrap:break-word;}
a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:2px;}
code,kbd,samp{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:.86em;
  background:var(--code-bg);padding:.1em .35em;border-radius:4px;}
pre{background:var(--code-bg);border:1px solid var(--rule);border-radius:8px;
  padding:1rem 1.15rem;overflow:auto;font-size:.84rem;line-height:1.55;}
pre code{background:none;padding:0;}
blockquote{margin:1.3rem 0;padding:.85rem 1.2rem;background:var(--callout-bg);
  border-left:4px solid var(--warn-bar);border-radius:0 8px 8px 0;color:var(--ink-soft);}
blockquote p{margin:.4rem 0;}
blockquote strong{color:var(--ink);}
table{border-collapse:collapse;width:100%;margin:1.4rem 0;font-size:.88rem;
  font-family:'Manrope',system-ui,sans-serif;}
@media screen and (max-width:1179.98px){table{display:block;overflow-x:auto;}.topnav{position:static;}}
th,td{border:1px solid var(--rule);padding:.5rem .7rem;text-align:left;vertical-align:top;}
th{background:var(--accent);color:#fff;font-weight:600;}
tr:nth-child(even) td{background:var(--rule-soft);}
hr{border:none;border-top:1px solid var(--rule);margin:2.4rem 0;}
.dps-figure{margin:1.8rem 0;text-align:center;}
.dps-figure img{max-width:100%;height:auto;background:#fff;border:1px solid var(--rule);
  border-radius:8px;padding:.6rem;}
.dps-figure figcaption{font-family:'Manrope',system-ui,sans-serif;font-size:.8rem;
  color:var(--ink-soft);margin-top:.55rem;line-height:1.5;text-align:left;}
ul,ol{padding-left:1.4rem;}
li{margin:.3rem 0;}
.toc{font-family:'Manrope',system-ui,sans-serif;font-size:.82rem;
  background:var(--card);border:1px solid var(--rule);border-radius:8px;padding:1rem 1.1rem;
  max-height:calc(100vh - 96px);overflow:auto;margin:0 0 2rem;}
.toc-title{font-weight:700;color:var(--accent);margin-bottom:.5rem;font-size:.78rem;
  text-transform:uppercase;letter-spacing:.06em;}
.toc-summary{cursor:pointer;font-family:'Manrope',system-ui,sans-serif;font-weight:700;
  color:var(--accent);text-transform:uppercase;letter-spacing:.06em;font-size:.78rem;
  list-style:none;margin-bottom:.5rem;}
.toc-summary::-webkit-details-marker{display:none;}
.toc-summary::marker{content:"";}
@media(min-width:1180px){.toc-summary{display:none;}}
.toc ul{list-style:none;margin:0;padding:0;}
.toc li{margin:.12rem 0;}
.toc a{color:var(--ink-soft);text-decoration:none;display:block;padding:.12rem .3rem;border-radius:4px;}
.toc a:hover{background:var(--rule-soft);color:var(--accent);}
.toc a.active{color:var(--accent);font-weight:700;background:var(--rule-soft);
  box-shadow:inset 2px 0 0 var(--accent);}
.toc-l3{padding-left:.9rem;font-size:.95em;}
.docfoot{font-family:'Manrope',system-ui,sans-serif;font-size:.78rem;color:var(--ink-soft);
  border-top:1px solid var(--rule);margin-top:3rem;padding-top:1rem;}
.related{font-family:'Manrope',system-ui,sans-serif;font-size:.9rem;background:var(--callout-bg);
  border:1px solid var(--rule);border-left:4px solid var(--accent);border-radius:0 8px 8px 0;
  padding:.8rem 1.1rem;margin:2.2rem 0 .5rem;}
@media print{
  .topnav,.toc{display:none!important;}
  body{background:#fff;font-size:11pt;}
  .layout{grid-template-columns:1fr;max-width:none;}
  .wrap{max-width:none;padding:0;}
  h2{border-color:#999;} th{background:#333;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
  .dps-figure img{border-color:#bbb;}
  a{color:var(--ink);text-decoration:none;}
}
"""
# No smooth scrolling: with it, a link to a section scrolled past lazily loaded figures, which
# then loaded and pushed the target down. The pages jump straight to the anchor.

FAVICON = ("data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
           "<rect width='32' height='32' rx='6' fill='%233A5A78'/>"
           "<rect x='9' y='8' width='14' height='3' rx='1.5' fill='white'/>"
           "<rect x='9' y='14.5' width='14' height='3' rx='1.5' fill='white'/>"
           "<rect x='9' y='21' width='9' height='3' rx='1.5' fill='%238FA8C0'/></svg>")

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="index,follow">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Decision Provenance Standard">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{domain}/assets/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Decision Provenance Standard — audit-ready provenance for decisions made by humans and AI together.">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{domain}/assets/og-image.png">
<link rel="icon" type="image/svg+xml" href="{favicon}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
{jsonld}
<style>{css}</style>
</head>
<body>
<a class="skip-link" href="#top">Skip to main content</a>
{nav}
<div class="layout">
<main class="wrap" id="top">
{body}
<div class="docfoot"><strong>The records are input, not evidence. The Standard informs frameworks without satisfying them. Conformance is self-declared; no body certifies it. It is not legal advice and not a regulatory substitute.</strong><br>Decision Provenance Standard&trade; {foot_version}. Open standard under CC-BY&nbsp;4.0. Not a certified product. Founding Steward: Yohay Etsion; institutional Steward: Etsion Brands Ltd.</div>
</main>
{toc}
</div>
</body>
</html>
"""

SCROLL_SPY_JS = """<script>
/* TOC scroll-spy: highlight the section currently in view and keep it visible in the rail. */
(function(){
  var links={};
  document.querySelectorAll('.toc a').forEach(function(a){
    links[a.getAttribute('href').slice(1)]=a;
  });
  var heads=[].slice.call(document.querySelectorAll('main h2[id], main h3[id]'))
    .filter(function(h){return links[h.id];});
  if(!heads.length) return;
  var cur=null;
  function setActive(id){
    if(cur===id) return;
    if(cur&&links[cur]) links[cur].classList.remove('active');
    cur=id;
    var a=links[id]; if(!a) return;
    a.classList.add('active');
    var toc=a.closest('.toc');
    if(toc){var ar=a.getBoundingClientRect(),tr=toc.getBoundingClientRect();
      if(ar.top<tr.top||ar.bottom>tr.bottom) a.scrollIntoView({block:'nearest'});}
  }
  var ticking=false;
  function onScroll(){
    if(ticking) return; ticking=true;
    requestAnimationFrame(function(){
      var top=heads[0], y=110;
      for(var i=0;i<heads.length;i++){
        if(heads[i].getBoundingClientRect().top<=y) top=heads[i]; else break;
      }
      setActive(top.id); ticking=false;
    });
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  window.addEventListener('resize',onScroll,{passive:true});
  onScroll();
})();
/* Mobile Contents drawer: open on desktop, collapsed on phones; sync on resize. */
(function(){
  function syncTOC(){var d=document.querySelector('details.toc');if(d)d.open=window.innerWidth>=1180;}
  syncTOC();
  window.addEventListener('resize',syncTOC);
})();
</script>"""


def render_page(text, doc, docs, rel, diagrams):
    _id, _src, page, _label, title, desc, related = doc
    md = markdown.Markdown(extensions=["extra", "toc", "sane_lists", "admonition"],
                           extension_configs={"toc": {"permalink": False}})
    body = md.convert(text)
    body = demote_headings(body)
    body = wrap_masthead(body, rel)
    body, stats = embed_images(body, diagrams)
    body = prepare_tables(body)
    body += related
    canonical = f"{DOMAIN}/{page}"
    out = PAGE.format(title=html.escape(title), favicon=FAVICON, css=CSS,
                      nav=nav_bar(page, docs, rel), body=body, toc=build_toc(body),
                      desc=html.escape(desc), canonical=html.escape(canonical),
                      domain=DOMAIN, jsonld=jsonld(page, title, desc), foot_version=rel.foot_version)
    return out.replace("</body>", SCROLL_SPY_JS + "\n</body>"), stats


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the six Standard reading pages of one release.")
    ap.add_argument("--edition", required=True, help="release id, v<major>.<minor>-rev<n> (the release tag)")
    ap.add_argument("--editions", required=True, help="spec/editions.json as it stands at the release tag")
    ap.add_argument("--src", required=True, help="folder of joined Markdown from check_split.py --write-joined")
    ap.add_argument("--diagrams", required=True, help="the standard repository's spec/diagrams folder at the tag")
    ap.add_argument("--outdir", required=True, help="output folder")
    args = ap.parse_args(argv)
    rel = Release(args.edition)
    docs = load_docs(args.editions, rel)
    src, diagrams, outdir = (os.path.abspath(p) for p in (args.src, args.diagrams, args.outdir))
    os.makedirs(outdir, exist_ok=True)
    report = []
    for doc in docs:
        with open(os.path.join(src, doc[1]), encoding="utf-8") as fh:
            text = fh.read()
        page, stats = render_page(text, doc, docs, rel, diagrams)
        if stats["missing"]:
            raise SystemExit(f"FAILED: {doc[2]}: figures not found in {diagrams}: {stats['missing']}")
        name = doc[2]
        assert not FROZEN_PAGE_RE.match(name) and os.path.basename(name) == name, name
        with open(os.path.join(outdir, name), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(page)
        report.append((name, len(page), stats["embedded"]))
    print(f"Output dir: {outdir}  (release {rel.id}; Python-Markdown {markdown.__version__})")
    for name, size, emb in report:
        print(f"  {name:40s} {size / 1024:7.1f} KB  figures-embedded={emb}")


if __name__ == "__main__":
    main()
