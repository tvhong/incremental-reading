from unittest import TestCase
from unittest.mock import MagicMock, patch


class HtmlCleanerTests(TestCase):
    def setUp(self):
        modules = {
            "aqt": MagicMock(),
        }
        self.patcher = patch.dict("sys.modules", modules)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_ignored_tags_are_removed(self):
        sut = self._get_sut()

        html = """<html>
        <body>
            <h1>Test Content</h1>
            <iframe src="https://example.com"></iframe>
            <p>Some text</p>
            <script>alert('test');</script>
            <nav>
                <ul>
                    <li><a href="#">Home</a></li>
                </ul>
            </nav>
            <div>More content</div>
        </body>
        </html>
        """
        result = sut.clean(html, "https://example.com")

        # Check that ignored tags are removed
        for tag in sut._IGNORED_TAGS:
            assert not result.find_all(tag), f"{tag} tag was not removed"

        # Check that other content is preserved
        assert result.find("h1").text == "Test Content"
        assert result.find("p").text == "Some text"
        assert result.find("div").text == "More content"

    def _get_sut(self):
        from ir.importer.html_cleaner import HtmlCleaner

        return HtmlCleaner()
