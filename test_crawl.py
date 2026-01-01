import unittest
from unittest.mock import patch

from crawl import (
    normalize_url,
    get_h1_from_html,
    get_first_paragraph_from_html,
    get_urls_from_html,
    get_images_from_html,
    extract_page_data,
    crawl_page,
)


class TestCrawl(unittest.TestCase):
    # --- normalize_url ---
    def test_normalize_url_basic(self):
        self.assertEqual(normalize_url("https://blog.boot.dev/path"), "blog.boot.dev/path")

    def test_normalize_url_scheme_ignored_and_trailing_slash_removed(self):
        self.assertEqual(normalize_url("https://blog.boot.dev/path/"), "blog.boot.dev/path")
        self.assertEqual(normalize_url("http://blog.boot.dev/path/"), "blog.boot.dev/path")
        self.assertEqual(normalize_url("http://blog.boot.dev/path"), "blog.boot.dev/path")

    def test_normalize_url_root_path(self):
        self.assertEqual(normalize_url("https://blog.boot.dev/"), "blog.boot.dev")
        self.assertEqual(normalize_url("http://blog.boot.dev"), "blog.boot.dev")

    # --- get_h1_from_html ---
    def test_get_h1_from_html_basic(self):
        html = "<html><body><h1>Test Title</h1></body></html>"
        self.assertEqual(get_h1_from_html(html), "Test Title")

    def test_get_h1_from_html_missing_returns_empty(self):
        html = "<html><body><p>No title here</p></body></html>"
        self.assertEqual(get_h1_from_html(html), "")

    def test_get_h1_from_html_nested_and_whitespace(self):
        html = "<html><body><h1>  Hello <span>World</span>  </h1></body></html>"
        self.assertEqual(get_h1_from_html(html), "Hello World")

    # --- get_first_paragraph_from_html ---
    def test_get_first_paragraph_from_html_main_priority(self):
        html = """<html><body>
            <p>Outside paragraph.</p>
            <main>
                <p>Main paragraph.</p>
            </main>
        </body></html>"""
        self.assertEqual(get_first_paragraph_from_html(html), "Main paragraph.")

    def test_get_first_paragraph_from_html_fallback_to_first_p(self):
        html = "<html><body><p>First.</p><p>Second.</p></body></html>"
        self.assertEqual(get_first_paragraph_from_html(html), "First.")

    def test_get_first_paragraph_from_html_no_p_returns_empty(self):
        html = "<html><body><main><div>No paragraphs</div></main></body></html>"
        self.assertEqual(get_first_paragraph_from_html(html), "")

    # --- get_urls_from_html ---
    def test_get_urls_from_html_absolute(self):
        base_url = "https://blog.boot.dev"
        html = '<html><body><a href="https://blog.boot.dev"><span>Boot.dev</span></a></body></html>'
        self.assertEqual(get_urls_from_html(html, base_url), ["https://blog.boot.dev"])

    def test_get_urls_from_html_relative_to_absolute(self):
        base_url = "https://blog.boot.dev"
        html = '<html><body><a href="/path/one">One</a></body></html>'
        self.assertEqual(get_urls_from_html(html, base_url), ["https://blog.boot.dev/path/one"])

    def test_get_urls_from_html_finds_all_anchors_and_ignores_missing_href(self):
        base_url = "https://blog.boot.dev"
        html = """<html><body>
            <a href="/a">A</a>
            <a>No href</a>
            <div><a href="https://example.com/b">B</a></div>
        </body></html>"""
        self.assertEqual(get_urls_from_html(html, base_url), ["https://blog.boot.dev/a", "https://example.com/b"])

    # --- get_images_from_html ---
    def test_get_images_from_html_relative(self):
        base_url = "https://blog.boot.dev"
        html = '<html><body><img src="/logo.png" alt="Logo"></body></html>'
        self.assertEqual(get_images_from_html(html, base_url), ["https://blog.boot.dev/logo.png"])

    def test_get_images_from_html_absolute(self):
        base_url = "https://blog.boot.dev"
        html = '<html><body><img src="https://cdn.example.com/x.png"></body></html>'
        self.assertEqual(get_images_from_html(html, base_url), ["https://cdn.example.com/x.png"])

    def test_get_images_from_html_ignores_missing_src_and_finds_all(self):
        base_url = "https://blog.boot.dev"
        html = """<html><body>
            <img alt="no src">
            <img src="/a.png">
            <div><img src="b.png"></div>
        </body></html>"""
        self.assertEqual(
            get_images_from_html(html, base_url),
            ["https://blog.boot.dev/a.png", "https://blog.boot.dev/b.png"],
        )

    # --- extract_page_data ---
    def test_extract_page_data_basic(self):
        input_url = "https://blog.boot.dev"
        input_body = '''<html><body>
            <h1>Test Title</h1>
            <p>This is the first paragraph.</p>
            <a href="/link1">Link 1</a>
            <img src="/image1.jpg" alt="Image 1">
        </body></html>'''
        actual = extract_page_data(input_body, input_url)
        expected = {
            "url": "https://blog.boot.dev",
            "h1": "Test Title",
            "first_paragraph": "This is the first paragraph.",
            "outgoing_links": ["https://blog.boot.dev/link1"],
            "image_urls": ["https://blog.boot.dev/image1.jpg"],
        }
        self.assertEqual(actual, expected)

    def test_extract_page_data_missing_fields_returns_empties(self):
        input_url = "https://example.com"
        input_body = "<html><body><div>No h1, no p, no links, no images</div></body></html>"
        actual = extract_page_data(input_body, input_url)
        expected = {
            "url": "https://example.com",
            "h1": "",
            "first_paragraph": "",
            "outgoing_links": [],
            "image_urls": [],
        }
        self.assertEqual(actual, expected)

    # --- crawl_page (3+ tests) ---
    @patch("crawl.get_html")
    def test_crawl_page_crawls_same_domain_only(self, mock_get_html):
        base = "https://example.com"
        html_map = {
            "https://example.com": '<a href="/a">A</a><a href="https://other.com/x">X</a>',
            "https://example.com/a": '<a href="/b">B</a>',
            "https://example.com/b": "<p>Done</p>",
        }

        def side_effect(url: str) -> str:
            return html_map[url]

        mock_get_html.side_effect = side_effect

        data = crawl_page(base)

        self.assertIn("example.com", data)
        self.assertIn("example.com/a", data)
        self.assertIn("example.com/b", data)
        self.assertNotIn("other.com/x", data)

    @patch("crawl.get_html")
    def test_crawl_page_does_not_crawl_same_page_twice(self, mock_get_html):
        base = "https://example.com"
        html_map = {
            "https://example.com": '<a href="/a">A</a><a href="/a">A2</a>',
            "https://example.com/a": '<a href="/">Home</a>',
        }

        def side_effect(url: str) -> str:
            return html_map[url]

        mock_get_html.side_effect = side_effect

        data = crawl_page(base)
        self.assertEqual(mock_get_html.call_count, 2)
        self.assertEqual(set(data.keys()), {"example.com", "example.com/a"})

    @patch("crawl.get_html")
    def test_crawl_page_skips_other_domains_without_fetching(self, mock_get_html):
        base = "https://example.com"
        crawl_page(base, "https://other.com/x", {})
        mock_get_html.assert_not_called()


if __name__ == "__main__":
    unittest.main()
