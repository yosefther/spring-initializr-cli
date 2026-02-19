import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from spring_initializr_cli.commands import _search_dependencies, safe_extractall


class CommandHelpersTests(unittest.TestCase):
    def test_safe_extractall_rejects_path_traversal(self):
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, mode="w") as archive:
            archive.writestr("../../evil.txt", "bad")

        archive_bytes.seek(0)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            with zipfile.ZipFile(archive_bytes) as archive:
                with self.assertRaises(ValueError):
                    safe_extractall(archive, target)

    def test_safe_extractall_extracts_regular_files(self):
        archive_bytes = io.BytesIO()
        with zipfile.ZipFile(archive_bytes, mode="w") as archive:
            archive.writestr("demo/README.md", "ok")

        archive_bytes.seek(0)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            with zipfile.ZipFile(archive_bytes) as archive:
                safe_extractall(archive, target)

            self.assertTrue((target / "demo" / "README.md").exists())

    def test_search_dependencies_scores_exact_then_prefix(self):
        dep_map = {
            "web": "Spring Web",
            "web-services": "Spring Web Services",
            "graphql": "Spring for GraphQL",
        }

        matches = _search_dependencies(dep_map, "web")

        self.assertEqual(matches[0][1], "web")
        self.assertEqual(matches[1][1], "web-services")


if __name__ == "__main__":
    unittest.main()
