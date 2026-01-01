import unittest

from crawl import (
    extract_page_data,
    get_first_paragraph_from_html,
    get_h1_from_html,
    get_images_from_html,
    get_urls_from_html,
    normalize_url,
)


class TestCrawl(unittest.TestCase):
    def test_normalize_url_basic(self):
        self.assertEqual(normalize_url("https://blog.boot.dev/path"), "blog.boot.dev/path")

    def test_get_h1_from_html_basic(self):
        self.assertEqual(get_h1_from_html("<h1>Hello</h1>"), "Hello")

    def test_get_first_paragraph_from_html_main_priority(self):
        html = "<main><p>Inside</p></main><p>Outside</p>"
        self.assertEqual(get_first_paragraph_from_html(html), "Inside")

    def test_get_urls_from_html_relative(self):
        self.assertEqual(
            get_urls_from_html('<a href="/a">A</a>', "https://example.com"),
            ["https://example.com/a"],
        )

    def test_get_images_from_html_relative(self):
        self.assertEqual(
            get_images_from_html('<img src="/x.png">', "https://example.com"),
            ["https://example.com/x.png"],
        )

    def test_extract_page_data(self):
        html = '<h1>T</h1><p>P</p><a href="/a">A</a><img src="/i.png">'
        data = extract_page_data(html, "https://example.com")
        self.assertEqual(data["h1"], "T")
        self.assertEqual(data["first_paragraph"], "P")
        self.assertEqual(data["outgoing_links"], ["https://example.com/a"])
        self.assertEqual(data["image_urls"], ["https://example.com/i.png"])


if __name__ == "__main__":
    unittest.main()
