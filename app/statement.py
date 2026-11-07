"""Fetch one LeetCode problem statement and turn its HTML into plain text.

LeetCode has no official API. This asks the GraphQL endpoint its own site uses, one problem at a time, when a solve
opens without a statement. Premium problems need a login, so they fail here and he pastes them instead.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import urllib.error
import urllib.request
from html.parser import HTMLParser

ENDPOINT = "https://leetcode.com/graphql"
QUERY = "query q($titleSlug: String!) { question(titleSlug: $titleSlug) { title content isPaidOnly } }"


# Root certificates to fall back on: macOS's system bundle, then the usual Linux places.
CA_FILES = ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt")


def ssl_context() -> ssl.SSLContext:
    """A verifying context with root certificates, even on a Python that ships none.

    python.org's macOS installer leaves Python without any until "Install Certificates.command" is run, and then every
    HTTPS request fails with CERTIFICATE_VERIFY_FAILED. Use certifi if it's installed, else the system's bundle.
    """
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats()["x509_ca"]:
        return ctx
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
        return ctx
    except (ImportError, OSError):
        pass
    for path in CA_FILES:
        if os.path.isfile(path):
            ctx.load_verify_locations(path)
            break
    return ctx


class StatementError(Exception):
    """Why the statement couldn't be fetched, in a few words for the learner."""


def problem_url(slug: str) -> str:
    return f"https://leetcode.com/problems/{slug}/"


def fetch(slug: str, opener=urllib.request.urlopen, timeout: float = 10) -> tuple[str, str]:
    """(title, content HTML) for one free problem, or StatementError."""
    req = urllib.request.Request(
        ENDPOINT, method="POST",
        data=json.dumps({"query": QUERY, "variables": {"titleSlug": slug}}).encode(),
        headers={"Content-Type": "application/json", "Referer": problem_url(slug),
                 "User-Agent": "dsa-coach-study-app"})
    try:
        with opener(req, timeout=timeout, context=ssl_context()) as res:
            body = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise StatementError(f"LeetCode answered HTTP {e.code}") from None
    except (urllib.error.URLError, OSError) as e:
        if isinstance(getattr(e, "reason", e), ssl.SSLCertVerificationError):
            raise StatementError("this Python couldn't verify LeetCode's certificate. On python.org's macOS Python, "
                                 "run its Install Certificates.command once") from None
        raise StatementError(f"no connection to LeetCode ({getattr(e, 'reason', e)})") from None
    except ValueError:
        raise StatementError("LeetCode's answer wasn't the expected data") from None
    q = ((body or {}).get("data") or {}).get("question") if isinstance(body, dict) else None
    if not q:
        raise StatementError(f"LeetCode has no problem called {slug!r}")
    if q.get("isPaidOnly") and not q.get("content"):
        raise StatementError("it's a premium problem, which needs your LeetCode login")
    if not q.get("content"):
        raise StatementError("LeetCode sent an empty statement")
    return q.get("title") or slug, q["content"]


class _Text(HTMLParser):
    BLOCKS = {"p", "div", "pre", "ul", "ol", "table", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.pre = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKS:
            self.out.append("\n\n")
        if tag == "pre":
            self.pre += 1
        elif tag == "li":
            self.out.append("\n- ")
        elif tag == "br":
            self.out.append("\n")
        elif tag == "sup":
            self.out.append("^")
        elif tag == "img":
            alt = dict(attrs).get("alt")
            self.out.append(f"[image{': ' + alt if alt else ''}]")

    def handle_endtag(self, tag):
        if tag == "pre":
            self.pre -= 1
        if tag in self.BLOCKS:
            self.out.append("\n\n")

    def handle_data(self, data):
        data = data.replace("\xa0", " ")
        self.out.append(data if self.pre else re.sub(r"\s+", " ", data))


def to_text(html: str) -> str:
    p = _Text()
    p.feed(html)
    p.close()
    lines = [line.rstrip() for line in "".join(p.out).split("\n")]
    lines = [line.lstrip() if line.lstrip().startswith("- ") else line for line in lines]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def document(slug: str, title: str, html: str) -> str:
    """What goes into problems/<slug>/problem.md."""
    return f"# {title}\n\n{problem_url(slug)}\n\n{to_text(html)}\n"
