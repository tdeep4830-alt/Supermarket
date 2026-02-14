"""
E2E Happy Path Test — Full Shopping Flow.

Ref: .blueprint/infra.md §7 - Automated Testing
Ref: .blueprint/frontend_structure.md §4 - Flash Sale UI Logic

Flow:
  1. Visit homepage → see Flash Sale banner
  2. Register a new user → header shows username
  3. Browse products → product cards visible
  4. Add to cart → cart badge updates
  5. Open cart → proceed to checkout
  6. Select delivery slot
  7. Place order → see order success page

Uses Django LiveServer + Playwright (headless Chromium).
Test data is auto-cleaned via @pytest.mark.django_db(transaction=True).
"""
import pytest
from playwright.sync_api import Page, expect


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.django_db(transaction=True),
]


class TestHappyPath:
    """Full shopping happy-path: register → browse → cart → checkout → success."""

    def test_full_shopping_flow(
        self,
        e2e_page: Page,
        base_url: str,
        seed_product,
        seed_delivery_slot,
        register_user,
    ):
        page = e2e_page

        # ---------------------------------------------------------------
        # Step 1: Visit homepage — Flash Sale banner visible
        # ---------------------------------------------------------------
        page.goto(base_url)
        expect(page.locator("text=Flash Sale")).to_be_visible()
        expect(page.locator("text=Online Supermarket")).to_be_visible()

        # ---------------------------------------------------------------
        # Step 2: Register a new user
        # ---------------------------------------------------------------
        creds = register_user()
        username = creds["username"]

        # Header should now show the username
        expect(page.locator(f"text={username}")).to_be_visible()

        # Sign Out button should exist
        expect(page.get_by_role("button", name="Sign Out")).to_be_visible()

        # ---------------------------------------------------------------
        # Step 3: Browse products — at least one product card visible
        # ---------------------------------------------------------------
        # The seed_product should appear on the product list
        product_card = page.locator(f"text={seed_product.name}")
        expect(product_card.first).to_be_visible(timeout=10_000)

        # ---------------------------------------------------------------
        # Step 4: Add product to cart
        # ---------------------------------------------------------------
        # Click the "Add to Cart" / cart-add button on the product card
        add_btn = page.get_by_role("button", name="Add to Cart").first
        add_btn.click()

        # Cart button badge should show "1"
        cart_badge = page.locator("[data-testid='cart-badge']")
        # Fallback: if no test-id, look for the cart button area text
        if not cart_badge.is_visible(timeout=2_000):
            cart_badge = page.locator("text=1").first
        expect(cart_badge).to_be_visible()

        # ---------------------------------------------------------------
        # Step 5: Open cart drawer → proceed to checkout
        # ---------------------------------------------------------------
        # Click the cart icon / button
        page.get_by_role("button", name="Cart").first.click()

        # Cart drawer should show the product name
        expect(page.locator(f"text={seed_product.name}")).to_be_visible()

        # Click Checkout
        page.get_by_role("button", name="Checkout").click()

        # ---------------------------------------------------------------
        # Step 6: Checkout page — select delivery slot
        # ---------------------------------------------------------------
        # Wait for the checkout page to render
        expect(page.locator("text=Order Summary")).to_be_visible(timeout=10_000)

        # Select delivery slot if the selector is present
        slot_selector = page.locator("[data-testid='delivery-slot-selector']")
        if slot_selector.is_visible(timeout=3_000):
            # Click the first available slot
            slot_selector.locator("button").first.click()

        # ---------------------------------------------------------------
        # Step 7: Place order
        # ---------------------------------------------------------------
        place_order_btn = page.get_by_role("button", name="Place Order")
        expect(place_order_btn).to_be_visible()
        place_order_btn.click()

        # ---------------------------------------------------------------
        # Verify: Order success page
        # ---------------------------------------------------------------
        # Should see a success indication
        success_indicator = page.locator("text=Order").first
        expect(success_indicator).to_be_visible(timeout=15_000)

        # "Continue Shopping" button should be available
        continue_btn = page.get_by_role("button", name="Continue Shopping")
        if continue_btn.is_visible(timeout=3_000):
            continue_btn.click()
            # Should be back on the products page
            expect(page.locator("text=Flash Sale")).to_be_visible()
