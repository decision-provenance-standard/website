# SPDX-License-Identifier: Apache-2.0
"""Build the website files for one release of the Standard from its tag in the standard repository.

Every step reads only what the release tag holds:
  - the joined text written by the standard repository's `tools/check_split.py --write-joined`,
  - spec/editions.json at the tag (`git show <tag>:spec/editions.json`),
  - spec/diagrams/ and standard/v5.0/ at the tag,
and the page builder beside this file (tools/build_spec_pages.py).

Before any step, the run is refused unless:
  - --tag has the form v<major>.<minor>-rev<n> and is not the frozen rev. 8 release;
  - the clone given by --standard is detached at <tag>^{commit}, with a clean `git status`;
  - <ref-tag>^{commit} is the same commit (the text tag and the reference-files tag name the
    same merge);
  - every edition in editions.json at the tag has exactly one `releases` entry for --tag;
  - --site is a git work tree, and --work lies outside both repositories.

Steps (each can run alone):
  joined     check_split.py --write-joined into <work>/joined; each file must match its
             editions.json digest and size
  pages      joined text -> the release's six pages, written into <site>/docs/ with LF endings
  pdf        each page -> PDF with headless Chromium (served over http, print CSS); links to
             other site pages are pointed at the public site before printing
  diagrams   the tag's spec/diagrams: the SVGs into <site>/docs/diagrams/ (the site's current
             figures), and SVG + PNG into the release folder's diagrams/
  downloads  the release folder: Markdown (byte for byte), HTML, PDF, and the bundle zip, whose
             md/diagrams/ holds the same figures as the folder's diagrams/
  reffiles   the tag's standard/v5.0/ (reference files), byte for byte, into <site>/docs/standard/v5.0/
  gallery    re-embed the tag's SVGs in <site>/docs/diagram-gallery.html (each figure is found
             by its figure number; all must be found exactly once)
  schemas    every JSON Schema at the tag under standard/v5.0/ and kit/declaration/, byte for
             byte, served at the address its own $id names (<site>/docs/schemas/...), and also at
             every address a relative $ref in another of these schemas resolves to, so a validator
             that fetches referenced schemas over the web finds each one
  sums       SHA256SUMS.txt for the release folder, from COMMITTED bytes; run after the release
             files are committed, then commit SHA256SUMS.txt
  filldate   --date YYYY-MM-DD: fill <RELEASE-DATE> and <RELEASE-COMMIT> in the hand-edited
             site files (the commit is the tag's)
  all        pages, pdf, diagrams, downloads, reffiles, gallery, schemas (not sums, not filldate)

The release folder is <site>/docs/downloads/<tag>/, or --release-dir outside the site (for a
rehearsal). Published downloads are never rewritten: nothing under docs/downloads/ except the new
release folder may be written, and a release folder whose SHA256SUMS.txt is already committed is
refused. The pages of v1.0 (rev. 8) are frozen and cannot be rebuilt.

Release build after the tag (example):
  python tools/build_release.py all --tag v1.2-rev10 --ref-tag ref-5.1.2 \\
      --standard <clean clone, detached at the tag> --site <website clone> --work <scratch> \\
      --zip-date YYYY-MM-DD
  (commit the files) ; python tools/build_release.py sums ... ; (commit SHA256SUMS.txt)
"""
import argparse
import base64
import hashlib
import http.server
import io
import json
import os
import pathlib
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import zipfile

SITE_URL = "https://decisionprovenancestandard.org"
TAG_RE = re.compile(r"^v(\d+)\.(\d+)-rev(\d+)$")
LAST_FROZEN_REV = 8
FROZEN_PAGE_RE = re.compile(r"^dps-v1\.0-rev8-")
PAGE_BUILDER = pathlib.Path(__file__).resolve().parent / "build_spec_pages.py"
PLACEHOLDER = "<RELEASE-DATE>"
# Hand-edited site files that may carry <RELEASE-DATE> (raw or HTML-escaped) and, on the
# downloads page, <RELEASE-COMMIT>. Files generated from the tagged text already carry the date.
PLACEHOLDER_FILES = ["CITATION.cff", "docs/index.html", "docs/downloads.html", "docs/sitemap.xml",
                     "docs/dps-academic-summary.html"]


