# Changelog

## 2026-08-25 — Hardened Codex Desktop profile (unreleased)

- Added `GSC_ACCESS_MODE`, defaulting to Google's `webmasters.readonly` OAuth scope and a separate `token.readonly.json` cache.
- Removed Search Console write tools and browser reauthentication from the default MCP tool surface; both now require explicit profiles.
- Made `get_capabilities` non-interactive so a status check cannot open OAuth or write a token.
- Replaced direct token writes with atomic replacement and private POSIX directory/file permissions; failed reauthentication preserves the prior token.
- Disabled unauthenticated SSE/HTTP transport in favor of local STDIO for Codex Desktop.
- Changed bundled MCP launchers to execute this checkout with `uv run --frozen` instead of the separately published `uvx` package.
- Removed the unsupported Docker/network launcher and updated repository guidance to use the reviewed lockfile.
- Added a non-interactive warning when an ignored legacy broad-scope `token.json` remains in the checkout.
- Raised advisory-affected dependency floors and refreshed the locked MCP, HTTP, crypto, ASN.1, and settings packages.
- Added a Codex Desktop configuration example with a reviewed local interpreter, read-only tool allowlist, and approval prompts.
- Validation: 51 unit tests pass; a real STDIO initialize/list-tools probe exposed 15 read-only tools and zero write/reauth tools; a live read-only OAuth property-list query succeeded; `pip-audit` found no known vulnerabilities; Bandit found no medium/high issues (two low exception-handling findings remain); critical Ruff checks passed.

## 2026-04-13

- Bump all Python dependencies to their latest minor/patch versions via `uv lock --upgrade` (thanks @Herriaan, #24)
  - google-api-python-client 2.163.0 -> 2.194.0
  - google-auth 2.38.0 -> 2.49.2
  - google-auth-httplib2 0.2.0 -> 0.3.1
  - google-auth-oauthlib 1.2.1 -> 1.3.1
  - mcp 1.3.0 -> 1.27.2
  - pydantic 2.10.6 -> 2.13.4
  - plus various transitive dependencies
