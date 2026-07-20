import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shuanglai_corpus.parsing import extract_document_number, extract_html, extract_issuing_authority, parse_chinese_date


class ParsingTests(unittest.TestCase):
    def test_chinese_date(self):
        self.assertEqual(parse_chinese_date("发布日期：2022年7月4日"), "2022-07-04")

    def test_document_number(self):
        self.assertEqual(extract_document_number("烟政发〔2022〕18号"), "烟政发〔2022〕18号")

    def test_issuing_authority(self):
        self.assertEqual(extract_issuing_authority("发布机构：烟台市发展和改革委员会\n正文"), "烟台市发展和改革委员会")

    def test_html_body_and_attachment(self):
        html = """<html><head><title>fallback</title></head><body><nav>menu</nav><article><h1>政策标题</h1><p>政策正文</p><a href='/files/a.pdf'>附件</a></article></body></html>"""
        title, text, attachments = extract_html(html, "https://www.example.gov.cn/page/")
        self.assertEqual(title, "政策标题")
        self.assertIn("政策正文", text)
        self.assertEqual(attachments[0]["url"], "https://www.example.gov.cn/files/a.pdf")


if __name__ == "__main__": unittest.main()