def fail(msg):
    raise SystemExit("REFUSED: " + msg)


def git(repo, *args, binary=False, check=True):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=not binary)
    if check and r.returncode != 0:
        err = r.stderr if not binary else r.stderr.decode(errors="replace")
        fail(f"git {' '.join(args)} failed in {repo}: {err.strip()}")
    return r


def norm(p):
    return os.path.normcase(os.path.abspath(str(p)))


def is_under(p, root):
    p, root = norm(p), norm(root)
    try:
        return os.path.commonpath([p, root]) == root
    except ValueError:  # different drives
        return False


def sha256(b):
    return hashlib.sha256(b).hexdigest()


class Ctx:
    """The checked inputs of one run, and the only places it may write."""

    def __init__(self, a):
        m = TAG_RE.match(a.tag)
        if not m:
            fail(f"--tag {a.tag!r} is not of the form v<major>.<minor>-rev<n>")
        major, minor, rev = (int(x) for x in m.groups())
        if rev <= LAST_FROZEN_REV or (major, minor) <= (1, 0):
            fail(f"{a.tag}: the rev. 8 (v1.0) release is frozen as published and is never rebuilt")
        self.tag, self.ver, self.rev = a.tag, f"{major}.{minor}", rev
        self.standard = pathlib.Path(a.standard).resolve()
        self.site = pathlib.Path(a.site).resolve()
        self.work = pathlib.Path(a.work).resolve()
        self.docs = self.site / "docs"

        # The standard clone: detached at the tag, clean, and the reference tag on the same commit.
        want = git(self.standard, "rev-parse", "--verify", "--quiet", f"{a.tag}^{{commit}}", check=False)
        if want.returncode != 0:
            fail(f"tag {a.tag} does not exist in {self.standard}")
        self.commit = want.stdout.strip()
        head = git(self.standard, "rev-parse", "HEAD").stdout.strip()
        if git(self.standard, "symbolic-ref", "-q", "HEAD", check=False).returncode == 0:
            fail(f"{self.standard} is on a branch; check out the tag detached (git checkout --detach {a.tag})")
        if head != self.commit:
            fail(f"{self.standard} is at {head}, not at {a.tag} ({self.commit})")
        dirty = git(self.standard, "status", "--porcelain", "--untracked-files=all").stdout
        if dirty.strip():
            fail(f"{self.standard} is not clean:\n{dirty}")
        ref = git(self.standard, "rev-parse", "--verify", "--quiet", f"{a.ref_tag}^{{commit}}", check=False)
        if ref.returncode != 0:
            fail(f"reference tag {a.ref_tag} does not exist in {self.standard}")
        if ref.stdout.strip() != self.commit:
            fail(f"--ref-tag {a.ref_tag} is at {ref.stdout.strip()}, not at {a.tag} ({self.commit})")

        # The site and the work folder.
        top = git(self.site, "rev-parse", "--show-toplevel", check=False)
        if top.returncode != 0 or norm(top.stdout.strip()) != norm(self.site) or not self.docs.is_dir():
            fail(f"--site {self.site} is not the top of a git work tree with a docs/ folder")
        for other in (self.site, self.standard):
            if is_under(self.work, other) or is_under(other, self.work):
                fail(f"--work {self.work} must lie outside {other}")
        self.work.mkdir(parents=True, exist_ok=True)

        # editions.json at the tag: one release entry per edition for this tag.
        raw = git(self.standard, "show", f"{self.commit}:spec/editions.json", binary=True).stdout
        self.editions_file = self.work / "editions.json"
        self.editions_file.write_bytes(raw)
        data = json.loads(raw.decode("utf-8"))
        self.releases = []
        for e in data["editions"]:
            found = [r for r in e.get("releases", []) if r.get("tag") == a.tag]
            if len(found) != 1:
                fail(f"edition {a.tag!r} is not in editions.json at the tag for {e['id']} "
                     f"({len(found)} release entries)")
            r = found[0]
            for k in ("published_name", "page_name", "bundle_name"):
                if os.path.basename(r[k]) != r[k]:
                    fail(f"{e['id']}: {k} {r[k]!r} is not a plain file name")
            if not r["page_name"].startswith(f"dps-{a.tag}-") or FROZEN_PAGE_RE.match(r["page_name"]):
                fail(f"{e['id']}: page name {r['page_name']!r} does not belong to {a.tag}")
            self.releases.append((e["id"], r))
        bundles = {r["bundle_name"] for _, r in self.releases}
        if bundles != {f"decision-provenance-standard-{a.tag}-bundle.zip"}:
            fail(f"unexpected bundle names in editions.json: {sorted(bundles)}")
        self.bundle_name = bundles.pop()
        self.page_names = {r["page_name"] for _, r in self.releases}

        # The release folder: the site's docs/downloads/<tag>/, or a folder outside the site.
        self.site_release = self.docs / "downloads" / a.tag
        self.release_dir = pathlib.Path(a.release_dir).resolve() if a.release_dir else self.site_release
        if is_under(self.release_dir, self.site):
            if norm(self.release_dir) != norm(self.site_release):
                fail(f"release folder {self.release_dir}: inside the site it can only be "
                     f"docs/downloads/{a.tag}/; published downloads are never rewritten")
            self.release_in_site = True
        else:
            if is_under(self.release_dir, self.standard):
                fail(f"release folder {self.release_dir} lies inside the standard clone")
            self.release_in_site = False
        self.site_sealed = self.sealed()
        self.step = None  # the step being run; it decides where put() may write
        self.a = a

    def sealed(self):
        """True when the site's release folder already has a committed SHA256SUMS.txt."""
        path = f"docs/downloads/{self.tag}/SHA256SUMS.txt"
        return git(self.site, "cat-file", "-e", f"HEAD:{path}", check=False).returncode == 0

    def require_release_writable(self):
        if self.release_in_site and self.site_sealed:
            fail(f"docs/downloads/{self.tag}/ is a published release (its SHA256SUMS.txt is committed); "
                 "published downloads are never rewritten")

    def may_write(self, p):
        """Each step may write only its own files (and anything in the work folder)."""
        s, docs = self.step, self.docs
        if is_under(p, self.work):
            return True
        if s == "pages":
            return norm(p) in {norm(docs / n) for n in self.page_names}
        if s == "diagrams":
            return is_under(p, docs / "diagrams") or is_under(p, self.release_dir / "diagrams")
        if s == "downloads":
            return is_under(p, self.release_dir)
        if s == "reffiles":
            return is_under(p, docs / "standard" / "v5.0")
        if s == "gallery":
            return norm(p) == norm(docs / "diagram-gallery.html")
        if s == "schemas":
            return is_under(p, docs / "schemas")
        if s == "sums":
            return norm(p) == norm(self.site_release / "SHA256SUMS.txt")
        if s == "filldate":
            return norm(p) in {norm(self.site / f) for f in PLACEHOLDER_FILES}
        return False

    def put(self, path, data):
        """The only way this tool writes a file."""
        p = pathlib.Path(path)
        ok = self.may_write(p)
        if is_under(p, self.docs / "downloads") and not (self.release_in_site and is_under(p, self.site_release)):
            ok = False
        if is_under(p, self.site_release) and self.site_sealed:
            ok = False
        if FROZEN_PAGE_RE.match(p.name):
            ok = False
        if not ok:
            fail(f"write outside the places this release may change: {p}")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def tag_files(self, folder, recursive=True):
        """{path relative to folder: bytes} for every file under <folder> at the tag."""
        flags = ["-r"] if recursive else []
        listing = git(self.standard, "ls-tree", *flags, self.commit, "--", folder + "/").stdout.split("\n")
        out = {}
        for line in filter(None, listing):
            meta, n = line.split("\t", 1)
            if meta.split()[1] != "blob":
                continue
            out[n[len(folder) + 1:]] = git(self.standard, "cat-file", "blob", f"{self.commit}:{n}", binary=True).stdout
        if not out:
            fail(f"no files under {folder}/ at {self.tag}")
        return out


