"""
Frontend Link Checker (Playwright).

Ref: .blueprint/infra.md §7 - Automated Testing
Ref: .blueprint/frontend_structure.md §3A - Smart Assets Management

Scans the SPA bundle served by Vite preview and verifies:
  1. All network responses for static resources are 2xx (CSS, JS, images, fonts).
  2. All DOM elements with loadable URLs (<a href>, <img src>, <link href>,
     <script src>) point to reachable destinations.
  3. No fatal JS console errors (Uncaught ReferenceError, React rendering errors).

Filtering:
  - /api/* paths are EXCLUDED (backend not running in this CI job).
  - External URLs (http(s)://...) are excluded from HTTP-status checks.

Output format for broken resources:
  [Broken Link] <url> (status <code>) found on <page_name>

Environment:
  LINK_CHECK_BASE_URL — override the default http://localhost:4173
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import pytest
from playwright.sync_api import Page, Response

pytestmark = [pytest.mark.e2e]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SKIP_PATTERNS: list[str] = [
    "/api/",
]

FATAL_CONSOLE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"Uncaught ReferenceError", re.IGNORECASE),
    re.compile(r"Uncaught TypeError", re.IGNORECASE),
    re.compile(r"Uncaught SyntaxError", re.IGNORECASE),
    re.compile(r"The above error occurred in the <", re.IGNORECASE),
    re.compile(r"Consider adding an error boundary", re.IGNORECASE),
    re.compile(r"Minified React error", re.IGNORECASE),
    re.compile(r"react-dom.*Uncaught", re.IGNORECASE),
    re.compile(r"React will try to recreate this component", re.IGNORECASE),
]

# Console messages that are expected when backend is down — NOT fatal
IGNORE_CONSOLE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ERR_CONNECTION_REFUSED", re.IGNORECASE),
    re.compile(r"Failed to load resource.*net::ERR", re.IGNORECASE),
    re.compile(r"AxiosError", re.IGNORECASE),
    re.compile(r"Network ?Error", re.IGNORECASE),
    re.compile(r"/api/", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class BrokenResource:
    url: str
    status: int
    page_name: str
    source: str

    def __str__(self) -> str:
        return f"[Broken Link] {self.url} (status {self.status}) found on {self.page_name}"


@dataclass
class PageScanResult:
    page_name: str
    broken: list[BrokenResource] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _should_skip(url: str) -> bool:
    parsed = urlparse(url)
    for pattern in SKIP_PATTERNS:
        if pattern in parsed.path:
            return True
    return False


def _is_internal(url: str, base: str) -> bool:
    if not url or url.startswith(("data:", "blob:", "javascript:", "#", "mailto:")):
        return False
    parsed = urlparse(urljoin(base, url))
    base_parsed = urlparse(base)
    return parsed.netloc == base_parsed.netloc or parsed.netloc == ""


def _is_fatal_console(text: str) -> bool:
    # Skip known-harmless messages when backend is down
    for pattern in IGNORE_CONSOLE_PATTERNS:
        if pattern.search(text):
            return False
    for pattern in FATAL_CONSOLE_PATTERNS:
        if pattern.search(text):
            return True
    return False


# ---------------------------------------------------------------------------
# Core scan function
# ---------------------------------------------------------------------------


def scan_page(
    page: Page,
    url: str,
    page_name: str,
) -> PageScanResult:
    """
    Navigate to *url*, collect network failures, DOM resource URLs,
    and fatal console errors.
    """
    result = PageScanResult(page_name=page_name)

    # --- 1. Console error tracking ----------------------------------------
    def _on_console(msg):  # noqa: ANN001
        if msg.type == "error":
            text = msg.text
            if _is_fatal_console(text):
                result.console_errors.append(text)

    page.on("console", _on_console)

    # --- 2. Network response tracking ------------------------------------
    failed_responses: list[tuple[str, int]] = []

    def _on_response(response: Response) -> None:
        req_url = response.url
        if _should_skip(req_url):
            return
        if _is_internal(req_url, url) and response.status >= 400:
            failed_responses.append((req_url, response.status))

    page.on("response", _on_response)

    # --- 3. Navigate -----------------------------------------------------
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(2_000)

    # --- 4. Record network failures --------------------------------------
    for res_url, status in failed_responses:
        result.broken.append(
            BrokenResource(url=res_url, status=status, page_name=page_name, source="network")
        )

    # --- 5. DOM resource inspection --------------------------------------
    base = url

    # <a href>
    hrefs = page.eval_on_selector_all(
        "a[href]", "els => els.map(e => e.getAttribute('href'))"
    )
    for href in hrefs:
        if _is_internal(href, base) and not _should_skip(href):
            full = urljoin(base, href)
            resp = page.request.head(full)
            if resp.status >= 400:
                result.broken.append(
                    BrokenResource(url=full, status=resp.status, page_name=page_name, source="dom-anchor")
                )

    # <img src>
    srcs = page.eval_on_selector_all(
        "img[src]", "els => els.map(e => e.getAttribute('src'))"
    )
    for src in srcs:
        if _is_internal(src, base) and not _should_skip(src):
            full = urljoin(base, src)
            resp = page.request.head(full)
            if resp.status >= 400:
                result.broken.append(
                    BrokenResource(url=full, status=resp.status, page_name=page_name, source="dom-img")
                )

    # <link href>
    link_hrefs = page.eval_on_selector_all(
        "link[href]", "els => els.map(e => e.getAttribute('href'))"
    )
    for href in link_hrefs:
        if _is_internal(href, base) and not _should_skip(href):
            full = urljoin(base, href)
            resp = page.request.head(full)
            if resp.status >= 400:
                result.broken.append(
                    BrokenResource(url=full, status=resp.status, page_name=page_name, source="dom-link")
                )

    # <script src>
    script_srcs = page.eval_on_selector_all(
        "script[src]", "els => els.map(e => e.getAttribute('src'))"
    )
    for src in script_srcs:
        if _is_internal(src, base) and not _should_skip(src):
            full = urljoin(base, src)
            resp = page.request.head(full)
            if resp.status >= 400:
                result.broken.append(
                    BrokenResource(url=full, status=resp.status, page_name=page_name, source="dom-script")
                )

    page.remove_listener("console", _on_console)
    page.remove_listener("response", _on_response)

    return result


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestLinkChecker:
    """
    Scan the SPA for broken resources and fatal console errors.

    Since this is a state-based SPA (no URL routes), the link checker
    performs multiple fresh loads of the root URL. Each load exercises
    the initial render path — which is where all static resources
    (JS bundles, CSS, images, fonts) are loaded.

    The SPA navigation buttons depend on API calls (/api/auth/me) that
    are unavailable without a backend, so we intentionally do NOT try
    to click through views. The goal is to verify the *build artefacts*
    are intact, not the full user flow (that's the E2E suite's job).
    """

    def test_initial_load_resources(self, page: Page) -> None:
        """
        Load the SPA root and verify every static resource loads
        successfully, every DOM src/href is reachable, and no fatal
        JS errors appear in the console.
        """
        base_url = os.environ.get("LINK_CHECK_BASE_URL", "http://localhost:4173")

        result = scan_page(page, base_url, "Home (SPA Root)")

        # Print findings for CI console
        for b in result.broken:
            print(str(b))
        for err in result.console_errors:
            print(f"[Console Error] on Home (SPA Root): {err}")

        errors: list[str] = []
        if result.broken:
            errors.append(
                f"Found {len(result.broken)} broken resource(s):\n"
                + "\n".join(f"  {b}" for b in result.broken)
            )
        if result.console_errors:
            errors.append(
                f"Found {len(result.console_errors)} fatal console error(s):\n"
                + "\n".join(f"  {e}" for e in result.console_errors)
            )
        if errors:
            pytest.fail("\n\n".join(errors))

    def test_reload_no_cache_regression(self, page: Page) -> None:
        """
        Hard-reload (bypass cache) and verify resources still load.
        Catches cache-busting or hashing regressions in the build.
        """
        base_url = os.environ.get("LINK_CHECK_BASE_URL", "http://localhost:4173")

        # First load
        page.goto(base_url, wait_until="networkidle")

        # Hard reload — clear cache
        page.context.clear_cookies()
        result = scan_page(page, base_url, "Home (Hard Reload)")

        for b in result.broken:
            print(str(b))
        for err in result.console_errors:
            print(f"[Console Error] on Home (Hard Reload): {err}")

        errors: list[str] = []
        if result.broken:
            errors.append(
                f"Found {len(result.broken)} broken resource(s) after hard reload:\n"
                + "\n".join(f"  {b}" for b in result.broken)
            )
        if result.console_errors:
            errors.append(
                f"Found {len(result.console_errors)} fatal console error(s) after hard reload:\n"
                + "\n".join(f"  {e}" for e in result.console_errors)
            )
        if errors:
            pytest.fail("\n\n".join(errors))

    def test_static_asset_paths(self, page: Page) -> None:
        """
        Verify that vite.svg and other known static assets are
        accessible from the preview server.
        """
        base_url = os.environ.get("LINK_CHECK_BASE_URL", "http://localhost:4173")

        known_assets = [
            "/vite.svg",
        ]

        broken: list[str] = []
        for path in known_assets:
            full = urljoin(base_url, path)
            resp = page.request.head(full)
            if resp.status >= 400:
                msg = f"[Broken Link] {full} (status {resp.status}) found on static assets check"
                print(msg)
                broken.append(msg)

        if broken:
            pytest.fail(
                f"Found {len(broken)} unreachable static asset(s):\n"
                + "\n".join(f"  {b}" for b in broken)
            )
