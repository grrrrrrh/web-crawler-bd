import unittest
from crawl import normalize_url


class TestCrawl(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