def lf_only(data, name):
    """docs/diagrams/ and docs/standard/v5.0/ are stored with LF endings (.gitattributes), so git
    would rewrite a file with CR bytes on commit and the site would no longer serve the tag's bytes."""
    if b"\r" in data:
        fail(f"{name} contains CR bytes; git would normalize the site's copy to LF on commit")


def path_key(rel):
    """Order of the bundle entries: path parts compared without regard to case."""
    return [part.lower() for part in rel.split("/")]


def downloads_snapshot(ctx):
    """SHA-256 of every file under docs/downloads/ that this run must not change."""
    root = ctx.docs / "downloads"
    snap = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and not (ctx.release_in_site and is_under(p, ctx.site_release)):
            snap[p.relative_to(root).as_posix()] = sha256(p.read_bytes())
    return snap


def joined(ctx):
    """{published_name: bytes} of the joined text, each checked against editions.json."""
    j = ctx.work / "joined"
    out = {}
    for eid, r in ctx.releases:
        p = j / r["published_name"]
        if not p.is_file():
            return None
        b = p.read_bytes()
        if sha256(b) != r["sha256"] or len(b) != r["bytes"]:
            fail(f"{p} does not match editions.json ({eid})")
        out[r["published_name"]] = b
    return out


def step_joined(ctx):
    j = ctx.work / "joined"
    if j.exists():
        assert is_under(j, ctx.work)
        shutil.rmtree(j)
    subprocess.run([sys.executable, "tools/check_split.py", "--write-joined", str(j)],
                   cwd=ctx.standard, check=True)
    if joined(ctx) is None:
        fail("check_split.py did not write every edition")
    print(f"joined: {len(ctx.releases)} editions match editions.json at {ctx.tag}")


