from __future__ import annotations

import subprocess
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

    def test_current_history_is_portable(self) -> None:
        self.assertEqual([], check_public_source.scan_history(ROOT))

    def test_current_commit_and_annotated_tag_messages_are_portable(self) -> None:
        self.assertEqual([], check_public_source.scan_commit_messages(ROOT))
        self.assertEqual(
            [], check_public_source.scan_annotated_tag_messages(ROOT)
        )

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

    def test_history_detects_locator_deleted_from_current_tree(self) -> None:
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Public Source Test"],
                cwd=root,
                check=True,
            )
            locator = b"/" + b"Users" + b"/" + b"example" + b"/private"
            artifact = root / "artifact.txt"
            artifact.write_bytes(locator)
            subprocess.run(["git", "add", "artifact.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "add artifact"],
                cwd=root,
                check=True,
            )
            artifact.unlink()
            subprocess.run(["git", "add", "-u"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "remove artifact"],
                cwd=root,
                check=True,
            )

            self.assertEqual([], check_public_source.scan_repo(root))
            violations = check_public_source.scan_history(root)
            self.assertEqual(1, len(violations))
            self.assertEqual("absolute-home", violations[0].rule)
            self.assertTrue(violations[0].path.startswith("artifact.txt@"))

    def test_commit_metadata_detects_external_pattern_without_echoing_it(self) -> None:
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Public Source Test"],
                cwd=root,
                check=True,
            )
            sentinel = b"private" + b"-relationship"
            (root / "clean.txt").write_text("clean")
            subprocess.run(["git", "add", "clean.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", sentinel.decode()],
                cwd=root,
                check=True,
            )

            violations = check_public_source.scan_commit_messages(
                root, (sentinel,)
            )

            self.assertEqual(1, len(violations))
            self.assertEqual("external-pattern", violations[0].rule)
            self.assertTrue(violations[0].path.startswith("commit@"))
            self.assertNotIn(sentinel.decode(), repr(violations))

    def test_annotated_tag_detects_external_pattern_without_echoing_it(self) -> None:
        with tempfile.TemporaryDirectory() as root_dir:
            root = Path(root_dir)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Public Source Test"],
                cwd=root,
                check=True,
            )
            (root / "clean.txt").write_text("clean")
            subprocess.run(["git", "add", "clean.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "clean commit"],
                cwd=root,
                check=True,
            )
            sentinel = b"private" + b"-relationship"
            subprocess.run(
                ["git", "tag", "-a", "v-test", "-m", sentinel.decode()],
                cwd=root,
                check=True,
            )

            violations = check_public_source.scan_annotated_tag_messages(
                root, (sentinel,)
            )

            self.assertEqual(1, len(violations))
            self.assertEqual("external-pattern", violations[0].rule)
            self.assertTrue(violations[0].path.startswith("tag@"))
            self.assertNotIn("v-test", violations[0].path)
            self.assertNotIn(sentinel.decode(), repr(violations))


if __name__ == "__main__":
    unittest.main()
