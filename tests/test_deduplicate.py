import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from deduplicate import mark_duplicates


class DeduplicateTests(unittest.TestCase):
    def test_marks_binary_duplicate(self):
        rows = [
            {"record_id": "a", "sha256": "same", "text_path": "", "status": "extracted", "duplicate_of": ""},
            {"record_id": "b", "sha256": "same", "text_path": "", "status": "extracted", "duplicate_of": ""},
        ]
        result = mark_duplicates(rows)
        self.assertEqual(result[1]["duplicate_of"], "a")
        self.assertEqual(result[1]["status"], "duplicate")

    def test_marks_normalized_text_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "a.txt"
            second = Path(directory) / "b.txt"
            first.write_text("双莱—一体化", encoding="utf-8")
            second.write_text("双莱一体化", encoding="utf-8")
            rows = [
                {"record_id": "a", "sha256": "", "text_path": str(first), "status": "extracted", "duplicate_of": ""},
                {"record_id": "b", "sha256": "", "text_path": str(second), "status": "extracted", "duplicate_of": ""},
            ]
            self.assertEqual(mark_duplicates(rows)[1]["duplicate_of"], "a")


if __name__ == "__main__":
    unittest.main()
