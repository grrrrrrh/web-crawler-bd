import unittest

from crawl import (
    normalize_url,
    get_h1_from_html,
    get_first_paragraph_from_html,
    get_urls_from_html,
    get_images_from_html,
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

    # --- get_urls_from_html (3+ tests) ---
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

    # --- get_images_from_html (3+ tests) ---
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


if __name__ == "__main__":
    unittest.main()
