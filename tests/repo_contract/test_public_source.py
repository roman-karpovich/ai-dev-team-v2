from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_public_source


class PublicSourceTest(unittest.TestCase):
    def test_current_tree_is_portable(self) -> None:
        self.assertEqual([], check_public_source.scan_repo(ROOT))

    def test_detects_absolute_home_locator_without_echoing_content(self) -> None:
        locator = b"/" + b"Users" + b"/" + b"example" + b"/project"
        violations = check_public_source.find_line_violations(
            "sample.txt", b"prefix\n" + locator + b"\n"
        )
        self.assertEqual(
            [check_public_source.Violation("sample.txt", 2, "absolute-home")],
            violations,
        )
        self.assertNotIn("example", repr(violations))

    def test_detects_parent_locator(self) -> None:
        locator = b".." + b"/outside"
        violations = check_public_source.find_line_violations(
            "sample.txt", locator
        )
        self.assertEqual("parent-locator", violations[0].rule)

    def test_detects_windows_home_locator(self) -> None:
        separator = b"\\"
        locator = b"C:" + separator + b"Users" + separator + b"example" + separator
        violations = check_public_source.find_line_violations(
            "sample.txt", locator
        )
        self.assertEqual("absolute-home", violations[0].rule)

    def test_external_pattern_is_supplied_outside_source(self) -> None:
        pattern = b"private" + b"-sentinel"
        violations = check_public_source.find_line_violations(
            "sample.txt", pattern, (pattern,)
        )
        self.assertEqual("external-pattern", violations[0].rule)

    def test_detects_escaping_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            target = root.parent / "outside.txt"
            target.write_text("outside")
            link = root / "link.txt"
            link.symlink_to(target)
            self.assertTrue(
                check_public_source._escapes_root(
                    root.resolve(), link.resolve(strict=False)
                )
            )


if __name__ == "__main__":
    unittest.main()
