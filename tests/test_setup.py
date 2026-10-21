import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

from koans_lib.runner import CourseError
from koans_lib.setup import download, unpack_tar


class SetupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.spec = {"archive": "tool.tar.gz", "url": "https://example.invalid/tool",
                     "sha256": hashlib.sha256(b"verified").hexdigest()}

    def test_checksum_mismatch_is_not_installed(self):
        with patch("urllib.request.urlopen", return_value=io.BytesIO(b"wrong")), self.assertRaisesRegex(CourseError, "Checksum"):
            download(self.spec, self.root)
        self.assertFalse((self.root / self.spec["archive"]).exists())
        self.assertEqual(list(self.root.glob("*.part")), [])

    def test_cached_download_needs_no_network(self):
        cached = self.root / self.spec["archive"]
        cached.write_bytes(b"verified")
        with patch("urllib.request.urlopen", side_effect=AssertionError("network accessed")):
            self.assertEqual(download(self.spec, self.root), cached)

    def test_partial_download_recovers_on_retry(self):
        (self.root / "tool.tar.gz.part").write_bytes(b"partial old data")
        with patch("time.sleep"), patch("urllib.request.urlopen", side_effect=[urllib.error.URLError("interrupted"), io.BytesIO(b"verified")]):
            result = download(self.spec, self.root)
        self.assertEqual(result.read_bytes(), b"verified")
        self.assertFalse((self.root / "tool.tar.gz.part").exists())

    def test_archive_cannot_escape_destination(self):
        for name, link in (("../escape", None), ("link", "/outside")):
            with self.subTest(name=name):
                archive = self.root / "unsafe.tar"
                with tarfile.open(archive, "w") as tar:
                    info = tarfile.TarInfo(name)
                    if link:
                        info.type, info.linkname = tarfile.SYMTYPE, link
                    tar.addfile(info)
                with self.assertRaisesRegex(CourseError, "Unsafe"):
                    unpack_tar(archive, self.root / "dest")
