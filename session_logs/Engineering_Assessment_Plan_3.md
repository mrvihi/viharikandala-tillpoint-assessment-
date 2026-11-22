
Loading older messages…
Continued from
Engineering Assessment Plan (2)
C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tillpoint\pricing.py
"""Order maths: subtotal, coupon discount, tax, total. Integer cents throughout."""

# Sales tax in basis points (1/100 of a percent) by region.
TAX_BPS = {"NONE": 0, "CA": 725, "NY": 888, "TX": 625, "DE": 1900}


class CouponRejected(Exception):
    pass


def subtotal(lines):
    """lines: iterable of (unit_price_cents, qty)."""
    return sum(price * qty for price, qty in lines)


def discount_for(coupon, subtotal_cents):
    """Discount in cents for a coupon row (or None) against a subtotal. Never more than the subtotal."""
    if coupon is None:
        return 0
    if subtotal_cents < coupon["min_subtotal_cents"]:
        raise CouponRejected(f"{coupon['code']} needs a subtotal of at least {coupon['min_subtotal_cents']}")
    if coupon["max_uses"] is not None and coupon["uses"] >= coupon["max_uses"]:
        raise CouponRejected(f"{coupon['code']} has been used up")
    if coupon["kind"] == "percent":
        amount = round_half_up(subtotal_cents * coupon["value"], 100)
    else:
        amount = coupon["value"]
    return min(amount, subtotal_cents)


def tax_for(taxable_cents, region):
    if region not in TAX_BPS:
        raise ValueError(f"unknown region {region!r}")
    return round_half_up(taxable_cents * TAX_BPS[region], 10_000)


def round_half_up(numerator, denominator):
    return (2 * numerator + denominator) // (2 * denominator)


def price_order(lines, region, coupon=None):
    """Return dict(subtotal_cents, discount_cents, tax_cents, total_cents)."""
    sub = subtotal(lines)
    tax = tax_for(sub, region)
    discount = discount_for(coupon, sub)
    return {
        "subtotal_cents": sub,
        "discount_cents": discount,
        "tax_cents": tax,
        "total_cents": sub - discount + tax,
    }
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
…
I've found the bug in tillpoint/pricing.py.

Report 3: Root cause
Your current price_order() function calculates tax before applying the coupon discount.

Current implementation:

sub = subtotal(lines)
tax = tax_for(sub, region)
discount = discount_for(coupon, sub)

This means the customer pays tax on the original price instead of the discounted price.

Example using your existing MUG product:

Calculation

Amount

Original price

₹12.00

10% discount

₹1.20

Taxable amount

₹10.80

Correct CA tax (7.25%)

₹0.78

Correct total

₹11.58

Your current implementation calculates ₹0.87 tax and ₹11.67 total.

Step 1: Add a regression test
Open tests/test_orders.py.

Inside OrderDeskTest, add this method immediately below test_coupon_takes_ten_percent:


    def test_coupon_discount_is_applied_before_tax(self):
        order = self.app.orders.create(
            "ana",
            [("MUG", 1)],
            region="CA",
            coupon_code="TEN"
        )

        self.assertEqual(order["subtotal_cents"], 1200)
        self.assertEqual(order["discount_cents"], 120)
        self.assertEqual(order["tax_cents"], 78)
        self.assertEqual(order["total_cents"], 1158)


Step 2: Run only this test
python -m unittest tests.test_orders.OrderDeskTest.test_coupon_discount_is_applied_before_tax -v

Expected: test fails
It should report that the tax is 87 instead of 78.

Don't modify pricing.py yet. First, we need to confirm the bug with the failing test. Send me the output.

import unittest
from datetime import datetime, timezone

from tillpoint import db, reports
from tillpoint.api import App
from tillpoint.catalog import OutOfStock, Catalog


