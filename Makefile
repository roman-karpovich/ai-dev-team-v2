.PHONY: test mvp-install mvp-replace-v1 mvp-install-codex mvp-install-claude

test:
	@./scripts/test-fast

mvp-install:
	@./scripts/install-mvp --all

mvp-replace-v1:
	@./scripts/install-mvp --all --replace-v1

mvp-install-codex:
	@./scripts/install-mvp --codex

mvp-install-claude:
	@./scripts/install-mvp --claude