def step_pages(ctx):
    step_joined(ctx)
    out = ctx.work / "pages"
    subprocess.run([sys.executable, str(PAGE_BUILDER), "--edition", ctx.tag,
                    "--editions", str(ctx.editions_file), "--src", str(ctx.work / "joined"),
                    "--diagrams", str(ctx.standard / "spec" / "diagrams"), "--outdir", str(out)], check=True)
    for eid, r in ctx.releases:
        b = (out / r["page_name"]).read_bytes()
        if b"\r" in b:
            fail(f"{r['page_name']} has CR characters; pages are written with LF")
        ctx.put(ctx.docs / r["page_name"], b)
    print(f"pages: {len(ctx.releases)} written into docs/")


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def step_pdf(ctx):
    from playwright.sync_api import sync_playwright
    for _, r in ctx.releases:
        if not (ctx.docs / r["page_name"]).is_file():
            fail(f"docs/{r['page_name']} is missing; run the pages step first")
    docs = ctx.docs
    handler = lambda *x, **k: _Quiet(*x, directory=str(docs), **k)
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pdfdir = ctx.work / "pdf"
    pdfdir.mkdir(parents=True, exist_ok=True)
    foot = ('<div style="font-family:Arial,sans-serif;font-size:7.5px;color:#555;width:100%;'
            'padding:0 16mm;display:flex;justify-content:space-between;">'
            f'<span>Decision Provenance Standard&trade; v{ctx.ver}, Reading Edition (rev.&nbsp;{ctx.rev}) &middot; '
            '<span class="title"></span></span>'
            '<span><span class="pageNumber"></span> / <span class="totalPages"></span></span></div>')
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            for _, r in ctx.releases:
                pg.goto(f"http://127.0.0.1:{port}/{r['page_name']}", wait_until="networkidle")
                # load every figure before printing (the pages mark figures loading="lazy")
                pg.evaluate("""async () => {
                    document.querySelectorAll('img').forEach(i => i.loading = 'eager');
                    await Promise.all([...document.images].map(i => i.decode().catch(() => {})));
                    await document.fonts.ready; }""")
                # the page is served from a local address: a link to another site page would be
                # printed as that local address, so point it at the public site instead
                local = pg.evaluate("""(site) => { let n = 0;
                    for (const a of document.querySelectorAll('a[href]')) {
                        const u = new URL(a.href, location.href);
                        if (u.origin !== location.origin || u.pathname === location.pathname) continue;
                        a.setAttribute('href', site + u.pathname + u.search + u.hash); n++; }
                    return n; }""", SITE_URL)
                name = r["published_name"][:-3] + ".pdf"
                pg.pdf(path=str(pdfdir / name), format="A4", print_background=True,
                       display_header_footer=True, header_template="<div></div>", footer_template=foot,
                       margin={"top": "16mm", "bottom": "18mm", "left": "16mm", "right": "16mm"})
                print("pdf:", name, (pdfdir / name).stat().st_size, f"({local} links pointed at {SITE_URL})")
            b.close()
    finally:
        srv.shutdown()


