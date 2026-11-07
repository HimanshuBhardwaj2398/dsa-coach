"""Tests for app/statement.py. They never touch the network: fetch() gets a fake opener."""
import io
import json
import os
import ssl
import sys
import unittest
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "app"))
import statement  # noqa: E402

# Shaped like LeetCode's `content` field.
HTML = (
    "<p>Koko loves to eat bananas. There are <code>n</code> piles of bananas, the <code>i<sup>th</sup></code> "
    "pile has <code>piles[i]</code> bananas.</p>\n\n"
    "<p>Return <em>the minimum integer</em> <code>k</code> such that she can eat all the bananas within "
    "<code>h</code> hours.</p>\n\n<p>&nbsp;</p>\n"
    "<p><strong class=\"example\">Example 1:</strong></p>\n\n"
    "<pre>\n<strong>Input:</strong> piles = [3,6,7,11], h = 8\n<strong>Output:</strong> 4\n</pre>\n\n"
    "<p><strong>Constraints:</strong></p>\n\n<ul>\n"
    "\t<li><code>1 &lt;= piles.length &lt;= 10<sup>4</sup></code></li>\n"
    "\t<li><code>piles.length &lt;= h &lt;= 10<sup>9</sup></code></li>\n</ul>\n"
)


def opener_returning(payload, seen=None):
    def opener(req, timeout=None, context=None):
        if seen is not None:
            seen.append((req, timeout))
        return io.BytesIO(payload if isinstance(payload, bytes) else json.dumps(payload).encode())
    return opener


class SSLContextTest(unittest.TestCase):
    def test_a_python_without_root_certificates_still_gets_some(self):
        """python.org's macOS Python ships with none until Install Certificates.command runs: the fetch then failed
        with CERTIFICATE_VERIFY_FAILED. Pointing OpenSSL at nothing reproduces that Python."""
        import subprocess
        env = dict(os.environ, SSL_CERT_FILE="/nonexistent/cert.pem", SSL_CERT_DIR="/nonexistent")
        code = ("import ssl, sys; sys.path.insert(0, %r); import statement; "
                "print(ssl.create_default_context().cert_store_stats()['x509_ca'], "
                "statement.ssl_context().cert_store_stats()['x509_ca'])" % str(REPO / "app"))
        out = subprocess.run([sys.executable, "-I", "-c", code], env=env, capture_output=True, text=True, timeout=30)
        default, ours = map(int, out.stdout.split())
        if default:  # Apple's /usr/bin/python3 (LibreSSL) loads the system bundle whatever the environment says
            self.skipTest("this Python's TLS library can't be left without certificates")
        self.assertGreater(ours, 0)

    def test_fetch_passes_a_verifying_context(self):
        seen = []
        def opener(req, timeout=None, context=None):
            seen.append(context)
            return io.BytesIO(json.dumps({"data": {"question": {"title": "T", "content": "<p>x</p>"}}}).encode())
        statement.fetch("two-sum", opener=opener)
        self.assertEqual(seen[0].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(seen[0].check_hostname)


class ToTextTest(unittest.TestCase):
    def test_paragraphs_examples_and_constraints_read_as_text(self):
        text = statement.to_text(HTML)
        self.assertIn("Koko loves to eat bananas. There are n piles of bananas, the i^th pile has piles[i] bananas.",
                      text)
        self.assertIn("Example 1:\n\nInput: piles = [3,6,7,11], h = 8\nOutput: 4", text)
        self.assertIn("- 1 <= piles.length <= 10^4\n- piles.length <= h <= 10^9", text)
        self.assertNotIn("<", text.replace("<=", ""))
        self.assertNotIn("\n\n\n", text)
        self.assertEqual(text, text.strip())


class FetchTest(unittest.TestCase):
    def test_returns_title_and_html_and_sends_one_post_to_leetcode(self):
        seen = []
        opener = opener_returning({"data": {"question": {"title": "Koko Eating Bananas", "content": HTML,
                                                          "isPaidOnly": False}}}, seen)
        self.assertEqual(statement.fetch("koko-eating-bananas", opener=opener), ("Koko Eating Bananas", HTML))
        (req, timeout), = seen
        self.assertEqual(req.full_url, "https://leetcode.com/graphql")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(json.loads(req.data)["variables"], {"titleSlug": "koko-eating-bananas"})
        self.assertEqual(req.get_header("Referer"), "https://leetcode.com/problems/koko-eating-bananas/")
        self.assertTrue(timeout)

    def test_failures_raise_statement_error_with_a_reason(self):
        cases = {
            "premium": opener_returning({"data": {"question": {"title": "X", "content": None, "isPaidOnly": True}}}),
            "no such problem": opener_returning({"data": {"question": None}}),
            "empty": opener_returning({"data": {"question": {"title": "X", "content": "", "isPaidOnly": False}}}),
            "not json": opener_returning(b"<html>blocked</html>"),
        }

        def offline(req, timeout=None, context=None):
            raise urllib.error.URLError("nodename nor servname provided")
        cases["offline"] = offline
        for name, opener in cases.items():
            with self.subTest(name), self.assertRaises(statement.StatementError) as cm:
                statement.fetch("some-problem", opener=opener)
            self.assertTrue(str(cm.exception))
        with self.assertRaisesRegex(statement.StatementError, "premium"):
            statement.fetch("x", opener=cases["premium"])

    def test_document_has_title_link_and_text(self):
        doc = statement.document("koko-eating-bananas", "Koko Eating Bananas", HTML)
        self.assertTrue(doc.startswith("# Koko Eating Bananas\n\nhttps://leetcode.com/problems/koko-eating-bananas/\n\n"))
        self.assertIn("Output: 4", doc)
        self.assertTrue(doc.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
