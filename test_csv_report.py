import csv
import os
import tempfile
import unittest

from csv_report import write_csv_report


class TestCSVReport(unittest.TestCase):
    def test_write_csv_report_creates_file_and_headers(self):
        page_data = {
            "example.com": {
                "url": "https://example.com",
                "h1": "Title",
                "first_paragraph": "Hello",
                "outgoing_links": ["https://example.com/a", "https://example.com/b"],
                "image_urls": ["https://example.com/x.png"],
            }
        }

        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "report.csv")
            write_csv_report(page_data, filename=out)

            with open(out, "r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))

            self.assertEqual(
                rows[0].keys(),
                {"page_url", "h1", "first_paragraph", "outgoing_link_urls", "image_urls"},
            )
            self.assertEqual(rows[0]["page_url"], "https://example.com")
            self.assertEqual(rows[0]["h1"], "Title")
            self.assertEqual(rows[0]["first_paragraph"], "Hello")
            self.assertEqual(rows[0]["outgoing_link_urls"], "https://example.com/a;https://example.com/b")
            self.assertEqual(rows[0]["image_urls"], "https://example.com/x.png")


if __name__ == "__main__":
    unittest.main()
