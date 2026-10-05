# SPDX-License-Identifier: Apache-2.0
"""Check that the website serves the release's JSON Schemas where a validator looks for them.

Run after the website is published (or against a local copy served over http):

  python tools/check_schemas_live.py --standard <clone with the tag> --tag v1.3-rev11
  python tools/check_schemas_live.py --standard <clone> --tag v1.3-rev11 --base http://127.0.0.1:8000

Three checks, all read-only:
  1. every JSON Schema with a $id under standard/v5.0/ and kit/declaration/ at the tag answers
     200 at the address its $id names, with the tag's bytes;
  2. the addresses given with --also (default: the attestation schema's second address,
     /schemas/mode-drift/layer-4-attestation.schema.json) answer 200 with the bytes of the schema
     whose file name they end with;
  3. known-defect case C13 (tests/known-defects/cases.json at the tag) validates, with Draft 2020-12,
     against the decision-record schema fetched from its $id address, every referenced schema being
     fetched over http as a standard validator would. Nothing is preloaded.

Exit 0 only if every check passes. This script does not change the known-defect files: KD-01 stays
"open" there, because the offline runner cannot see the website.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SITE_URL = "https://decisionprovenancestandard.org"
SOURCES = ["standard/v5.0", "kit/declaration"]
DEFAULT_ALSO = ["/schemas/mode-drift/layer-4-attestation.schema.json"]


def git_show(repo, rev, path):
    return subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True, check=True).stdout


def tag_schemas(repo, tag):
    out = {}
    for folder in SOURCES:
        names = subprocess.run(["git", "-C", repo, "ls-tree", "-r", "--name-only", tag, "--", folder + "/"],
                               capture_output=True, text=True, check=True).stdout.split()
        for n in names:
            if n.endswith(".json"):
                b = git_show(repo, tag, n)
                d = json.loads(b.decode("utf-8"))
                if isinstance(d, dict) and "$id" in d:
                    out[n] = (b, d)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--standard", required=True, help="a clone of the standard repository that has the tag")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--base", default=SITE_URL, help="where to fetch from (default: the public site)")
    ap.add_argument("--also", nargs="*", default=DEFAULT_ALSO, help="further addresses to check")
    a = ap.parse_args()
    base = a.base.rstrip("/")
    fetched = []

    def get(url):
        """(status, bytes) for an address on the site, fetched from --base."""
        if url.startswith(SITE_URL):
            url = base + url[len(SITE_URL):]
        fetched.append(url)
        req = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "User-Agent": "dps-schema-check"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, b""

    schemas = tag_schemas(a.standard, a.tag)
    failures = []

    def check(ok, label, detail=""):
        print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f": {detail}" if detail else ""))
        if not ok:
            failures.append(label)

    print(f"tag {a.tag}; fetching from {base}; {len(schemas)} schemas with a $id")
    for src, (b, d) in sorted(schemas.items()):
        status, got = get(d["$id"])
        check(status == 200 and got == b, f"{d['$id']} serves {src}",
              f"HTTP {status}, sha256 {hashlib.sha256(got).hexdigest()[:12]} vs tag {hashlib.sha256(b).hexdigest()[:12]}")
    for path in a.also:
        name = path.rsplit("/", 1)[-1]
        match = [(src, b) for src, (b, _) in schemas.items() if src.rsplit("/", 1)[-1] == name]
        if len(match) != 1:
            check(False, f"{path}: one schema at the tag named {name}", f"{len(match)} found")
            continue
        src, b = match[0]
        status, got = get(SITE_URL + path)
        check(status == 200 and got == b, f"{SITE_URL}{path} serves {src}",
              f"HTTP {status}, sha256 {hashlib.sha256(got).hexdigest()[:12]} vs tag {hashlib.sha256(b).hexdigest()[:12]}")

    # C13: validate with remote retrieval only.
    cases = json.loads(git_show(a.standard, a.tag, "tests/known-defects/cases.json").decode("utf-8"))
    c13 = [c for c in cases["cases"] if c["id"] == "C13"]
    if len(c13) != 1:
        check(False, "case C13 found once in cases.json at the tag", f"{len(c13)} found")
    else:
        c = c13[0]
        root_id = schemas[c["schema"]][1]["$id"]
        retrieved = []

        def retrieve(uri):
            status, body = get(uri)
            retrieved.append(f"{uri} -> {status}")
            if status != 200:
                raise LookupError(f"HTTP {status} for {uri}")
            return Resource.from_contents(json.loads(body.decode("utf-8")))

        status, body = get(root_id)
        if status != 200:
            check(False, f"C13: fetch {root_id}", f"HTTP {status}")
        else:
            v = Draft202012Validator(json.loads(body.decode("utf-8")), registry=Registry(retrieve=retrieve),
                                     format_checker=FormatChecker())
            try:
                errs = [e.message[:120] for e in v.iter_errors(c["instance"])]
                outcome = "pass" if not errs else "fail"
                detail = "; ".join(errs[:2])
            except Exception as exc:  # an unresolvable reference lands here
                outcome, detail = "fail", f"{type(exc).__name__}: {str(exc)[:160]}"
            check(outcome == c["expected"] and outcome == "pass",
                  f"C13 ({c['description']}) validates against {root_id} with remote retrieval",
                  f"got {outcome}" + (f" ({detail})" if detail else "") + "; retrieved: " + (", ".join(retrieved) or "nothing"))

    print(f"\n{len(fetched)} requests. " + ("PASS: every address answers with the tag's bytes, and C13 validates."
                                          if not failures else f"FAIL: {len(failures)} check(s) failed."))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
