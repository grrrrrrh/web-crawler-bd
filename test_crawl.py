import unittest

from crawl import (
    normalize_url,
    get_h1_from_html,
    get_first_paragraph_from_html,
    get_urls_from_html,
    get_images_from_html,
    extract_page_data,
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
        self.assertEqual(get_images_from_html(html, base_url), ["https://blog.boot.dev/a.png", "https://blog.boot.dev/b.png"])

    # --- extract_page_data (3+ tests) ---
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

    def test_extract_page_data_prefers_main_paragraph_and_collects_all(self):
        input_url = "https://example.com/base"
        input_body = """<html><body>
            <h1>Title</h1>
            <p>Outside P.</p>
            <main>
                <p>Main P.</p>
                <a href="/a">A</a>
                <a href="https://other.com/b">B</a>
                <img src="img.png">
            </main>
            <a href="/c">C</a>
            <img src="/d.jpg">
        </body></html>"""
        actual = extract_page_data(input_body, input_url)
        expected = {
            "url": "https://example.com/base",
            "h1": "Title",
            "first_paragraph": "Main P.",
            "outgoing_links": [
                "https://example.com/a",
                "https://other.com/b",
                "https://example.com/c",
            ],
            "image_urls": [
                "https://example.com/img.png",
                "https://example.com/d.jpg",
            ],
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


if __name__ == "__main__":
    unittest.main()
