# SPDX-License-Identifier: Apache-2.0
"""Open each Section 7 deep link fresh in headless Chromium and report where the heading sits
once the page has stopped moving. It lands when the heading's top is within the sticky-header
margin (0-120 px from the top of the window) and the page has settled.

Usage:  python tools/check_deeplinks.py docs [--page dps-v1.2-rev10-core.html ...] [--shot file.png]
  --page  the pages to test (default: the newest dps-v<major>.<minor>-rev<n>-core.html in docs,
          by version order); a miss on a tested page fails the run
  --ids   the anchors to open (default: the Section 7 headings)
  --shot  save a screenshot of the first tested page at its Level 2 heading
The rev. 8 core page (dps-v1.0-rev8-core.html) is also opened, for information only: it keeps
smooth scrolling as published, so its misses never fail the run.
Exit code 0 = every tested link lands, 1 = at least one misses.
"""
import argparse
import http.server
import os
import re
import socketserver
import sys
import threading

REV8_CORE = "dps-v1.0-rev8-core.html"
IDS = ["section-7-conformance-levels", "72-conformance-level-1-charter-conformant", "721-level-1-criteria",
       "73-conformance-level-2-mode-disambiguated", "731-level-2-criteria",
       "74-conformance-level-3-continuously-auditable", "741-level-3-criteria"]
SHOT_ID = "73-conformance-level-2-mode-disambiguated"
CORE_RE = re.compile(r"^dps-v(\d+)\.(\d+)-rev(\d+)-core\.html$")


def newest_core(docs):
    found = []
    for f in os.listdir(docs):
        m = CORE_RE.match(f)
        if m and f != REV8_CORE:
            found.append((tuple(int(x) for x in m.groups()), f))
    if not found:
        raise SystemExit(f"no dps-v*-core.html page in {docs}")
    return max(found)[1]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check that Section 7 deep links land on their heading.")
    ap.add_argument("docs", help="the site's docs folder")
    ap.add_argument("--page", action="append", help="page to test (repeatable)")
    ap.add_argument("--ids", nargs="+", default=IDS, help="anchors to open")
    ap.add_argument("--shot", help="screenshot file for the first tested page")
    a = ap.parse_args(argv)
    docs = os.path.abspath(a.docs)
    tested = a.page or [newest_core(docs)]
    for p in tested:
        if not os.path.isfile(os.path.join(docs, p)):
            raise SystemExit(f"no such page: {p}")
    info = [REV8_CORE] if REV8_CORE not in tested and os.path.isfile(os.path.join(docs, REV8_CORE)) else []

    from playwright.sync_api import sync_playwright
    srv = socketserver.TCPServer(("127.0.0.1", 0), lambda *x, **k: Quiet(*x, directory=docs, **k))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    bad = 0
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            for page in tested + info:
                for i in a.ids:
                    pg = b.new_page(viewport={"width": 1440, "height": 900})
                    pg.goto(f"http://127.0.0.1:{port}/{page}#{i}", wait_until="networkidle")
                    js = (f"[Math.round(window.scrollY), Math.round(document.getElementById('{i}')"
                          f".getBoundingClientRect().top + window.scrollY), "
                          f"Math.round(document.getElementById('{i}').getBoundingClientRect().top)]")
                    pg.wait_for_timeout(2000)
                    first = pg.evaluate(js)
                    pg.wait_for_timeout(1500)
                    y, head_y, top = pg.evaluate(js)
                    settled = first == [y, head_y, top]
                    ok = 0 <= top <= 120 and settled
                    note = "" if page in tested else "  (information only)"
                    if page in tested and not ok:
                        bad += 1
                    print(f"{page:28s} #{i:46s} scrollY={y:6d} heading at {head_y:6d} "
                          f"-> {top:5d}px from top, settled={settled} {'LANDS' if ok else 'MISSES'}{note}")
                    if a.shot and page == tested[0] and i == SHOT_ID:
                        pg.screenshot(path=a.shot)
                    pg.close()
            b.close()
    finally:
        srv.shutdown()
    print(f"tested pages: {', '.join(tested)}; misses: {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
