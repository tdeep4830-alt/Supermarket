"""
E2E Test Fixtures (Playwright).

Ref: .blueprint/infra.md §7 - Automated Testing
Ref: .blueprint/code_structure.md §5 - Test Isolation

All E2E tests use a SEPARATE test database managed by Django's test runner
(via --reuse-db or TransactionTestCase). Playwright talks to a live server
that is backed by this throwaway DB, so local development data is NEVER
touched.

Key design decisions:
- `live_server` fixture spins up Django's LiveServerTestCase on a random port
- Seed data is created per-test via Django ORM, then auto-rolled-back
- Playwright browser context is isolated per test (fresh cookies / storage)
"""
import uuid
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import Page

from apps.products.models import Category, Product, Stock
from apps.delivery.models import DeliverySlot

User = get_user_model()

# ---------------------------------------------------------------------------
# Unique-per-run prefix to avoid collisions if tests run in parallel
# ---------------------------------------------------------------------------
RUN_ID = uuid.uuid4().hex[:8]


def _unique(base: str) -> str:
    """Return a name that is unique per test run."""
    return f"{base}_{RUN_ID}"


# ---------------------------------------------------------------------------
# Django data fixtures (auto-cleaned by @pytest.mark.django_db transaction)
# ---------------------------------------------------------------------------


@pytest.fixture
def seed_category(db) -> Category:
    """Create a test category."""
    return Category.objects.create(
        name=_unique("E2E Fruits"),
        slug=_unique("e2e-fruits"),
        is_active=True,
    )


@pytest.fixture
def seed_product(db, seed_category) -> Product:
    """Create a test product with stock."""
    product = Product.objects.create(
        category=seed_category,
        name=_unique("E2E Apple"),
        description="Fresh apple for E2E testing",
        price=Decimal("12.50"),
        is_active=True,
    )
    Stock.objects.create(product=product, quantity=50)
    return product


@pytest.fixture
def seed_delivery_slot(db) -> DeliverySlot:
    """Create a test delivery slot for tomorrow."""
    tomorrow = date.today() + timedelta(days=1)
    return DeliverySlot.objects.create(
        date=tomorrow,
        start_time=time(9, 0),
        end_time=time(12, 0),
        max_capacity=20,
        current_count=0,
        is_active=True,
    )


@pytest.fixture
def seed_admin_user(db) -> User:
    """Create an admin (staff) user for backend seeding."""
    return User.objects.create_superuser(
        username=_unique("e2e_admin"),
        email=f"{_unique('e2e_admin')}@test.local",
        password="AdminPass123!",
    )


# ---------------------------------------------------------------------------
# Playwright helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def base_url(live_server) -> str:
    """Return the live-server base URL for Playwright."""
    return live_server.url


@pytest.fixture
def e2e_page(page: Page, base_url: str) -> Page:
    """Playwright page pre-configured with base URL and default timeout."""
    page.set_default_timeout(15_000)
    page.set_default_navigation_timeout(15_000)
    return page


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


@pytest.fixture
def register_user(e2e_page: Page, base_url: str):
    """
    Factory fixture: register a fresh user via the UI and return credentials.

    Usage:
        creds = register_user()
        # creds == {"username": "...", "password": "..."}
    """

    def _register(
        username: str | None = None,
        password: str = "TestPass123!",
    ) -> dict[str, str]:
        uname = username or _unique("e2euser")
        e2e_page.goto(base_url)

        # Click Sign Up
        e2e_page.get_by_role("button", name="Sign Up").click()

        # Fill registration form
        e2e_page.get_by_label("Username").fill(uname)
        e2e_page.get_by_label("Email").fill(f"{uname}@test.local")
        e2e_page.get_by_label("Password", exact=True).fill(password)
        e2e_page.get_by_label("Confirm Password").fill(password)

        # Submit
        e2e_page.get_by_role("button", name="Create Account").click()

        # Wait for redirect back to products
        e2e_page.wait_for_selector("text=Online Supermarket", timeout=10_000)

        return {"username": uname, "password": password}

    return _register
