from unittest import TestCase
from unittest.mock import MagicMock, mock_open, patch


class SettingsTests(TestCase):
    def setUp(self):
        # TODO: use patch.dict for all
        modules = {
            "anki.hooks": MagicMock(),
            "aqt": MagicMock(),
            "aqt.mw": MagicMock(),
            "aqt.utils": MagicMock(),
            "ir.about": MagicMock(),
            "ir.main": MagicMock(),
            "ir.util": MagicMock(),
            "ir.settings.json.load": MagicMock(),
            "ir.settings.mw.pm.profileFolder": MagicMock(return_value=str()),
            "ir.settings.open": mock_open(),
            "ir.settings.os.path.isfile": MagicMock(return_value=True)
        }
        self.patcher = patch.dict("sys.modules", modules)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _create_sut(self):
        from ir.settings import SettingsManager

        return SettingsManager()

class SaveTests(SettingsTests):
    def test_save(self):
        with patch("ir.settings.open", mock_open()) as open_mock, \
            patch("ir.settings.json.dump", MagicMock()) as dump_mock, \
            patch("ir.settings.updateModificationTime", MagicMock()) as update_mock:

            sut = self._create_sut()

            sut.getSettingsPath = MagicMock(return_value="foo.json")
            sut.settings = {"foo": "bar"}
            sut.save()

            open_mock.assert_called_once_with("foo.json", "w", encoding="utf-8")
            dump_mock.assert_called_once_with({"foo": "bar"}, open_mock())
            update_mock.assert_called_once()

class PathTests(SettingsTests):
    def test_getMediaDir(self):
        with patch("ir.settings.mw.pm.profileFolder", MagicMock(return_value="foo")):
            sut = self._create_sut()

            self.assertEqual(sut.getMediaDir(), "foo/collection.media")

    def test_getSettingsPath(self):
        sut = self._create_sut()

        sut.getMediaDir = MagicMock(return_value="foo")

        self.assertEqual(sut.getSettingsPath(), "foo/_ir.json")


class ValidateFormatStringsTests(SettingsTests):
    def test_valid(self):
        sut = self._create_sut()

        sut.defaults = {"fooFormat": "{foo} {bar}", "barFormat": "{baz} {qux}"}
        sut.settings = sut.defaults.copy()
        sut.requiredFormatKeys = {
            "fooFormat": ["foo", "bar"],
            "barFormat": ["baz", "qux"],
        }
        sut._validateFormatStrings()

        self.assertEqual(sut.settings, sut.defaults)

    def test_invalid(self):
        sut = self._create_sut()

        sut.defaults = {"fooFormat": "{foo} {bar}", "barFormat": "{baz} {qux}"}
        invalidSettings = {"fooFormat": "{baz} {qux}", "barFormat": "{foo} {bar}"}
        sut.settings = invalidSettings
        sut.requiredFormatKeys = {
            "fooFormat": ["foo", "bar"],
            "barFormat": ["baz", "qux"],
        }

        sut._validateFormatStrings()

        self.assertEqual(sut.settings, sut.defaults)


class ValidFormatTests(SettingsTests):
    def test_valid(self):
        sut = self._create_sut()

        sut.requiredFormatKeys = {"test": ["foo", "bar", "baz"]}
        self.assertTrue(sut.validFormat("test", "{foo} {bar} {baz}"))

    def test_invalid(self):
        sut = self._create_sut()

        sut.requiredFormatKeys = {"test": ["foo", "bar", "baz"]}
        self.assertFalse(sut.validFormat("test", "{foo} {baz}"))