def tag_diagrams(ctx):
    files = ctx.tag_files("spec/diagrams")
    for n in files:
        if "/" in n or not re.fullmatch(r"[A-Za-z0-9._-]+\.(svg|png)", n):
            fail(f"unexpected file at spec/diagrams/{n}")
    return files


def step_diagrams(ctx):
    ctx.require_release_writable()
    files = tag_diagrams(ctx)
    svgs = sorted(n for n in files if n.endswith(".svg"))
    for n in svgs:
        lf_only(files[n], f"spec/diagrams/{n}")
        ctx.put(ctx.docs / "diagrams" / n, files[n])
    for n in sorted(files):
        ctx.put(ctx.release_dir / "diagrams" / n, files[n])
    extra = sorted(p.name for p in (ctx.docs / "diagrams").iterdir() if p.is_file() and p.name not in svgs)
    print(f"diagrams: {len(svgs)} SVG into docs/diagrams/; {len(files)} files into the release folder's diagrams/")
    if extra:
        print("diagrams: warning, docs/diagrams/ also holds files not at the tag:", ", ".join(extra))


def offline_links(page, own_pages):
    """The download copy of a page sits in the release folder and in the bundle's html/ folder.
    Links to the release's other pages stay relative (the files sit beside it); links to any
    other site page become absolute, so they work from the download folder and offline."""

    def fix(m):
        target = m.group(1).decode()
        if target.split("#")[0] in own_pages:
            return m.group(0)
        return ('href="' + SITE_URL + "/" + target + '"').encode()

    return re.sub(rb'href="((?![a-z]+:|#|/)[^"]+)"', fix, page)


def step_downloads(ctx):
    ctx.require_release_writable()
    if not ctx.a.zip_date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ctx.a.zip_date):
        fail("downloads needs --zip-date YYYY-MM-DD (the release date, stamped on the bundle entries)")
    texts = joined(ctx)
    if texts is None:
        step_joined(ctx)
        texts = joined(ctx)
    dl = ctx.release_dir
    y, m, d = (int(x) for x in ctx.a.zip_date.split("-"))
    stamp = (y, m, d, 0, 0, 0)
    entries = []
    for eid, r in ctx.releases:
        md = texts[r["published_name"]]
        ctx.put(dl / r["published_name"], md)  # byte for byte (the core is CRLF)
        pdfname = r["published_name"][:-3] + ".pdf"
        pdfpath = ctx.work / "pdf" / pdfname
        if not pdfpath.is_file():
            fail(f"{pdfpath} is missing; run the pdf step first")
        pdf = pdfpath.read_bytes()
        ctx.put(dl / pdfname, pdf)
        page = offline_links((ctx.docs / r["page_name"]).read_bytes(), ctx.page_names)
        if b"\r" in page:
            fail(f"{r['page_name']} has CR characters")
        ctx.put(dl / r["page_name"], page)
        entries += [("md/" + r["published_name"], md), ("html/" + r["page_name"], page),
                    ("pdf/" + pdfname, pdf)]
    # The Markdown links diagrams/<file> relative to itself: the figures sit beside it.
    figs = tag_diagrams(ctx)
    for n in sorted(figs, key=path_key):
        held = dl / "diagrams" / n
        if not held.is_file() or held.read_bytes() != figs[n]:
            fail(f"{held} is missing or differs from the tag; run the diagrams step first")
        entries.append(("md/diagrams/" + n, figs[n]))
    ref = ctx.tag_files("standard/v5.0")
    for n in sorted(ref, key=path_key):
        entries.append(("standard/v5.0/" + n, ref[n]))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for arc, data in entries:
            zi = zipfile.ZipInfo(arc, date_time=stamp)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
    zpath = dl / ctx.bundle_name
    ctx.put(zpath, buf.getvalue())
    with zipfile.ZipFile(zpath) as z:
        assert z.testzip() is None
        assert [i.filename for i in z.infolist()] == [arc for arc, _ in entries]
        for arc, data in entries:
            assert z.read(arc) == data, arc
    print(f"downloads: {len(entries)} entries in {ctx.bundle_name} ({len(figs)} in md/diagrams/); "
          f"release folder {dl} has {sum(1 for p in dl.rglob('*') if p.is_file())} files")


