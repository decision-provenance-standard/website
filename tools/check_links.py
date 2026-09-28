# SPDX-License-Identifier: Apache-2.0
"""Check every internal link on the site's pages: the target file exists, and any #anchor exists
in the target page. Links to https://decisionprovenancestandard.org/... count as internal.

Usage:  python tools/check_links.py docs
Exit code 0 = no broken link, 1 = at least one.
"""
import argparse
import os
import sys
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

SITE = "https://decisionprovenancestandard.org"


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ids = [], set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "name" in a:
            self.ids.add(a["name"])
        for k in ("href", "src"):
            v = a.get(k)
            if v and not (tag == "link" and a.get("rel") in ("canonical", "preconnect")):
                self.links.append((tag, k, v))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check the site's internal links and anchors.")
    ap.add_argument("docs", help="the site's docs folder")
    docs = os.path.abspath(ap.parse_args(argv).docs)
    pages, parsed = [], {}
    for root, _, files in os.walk(docs):
        for f in files:
            if f.endswith(".html"):
                pages.append(os.path.join(root, f))

    def parse(path):
        if path not in parsed:
            p = Page()
            with open(path, encoding="utf-8") as fh:
                p.feed(fh.read())
            parsed[path] = p
        return parsed[path]

    def resolve(base_page, url):
        u = urlsplit(url)
        if u.scheme in ("http", "https"):
            if not url.startswith(SITE):
                return None
            target = os.path.join(docs, u.path.lstrip("/"))
        elif u.scheme:
            return None  # data:, mailto:, etc.
        else:
            path = unquote(u.path)
            if not path:
                target = base_page
            elif path.startswith("/"):
                target = os.path.join(docs, path.lstrip("/"))
            else:
                target = os.path.join(os.path.dirname(base_page), path)
        target = os.path.normpath(target)
        if os.path.isdir(target):
            target = os.path.join(target, "index.html")
        return target, u.fragment

    broken, checked = [], 0
    for page in sorted(pages):
        for tag, attr, url in parse(page).links:
            r = resolve(page, url)
            if r is None:
                continue
            target, frag = r
            checked += 1
            rel = os.path.relpath(page, docs).replace(os.sep, "/")
            if not os.path.exists(target):
                broken.append(f"{rel}: {attr}={url} -> missing file")
                continue
            if frag and target.endswith(".html") and frag not in parse(target).ids:
                broken.append(f"{rel}: {attr}={url} -> missing anchor #{frag}")

    print(f"pages scanned: {len(pages)}; internal links checked: {checked}; broken: {len(broken)}")
    for b in broken:
        print("  BROKEN", b)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
