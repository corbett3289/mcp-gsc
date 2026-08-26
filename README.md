# Google Search Console MCP Server for SEOs

A Model Context Protocol (MCP) server that connects [Google Search Console](https://search.google.com/search-console/about) (GSC) to AI assistants, allowing you to analyze your SEO data through natural language conversations. Works with **Claude Desktop**, **Cursor**, **Codex Desktop and CLI**, **Gemini CLI**, **Antigravity**, and any other MCP-compatible client.

> **Skip setup, get more.** A more advanced hosted version — one-click sign-in, added GA4 tools. Works with Claude Desktop, Claude Code, Claude.ai, Codex, Cursor, and any MCP client. Only **100 seats**.
> → [**Advanced GSC MCP (hosted)**](https://www.advancedgsc.com/mcp?utm_source=github&utm_medium=readme&utm_campaign=mcp-gsc&utm_content=hero-callout)

---

## What's New

### [Unreleased] — Hardened Codex Desktop profile

Security and behavior:

- **Read-only by default** — `GSC_ACCESS_MODE=read_only` requests Google's `webmasters.readonly` scope, stores it separately in `token.readonly.json`, and does not register Search Console mutation tools.
- **Explicit write profiles** — sitemap submission, property/sitemap deletion, property addition, and browser reauthentication are absent from the default MCP surface and require separate operator opt-ins.
- **Non-interactive status checks** — `get_capabilities` reports configuration state without contacting Google, opening OAuth, or writing a token.
- **Safer OAuth persistence** — token refresh and reauthentication use atomic replacement; failed replacement preserves the prior credential, while private POSIX permissions and symbolic-link checks protect local token storage.
- **Legacy-token warning** — read-only mode never reuses a legacy broad-scope `token.json` and reports when one remains for manual revocation/removal.
- **Local-only transport** — unauthenticated SSE/HTTP is rejected; this branch supports local STDIO rather than disabling DNS-rebinding protection.

Installation and supply chain:

- **Codex Desktop and CLI support** — documented the shared Codex MCP configuration with a reviewed local interpreter, nine-tool allowlist, approval prompts, and conservative timeouts.
- **Checkout-bound launchers** — bundled Claude and Cursor launchers run this checkout with `uv run --frozen` and bind both working directory and script path to the host-provided plugin root.
- **Locked dependency path** — clone instructions use `uv sync --frozen`; advisory-affected floors and lock entries were refreshed for MCP, `httplib2`, `cryptography`, `pyasn1`, and `pydantic-settings`.
- **Unsupported remote path removed** — the prior Docker/network launcher and runnable SSE guidance were removed from this hardened local branch.

Validation:

- **51 unit tests pass**, Python compilation succeeds, and critical Ruff checks pass.
- **Security scans pass** — `pip-audit` reports no known vulnerabilities and Bandit reports no medium/high findings (two low exception-handling findings remain).
- **Live MCP proof passes** — a real STDIO session exposes 15 read-only tools, zero write/reauthentication tools, and successfully completes read-only OAuth property and Search Analytics queries.

### [0.3.3] — July 2026
- **Fixed fresh installs broken by `mcp` 2.0** — pinned `mcp[cli]<2.0.0`. The `mcp` SDK 2.0.0 (released 2026-07-28) removed the `mcp.server.fastmcp` module, so every fresh `uvx mcp-search-console` install crashed on startup with `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`. New installs now resolve a working 1.x SDK again — no `--with "mcp<2"` workaround needed.

### [0.3.2] — April 2026
- **OAuth browser flow fixed for uvx** — removed the `isatty` block that prevented the browser login window from opening when running as an MCP subprocess on macOS. OAuth now works out of the box with `uvx`, no manual terminal run needed.
- **`get_capabilities` tool added** — call this to get a full list of available tools and current auth status in one shot. Useful when your AI assistant isn't sure what tools are available.
- **Better auth error messages** — all tools now tell you exactly what to do when credentials are missing or expired.

---

## What Can This Do?

**Property Management**
- See all your GSC properties in one place
- Get verification details and ownership information
- Add or remove properties from a separately enabled read/write profile

**Search Analytics & Reporting**
- Discover which queries bring visitors to your site
- Track impressions, clicks, and click-through rates
- Analyze performance trends and compare time periods
- Visualize data with charts created by your AI assistant

**URL Inspection & Indexing**
- Check if specific pages have indexing problems
- See when Google last crawled your pages
- Inspect multiple URLs at once to identify patterns

**Sitemap Management**
- View all sitemaps and their status
- Submit new sitemaps from a separately enabled read/write profile
- Check for errors or warnings

---

## Available Tools

| Tool | What It Does | What You Need to Provide |
|------|-------------|--------------------------|
| `get_capabilities` | Lists all tools and shows auth status — call this first if unsure | Nothing |
| `list_properties` | Shows all your GSC properties | Nothing |
| `get_site_details` | Details about a specific site | Site URL |
| `get_search_analytics` | Top queries and pages with clicks, impressions, CTR, position | Site URL, time period |
| `get_performance_overview` | Summary of site performance | Site URL, time period |
| `compare_search_periods` | Compare performance between two time periods | Site URL, two date ranges |
| `get_search_by_page_query` | Search terms driving traffic to a specific page | Site URL, page URL |
| `get_advanced_search_analytics` | Analytics with filters by country, device, query, page | Site URL |
| `inspect_url_enhanced` | Detailed crawl/index status for a URL | Site URL, page URL |
| `batch_url_inspection` | Inspect up to 10 URLs at once | Site URL, list of URLs |
| `check_indexing_issues` | Check multiple URLs for indexing problems | Site URL, list of URLs |
| `get_sitemaps` | Lists all sitemaps for a site | Site URL |
| `list_sitemaps_enhanced` | Detailed sitemap info including errors and warnings | Site URL |
| `get_sitemap_details` | Details for one submitted sitemap | Site URL, sitemap URL |
| `get_creator_info` | Project author and related-tool metadata | Nothing |

The default `read_only` profile registers 15 tools and omits all Search Console writes plus `reauthenticate`. A separately configured `read_write` profile can expose `submit_sitemap`, `manage_sitemaps`, `add_site`, `delete_site`, and `delete_sitemap`; `reauthenticate` has its own explicit opt-in.

---

<div align="center">
  <a href="https://www.advancedgsc.com/mcp?utm_source=github&utm_medium=readme&utm_campaign=mcp-gsc&utm_content=banner">
    <img src="assets/banner-1.jpg" alt="Skip setup — try the hosted MCP server with one-click Google sign-in. Works in ChatGPT and Claude web. Includes GA4 and advanced SEO tools." width="800" style="margin: 20px 0; border-radius: 8px;">
  </a>
</div>

---

## Getting Started

### Step 1 — Set Up Google API Credentials

You need credentials before configuring any client. Pick one method:

#### Option A — OAuth (Recommended — uses your own Google account)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create or select a project
2. [Enable the Search Console API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com)
3. Go to [Credentials](https://console.cloud.google.com/apis/credentials) → Create Credentials → **OAuth client ID**
4. Configure the OAuth consent screen, select **Desktop app**, click Create
5. Download the JSON file — save it somewhere permanent (e.g. `~/Documents/client_secrets.json`)

On first use, a browser window will open asking you to sign in to your Google account. After that, the token is saved and no browser interaction is needed again.

#### Option B — Service Account (For automation or team use)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create or select a project
2. [Enable the Search Console API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com)
3. Go to [Credentials](https://console.cloud.google.com/apis/credentials) → Create Credentials → **Service Account**
4. Go to the Keys tab → Add Key → Create new key → JSON → Download
5. Save the file somewhere permanent (e.g. `~/Documents/service_account.json`)
6. Add the service account email to your GSC property: Search Console → Settings → Users and permissions → Add user → Full access

#### 🎥 Watch the step-by-step setup tutorial for this section

<div align="center">
  <a href="https://www.youtube.com/watch?v=vhIOoD7B8Ow">
    <img src="assets/seo-mcp-install-video-1.jpg" alt="GSC MCP Server Installation Guide 2026" width="600" style="margin: 20px 0; border-radius: 8px;">
  </a>
</div>

*The video covers the upstream published-package flow. For this hardened branch, use the locked local-clone instructions below.*

---

### Step 2 — Installation

#### Install `uv`

`uv` provisions the required Python runtime and installs the exact dependency graph from `uv.lock`. This hardened branch deliberately does not use `uvx mcp-search-console`: that command runs the separately published upstream package rather than the source in this checkout.

**Install uv** — on Windows PowerShell:

```powershell
winget install --id astral-sh.uv -e
```

On macOS/Linux, run all three commands in order:

```bash
# 1. Download and install
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Activate in the current Terminal session
source $HOME/.local/bin/env

# 3. Make it permanent for all future sessions
echo 'source $HOME/.local/bin/env' >> ~/.zshrc
```

Verify:
```bash
uv --version
```

> **Why all three commands?** The installer puts `uv` in `~/.local/bin`, but your already-open Terminal session doesn't know about that folder yet. Step 2 activates it immediately. Step 3 ensures every future Terminal window has it automatically.

Clone and sync the reviewed branch before configuring your AI client:

```bash
git clone --branch security/codex-desktop-readonly --single-branch https://github.com/corbett3289/mcp-gsc.git
cd mcp-gsc
uv sync --frozen
```

`uv sync --frozen` provisions the Python version declared by the repository when needed. On macOS/Linux the interpreter is `.venv/bin/python`; on Windows it is `.venv/Scripts/python.exe`.

---

**Claude Desktop**

Config file: `~/Library/Application Support/Claude/claude_desktop_config.json`

OAuth:
```json
{
  "mcpServers": {
    "gscServer": {
      "command": "/FULL/PATH/TO/mcp-gsc/.venv/bin/python",
      "args": ["/FULL/PATH/TO/mcp-gsc/gsc_server.py"],
      "env": {
        "GSC_OAUTH_CLIENT_SECRETS_FILE": "/full/path/to/client_secrets.json",
        "GSC_ACCESS_MODE": "read_only",
        "GSC_ENABLE_REAUTH_TOOL": "false",
        "GSC_ALLOW_DESTRUCTIVE": "false"
      }
    }
  }
}
```

Service Account:
```json
{
  "mcpServers": {
    "gscServer": {
      "command": "/FULL/PATH/TO/mcp-gsc/.venv/bin/python",
      "args": ["/FULL/PATH/TO/mcp-gsc/gsc_server.py"],
      "env": {
        "GSC_CREDENTIALS_PATH": "/full/path/to/service_account.json",
        "GSC_SKIP_OAUTH": "true",
        "GSC_ACCESS_MODE": "read_only",
        "GSC_ENABLE_REAUTH_TOOL": "false",
        "GSC_ALLOW_DESTRUCTIVE": "false"
      }
    }
  }
}
```

---

**Cursor**

Config file: `~/.cursor/mcp.json`

OAuth:
```json
{
  "mcpServers": {
    "gscServer": {
      "command": "/FULL/PATH/TO/mcp-gsc/.venv/bin/python",
      "args": ["/FULL/PATH/TO/mcp-gsc/gsc_server.py"],
      "env": {
        "GSC_OAUTH_CLIENT_SECRETS_FILE": "/full/path/to/client_secrets.json",
        "GSC_ACCESS_MODE": "read_only",
        "GSC_ENABLE_REAUTH_TOOL": "false",
        "GSC_ALLOW_DESTRUCTIVE": "false"
      }
    }
  }
}
```

---

**Codex Desktop and CLI — hardened local clone**

Config file: `~/.codex/config.toml`

The Desktop app and CLI share this configuration on the same Codex host. Point them at the reviewed clone and begin with a small read-only allowlist:

```toml
[mcp_servers.gscServer]
command = "C:/FULL/PATH/TO/mcp-gsc/.venv/Scripts/python.exe"
args = ["C:/FULL/PATH/TO/mcp-gsc/gsc_server.py"]
cwd = "C:/FULL/PATH/TO/mcp-gsc"
enabled = true
required = false
enabled_tools = [
  "get_capabilities",
  "list_properties",
  "get_site_details",
  "get_search_analytics",
  "get_performance_overview",
  "get_sitemaps",
  "list_sitemaps_enhanced",
  "get_sitemap_details",
  "inspect_url_enhanced",
]
default_tools_approval_mode = "prompt"
startup_timeout_sec = 30
tool_timeout_sec = 120

[mcp_servers.gscServer.env]
GSC_OAUTH_CLIENT_SECRETS_FILE = "C:/FULL/PATH/TO/client_secrets.json"
GSC_ACCESS_MODE = "read_only"
GSC_ENABLE_REAUTH_TOOL = "false"
GSC_ALLOW_DESTRUCTIVE = "false"
GSC_DATA_STATE = "final"
```

Save the file, restart Codex Desktop, and use `/mcp` to confirm the server attached. `get_capabilities` is non-interactive; the first call to `list_properties` starts the local Google OAuth flow when login is still required.

---

> **Why absolute paths?** GUI apps may launch with a smaller environment than your terminal. Pointing directly at the clone's virtual-environment interpreter and `gsc_server.py` ensures the reviewed local code is what receives the Google credential.

After saving the config, **fully quit the app (`Cmd+Q`) and reopen it**.

For OAuth: on first use, a browser window will open automatically for login. After that, the token is cached and you won't be asked again.

---

### Step 3 — Test

Ask your AI assistant: **"List my GSC properties"**

If you see your properties — it's working. If not, ask: **"Call get_capabilities"** to see auth status and diagnose the issue.

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `GSC_OAUTH_CLIENT_SECRETS_FILE` | OAuth only | — | Absolute path to your OAuth client secrets JSON. Keep it outside the repository. |
| `GSC_CREDENTIALS_PATH` | Service account only | — | Absolute path to your service account JSON key. Keep it outside the repository. |
| `GSC_SKIP_OAUTH` | No | `false` | Set to `"true"` to force service account auth and skip OAuth entirely |
| `GSC_ACCESS_MODE` | No | `"read_only"` | `"read_only"` requests the Google read-only scope and does not register write tools. `"read_write"` uses a separate token cache and exposes write tools. |
| `GSC_ENABLE_REAUTH_TOOL` | No | `false` | Set to `"true"` only when the model-visible browser reauthentication tool is explicitly needed. |
| `GSC_DATA_STATE` | No | `"all"` | `"all"` matches the GSC dashboard. `"final"` returns only confirmed data (2–3 day lag). |
| `GSC_ALLOW_DESTRUCTIVE` | No | `false` | In a `read_write` profile, set to `"true"` to enable add/delete site and delete sitemap operations. It has no effect in `read_only`. |

---

## Cursor Marketplace

The one-click Cursor Marketplace entry installs the separately published upstream package, not this hardened checkout. Use the local-clone configuration above when you need this branch's security profile.

After installing, configure your credentials (see Step 1 above) then use the bundled skills directly in Cursor Agent chat:

| Skill | How to invoke | What it does |
|---|---|---|
| `seo-weekly-report` | *"Run the SEO weekly report for example.com"* | Full 28-day performance summary with period-over-period comparison and top queries |
| `cannibalization-check` | *"Check for keyword cannibalization on example.com"* | Finds queries where multiple pages compete; recommends which to keep |
| `indexing-audit` | *"Audit indexing for my top pages"* | Batch-inspects top 20 pages and returns a prioritized fix list |
| `content-opportunities` | *"Find content opportunities for example.com"* | Surfaces position-11-20 queries with high impressions and low CTR |

---

## Sample Prompts

| Tool | Sample Prompt |
|------|--------------|
| `list_properties` | "List all my GSC properties and tell me which ones have the most pages indexed." |
| `get_search_analytics` | "Show me the top 20 search queries for mywebsite.com in the last 30 days, highlight any with CTR below 2%, and suggest title improvements." |
| `get_performance_overview` | "Create a visual performance overview of mywebsite.com for the last 28 days, identify any unusual drops or spikes, and explain possible causes." |
| `check_indexing_issues` | "Check these pages for indexing issues: mywebsite.com/product, mywebsite.com/services, mywebsite.com/about" |
| `inspect_url_enhanced` | "Do a comprehensive inspection of mywebsite.com/landing-page and give me actionable recommendations." |
| `compare_search_periods` | "Compare my site's performance between January and February. What queries improved the most?" |
| `get_advanced_search_analytics` | "Analyze queries with high impressions but positions below 10, filtered to mobile traffic in the US only." |

---

## Troubleshooting

### `spawn uv ENOENT` or `command not found: uv`

Your AI client can't find `uv`. Use the full path instead of just `uv` in repository-owned launch configurations:

```bash
# Find your full path (macOS/Linux):
which uv
# Typically: /Users/YOUR_NAME/.local/bin/uv
```

```powershell
# Find your full path (Windows PowerShell):
Get-Command uv | Select-Object -ExpandProperty Source
# Typically: C:\Users\YOUR_NAME\.local\bin\uv.exe
```

Replace `"command": "uv"` with the full executable path. Do not replace it with `uvx mcp-search-console`, which bypasses the local checkout.

### `uv --version` gives "command not found" right after installing

The installer updates `~/.local/bin` but your current Terminal session doesn't see it yet. Run:

```bash
source $HOME/.local/bin/env
```

Then add it permanently:
```bash
echo 'source $HOME/.local/bin/env' >> ~/.zshrc
```

### Authentication failed / credentials file not found

Use an **absolute path** or a `~/` path to your credentials file, not a path relative to the repository. Example:
```
/Users/yourname/Documents/client_secrets.json   ✅
~/Documents/client_secrets.json                 ✅
client_secrets.json                              ❌
```

### MCP only works in Claude Desktop app, not the website

The MCP server runs locally on your machine. It only works in the **Claude Desktop app** (downloaded from [claude.ai/download](https://claude.ai/download)), not in the claude.ai browser interface.

### AI Client Configuration Issues

1. Make sure all file paths in your config are correct absolute paths
2. Fully quit (`Cmd+Q`) and reopen the app after any config change — just closing the window is not enough
3. Ask your AI assistant to "call get_capabilities" — it will report the exact auth status and error

---

## Safety: Destructive Operations

The default `GSC_ACCESS_MODE=read_only` profile requests Google's read-only OAuth scope and does not register any Search Console mutation tools. Keep that profile for routine analysis.

If upgrading from version 0.3.3 or earlier, the hardened read-only profile intentionally ignores any legacy `token.json` in the checkout because it may carry the broader read/write scope. After confirming no separate read/write profile needs it, revoke that grant in your Google Account and remove the legacy file; never copy it to `token.readonly.json`.

If writes are genuinely required, configure a separately named server with a separate token/config directory, set `GSC_ACCESS_MODE=read_write`, and complete new OAuth consent. Sitemap submission is then available; add/delete property and delete sitemap remain blocked unless this second flag is also present:

```json
"GSC_ALLOW_DESTRUCTIVE": "true"
```

---

## Remote Deployment (Unsupported in This Branch)

This hardened build intentionally supports local STDIO only. The prior SSE example exposed Google-authorized tools without server authentication and disabled the SDK's DNS-rebinding protection.

Do not re-enable a network transport by merely binding a port. A remote deployment needs TLS, bearer/OAuth authentication, network access controls, and explicit Host/Origin validation before it can be considered safe.

---

## Related Tools

**[Advanced GSC Visualizer](https://www.advancedgsc.com/?utm_source=github&utm_medium=readme&utm_campaign=mcp-gsc&utm_content=related-tools)** — A Chrome extension (14,000+ users) with interactive charts, one-click export of up to 25,000 rows, keyword cannibalization detection, and an AI assistant — all directly inside Google Search Console. Built by the same author. [Install from the Chrome Web Store →](https://chromewebstore.google.com/detail/advanced-gsc-visualizer/cdiccpnglfpnclonhpchpaaoigfpieel)

---

## Contributing

Found a bug or have an idea for improvement? Open an issue or submit a pull request on GitHub.

---

## License

MIT License. See the [LICENSE](LICENSE) file for details.

---

## Changelog

### [0.3.3] — July 2026
- Pinned `mcp[cli]>=1.3.0,<2.0.0`. The `mcp` SDK 2.0.0 removed `mcp.server.fastmcp`, breaking all fresh `uvx` installs with `ModuleNotFoundError`. Capping below 2.0 restores working installs. (Fixes #41)

### [0.3.2] — April 2026
- **OAuth browser flow fixed for uvx** — removed `isatty` block that prevented the OAuth browser window from opening when running as an MCP subprocess on macOS. OAuth + `uvx` now works out of the box.
- **`get_capabilities` tool** — returns all available tools grouped by category plus live auth status in one call.
- **Better auth error messages** — all tools now explicitly tell you to call `reauthenticate` when credentials are missing or expired.
- **Improved `list_properties` description** — better semantic tool discovery in clients that use lazy tool loading.

### [0.3.1] — April 2026
- Fixed `list_properties` masking real auth errors; fail-fast on missing credentials.

### [0.3.0] — April 2026
- Cursor Marketplace plugin with 4 bundled SEO skills
- Stable token storage in platform user config dir (survives `uvx` upgrades)
- Structured JSON output for all data tools
- 39 unit tests

### [0.2.2] — April 2026
- Safety mode for destructive tools (disabled by default)
- HTTP/SSE transport for remote deployments
- Dockerfile

### [0.2.1] — March 2026
- `reauthenticate` tool for switching Google accounts
- Fixed sitemap TypeError crash
- Fixed domain property 404 errors

### [0.2.0] — March 2026
- `dataState: "all"` by default (matches GSC dashboard)
- Flexible `row_limit` parameter (up to 500)
- Multi-dimension filtering for advanced analytics

### [0.1.0] — Initial release
- 19 tools covering property management, search analytics, URL inspection, and sitemap management
- OAuth and service account authentication
