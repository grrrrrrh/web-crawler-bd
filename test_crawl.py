import unittest

from crawl import (
    normalize_url,
    get_h1_from_html,
    get_first_paragraph_from_html,
)


class TestCrawl(unittest.TestCase):
    # --- normalize_url tests (existing) ---
    def test_normalize_url_basic(self):
        self.assertEqual(normalize_url("https://blog.boot.dev/path"), "blog.boot.dev/path")

    def test_normalize_url_scheme_ignored_and_trailing_slash_removed(self):
        self.assertEqual(normalize_url("https://blog.boot.dev/path/"), "blog.boot.dev/path")
        self.assertEqual(normalize_url("http://blog.boot.dev/path/"), "blog.boot.dev/path")
        self.assertEqual(normalize_url("http://blog.boot.dev/path"), "blog.boot.dev/path")

    def test_normalize_url_root_path(self):
        self.assertEqual(normalize_url("https://blog.boot.dev/"), "blog.boot.dev")
        self.assertEqual(normalize_url("http://blog.boot.dev"), "blog.boot.dev")

    def test_normalize_url_hostname_lowercased(self):
        self.assertEqual(normalize_url("https://EXAMPLE.com/Path"), "example.com/Path")

    def test_normalize_url_query_preserved(self):
        self.assertEqual(normalize_url("https://example.com/path?x=1"), "example.com/path?x=1")

    def test_normalize_url_fragment_removed(self):
        self.assertEqual(normalize_url("https://example.com/path#section"), "example.com/path")

    def test_normalize_url_default_ports_stripped(self):
        self.assertEqual(normalize_url("http://example.com:80/path"), "example.com/path")
        self.assertEqual(normalize_url("https://example.com:443/path"), "example.com/path")

    def test_normalize_url_non_default_port_kept(self):
        self.assertEqual(normalize_url("https://example.com:8443/path"), "example.com:8443/path")

    def test_normalize_url_schemeless_input(self):
        self.assertEqual(normalize_url("blog.boot.dev/path/"), "blog.boot.dev/path")

    # --- get_h1_from_html tests (>= 3) ---
    def test_get_h1_from_html_basic(self):
        input_body = "<html><body><h1>Test Title</h1></body></html>"
        self.assertEqual(get_h1_from_html(input_body), "Test Title")

    def test_get_h1_from_html_missing_returns_empty(self):
        input_body = "<html><body><p>No title here</p></body></html>"
        self.assertEqual(get_h1_from_html(input_body), "")

    def test_get_h1_from_html_nested_and_whitespace(self):
        input_body = "<html><body><h1>  Hello <span>World</span>  </h1></body></html>"
        self.assertEqual(get_h1_from_html(input_body), "Hello World")

    # --- get_first_paragraph_from_html tests (>= 3) ---
    def test_get_first_paragraph_from_html_main_priority(self):
        input_body = """<html><body>
            <p>Outside paragraph.</p>
            <main>
                <p>Main paragraph.</p>
            </main>
        </body></html>"""
        self.assertEqual(get_first_paragraph_from_html(input_body), "Main paragraph.")

    def test_get_first_paragraph_from_html_fallback_to_first_p(self):
        input_body = "<html><body><p>First.</p><p>Second.</p></body></html>"
        self.assertEqual(get_first_paragraph_from_html(input_body), "First.")

    def test_get_first_paragraph_from_html_no_p_returns_empty(self):
        input_body = "<html><body><main><div>No paragraphs</div></main></body></html>"
        self.assertEqual(get_first_paragraph_from_html(input_body), "")

    def test_get_first_paragraph_from_html_main_without_p_falls_back(self):
        input_body = """<html><body>
            <main><div>Nothing here</div></main>
            <p>Outside fallback.</p>
        </body></html>"""
        self.assertEqual(get_first_paragraph_from_html(input_body), "Outside fallback.")


if __name__ == "__main__":
    unittest.main()