def step_reffiles(ctx):
    """The reference files (standard/v5.0/) at the tag, byte for byte."""
    ref = ctx.tag_files("standard/v5.0")
    root = ctx.docs / "standard" / "v5.0"
    for n in sorted(ref, key=path_key):
        lf_only(ref[n], f"standard/v5.0/{n}")
        ctx.put(root / n, ref[n])
    extra = sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                   if p.is_file() and p.relative_to(root).as_posix() not in ref and p.name != "index.html")
    print(f"reffiles: {len(ref)} files copied into docs/standard/v5.0/ from {ctx.tag}")
    if extra:
        print("reffiles: warning, docs/standard/v5.0/ also holds files not at the tag:", ", ".join(extra))


GALLERY_FIG_RE = re.compile(
    r'(<figure class="dps-figure"><img\b[^>]*?\bsrc="data:image/svg\+xml;base64,)([A-Za-z0-9+/=]*)'
    r'("[^>]*>\s*<figcaption>\s*<strong>(Figure \d+-\d+)\b)')
TEXT_FIG_RE = re.compile(r'!\[(Figure \d+-\d+)\b[^\]]*\]\(diagrams/([A-Za-z0-9._-]+)\.(?:png|svg)\)')


def step_gallery(ctx):
    svgs = {n: b for n, b in tag_diagrams(ctx).items() if n.endswith(".svg")}
    # Which file is which figure: the figure references in the text at the tag.
    fig_to_svg = {}
    for n, text in ctx.tag_files("spec", recursive=False).items():
        if not n.endswith(".md"):
            continue
        for m in TEXT_FIG_RE.finditer(text.decode("utf-8")):
            fig, svg = m.group(1), m.group(2) + ".svg"
            if fig_to_svg.setdefault(fig, svg) != svg:
                fail(f"{fig} names two files in the text: {fig_to_svg[fig]} and {svg}")
    if sorted(fig_to_svg.values()) != sorted(svgs):
        fail(f"the text's figures {sorted(fig_to_svg.values())} are not the tag's SVGs {sorted(svgs)}")
    path = ctx.docs / "diagram-gallery.html"
    s = path.read_text(encoding="utf-8")
    found = GALLERY_FIG_RE.findall(s)
    total = s.count("data:image/svg+xml;base64,")
    if len(found) != total or total != len(svgs):
        fail(f"the gallery holds {total} embedded SVGs, {len(found)} of them in a numbered figure; "
             f"expected {len(svgs)}")
    used = [fig_to_svg.get(f[3]) for f in found]
    if None in used or sorted(used) != sorted(svgs):
        fail(f"the gallery's figures {[f[3] for f in found]} do not map one to one onto the tag's SVGs")

    def repl(m):
        return m.group(1) + base64.b64encode(svgs[fig_to_svg[m.group(4)]]).decode("ascii") + m.group(3)

    new = GALLERY_FIG_RE.sub(repl, s)
    changed = [f[3] for f, u in zip(found, used) if base64.b64decode(f[1]) != svgs[u]]
    if new != s:
        ctx.put(path, new.encode("utf-8"))
    print(f"gallery: {len(found)} figures matched; re-embedded from {ctx.tag}: "
          f"{', '.join(changed) if changed else 'none (unchanged)'}")


SCHEMA_SOURCES = ["standard/v5.0", "kit/declaration"]  # folders whose JSON Schemas the site serves
SCHEMA_PATH_RE = re.compile(r"schemas/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\.json")


