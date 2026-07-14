# Contributing

AI Dev Team v2 is intentionally greenfield. Contributions must implement a
checked-in public contract and must not import v1 implementation artifacts.

## Workflow

1. Identify the contract or active spike that authorizes the change.
2. Add the smallest behavior-focused failing test.
3. Implement the minimum change that makes it pass.
4. Run the smallest relevant test tier once.
5. Record evidence, limitations, and any deferred boundary.

For documentation-only changes, run `make test`; do not launch future
integration or evaluation tiers.

## Public-source hygiene

Repository files must be portable and self-contained. Do not commit absolute
home-directory paths, local file URIs, sibling-repository locators, escaping
symlinks, credentials, or references to external private documentation.

Owner-specific forbidden patterns belong in an untracked pattern file supplied
to the public-source checker at review time.

