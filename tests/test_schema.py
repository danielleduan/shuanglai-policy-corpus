import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shuanglai_corpus.schema import FIELDS, empty_record, validate_record, write_csv


class SchemaTests(unittest.TestCase):
    def test_required_fields_complete(self):
        self.assertEqual(validate_record(empty_record()), [])
        for field in ("record_id", "local_raw_path", "text_path", "relevance_level", "relevance_reason", "parsing_status", "review_status"):
            self.assertIn(field, FIELDS)

    def test_csv_field_completeness(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.csv"
            write_csv(path, [empty_record(record_id="one")])
            with path.open(encoding="utf-8-sig", newline="") as handle:
                self.assertEqual(next(csv.reader(handle)), FIELDS)


if __name__ == "__main__": unittest.main()