def tag_schemas(ctx):
    """{tag path: (bytes, parsed)} for every JSON file with a $id under SCHEMA_SOURCES at the tag."""
    out = {}
    for folder in SCHEMA_SOURCES:
        if not git(ctx.standard, "ls-tree", ctx.commit, "--", folder + "/").stdout.strip():
            print(f"schemas: no {folder}/ at {ctx.tag}; skipped")
            continue
        for n, b in ctx.tag_files(folder).items():
            if not n.endswith(".json"):
                continue
            d = json.loads(b.decode("utf-8"))
            if isinstance(d, dict) and "$id" in d:
                out[f"{folder}/{n}"] = (b, d)
    if not out:
        fail(f"no JSON Schema with a $id under {', '.join(SCHEMA_SOURCES)} at {ctx.tag}")
    return out


def site_path(url, what):
    """The site path an https://decisionprovenancestandard.org/schemas/... address names."""
    if not url.startswith(SITE_URL + "/"):
        fail(f"{what}: {url} is not an address on {SITE_URL}")
    rel = url[len(SITE_URL) + 1:]
    if not SCHEMA_PATH_RE.fullmatch(rel) or ".." in rel.split("/"):
        fail(f"{what}: {url} is not a plain address under /schemas/")
    return rel


def schema_addresses(ctx):
    """{site path: (bytes, why)}: each schema at its own $id, and each target of a relative $ref
    at the address that reference resolves to (a validator resolves it against the $id)."""
    import posixpath
    import urllib.parse
    schemas = tag_schemas(ctx)
    out = {}

    def add(path, data, why):
        if path in out and out[path][0] != data:
            fail(f"two different files would be served at /{path}: {out[path][1]} and {why}")
        out.setdefault(path, (data, why))

    for src, (b, d) in schemas.items():
        add(site_path(d["$id"], src), b, f"{src} ($id)")

    def refs(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str):
                    yield v
                else:
                    yield from refs(v)
        elif isinstance(node, list):
            for v in node:
                yield from refs(v)

    for src, (b, d) in schemas.items():
        for ref in refs(d):
            target = ref.split("#", 1)[0]
            if not target:
                continue  # a reference inside the same schema
            if urllib.parse.urlsplit(target).scheme:
                if not any(d2["$id"] == target for _, d2 in schemas.values()):
                    fail(f"{src}: $ref {ref} names no schema served from {', '.join(SCHEMA_SOURCES)}")
                continue
            file = posixpath.normpath(posixpath.join(posixpath.dirname(src), target))
            if file not in schemas:
                fail(f"{src}: $ref {ref} points to {file}, which is not a schema at {ctx.tag}")
            url = urllib.parse.urljoin(d["$id"], target)
            add(site_path(url, f"{src} $ref {ref}"), schemas[file][0], f"{file} (as {src} refers to it)")
    return out


def step_schemas(ctx):
    root = ctx.docs / "schemas"
    addresses = schema_addresses(ctx)
    for path, (data, why) in sorted(addresses.items()):
        lf_only(data, why)
        ctx.put(ctx.docs / path, data)
        print(f"schemas: /{path} <- {why}")
    extra = sorted(p.relative_to(ctx.docs).as_posix() for p in root.rglob("*")
                   if p.is_file() and p.relative_to(ctx.docs).as_posix() not in addresses)
    print(f"schemas: {len(addresses)} addresses written under docs/schemas/ from {ctx.tag}")
    if extra:
        print("schemas: warning, docs/schemas/ also holds files not produced from the tag:", ", ".join(extra))


