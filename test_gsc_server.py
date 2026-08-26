"""
Tests for gsc_server.py.

All Google API calls are mocked — no real credentials are needed to run these tests.
Run with: pytest test_gsc_server.py -v
"""
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Helpers to reload the module with a clean environment each test
# ---------------------------------------------------------------------------

def _load_module(env_overrides: dict | None = None):
    """Import gsc_server with a fresh environment."""
    env = {
        "GSC_SKIP_OAUTH": "true",          # prevent live OAuth attempts by default
        "GSC_DATA_STATE": "all",
        "GSC_ALLOW_DESTRUCTIVE": "false",
        "GSC_ACCESS_MODE": "read_only",
        "GSC_ENABLE_REAUTH_TOOL": "false",
        **(env_overrides or {}),
    }
    with patch.dict(os.environ, env, clear=False):
        if "gsc_server" in sys.modules:
            del sys.modules["gsc_server"]
        import gsc_server as mod
    return mod


# ---------------------------------------------------------------------------
# TestAuth
# ---------------------------------------------------------------------------

class TestAuth(unittest.TestCase):

    def test_token_loaded_from_config_dir(self):
        """TOKEN_FILE must resolve inside the user config dir, not SCRIPT_DIR."""
        mod = _load_module()
        # By default, TOKEN_FILE should NOT equal os.path.join(SCRIPT_DIR, "token.json").
        self.assertNotEqual(mod.TOKEN_FILE, os.path.join(mod.SCRIPT_DIR, "token.json"))

    def test_old_token_migrated_silently(self):
        """On first run after upgrade, a token at the old SCRIPT_DIR location is moved.

        SCRIPT_DIR is derived from __file__ at module load time, so this test places a
        real token.json in the actual SCRIPT_DIR and re-imports with a fresh GSC_CONFIG_DIR.
        The test cleans up after itself regardless of outcome.
        """
        # Discover the real SCRIPT_DIR by importing once
        if "gsc_server" in sys.modules:
            del sys.modules["gsc_server"]
        with patch.dict(os.environ, {"GSC_SKIP_OAUTH": "true", "GSC_DATA_STATE": "all",
                                     "GSC_ALLOW_DESTRUCTIVE": "false",
                                     "GSC_ACCESS_MODE": "read_write"}, clear=False):
            import gsc_server as _tmp
        actual_script_dir = _tmp.SCRIPT_DIR
        del sys.modules["gsc_server"]

        old_token_path = os.path.join(actual_script_dir, "token.json")
        old_token_content = '{"test": "migration_test"}'
        preexisting_backup = None

        with tempfile.TemporaryDirectory() as new_config_dir:
            try:
                # Back up any real existing token so we don't destroy it
                if os.path.exists(old_token_path):
                    preexisting_backup = old_token_path + ".test_bak"
                    import shutil as _shutil
                    _shutil.copy2(old_token_path, preexisting_backup)

                # Place test token in old location
                with open(old_token_path, "w") as f:
                    f.write(old_token_content)

                # Re-import with new config dir (no token there yet → migration should fire)
                env = {
                    "GSC_SKIP_OAUTH": "true",
                    "GSC_DATA_STATE": "all",
                    "GSC_ALLOW_DESTRUCTIVE": "false",
                    "GSC_ACCESS_MODE": "read_write",
                    "GSC_CONFIG_DIR": new_config_dir,
                }
                with patch.dict(os.environ, env, clear=False):
                    import gsc_server as mod

                new_token_path = os.path.join(new_config_dir, "token.json")
                self.assertTrue(os.path.exists(new_token_path), "Token was not migrated to new location")
                self.assertFalse(os.path.exists(old_token_path), "Old token was not removed after migration")
                with open(new_token_path) as f:
                    self.assertEqual(f.read(), old_token_content)

            finally:
                del sys.modules["gsc_server"]
                # Clean up any leftover test token in SCRIPT_DIR
                if os.path.exists(old_token_path):
                    os.remove(old_token_path)
                # Restore original token if it existed
                if preexisting_backup and os.path.exists(preexisting_backup):
                    import shutil as _shutil
                    _shutil.move(preexisting_backup, old_token_path)

    def test_expired_token_refresh_succeeds(self):
        """If refresh succeeds, get_gsc_service_oauth returns without error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"GSC_SKIP_OAUTH": "false", "GSC_DATA_STATE": "all",
                   "GSC_ALLOW_DESTRUCTIVE": "false", "GSC_CONFIG_DIR": tmpdir}
            with patch.dict(os.environ, env, clear=False):
                if "gsc_server" in sys.modules:
                    del sys.modules["gsc_server"]
                import gsc_server as mod

            mock_creds = MagicMock()
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = "refresh_token"
            mock_creds.to_json.return_value = '{"token": "refreshed"}'

            def fake_refresh(request):
                mock_creds.valid = True

            mock_creds.refresh.side_effect = fake_refresh

            with patch("gsc_server.Credentials.from_authorized_user_file", return_value=mock_creds), \
                 patch("gsc_server.build", return_value=MagicMock()), \
                 patch.object(mod, "TOKEN_FILE", os.path.join(tmpdir, "token.json")):
                with open(os.path.join(tmpdir, "token.json"), "w") as token_file:
                    token_file.write("{}")
                service = mod.get_gsc_service_oauth()
                self.assertIsNotNone(service)

    def test_expired_token_no_refresh_raises_runtime_error(self):
        """When refresh fails and no secrets file, get_gsc_service_oauth raises RuntimeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"GSC_SKIP_OAUTH": "false", "GSC_DATA_STATE": "all",
                   "GSC_ALLOW_DESTRUCTIVE": "false", "GSC_CONFIG_DIR": tmpdir}
            with patch.dict(os.environ, env, clear=False):
                if "gsc_server" in sys.modules:
                    del sys.modules["gsc_server"]
                import gsc_server as mod

            mock_creds = MagicMock()
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = None  # no refresh token available

            with patch("gsc_server.Credentials.from_authorized_user_file", return_value=mock_creds), \
                 patch.object(mod, "TOKEN_FILE", os.path.join(tmpdir, "token.json")), \
                 patch.object(mod, "OAUTH_CLIENT_SECRETS_FILE", os.path.join(tmpdir, "no_secrets.json")):
                with open(os.path.join(tmpdir, "token.json"), "w") as token_file:
                    token_file.write("{}")
                with self.assertRaises((RuntimeError, FileNotFoundError)):
                    mod.get_gsc_service_oauth()

    def test_no_token_no_secrets_raises_file_not_found(self):
        """With no token file and no secrets file, FileNotFoundError is raised."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {"GSC_SKIP_OAUTH": "false", "GSC_DATA_STATE": "all",
                   "GSC_ALLOW_DESTRUCTIVE": "false", "GSC_CONFIG_DIR": tmpdir}
            with patch.dict(os.environ, env, clear=False):
                if "gsc_server" in sys.modules:
                    del sys.modules["gsc_server"]
                import gsc_server as mod

            with patch.object(mod, "TOKEN_FILE", os.path.join(tmpdir, "nonexistent_token.json")), \
                 patch.object(mod, "OAUTH_CLIENT_SECRETS_FILE", os.path.join(tmpdir, "nonexistent_secrets.json")):
                with self.assertRaises(FileNotFoundError):
                    mod.get_gsc_service_oauth()

    def test_skip_oauth_env_var(self):
        """GSC_SKIP_OAUTH=true makes get_gsc_service skip OAuth."""
        mod = _load_module({"GSC_SKIP_OAUTH": "true"})
        self.assertTrue(mod.SKIP_OAUTH)

    def test_gsc_credentials_path_set_but_missing_fails_fast(self):
        """When GSC_CREDENTIALS_PATH is set but the file does not exist, get_gsc_service
        must raise FileNotFoundError immediately with a message that names the specific
        path AND mentions uvx — instead of silently falling through to SCRIPT_DIR/cwd
        fallbacks that uvx users cannot reach. Regression guard for issue #25.
        """
        missing_path = "/tmp/definitely-does-not-exist-issue-25.json"
        mod = _load_module({
            "GSC_CREDENTIALS_PATH": missing_path,
            "GSC_SKIP_OAUTH": "true",
        })
        with self.assertRaises(FileNotFoundError) as ctx:
            mod.get_gsc_service()
        msg = str(ctx.exception)
        self.assertIn("GSC_CREDENTIALS_PATH", msg)
        self.assertIn(missing_path, msg)
        self.assertIn("uvx", msg.lower())

    def test_gsc_oauth_client_secrets_file_set_but_missing_fails_fast(self):
        """Same symmetry for OAuth: if GSC_OAUTH_CLIENT_SECRETS_FILE is set to a
        nonexistent file, get_gsc_service must fail fast with a clear message
        instead of silently falling through.
        """
        missing_path = "/tmp/definitely-does-not-exist-oauth-issue-25.json"
        mod = _load_module({
            "GSC_OAUTH_CLIENT_SECRETS_FILE": missing_path,
            "GSC_SKIP_OAUTH": "false",
        })
        with self.assertRaises(FileNotFoundError) as ctx:
            mod.get_gsc_service()
        msg = str(ctx.exception)
        self.assertIn("GSC_OAUTH_CLIENT_SECRETS_FILE", msg)
        self.assertIn(missing_path, msg)
        self.assertIn("uvx", msg.lower())

    def test_gsc_credentials_path_expands_tilde(self):
        """GSC_CREDENTIALS_PATH must expand ~ so users can write ~/creds.json."""
        mod = _load_module({"GSC_CREDENTIALS_PATH": "~/this-should-be-expanded.json"})
        self.assertIsNotNone(mod.GSC_CREDENTIALS_PATH)
        self.assertNotIn("~", mod.GSC_CREDENTIALS_PATH)
        self.assertTrue(mod.GSC_CREDENTIALS_PATH.startswith(os.path.expanduser("~")))


# ---------------------------------------------------------------------------
# Shared fixture helper
# ---------------------------------------------------------------------------

def _make_service():
    """Return a MagicMock that mimics the Google Search Console service object."""
    return MagicMock()


# ---------------------------------------------------------------------------
# TestListProperties
# ---------------------------------------------------------------------------

class TestListProperties(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_with_properties_list(self):
        mod = _load_module()
        service = _make_service()
        service.sites().list().execute.return_value = {
            "siteEntry": [
                {"siteUrl": "https://example.com/", "permissionLevel": "siteOwner"},
                {"siteUrl": "sc-domain:example.com", "permissionLevel": "siteFullUser"},
            ]
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.list_properties()
        data = json.loads(result)
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["properties"][0]["site_url"], "https://example.com/")
        self.assertEqual(data["properties"][1]["permission_level"], "siteFullUser")

    async def test_returns_message_when_no_properties(self):
        mod = _load_module()
        service = _make_service()
        service.sites().list().execute.return_value = {}
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.list_properties()
        self.assertIsInstance(result, str)
        self.assertIn("No Search Console properties", result)

    async def test_handles_api_error(self):
        mod = _load_module()
        with patch("gsc_server.get_gsc_service", side_effect=Exception("API error")):
            result = await mod.list_properties()
        self.assertIn("Error", result)

    async def test_surfaces_real_auth_error_not_hardcoded_message(self):
        """When auth fails with a FileNotFoundError, list_properties must surface the
        actual exception text (e.g. the OAuth failure reason), NOT a hardcoded
        service-account-only message. Regression guard for issue #25 comment by
        platky: an OAuth user saw "Service account credentials file not found" even
        though they had never configured service accounts.
        """
        mod = _load_module()
        real_error = FileNotFoundError(
            "OAuth token is missing or expired and cannot be refreshed."
        )
        with patch("gsc_server.get_gsc_service", side_effect=real_error):
            result = await mod.list_properties()
        self.assertIn("OAuth token is missing", result)
        self.assertNotIn("1. Create a service account in Google Cloud Console", result)


# ---------------------------------------------------------------------------
# TestGetSearchAnalytics
# ---------------------------------------------------------------------------

class TestGetSearchAnalytics(unittest.IsolatedAsyncioTestCase):

    def _make_rows(self):
        return {
            "rows": [
                {"keys": ["seo tool"], "clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 5.0},
                {"keys": ["mcp server"], "clicks": 50, "impressions": 500, "ctr": 0.1, "position": 8.2},
            ]
        }

    async def test_returns_json_with_rows(self):
        mod = _load_module()
        service = _make_service()
        service.searchanalytics().query().execute.return_value = self._make_rows()
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_search_analytics("https://example.com/")
        data = json.loads(result)
        self.assertEqual(data["row_count"], 2)
        self.assertEqual(data["rows"][0]["query"], "seo tool")
        self.assertEqual(data["rows"][0]["clicks"], 100)
        self.assertIn("ctr", data["rows"][0])

    async def test_no_data_returns_string_message(self):
        mod = _load_module()
        service = _make_service()
        service.searchanalytics().query().execute.return_value = {}
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_search_analytics("https://example.com/")
        self.assertIsInstance(result, str)
        self.assertNotIn("{", result[:5])  # not JSON

    async def test_row_limit_capped_at_500(self):
        """Requesting more than 500 rows should be capped."""
        mod = _load_module()
        service = _make_service()
        service.searchanalytics().query().execute.return_value = {"rows": []}
        with patch("gsc_server.get_gsc_service", return_value=service):
            await mod.get_search_analytics("https://example.com/", row_limit=9999)
        # Verify the request body capped at 500
        call_args = service.searchanalytics().query.call_args
        if call_args:
            body = call_args[1].get("body") or (call_args[0][0] if call_args[0] else None)
            if body and "rowLimit" in body:
                self.assertLessEqual(body["rowLimit"], 500)

    async def test_handles_404(self):
        mod = _load_module()
        with patch("gsc_server.get_gsc_service", side_effect=Exception("404")):
            result = await mod.get_search_analytics("https://example.com/")
        self.assertIn("not found", result.lower())


# ---------------------------------------------------------------------------
# TestGetSiteDetails
# ---------------------------------------------------------------------------

class TestGetSiteDetails(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_with_permission_and_verification(self):
        mod = _load_module()
        service = _make_service()
        service.sites().get().execute.return_value = {
            "permissionLevel": "siteOwner",
            "siteVerificationInfo": {"verificationState": "VERIFIED"},
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_site_details("https://example.com/")
        data = json.loads(result)
        self.assertEqual(data["permission_level"], "siteOwner")
        self.assertEqual(data["verification"]["state"], "VERIFIED")

    async def test_handles_404(self):
        mod = _load_module()
        with patch("gsc_server.get_gsc_service", side_effect=Exception("404")):
            result = await mod.get_site_details("https://example.com/")
        self.assertIn("Error", result)


# ---------------------------------------------------------------------------
# TestGetSitemaps
# ---------------------------------------------------------------------------

class TestGetSitemaps(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_sitemap_list(self):
        mod = _load_module()
        service = _make_service()
        service.sitemaps().list().execute.return_value = {
            "sitemap": [
                {"path": "https://example.com/sitemap.xml", "errors": "0", "warnings": "1",
                 "contents": [{"type": "web", "submitted": "1000"}]},
            ]
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_sitemaps("https://example.com/")
        data = json.loads(result)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["sitemaps"][0]["warnings"], 1)
        self.assertEqual(data["sitemaps"][0]["status"], "Has warnings")
        self.assertEqual(data["sitemaps"][0]["indexed_urls"], "1000")

    async def test_no_sitemaps_returns_message(self):
        mod = _load_module()
        service = _make_service()
        service.sitemaps().list().execute.return_value = {}
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_sitemaps("https://example.com/")
        self.assertIsInstance(result, str)
        self.assertIn("No sitemaps", result)


# ---------------------------------------------------------------------------
# TestInspectUrl
# ---------------------------------------------------------------------------

class TestInspectUrl(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_with_verdict(self):
        mod = _load_module()
        service = _make_service()
        service.urlInspection().index().inspect().execute.return_value = {
            "inspectionResult": {
                "indexStatusResult": {
                    "verdict": "PASS",
                    "coverageState": "Submitted and indexed",
                    "pageFetchState": "SUCCESSFUL",
                    "robotsTxtState": "ALLOWED",
                    "lastCrawlTime": "2026-04-01T10:00:00Z",
                }
            }
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.inspect_url_enhanced("https://example.com/", "https://example.com/page/")
        data = json.loads(result)
        self.assertEqual(data["verdict"], "PASS")
        self.assertEqual(data["page_url"], "https://example.com/page/")
        self.assertIn("last_crawled", data)


# ---------------------------------------------------------------------------
# TestBatchUrlInspection
# ---------------------------------------------------------------------------

class TestBatchUrlInspection(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_with_results(self):
        mod = _load_module()
        service = _make_service()
        service.urlInspection().index().inspect().execute.return_value = {
            "inspectionResult": {
                "indexStatusResult": {
                    "verdict": "PASS",
                    "coverageState": "Submitted and indexed",
                    "lastCrawlTime": "2026-04-01T10:00:00Z",
                }
            }
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.batch_url_inspection(
                "https://example.com/",
                "https://example.com/a/\nhttps://example.com/b/"
            )
        data = json.loads(result)
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["results"][0]["verdict"], "PASS")

    async def test_batch_limit_enforced_at_10_urls(self):
        mod = _load_module()
        with patch("gsc_server.get_gsc_service", return_value=_make_service()):
            urls = "\n".join([f"https://example.com/{i}/" for i in range(11)])
            result = await mod.batch_url_inspection("https://example.com/", urls)
        self.assertIn("Too many URLs", result)


# ---------------------------------------------------------------------------
# TestCheckIndexingIssues
# ---------------------------------------------------------------------------

class TestCheckIndexingIssues(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_with_summary(self):
        mod = _load_module()
        service = _make_service()
        service.urlInspection().index().inspect().execute.return_value = {
            "inspectionResult": {
                "indexStatusResult": {
                    "verdict": "PASS",
                    "coverageState": "Submitted and indexed",
                }
            }
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.check_indexing_issues(
                "https://example.com/", "https://example.com/page/"
            )
        data = json.loads(result)
        self.assertIn("summary", data)
        self.assertEqual(data["summary"]["total_checked"], 1)
        self.assertEqual(data["summary"]["indexed"], 1)


# ---------------------------------------------------------------------------
# TestGetPerformanceOverview
# ---------------------------------------------------------------------------

class TestGetPerformanceOverview(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_with_totals_and_trend(self):
        mod = _load_module()
        service = _make_service()
        service.searchanalytics().query().execute.side_effect = [
            {"rows": [{"keys": [], "clicks": 500, "impressions": 5000, "ctr": 0.1, "position": 12.0}]},
            {"rows": [
                {"keys": ["2026-04-01"], "clicks": 250, "impressions": 2500, "ctr": 0.1, "position": 12.0},
                {"keys": ["2026-04-02"], "clicks": 250, "impressions": 2500, "ctr": 0.1, "position": 12.0},
            ]},
        ]
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_performance_overview("https://example.com/")
        data = json.loads(result)
        self.assertEqual(data["totals"]["clicks"], 500)
        self.assertEqual(len(data["daily_trend"]), 2)


# ---------------------------------------------------------------------------
# TestGetAdvancedSearchAnalytics
# ---------------------------------------------------------------------------

class TestGetAdvancedSearchAnalytics(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_with_rows(self):
        mod = _load_module()
        service = _make_service()
        service.searchanalytics().query().execute.return_value = {
            "rows": [
                {"keys": ["seo"], "clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 5.0},
            ]
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_advanced_search_analytics("https://example.com/")
        data = json.loads(result)
        self.assertEqual(data["rows"][0]["query"], "seo")
        self.assertIn("pagination", data)

    async def test_invalid_filters_json_returns_error_string(self):
        mod = _load_module()
        with patch("gsc_server.get_gsc_service", return_value=_make_service()):
            result = await mod.get_advanced_search_analytics(
                "https://example.com/", filters="not valid json"
            )
        self.assertIn("Invalid filters", result)

    async def test_pagination_info_included(self):
        mod = _load_module()
        service = _make_service()
        # Return exactly row_limit rows → has_more=True
        rows = [{"keys": [f"q{i}"], "clicks": 1, "impressions": 10, "ctr": 0.1, "position": 5.0}
                for i in range(10)]
        service.searchanalytics().query().execute.return_value = {"rows": rows}
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_advanced_search_analytics(
                "https://example.com/", row_limit=10
            )
        data = json.loads(result)
        self.assertTrue(data["pagination"]["has_more"])
        self.assertEqual(data["pagination"]["next_start_row"], 10)


# ---------------------------------------------------------------------------
# TestCompareSearchPeriods
# ---------------------------------------------------------------------------

class TestCompareSearchPeriods(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_comparison(self):
        mod = _load_module()
        service = _make_service()
        service.searchanalytics().query().execute.side_effect = [
            {"rows": [{"keys": ["seo"], "clicks": 100, "impressions": 1000, "ctr": 0.1, "position": 5.0}]},
            {"rows": [{"keys": ["seo"], "clicks": 120, "impressions": 1100, "ctr": 0.11, "position": 4.5}]},
        ]
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.compare_search_periods(
                "https://example.com/",
                "2026-03-01", "2026-03-28",
                "2026-04-01", "2026-04-07",
            )
        data = json.loads(result)
        self.assertIn("comparison", data)
        self.assertEqual(len(data["comparison"]), 1)
        self.assertEqual(data["comparison"][0]["key"], ["seo"])


# ---------------------------------------------------------------------------
# TestGetSearchByPageQuery
# ---------------------------------------------------------------------------

class TestGetSearchByPageQuery(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_with_totals(self):
        mod = _load_module()
        service = _make_service()
        service.searchanalytics().query().execute.return_value = {
            "rows": [
                {"keys": ["best seo tool"], "clicks": 50, "impressions": 500, "ctr": 0.1, "position": 7.5},
            ]
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_search_by_page_query(
                "https://example.com/", "https://example.com/blog/seo/"
            )
        data = json.loads(result)
        self.assertEqual(data["page_url"], "https://example.com/blog/seo/")
        self.assertEqual(data["totals"]["clicks"], 50)
        self.assertEqual(data["rows"][0]["query"], "best seo tool")


# ---------------------------------------------------------------------------
# TestListSitemapsEnhanced
# ---------------------------------------------------------------------------

class TestListSitemapsEnhanced(unittest.IsolatedAsyncioTestCase):

    async def test_returns_json_sitemap_list(self):
        mod = _load_module()
        service = _make_service()
        service.sitemaps().list().execute.return_value = {
            "sitemap": [
                {"path": "https://example.com/sitemap.xml", "errors": "0", "warnings": "0",
                 "isSitemapsIndex": False, "isPending": False},
            ]
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.list_sitemaps_enhanced("https://example.com/")
        data = json.loads(result)
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["pending_count"], 0)

    async def test_warning_status_correctly_set(self):
        """Regression: status should be 'Has warnings' when warnings > 0."""
        mod = _load_module()
        service = _make_service()
        service.sitemaps().list().execute.return_value = {
            "sitemap": [
                {"path": "https://example.com/sitemap.xml", "errors": "0", "warnings": "3"},
            ]
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.list_sitemaps_enhanced("https://example.com/")
        # list_sitemaps_enhanced returns JSON without a status field (it's in get_sitemaps),
        # but warnings count must still be 3
        data = json.loads(result)
        self.assertEqual(data["sitemaps"][0]["warnings"], 3)


# ---------------------------------------------------------------------------
# TestGetSitemapDetails
# ---------------------------------------------------------------------------

class TestGetSitemapDetails(unittest.IsolatedAsyncioTestCase):

    async def test_get_details_returns_json(self):
        mod = _load_module()
        service = _make_service()
        service.sitemaps().get().execute.return_value = {
            "isSitemapsIndex": False,
            "isPending": False,
            "errors": "0",
            "warnings": "0",
            "contents": [{"type": "web", "submitted": 500, "indexed": 480}],
        }
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.get_sitemap_details("https://example.com/", "https://example.com/sitemap.xml")
        data = json.loads(result)
        self.assertEqual(data["type"], "Sitemap")
        self.assertEqual(data["status"], "processed")
        self.assertEqual(data["content_breakdown"][0]["submitted"], 500)


# ---------------------------------------------------------------------------
# TestSafetyGuards
# ---------------------------------------------------------------------------

class TestSafetyGuards(unittest.IsolatedAsyncioTestCase):

    async def test_add_site_blocked_by_default(self):
        mod = _load_module({"GSC_ALLOW_DESTRUCTIVE": "false"})
        result = await mod.add_site("https://newsite.com/")
        self.assertIn("Safety", result)
        self.assertIn("read_only", result)

    async def test_delete_site_blocked_by_default(self):
        mod = _load_module({"GSC_ALLOW_DESTRUCTIVE": "false"})
        result = await mod.delete_site("https://newsite.com/")
        self.assertIn("Safety", result)

    async def test_delete_sitemap_blocked_by_default(self):
        mod = _load_module({"GSC_ALLOW_DESTRUCTIVE": "false"})
        result = await mod.delete_sitemap("https://example.com/", "https://example.com/sitemap.xml")
        self.assertIn("Safety", result)

    async def test_submit_sitemap_blocked_in_read_only_mode(self):
        mod = _load_module({"GSC_ALLOW_DESTRUCTIVE": "true"})
        with patch("gsc_server.get_gsc_service") as mock_service:
            result = await mod.submit_sitemap(
                "https://example.com/",
                "https://example.com/sitemap.xml",
            )
        self.assertIn("Safety", result)
        mock_service.assert_not_called()

    async def test_destructive_write_blocked_without_flag_in_read_write_mode(self):
        mod = _load_module({
            "GSC_ACCESS_MODE": "read_write",
            "GSC_ALLOW_DESTRUCTIVE": "false",
        })
        result = await mod.delete_site("https://example.com/")
        self.assertIn("Safety", result)
        self.assertIn("GSC_ALLOW_DESTRUCTIVE", result)

    async def test_add_site_allowed_when_flag_set(self):
        mod = _load_module({
            "GSC_ACCESS_MODE": "read_write",
            "GSC_ALLOW_DESTRUCTIVE": "true",
        })
        service = _make_service()
        service.sites().add().execute.return_value = {}
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.add_site("https://newsite.com/")
        self.assertNotIn("Safety", result)

    async def test_delete_site_allowed_when_flag_set(self):
        mod = _load_module({
            "GSC_ACCESS_MODE": "read_write",
            "GSC_ALLOW_DESTRUCTIVE": "true",
        })
        service = _make_service()
        service.sites().delete().execute.return_value = {}
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.delete_site("https://example.com/")
        self.assertNotIn("Safety", result)

    async def test_delete_sitemap_allowed_when_flag_set(self):
        mod = _load_module({
            "GSC_ACCESS_MODE": "read_write",
            "GSC_ALLOW_DESTRUCTIVE": "true",
        })
        service = _make_service()
        service.sitemaps().delete().execute.return_value = {}
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.delete_sitemap("https://example.com/", "https://example.com/sitemap.xml")
        self.assertNotIn("Safety", result)

    async def test_submit_sitemap_allowed_in_read_write_mode(self):
        mod = _load_module({"GSC_ACCESS_MODE": "read_write"})
        service = _make_service()
        service.sitemaps().submit().execute.return_value = {}
        service.sitemaps().get().execute.return_value = {}
        with patch("gsc_server.get_gsc_service", return_value=service):
            result = await mod.submit_sitemap(
                "https://example.com/",
                "https://example.com/sitemap.xml",
            )
        self.assertIn("Successfully submitted", result)


# ---------------------------------------------------------------------------
# TestHardenedProfile
# ---------------------------------------------------------------------------

class TestHardenedProfile(unittest.IsolatedAsyncioTestCase):

    async def test_default_profile_registers_read_only_tools_only(self):
        mod = _load_module()
        tools = await mod.mcp.list_tools()
        names = {tool.name for tool in tools}

        self.assertEqual(
            mod.SCOPES,
            ["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        self.assertTrue(mod.TOKEN_FILE.endswith("token.readonly.json"))
        for write_tool in {
            "add_site",
            "delete_site",
            "submit_sitemap",
            "delete_sitemap",
            "manage_sitemaps",
            "reauthenticate",
        }:
            self.assertNotIn(write_tool, names)

    async def test_read_write_profile_registers_write_tools_only_when_explicit(self):
        mod = _load_module({
            "GSC_ACCESS_MODE": "read_write",
            "GSC_ENABLE_REAUTH_TOOL": "true",
        })
        tools = await mod.mcp.list_tools()
        names = {tool.name for tool in tools}

        self.assertEqual(
            mod.SCOPES,
            ["https://www.googleapis.com/auth/webmasters"],
        )
        self.assertTrue(mod.TOKEN_FILE.endswith("token.json"))
        self.assertIn("submit_sitemap", names)
        self.assertIn("reauthenticate", names)

    async def test_get_capabilities_never_starts_oauth(self):
        mod = _load_module({"GSC_SKIP_OAUTH": "false"})
        with patch("gsc_server.get_gsc_service") as mock_service, \
             patch.object(mod, "_OLD_TOKEN", os.path.join(mod.SCRIPT_DIR, "missing-legacy-token.json")):
            result = await mod.get_capabilities()

        data = json.loads(result)
        self.assertEqual(data["access_mode"], "read_only")
        self.assertTrue(data["auth_status_is_non_interactive"])
        self.assertFalse(data["legacy_broad_scope_token_present_not_used"])
        mock_service.assert_not_called()

    async def test_get_capabilities_flags_ignored_legacy_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            legacy_token = os.path.join(tmpdir, "token.json")
            with open(legacy_token, "w") as token_file:
                token_file.write('{"legacy": true}')

            mod = _load_module({"GSC_CONFIG_DIR": tmpdir})
            with patch.object(mod, "_OLD_TOKEN", legacy_token):
                data = json.loads(await mod.get_capabilities())

        self.assertTrue(data["legacy_broad_scope_token_present_not_used"])

    def test_remote_transport_is_rejected(self):
        mod = _load_module()
        with patch.dict(os.environ, {"MCP_TRANSPORT": "sse"}, clear=False), \
             patch.object(mod.mcp, "run") as mock_run:
            with self.assertRaises(ValueError):
                mod.main()
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# TestReauthenticate
# ---------------------------------------------------------------------------

class TestReauthenticate(unittest.IsolatedAsyncioTestCase):

    async def test_replaces_token_file_after_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = os.path.join(tmpdir, "token.json")
            with open(token_path, "w") as token_file:
                token_file.write('{"old": "token"}')
            secrets_path = os.path.join(tmpdir, "secrets.json")
            with open(secrets_path, "w") as secrets_file:
                secrets_file.write("{}")

            mod = _load_module()

            mock_creds = MagicMock()
            mock_creds.to_json.return_value = '{"token": "new"}'

            with patch.object(mod, "TOKEN_FILE", token_path), \
                 patch.object(mod, "OAUTH_CLIENT_SECRETS_FILE", secrets_path), \
                 patch("gsc_server.InstalledAppFlow") as mock_flow_cls:
                mock_flow = MagicMock()
                mock_flow.run_local_server.return_value = mock_creds
                mock_flow_cls.from_client_secrets_file.return_value = mock_flow
                result = await mod.reauthenticate()

            self.assertIn("Successfully authenticated", result)
            self.assertIn("Previous session replaced", result)
            self.assertTrue(os.path.exists(token_path))
            with open(token_path) as token_file:
                self.assertEqual(token_file.read(), '{"token": "new"}')

    async def test_missing_secrets_preserves_existing_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token_path = os.path.join(tmpdir, "token.json")
            with open(token_path, "w") as token_file:
                token_file.write('{"old": "token"}')
            mod = _load_module()
            with patch.object(mod, "TOKEN_FILE", token_path), \
                 patch.object(mod, "OAUTH_CLIENT_SECRETS_FILE", os.path.join(tmpdir, "no_secrets.json")):
                result = await mod.reauthenticate()
            self.assertIn("Error", result)
            with open(token_path) as token_file:
                self.assertEqual(token_file.read(), '{"old": "token"}')


# ---------------------------------------------------------------------------
# TestStdoutClean
# ---------------------------------------------------------------------------

class TestStdoutClean(unittest.TestCase):

    def test_auth_fallback_does_not_write_to_stdout(self):
        """get_gsc_service must not print() to stdout on OAuth failure (prevents MCP corruption)."""
        mod = _load_module({"GSC_SKIP_OAUTH": "false"})

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        try:
            with patch("gsc_server.get_gsc_service_oauth", side_effect=RuntimeError("no token")), \
                 patch("gsc_server.service_account.Credentials.from_service_account_file",
                        side_effect=Exception("no file")):
                try:
                    mod.get_gsc_service()
                except Exception:
                    pass
        finally:
            sys.stdout = old_stdout

        stdout_output = captured.getvalue()
        self.assertEqual(stdout_output, "", f"Unexpected stdout: {stdout_output!r}")


if __name__ == "__main__":
    unittest.main()
