import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shuanglai_corpus.classify import classify_material, classify_topics, mark_duplicates, score_relevance


class ClassifyTests(unittest.TestCase):
    def test_direct_relevance_without_required_integration_keyword(self):
        result = score_relevance("莱西莱阳交通合作方案", "两地将共建道路并共享公共服务。")
        self.assertEqual(result["level"], "A")
        self.assertGreaterEqual(result["score"], 55)

    def test_background_relevance(self):
        result = score_relevance("青岛都市圈发展规划", "加强烟台方向交通衔接，支持莱阳融入青岛都市圈。")
        self.assertIn(result["level"], ("B", "C"))

    def test_qingdao_yantai_pair_is_retained_as_candidate(self):
        result = score_relevance("区域发展动态", "青岛与烟台发布年度经济数据。")
        self.assertEqual(result["level"], "C")
        self.assertIn("宽口径", result["reason"])

    def test_strategic_region_term_is_retained_without_city_names(self):
        for term in ("青岛都市圈", "胶东经济圈", "山东半岛城市群"):
            with self.subTest(term=term):
                result = score_relevance(f"{term}建设进展", "推进区域协调发展。")
                self.assertEqual(result["level"], "C")

    def test_irrelevant_integration_is_excluded(self):
        result = score_relevance("化工一体化项目公示", "某企业推进化工一体化建设。")
        self.assertEqual(result["level"], "D")
        self.assertEqual(result["score"], 0)

    def test_topics_are_multilabel(self):
        topics = classify_topics("推进铁路交通互联互通和跨域通办，强化生态环境治理")
        self.assertIn("交通互联", topics)
        self.assertIn("政务服务跨域通办", topics)
        self.assertIn("生态环境", topics)

    def test_policy_and_evidence(self):
        self.assertEqual(classify_material("关于区域合作的实施方案", "正文")[0], "policy")
        self.assertEqual(classify_material("重点项目进展", "官方新闻")[0], "evidence")

    def test_deduplicate_by_title_and_date(self):
        records = [
            {"record_id":"a", "source_page_url":"u1", "content_sha256":"x", "title":"政策", "publication_date":"2022-01-01", "full_text":"正文"},
            {"record_id":"b", "source_page_url":"u2", "content_sha256":"y", "title":"政策", "publication_date":"2022-01-01", "full_text":"转载正文"},
        ]
        self.assertEqual(mark_duplicates(records)[1]["duplicate_of"], "a")


if __name__ == "__main__": unittest.main()
