"""
E2E Edge Case Tests.

Ref: .blueprint/code_structure.md §6 - DoD edge cases
Ref: .blueprint/frontend_structure.md §4B - Optimistic UI error handling

Cases:
  1. Unauthenticated checkout → redirect to login → auto-resume checkout
  2. Out-of-stock product → add-to-cart button disabled / sold-out label
"""
import pytest
from decimal import Decimal
from playwright.sync_api import Page, expect

from tests.e2e.conftest import _unique

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.django_db(transaction=True),
]


class TestUnauthenticatedCheckout:
    """Verify that unauthenticated users are redirected to login
    and can resume checkout after signing in."""

    def test_redirect_to_login_then_resume_checkout(
        self,
        e2e_page: Page,
        base_url: str,
        seed_product,
    ):
        page = e2e_page
        page.goto(base_url)

        # Wait for products to load
        expect(page.locator(f"text={seed_product.name}").first).to_be_visible(
            timeout=10_000
        )

        # Add product to cart (no auth needed for local cart)
        page.get_by_role("button", name="Add to Cart").first.click()

        # Open cart → try to checkout
        page.get_by_role("button", name="Cart").first.click()
        page.get_by_role("button", name="Checkout").click()

        # Should be redirected to login page
        login_heading = page.locator("text=Sign In").first
        expect(login_heading).to_be_visible(timeout=5_000)

        # Register so we can authenticate
        page.get_by_role("button", name="Create Account").first.click()
        uname = _unique("edgeuser")
        page.get_by_label("Username").fill(uname)
        page.get_by_label("Email").fill(f"{uname}@test.local")
        page.get_by_label("Password", exact=True).fill("TestPass123!")
        page.get_by_label("Confirm Password").fill("TestPass123!")
        page.get_by_role("button", name="Create Account").click()

        # After successful auth, should auto-resume to checkout
        # (pendingCheckout flag should route to checkout page)
        checkout_indicator = page.locator("text=Order Summary")
        expect(checkout_indicator).to_be_visible(timeout=10_000)


class TestOutOfStockProduct:
    """Verify that out-of-stock products cannot be added to cart."""

    def test_sold_out_product_button_disabled(
        self,
        e2e_page: Page,
        base_url: str,
        seed_category,
        db,
    ):
        from apps.products.models import Product, Stock

        # Create an out-of-stock product
        product = Product.objects.create(
            category=seed_category,
            name=_unique("E2E Sold Out Item"),
            description="This item has zero stock",
            price=Decimal("5.00"),
            is_active=True,
        )
        Stock.objects.create(product=product, quantity=0)

        page = e2e_page
        page.goto(base_url)

        # Wait for the product to appear
        product_card = page.locator(f"text={product.name}")
        expect(product_card.first).to_be_visible(timeout=10_000)

        # The add-to-cart button should be disabled or show "Sold Out"
        # Look for a disabled button or a "Sold Out" / "Out of Stock" label
        sold_out = page.locator(
            f"text=Sold Out, text=Out of Stock, button[disabled]"
        ).first
        expect(sold_out).to_be_visible(timeout=5_000)
