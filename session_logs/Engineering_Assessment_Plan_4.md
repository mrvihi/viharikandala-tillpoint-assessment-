
Loading older messages…
Continued from
Engineering Assessment Plan (3)
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

        catalog_a.reserve("MUG", 9)

        self.assertEqual(catalog_a.get_product("MUG").stock, 1)

        catalog_b.release("MUG", 5)

        stock = self.conn.execute(
            "SELECT stock FROM products WHERE sku = 'MUG'"
        ).fetchone()["stock"]

        self.assertEqual(stock, 6)

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
Replace the entire contents of tests/test_orders.py with this code. I've preserved all your existing tests and added the new Report 4 timezone regression test.

Complete tests/test_orders.py

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
Open tests/test_orders.py.

Select all and replace it with the complete code above.

Press Ctrl + S.

Run:

python -m unittest tests.test_orders.OrderDeskTest.test_daily_sales_uses_india_local_date -v

Expected: The test should fail initially because we haven't fixed reports.py yet.

Send me the output. We'll fix the timezone logic only after confirming the failure.

C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> python -m unittest tests.test_orders.OrderDeskTest.test_daily_sales_uses_india_local_date -v
test_daily_sales_uses_india_local_date (tests.test_orders.OrderDeskTest.test_daily_sales_uses_india_local_date) ... FAIL

======================================================================
FAIL: test_daily_sales_uses_india_local_date (tests.test_orders.OrderDeskTest.test_daily_sales_uses_india_local_date)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment\tests\test_orders.py", line 168, in test_daily_sales_uses_india_local_date
    self.assertEqual(
    ~~~~~~~~~~~~~~~~^
        reports.daily_sales(
        ^^^^^^^^^^^^^^^^^^^^
    ...<8 lines>...
        }
        ^
    )
    ^
AssertionError: {'day': '2025-03-10', 'revenue_cents': 0, 'orders': 0} != {'day': '2025-03-10', 'revenue_cents': 1200, 'orders': 1}
- {'day': '2025-03-10', 'orders': 0, 'revenue_cents': 0}
?                                 ^

+ {'day': '2025-03-10', 'orders': 1, 'revenue_cents': 1200}
?                                 ^                   +++


----------------------------------------------------------------------
Ran 1 test in 0.035s

FAILED (failures=1)
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
…
Excellent! Report 4 bug reproduced

Your regression test failed exactly as expected:

Expected revenue on 10 March: 1200 cents

Actual revenue on 10 March: 0 cents

Expected orders: 1

Actual orders: 0

Why is this happening?
The payment occurred at:

2025-03-09 20:00 UTC

India is UTC+5:30, so the local time is:

2025-03-10 01:30 AM

The existing report is using the wrong UTC date boundaries.

Step 1: Open tillpoint/reports.py
Run this command to see your current code:

Get-Content tillpoint\reports.py

Send me the complete output.

Don't change anything yet. I'll check your existing implementation and then give you the complete corrected reports.py code without disturbing the other report functions.

C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tillpoint\reports.py
"""Sales reports for the shop owner."""
from datetime import datetime, timedelta, timezone

from . import db


def day_bounds_utc(day, utc_offset_minutes=0):
    """The UTC instants at which a shop-local calendar day starts and ends. day is 'YYYY-MM-DD'."""
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start += timedelta(minutes=utc_offset_minutes)
    return db.to_iso(start), db.to_iso(start + timedelta(days=1))


def daily_sales(conn, day, utc_offset_minutes=0):
    """Money received on one shop-local day, and how many orders it came from."""
    start, end = day_bounds_utc(day, utc_offset_minutes)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) AS revenue, COUNT(DISTINCT order_id) AS orders"
        " FROM payments WHERE received_at >= ? AND received_at < ?",
        (start, end),
    ).fetchone()
    return {"day": day, "revenue_cents": row["revenue"], "orders": row["orders"]}


def top_products(conn, limit=5):
    """Best sellers by units, counting orders that were paid or shipped."""
    rows = conn.execute(
        "SELECT i.sku, SUM(i.qty) AS units, SUM(i.qty * i.unit_price_cents) AS gross_cents"
        " FROM order_items i JOIN orders o ON o.id = i.order_id"
        " WHERE o.status IN ('paid', 'shipped') GROUP BY i.sku ORDER BY units DESC, i.sku LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
…
We found the Report 4 bug in day_bounds_utc().

The code currently adds the India offset (+330 minutes) to UTC midnight. It should subtract 330 minutes because India is ahead of UTC.

For example:

India local midnight: 2025-03-10 00:00

Corresponding UTC time: 2025-03-09 18:30

We'll change only tillpoint/reports.py. Your failing test should then pass, while the default UTC report should remain unchanged.

Step 1: Replace tillpoint/reports.py
Open the file in VS Code and replace its entire contents with:


"""Sales reports for the shop owner."""
from datetime import datetime, timedelta, timezone

from . import db


def day_bounds_utc(day, utc_offset_minutes=0):
    """The UTC instants at which a shop-local calendar day starts and ends. day is 'YYYY-MM-DD'."""
    start = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    # Convert local midnight to UTC by subtracting the local UTC offset.
    start -= timedelta(minutes=utc_offset_minutes)

    return db.to_iso(start), db.to_iso(start + timedelta(days=1))


def daily_sales(conn, day, utc_offset_minutes=0):
    """Money received on one shop-local day, and how many orders it came from."""
    start, end = day_bounds_utc(day, utc_offset_minutes)
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) AS revenue, COUNT(DISTINCT order_id) AS orders"
        " FROM payments WHERE received_at >= ? AND received_at < ?",
        (start, end),
    ).fetchone()
    return {"day": day, "revenue_cents": row["revenue"], "orders": row["orders"]}


def top_products(conn, limit=5):
    """Best sellers by units, counting orders that were paid or shipped."""
    rows = conn.execute(
        "SELECT i.sku, SUM(i.qty) AS units, SUM(i.qty * i.unit_price_cents) AS gross_cents"
        " FROM order_items i JOIN orders o ON o.id = i.order_id"
        " WHERE o.status IN ('paid', 'shipped') GROUP BY i.sku ORDER BY units DESC, i.sku LIMIT ?",
        (limit,),
    ).fetchall()

Step 2: Run the Report 4 test
In PowerShell:

python -m unittest tests.test_orders.OrderDeskTest.test_daily_sales_uses_india_local_date -v

Expected OK — 1 test passed.

Don't commit yet. Paste the test output here. Then we'll run the complete test suite, inspect the changes, and commit Report 4 separately.