class OrderDeskTest(unittest.TestCase):

    def setUp(self):
        self.conn = db.connect()
        self.app = App(self.conn)

        self.app.catalog.add_product("MUG", "Mug", 1200, stock=10)
        self.app.catalog.add_product("TEE", "T-shirt", 2500, stock=3)

        self.conn.execute(
            "INSERT INTO coupons (code, kind, value) VALUES ('TEN', 'percent', 10)"
        )

    def test_order_totals_with_tax(self):
        order = self.app.orders.create(
            "ana", [("MUG", 2), ("TEE", 1)], region="CA"
        )

        self.assertEqual(order["subtotal_cents"], 4900)
        self.assertEqual(order["tax_cents"], 355)
        self.assertEqual(order["total_cents"], 5255)
        self.assertEqual(self.app.catalog.get_product("MUG").stock, 8)

    def test_coupon_takes_ten_percent(self):
        order = self.app.orders.create(
            "ana", [("MUG", 1)], coupon_code="TEN"
        )

        self.assertEqual(order["discount_cents"], 120)
        self.assertEqual(order["total_cents"], 1080)

    def test_out_of_stock(self):
        with self.assertRaises(OutOfStock):
            self.app.orders.create("ana", [("TEE", 4)])

        self.assertEqual(self.app.catalog.get_product("TEE").stock, 3)

    def test_payment_marks_order_paid(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        status, payload = self.app.handle(
            "POST",
            "/webhooks/payments",
            {
                "id": "evt_1",
                "type": "payment.succeeded",
                "order_id": order["id"],
                "amount_cents": 1200
            }
        )

        self.assertEqual((status, payload["status"]), (200, "paid"))

    def test_cancel_paid_order_restocks(self):
        order = self.app.orders.create("ana", [("TEE", 2)])

        self.app.payments.handle_event(
            {
                "id": "evt_2",
                "type": "payment.succeeded",
                "order_id": order["id"],
                "amount_cents": 5000
            }
        )

        self.app.orders.cancel(order["id"])

        self.assertEqual(self.app.catalog.get_product("TEE").stock, 3)

    def test_cancel_pending_order_restocks(self):
        order = self.app.orders.create("ana", [("MUG", 2)])

        self.assertEqual(self.app.catalog.get_product("MUG").stock, 8)

        self.app.orders.cancel(order["id"])

        self.assertEqual(self.app.catalog.get_product("MUG").stock, 10)

    def test_stale_cache_refreshes_after_other_catalog_releases_stock(self):
        catalog_a = self.app.catalog
        catalog_b = Catalog(self.conn)

        # Catalog A reserves 9 mugs.
        catalog_a.reserve("MUG", 9)

        self.assertEqual(catalog_a.get_product("MUG").stock, 1)

        # Catalog B releases 5 mugs.
        catalog_b.release("MUG", 5)

        # Database stock should now be 6.
        stock = self.conn.execute(
            "SELECT stock FROM products WHERE sku = 'MUG'"
        ).fetchone()["stock"]

        self.assertEqual(stock, 6)

        # Catalog A should refresh its stale cache and reserve 2 mugs.
        catalog_a.reserve("MUG", 2)

        stock = self.conn.execute(
            "SELECT stock FROM products WHERE sku = 'MUG'"
        ).fetchone()["stock"]

        self.assertEqual(stock, 4)

    def test_daily_sales(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        noon = datetime(
            2025, 3, 10, 12, 0, tzinfo=timezone.utc
        )

        self.app.payments.handle_event(
            {
                "id": "evt_3",
                "type": "payment.succeeded",
                "order_id": order["id"],
                "amount_cents": 1200
            },
            now=noon
        )

        self.assertEqual(
            reports.daily_sales(self.conn, "2025-03-10"),
            {
                "day": "2025-03-10",
                "revenue_cents": 1200,
                "orders": 1
            }
        )

    def test_price_change(self):
        self.app.handle(
            "PUT",
            "/products/MUG",
            {"price_cents": 1500}
        )

        self.assertEqual(
            self.app.catalog.get_product("MUG").price_cents,
            1500
        )

    def test_duplicate_payment_webhook_is_not_counted_twice(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        event = {
            "id": "evt_duplicate",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 1200
        }

        self.app.payments.handle_event(event)
        self.app.payments.handle_event(event)

        self.assertEqual(
            self.app.payments.paid_cents(order["id"]),
            1200
        )

        count = self.conn.execute(
            "SELECT COUNT(*) FROM payments WHERE order_id = ?",
            (order["id"],)
        ).fetchone()[0]

        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
give entire code
…
Replace the complete contents of tests/test_orders.py with this version. It preserves all your existing tests and adds the new Report 3 regression test.


import unittest
from datetime import datetime, timezone

from tillpoint import db, reports
from tillpoint.api import App
from tillpoint.catalog import OutOfStock, Catalog


class OrderDeskTest(unittest.TestCase):

    def setUp(self):
        self.conn = db.connect()
        self.app = App(self.conn)

        self.app.catalog.add_product("MUG", "Mug", 1200, stock=10)
        self.app.catalog.add_product("TEE", "T-shirt", 2500, stock=3)

        self.conn.execute(
            "INSERT INTO coupons (code, kind, value) VALUES ('TEN', 'percent', 10)"
        )

    def test_order_totals_with_tax(self):
        order = self.app.orders.create(
            "ana", [("MUG", 2), ("TEE", 1)], region="CA"
        )

        self.assertEqual(order["subtotal_cents"], 4900)
        self.assertEqual(order["tax_cents"], 355)
        self.assertEqual(order["total_cents"], 5255)
        self.assertEqual(self.app.catalog.get_product("MUG").stock, 8)

    def test_coupon_takes_ten_percent(self):
        order = self.app.orders.create(
            "ana", [("MUG", 1)], coupon_code="TEN"
        )

Next: Run the new test
Save the file and execute:

python -m unittest tests.test_orders.OrderDeskTest.test_coupon_discount_is_applied_before_tax -v

Expected: It should fail because the current pricing code calculates tax on ₹12.00 instead of ₹10.80.

Send me the output. We will then fix pricing.py without disturbing your previous commits.

C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tillpoint\pricing.py
"""Order maths: subtotal, coupon discount, tax, total. Integer cents throughout."""

# Sales tax in basis points (1/100 of a percent) by region.
TAX_BPS = {"NONE": 0, "CA": 725, "NY": 888, "TX": 625, "DE": 1900}


class CouponRejected(Exception):
    pass


def subtotal(lines):
    """lines: iterable of (unit_price_cents, qty)."""
    return sum(price * qty for price, qty in lines)


def discount_for(coupon, subtotal_cents):
    """Discount in cents for a coupon row (or None) against a subtotal. Never more than the subtotal."""
    if coupon is None:
        return 0
    if subtotal_cents < coupon["min_subtotal_cents"]:
        raise CouponRejected(f"{coupon['code']} needs a subtotal of at least {coupon['min_subtotal_cents']}")
    if coupon["max_uses"] is not None and coupon["uses"] >= coupon["max_uses"]:
        raise CouponRejected(f"{coupon['code']} has been used up")
    if coupon["kind"] == "percent":
        amount = round_half_up(subtotal_cents * coupon["value"], 100)
    else:
        amount = coupon["value"]
    return min(amount, subtotal_cents)


def tax_for(taxable_cents, region):
    if region not in TAX_BPS:
        raise ValueError(f"unknown region {region!r}")
    return round_half_up(taxable_cents * TAX_BPS[region], 10_000)


def round_half_up(numerator, denominator):
    return (2 * numerator + denominator) // (2 * denominator)


def price_order(lines, region, coupon=None):
    """Return dict(subtotal_cents, discount_cents, tax_cents, total_cents)."""
    sub = subtotal(lines)
    tax = tax_for(sub, region)
    discount = discount_for(coupon, sub)
    return {
        "subtotal_cents": sub,
        "discount_cents": discount,
        "tax_cents": tax,
        "total_cents": sub - discount + tax,
    }
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> python -m unittest tests.test_orders.OrderDeskTest.test_coupon_discount_is_applied_before_tax -v
test_coupon_discount_is_applied_before_tax (tests.test_orders.OrderDeskTest.test_coupon_discount_is_applied_before_tax) ... FAIL

======================================================================
FAIL: test_coupon_discount_is_applied_before_tax (tests.test_orders.OrderDeskTest.test_coupon_discount_is_applied_before_tax)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment\tests\test_orders.py", line 51, in test_coupon_discount_is_applied_before_tax
    self.assertEqual(order["tax_cents"], 78)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 87 != 78

----------------------------------------------------------------------
Ran 1 test in 0.005s

FAILED (failures=1)
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
…
Perfect! Expected failure confirmed

Your new test failed for the exact reason we expected:

Expected tax: 78 cents

Actual tax: 87 cents

This confirms that price_order() calculates tax before applying the coupon discount.

Step 1: Fix tillpoint/pricing.py
Open tillpoint/pricing.py in VS Code.

Find the existing price_order() function at the bottom and replace only that function with:

def price_order(lines, region, coupon=None):
    """Return dict(subtotal_cents, discount_cents, tax_cents, total_cents)."""
    sub = subtotal(lines)

    # Apply the coupon discount first.
    discount = discount_for(coupon, sub)

    # Calculate tax on the discounted amount.
    taxable = sub - discount
    tax = tax_for(taxable, region)

    return {
        "subtotal_cents": sub,
        "discount_cents": discount,
        "tax_cents": tax,
        "total_cents": taxable + tax,
    }

What changed?

Calculate the original subtotal.

Apply the coupon discount.

Calculate tax on the remaining taxable amount.

Add the tax to get the final total.

Step 2: Run the targeted test
Save the file, then run:

python -m unittest tests.test_orders.OrderDeskTest.test_coupon_discount_is_applied_before_tax -v

Expected result:

Ran 1 test
OK
Send me the output. We'll then run the complete test suite before committing Report 3.


Context window full
Start a new chat with an automatic summary of this conversation, or upgrade to continue here with more context available in every chat.



