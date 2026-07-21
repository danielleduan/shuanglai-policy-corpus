import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from common import canonicalize_url, is_allowed_url, matches_keywords, normalized_text_fingerprint, safe_filename


class CommonTests(unittest.TestCase):
    def test_canonicalize_relative_url_and_fragment(self):
        self.assertEqual(canonicalize_url("../policy/a.html#top", "https://example.gov.cn/news/list/"), "https://example.gov.cn/news/policy/a.html")

    def test_domain_boundary(self):
        self.assertTrue(is_allowed_url("https://sub.laixi.gov.cn/a", ["laixi.gov.cn"]))
        self.assertFalse(is_allowed_url("https://laixi.gov.cn.evil.example/a", ["laixi.gov.cn"]))

    def test_keyword_matching_ignores_whitespace(self):
        self.assertEqual(matches_keywords("推进 双莱 一体化 建设", ["双莱一体化", "青岛都市圈"]), ["双莱一体化"])

    def test_safe_filename_is_stable(self):
        self.assertEqual(safe_filename("https://example.gov.cn/a/b.pdf", ".pdf"), safe_filename("https://example.gov.cn/a/b.pdf", ".pdf"))

    def test_normalized_fingerprint(self):
        self.assertEqual(normalized_text_fingerprint("莱西—莱阳\n一体化"), normalized_text_fingerprint("莱西莱阳一体化"))


if __name__ == "__main__":
    unittest.main()
