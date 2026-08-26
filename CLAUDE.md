# CLAUDE.md

Context for AI coding assistants (Claude, Cursor, Copilot, etc.) working in this repo.

## What this is

MCP server that connects Google Search Console to AI assistants.
Single file: `gsc_server.py` (~1,670 lines). Built with FastMCP — no custom framework.

## Running locally

```bash
uv sync --frozen
uv run --frozen python gsc_server.py
```

## Auth

Two modes, tried in order. Keep credentials outside the repository and pass an
absolute path:

1. **OAuth (default):** Set `GSC_OAUTH_CLIENT_SECRETS_FILE` to a Desktop-app OAuth client JSON. On first use, a browser opens for Google login. The default read-only profile saves `token.readonly.json` under the platform user config directory and auto-refreshes it when expired.
2. **Service account:** Set `GSC_CREDENTIALS_PATH` to the path of your service account JSON key file.

Set `GSC_SKIP_OAUTH=true` to force service account mode and skip OAuth entirely.

## Key environment variables

| Variable | Default | Description |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | Local STDIO only; other values fail closed in this hardened branch |
| `GSC_ACCESS_MODE` | `read_only` | `read_only` removes all Search Console writes and uses the read-only OAuth scope; use a separately configured `read_write` profile if required |
| `GSC_ENABLE_REAUTH_TOOL` | `false` | Opt in only if browser reauthentication must be model-visible |
| `GSC_DATA_STATE` | `all` | `all` = matches GSC dashboard; `final` = confirmed data only (2–3 day lag) |
| `GSC_ALLOW_DESTRUCTIVE` | `false` | In a `read_write` profile, set `true` to enable add/delete site and delete sitemap |
| `GSC_CREDENTIALS_PATH` | — | Path to service account JSON key file |
| `GSC_OAUTH_CLIENT_SECRETS_FILE` | `client_secrets.json` | Path to OAuth client secrets file |
| `GSC_SKIP_OAUTH` | `false` | Set `true` to skip OAuth and use service account only |

## Adding a new tool

1. Add an `@mcp.tool()` decorated async function anywhere in `gsc_server.py`
2. Use `get_gsc_service()` for auth — it handles OAuth and service account automatically
3. Return `json.dumps(result)` not formatted text strings (LLMs work better with structured data)
4. Handle `HttpError` and return a plain string error message on failure

```python
@mcp.tool()
async def my_new_tool(site_url: str) -> str:
    """One-line description shown to the AI as the tool's purpose."""
    try:
        service = get_gsc_service()
        result = service.someApi().someMethod(siteUrl=site_url).execute()
        return json.dumps(result)
    except Exception as e:
        if "404" in str(e):
            return _site_not_found_error(site_url)
        return f"Error: {str(e)}"
```

## Running tests

```bash
pytest test_gsc_server.py -v
```

No credentials needed — all Google API calls are mocked with `unittest.mock`.

## Network deployment

Remote transports and the previous Docker launcher are intentionally absent from
this hardened local branch. A safe remote MCP deployment requires TLS, client
authentication, network access controls, and explicit Host/Origin validation.