def step_sums(ctx):
    if not ctx.release_in_site:
        fail("sums reads the committed release folder in the site; do not pass --release-dir")
    rel = f"docs/downloads/{ctx.tag}"
    if ctx.sealed():
        fail(f"{rel}/SHA256SUMS.txt is already committed; a published list is never rewritten")
    pending = [l for l in git(ctx.site, "status", "--porcelain", "--untracked-files=all", "--", rel + "/").stdout.splitlines()
               if l[3:] != f"{rel}/SHA256SUMS.txt"]
    if pending:
        fail("commit the release files first; uncommitted:\n" + "\n".join(pending))
    names = sorted(n for n in git(ctx.site, "ls-tree", "-r", "--name-only", "HEAD", "--", rel + "/").stdout.split("\n")
                   if n and n != f"{rel}/SHA256SUMS.txt")
    if not names:
        fail(f"no committed files under {rel}/")
    by_name = {}
    lines = []
    for n in names:
        blob = git(ctx.site, "cat-file", "blob", f"HEAD:{n}", binary=True).stdout
        short = n[len(rel) + 1:]
        by_name[short] = blob
        lines.append(f"{sha256(blob)}  {short}\n")
    for eid, r in ctx.releases:  # the committed Markdown is the released text
        b = by_name.get(r["published_name"])
        if b is None or sha256(b) != r["sha256"] or len(b) != r["bytes"]:
            fail(f"committed {r['published_name']} does not match editions.json ({eid})")
    out = "".join(lines).encode("ascii")
    assert b"\r" not in out
    ctx.put(ctx.site_release / "SHA256SUMS.txt", out)
    print(out.decode("ascii"), end="")
    print(f"sums: {len(lines)} lines from committed bytes at {git(ctx.site, 'rev-parse', 'HEAD').stdout.strip()}")


def step_filldate(ctx):
    date, commit = ctx.a.date, ctx.a.commit
    if not date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        fail("filldate needs --date YYYY-MM-DD")
    if commit and not (len(commit) >= 7 and ctx.commit.startswith(commit)):
        fail(f"--commit {commit} is not the tag's commit {ctx.commit}")
    for f in PLACEHOLDER_FILES:
        p = ctx.site / f
        s = p.read_bytes()
        n = s.count(PLACEHOLDER.encode()) + s.count(b"&lt;RELEASE-DATE&gt;")
        s = s.replace(PLACEHOLDER.encode(), date.encode()).replace(b"&lt;RELEASE-DATE&gt;", date.encode())
        c = s.count(b"&lt;RELEASE-COMMIT&gt;")
        s = s.replace(b"&lt;RELEASE-COMMIT&gt;", ctx.commit.encode())
        if n or c:
            ctx.put(p, s)
        print(f"filldate: {f}: {n} date and {c} commit placeholder(s) replaced")
    left = git(ctx.site, "grep", "-n", "-e", "RELEASE-DATE", "-e", "RELEASE-COMMIT", "--", ".", check=False).stdout
    print("placeholders left:", left or "none")


STEPS = {"joined": [step_joined], "pages": [step_pages], "pdf": [step_pdf], "diagrams": [step_diagrams],
         "downloads": [step_downloads], "reffiles": [step_reffiles], "gallery": [step_gallery],
         "schemas": [step_schemas], "sums": [step_sums], "filldate": [step_filldate],
         "all": [step_pages, step_pdf, step_diagrams, step_downloads, step_reffiles, step_gallery,
                 step_schemas]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the website files for one release from its tag.")
    ap.add_argument("step", choices=list(STEPS))
    ap.add_argument("--tag", required=True, help="the release tag, v<major>.<minor>-rev<n>")
    ap.add_argument("--ref-tag", required=True, help="the reference-files tag; must name the same commit")
    ap.add_argument("--standard", required=True, help="a clean clone of the standard repository, detached at --tag")
    ap.add_argument("--site", required=True, help="the website repository's work tree")
    ap.add_argument("--work", required=True, help="a scratch folder outside both repositories")
    ap.add_argument("--release-dir", help="write the release folder here instead of docs/downloads/<tag>/ "
                                          "(a folder outside the site, for a rehearsal)")
    ap.add_argument("--zip-date", help="downloads: the release date, YYYY-MM-DD")
    ap.add_argument("--date", help="filldate: the release date, YYYY-MM-DD")
    ap.add_argument("--commit", help="filldate: optional check; must be the tag's commit")
    a = ap.parse_args(argv)
    ctx = Ctx(a)
    before = downloads_snapshot(ctx)
    for step in STEPS[a.step]:
        ctx.step = step.__name__[len("step_"):]
        step(ctx)
        after = downloads_snapshot(ctx)
        if after != before:
            changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
            raise SystemExit("FAILED: files under docs/downloads/ outside this release's folder changed: "
                             + ", ".join(changed))
    print(f"done: {a.step} for {a.tag} (commit {ctx.commit}); docs/downloads/ outside the release folder unchanged")


if __name__ == "__main__":
    main()
