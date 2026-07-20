from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADT = ROOT / "plugins" / "ai-dev-team-v2" / "scripts" / "adt.py"
MAX_INPUT_BYTES = 1024 * 1024


def _sensitive_patterns_sha256(*patterns: str) -> str:
    canonical_patterns = {item.casefold() for item in patterns}
    canonical = (
        ""
        if not canonical_patterns
        else "\n".join(sorted(canonical_patterns)) + "\n"
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class PublicationGateCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.candidate = self.root / "private-candidate-name.md"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _run(
        self,
        *extra: str,
        destination: str = "example-org/public-plugin",
        candidate: Path | None = None,
        expected_code: int = 0,
    ) -> tuple[dict[str, object], subprocess.CompletedProcess[str]]:
        selected = candidate or self.candidate
        result = subprocess.run(
            [
                sys.executable,
                str(ADT),
                "publication-gate",
                "--destination-repo",
                destination,
                "--input",
                str(selected),
                *extra,
            ],
            cwd=self.root,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            expected_code,
            result.returncode,
            msg=f"stdout={result.stdout!r}\nstderr={result.stderr!r}",
        )
        return json.loads(result.stdout or result.stderr), result

    def test_success_receipt_binds_exact_bytes_without_disclosing_path(self) -> None:
        raw = (
            b"Safe publication text.\n"
            b"Same repository: example-org/public-plugin#31\n"
            b"URL: https://github.com/Example-Org/Public-Plugin/pull/31\n"
        )
        self.candidate.write_bytes(raw)

        first, first_process = self._run()
        second, _ = self._run()

        self.assertEqual(first, second)
        self.assertEqual(
            {
                "ok": True,
                "command": "publication-gate",
                "receipt": {
                    "contract_version": "adt.publication-gate.v1",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_count": len(raw),
                    "destination_repo": "example-org/public-plugin",
                    "sensitive_patterns_sha256": _sensitive_patterns_sha256(),
                },
            },
            first,
        )
        self.assertNotIn(str(self.candidate), first_process.stdout)
        self.assertEqual("", first_process.stderr)

    def test_external_repositories_hold_with_only_line_and_rule(self) -> None:
        external_url = "https://github.com/private-org/service/pull/1"
        external_short = "private-org/planning#28"
        self.candidate.write_text(
            "safe first line\n"
            f"private link: {external_url}\n"
            f"private shorthand: {external_short}\n",
            encoding="utf-8",
        )

        payload, process = self._run(expected_code=5)

        self.assertEqual(
            {
                "ok": False,
                "command": "publication-gate",
                "verdict": "HOLD",
                "violations": [
                    {"line": 2, "rule": "external_github_owner"},
                    {"line": 3, "rule": "external_github_owner"},
                ],
            },
            payload,
        )
        emitted = process.stdout + process.stderr
        self.assertNotIn(external_url, emitted)
        self.assertNotIn(external_short, emitted)
        self.assertNotIn(str(self.candidate), emitted)

    def test_same_owner_is_the_default_github_trust_domain(self) -> None:
        self.candidate.write_text(
            "https://github.com/example-org/service/pull/1\n"
            "example-org/planning#28\n"
            "example-org/service@0123456789abcdef\n"
            "@example-org\n",
            encoding="utf-8",
        )

        payload, _ = self._run()

        self.assertTrue(payload["ok"])
        self.assertEqual(
            "example-org/public-plugin",
            payload["receipt"]["destination_repo"],
        )
        self.assertEqual(
            _sensitive_patterns_sha256(),
            payload["receipt"]["sensitive_patterns_sha256"],
        )

    def test_common_github_url_forms_are_parsed_fail_closed(self) -> None:
        self.candidate.write_text(
            "github.com/private-org/service/issues/2\n"
            "//github.com/private-org/service/pull/3\n"
            "https://api.github.com/repos/private-org/service/issues/4\n"
            "git@github.com:private-org/service.git\n"
            "ssh://git@github.com/private-org/service.git\n",
            encoding="utf-8",
        )

        payload, _ = self._run(expected_code=5)

        self.assertEqual(
            [
                {"line": line, "rule": "external_github_owner"}
                for line in range(1, 6)
            ],
            payload["violations"],
        )

    def test_external_accounts_hosts_and_encoded_links_hold(self) -> None:
        self.candidate.write_text(
            "https://github.com/private-org\n"
            "https://api.github.com/users/private-org\n"
            "https://gist.github.com/private-org/0123456789abcdef\n"
            "@private-user\n"
            "https://raw.githubusercontent.com/private-org/service/main/file.txt\n"
            "https://codeload.github.com/private-org/service/zip/main\n"
            "https://github.com/private-org&#47;service/pull/1\n"
            "https://github.com/private-org%2Fservice/issues/1\n",
            encoding="utf-8",
        )

        payload, _ = self._run(expected_code=5)

        self.assertEqual(
            [
                {"line": line, "rule": "external_github_owner"}
                for line in range(1, 9)
            ],
            payload["violations"],
        )

    def test_canonical_github_url_variants_hold(self) -> None:
        self.candidate.write_text(
            "https://github.com:443/private-org/service/issues/1\n"
            "https://github.com./private-org/service/issues/2\n"
            r"https://github.com\private-org\service\issues\3" "\n"
            r"[private](https://github\.com/private\-org/service)" "\n"
            "https://github.com/example-org/" ".." "/private-org/service\n"
            "//api.github.com/repos/private-org/service/issues/4\n"
            "//raw.githubusercontent.com/private-org/service/main/file.txt\n"
            "[issue](/private-org/service/issues/5)\n"
            "https://api.github.com/orgs/private-org\n"
            "https://gist.githubusercontent.com/private-user/id/raw/file.txt\n"
            "https://private-user.github.io/private-repo/\n"
            "https://private-user-images.githubusercontent.com/123/file.png\n"
            "www.github.com/private-org/service/issues/6\n",
            encoding="utf-8",
        )

        payload, _ = self._run(expected_code=5)

        self.assertEqual(
            [
                {"line": line, "rule": "external_github_owner"}
                for line in range(1, 14)
            ],
            payload["violations"],
        )

    def test_root_relative_reference_style_link_holds(self) -> None:
        self.candidate.write_text(
            "[source][private]\n"
            "[private]: /private-org/service/issues/1\n",
            encoding="utf-8",
        )

        payload, _ = self._run(expected_code=5)

        self.assertEqual(
            [{"line": 2, "rule": "external_github_owner"}],
            payload["violations"],
        )

    def test_over_indented_pseudo_fence_does_not_hide_mention(self) -> None:
        self.candidate.write_text(
            "    ```\n"
            "Thanks @private-user\n"
            "```\n",
            encoding="utf-8",
        )

        payload, _ = self._run(expected_code=5)

        self.assertEqual(
            [{"line": 2, "rule": "external_github_owner"}],
            payload["violations"],
        )

    def test_reserved_github_routes_and_markdown_code_do_not_hold(self) -> None:
        self.candidate.write_text(
            "https://github.com/features/actions\n"
            "   ```python\n"
            "@dataclass\n"
            "class Example:\n"
            "    pass\n"
            "   ```\n"
            "Use `@scope/package` in this example.\n",
            encoding="utf-8",
        )

        payload, _ = self._run()

        self.assertTrue(payload["ok"])

    def test_cross_repository_commit_shorthand_is_blocked(self) -> None:
        self.candidate.write_text(
            "private-org/service@0123456789abcdef\n"
            "example-org/public-plugin@fedcba9876543210\n",
            encoding="utf-8",
        )

        payload, _ = self._run(expected_code=5)

        self.assertEqual(
            [{"line": 1, "rule": "external_github_owner"}],
            payload["violations"],
        )

    def test_sensitive_patterns_are_literal_and_never_echoed(self) -> None:
        secret = "Private-Token=a+b[0]"
        patterns = self.root / "private-pattern-file-name.txt"
        patterns.write_text(f"{secret}\n\n", encoding="utf-8")
        self.candidate.write_text(
            "not a regex hit: private-token=aaab0\n"
            f"actual with different case: {secret.upper()}\n",
            encoding="utf-8",
        )

        payload, process = self._run(
            "--patterns-file",
            str(patterns),
            expected_code=5,
        )

        self.assertEqual(
            [{"line": 2, "rule": "sensitive_literal"}],
            payload["violations"],
        )
        self.assertNotIn("receipt", payload)
        emitted = process.stdout + process.stderr
        self.assertNotIn(secret, emitted)
        self.assertNotIn(str(patterns), emitted)
        self.assertNotIn(str(self.candidate), emitted)

        self.candidate.write_text("safe text\n", encoding="utf-8")
        success, _ = self._run("--patterns-file", str(patterns))
        self.assertEqual(
            _sensitive_patterns_sha256(secret),
            success["receipt"]["sensitive_patterns_sha256"],
        )

    def test_input_must_be_bounded_utf8_regular_file(self) -> None:
        invalid_utf8 = self.root / "invalid-utf8-private-name"
        invalid_utf8.write_bytes(b"safe\n\xff\n")
        oversized = self.root / "oversized-private-name"
        oversized.write_bytes(b"a" * (MAX_INPUT_BYTES + 1))
        directory = self.root / "directory-private-name"
        directory.mkdir()
        symlink = self.root / "symlink-private-name"
        symlink.symlink_to(self.candidate)
        self.candidate.write_text("safe\n", encoding="utf-8")

        for candidate in (invalid_utf8, oversized, directory, symlink):
            with self.subTest(kind=candidate.name):
                payload, process = self._run(
                    candidate=candidate,
                    expected_code=3,
                )
                self.assertEqual("publication_input_invalid", payload["error"]["code"])
                emitted = process.stdout + process.stderr
                self.assertNotIn(str(candidate), emitted)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX named pipes")
    def test_fifo_fails_closed_without_blocking(self) -> None:
        fifo = self.root / "fifo-private-name"
        os.mkfifo(fifo)

        result = subprocess.run(
            [
                sys.executable,
                str(ADT),
                "publication-gate",
                "--destination-repo",
                "example-org/public-plugin",
                "--input",
                str(fifo),
            ],
            cwd=self.root,
            check=False,
            text=True,
            capture_output=True,
            timeout=1,
        )

        self.assertEqual(3, result.returncode)
        self.assertEqual(
            "publication_input_invalid",
            json.loads(result.stderr)["error"]["code"],
        )

    def test_patterns_file_and_repository_arguments_fail_closed(self) -> None:
        self.candidate.write_text("safe\n", encoding="utf-8")
        invalid_patterns = self.root / "invalid-patterns-private-name"
        invalid_patterns.write_bytes(b"secret\n\xff")
        invalid_repositories = (
            "https://github.com/example-org/public-plugin",
            "example-org/public-plugin#31",
            "example-org",
            "example-org/public plugin",
        )

        payload, process = self._run(
            "--patterns-file",
            str(invalid_patterns),
            expected_code=3,
        )
        self.assertEqual("publication_patterns_invalid", payload["error"]["code"])
        self.assertNotIn(str(invalid_patterns), process.stdout + process.stderr)

        for repository in invalid_repositories:
            with self.subTest(repository=repository):
                payload, process = self._run(
                    destination=repository,
                    expected_code=3,
                )
                self.assertEqual(
                    "publication_repository_invalid",
                    payload["error"]["code"],
                )
                self.assertNotIn(repository, process.stdout + process.stderr)

    def test_missing_input_and_unknown_option_are_nonzero(self) -> None:
        missing = self.root / "missing-private-name"
        payload, process = self._run(candidate=missing, expected_code=3)
        self.assertEqual("publication_input_invalid", payload["error"]["code"])
        self.assertNotIn(str(missing), process.stdout + process.stderr)

        result = subprocess.run(
            [
                sys.executable,
                str(ADT),
                "publication-gate",
                "--destination-repo",
                "example-org/public-plugin",
                "--input",
                str(self.candidate),
                "--unknown",
            ],
            cwd=self.root,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(2, result.returncode)
        error = json.loads(result.stderr)["error"]
        self.assertEqual("usage", error["code"])
        self.assertEqual("Invalid publication-gate arguments.", error["message"])

        private_operand = "/" + "Users" + "/example/private-client-note"
        sensitive = subprocess.run(
            [
                sys.executable,
                str(ADT),
                "publication-gate",
                "--destination-repo",
                "example-org/public-plugin",
                "--input",
                str(self.candidate),
                private_operand,
            ],
            cwd=self.root,
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(2, sensitive.returncode)
        self.assertEqual(
            "Invalid publication-gate arguments.",
            json.loads(sensitive.stderr)["error"]["message"],
        )
        self.assertNotIn(private_operand, sensitive.stderr)


if __name__ == "__main__":
    unittest.main()
