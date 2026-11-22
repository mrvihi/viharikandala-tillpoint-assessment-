
Loading older messages…
Continued from
Engineering Assessment Plan (1)
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> python -m unittest tests.test_orders.OrderDeskTest.test_cancel_pending_order_restocks -v
test_cancel_pending_order_restocks (tests.test_orders.OrderDeskTest.test_cancel_pending_order_restocks) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.003s

OK
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
Regression test passed!
Great! The pending-order cancellation fix is working. Stock is now restored correctly from 8 to 10.

Step 2 — Run all tests
Now run the complete test suite:

python -m unittest discover -s tests -v

We need to confirm that the fix hasn't broken any existing functionality.

Send me the complete output. Don't commit yet—we still need to investigate the stale stock-cache issue in Report 2.

PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> git add tests/test_orders.py tillpoint/db.py tillpoint/payments.py
warning: in the working copy of 'tests/test_orders.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tillpoint/db.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tillpoint/payments.py', LF will be replaced by CRLF the next time Git touches it
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> git commit -m "Fix duplicate payment webhook processing"
[main 1172330] Fix duplicate payment webhook processing
 3 files changed, 101 insertions(+), 14 deletions(-)
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> git log --oneline -3
1172330 (HEAD -> main) Fix duplicate payment webhook processing
70c0fce Initial commit
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> git status
On branch main
nothing to commit, working tree clean
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tillpoint\catalog.py
"""Product catalog with a per-process read cache."""
from dataclasses import dataclass


class OutOfStock(Exception):
    def __init__(self, sku, wanted, available):
        super().__init__(f"{sku}: wanted {wanted}, {available} available")
        self.sku, self.wanted, self.available = sku, wanted, available


class UnknownProduct(Exception):
    pass


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price_cents: int
    stock: int


class Catalog:
    def __init__(self, conn):
        self.conn = conn
        self._cache = {}

    def add_product(self, sku, name, price_cents, stock=0):
        self.conn.execute(
            "INSERT INTO products (sku, name, price_cents, stock) VALUES (?, ?, ?, ?)",
            (sku, name, price_cents, stock),
        )
        self._cache.pop(sku, None)

    def get_product(self, sku):
        product = self._cache.get(sku)
        if product is None:
            row = self.conn.execute("SELECT * FROM products WHERE sku = ?", (sku,)).fetchone()
            if row is None:
                raise UnknownProduct(sku)
            product = Product(row["sku"], row["name"], row["price_cents"], row["stock"])
            self._cache[sku] = product
        return product

    def update_price(self, sku, price_cents):
        if price_cents < 0:
            raise ValueError("price must not be negative")
        cur = self.conn.execute("UPDATE products SET price_cents = ? WHERE sku = ?", (price_cents, sku))
        if cur.rowcount == 0:
            raise UnknownProduct(sku)
        self._cache.pop(sku, None)

    def reserve(self, sku, qty):
        """Take qty units out of stock, or raise OutOfStock."""
        product = self.get_product(sku)
        if product.stock < qty:
            raise OutOfStock(sku, qty, product.stock)
        self.conn.execute("UPDATE products SET stock = stock - ? WHERE sku = ?", (qty, sku))
        self._cache.pop(sku, None)

    def release(self, sku, qty):
        """Put qty units back into stock."""
        self.conn.execute("UPDATE products SET stock = stock + ? WHERE sku = ?", (qty, sku))
        self._cache.pop(sku, None)
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-ChildItem tests


    Directory: C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment\tests


Mode                 LastWriteTime         Length Name                                                                                    
----                 -------------         ------ ----                                                                                    
d-----        11/22/2026  12:47 PM                __pycache__                                                                             
-a----        11/22/2026  12:46 PM           3877 test_orders.py                                                                          
-a----        11/22/2026  11:49 AM              0 __init__.py                                                                             


PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tests\test_orders.py

import unittest
from datetime import datetime, timezone

from tillpoint import db, reports
from tillpoint.api import App
from tillpoint.catalog import OutOfStock


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

    def test_daily_sales(self):
        order = self.app.orders.create("ana", [("MUG", 1)])
        noon = datetime(2025, 3, 10, 12, 0, tzinfo=timezone.utc)

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
        self.app.handle("PUT", "/products/MUG", {"price_cents": 1500})
        self.assertEqual(self.app.catalog.get_product("MUG").price_cents, 1500)

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
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> python -m unittest tests.test_orders.OrderDeskTest.test_cancel_pending_order_restocks -v
test_cancel_pending_order_restocks (tests.test_orders.OrderDeskTest.test_cancel_pending_order_restocks) ... FAIL

======================================================================
FAIL: test_cancel_pending_order_restocks (tests.test_orders.OrderDeskTest.test_cancel_pending_order_restocks)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment\tests\test_orders.py", line 79, in test_cancel_pending_order_restocks
    self.assertEqual(self.app.catalog.get_product("MUG").stock, 10)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 8 != 10

----------------------------------------------------------------------
Ran 1 test in 0.005s

FAILED (failures=1)
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> python -m unittest tests.test_orders.OrderDeskTest.test_cancel_pending_order_restocks -v
test_orders (unittest.loader._FailedTest.test_orders) ... ERROR

======================================================================
ERROR: test_orders (unittest.loader._FailedTest.test_orders)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_orders
Traceback (most recent call last):
  File "C:\Python314\Lib\unittest\loader.py", line 137, in loadTestsFromName
    module = __import__(module_name)
  File "C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment\tests\test_orders.py", line 3, in <module>
    from . import db, pricing
ImportError: cannot import name 'db' from 'tests' (C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment\tests\__init__.py)


----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (errors=1)
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content test
…
All 9 tests passed!
Excellent. Your pending-order cancellation fix is working, and all existing tests still pass.

A few important points:

Report 1 is already committed as 1172330.

Report 2's fix is not committed yet.

The SQLite ResourceWarning messages are not test failures.

We still need to investigate the stale-cache problem before committing Report 2.

Next: Test the stale stock cache
This simulates two separate catalog instances (like two server workers) accessing the same database.

Step 1 — Add an import
In tests/test_orders.py, change:

from tillpoint.catalog import OutOfStock

to:

from tillpoint.catalog import OutOfStock, Catalog

Step 2 — Add this test
Place it below test_cancel_pending_order_restocks:

def test_stale_cache_does_not_hide_available_stock(self):
    catalog_a = self.app.catalog
    catalog_b = Catalog(self.conn)

    # Worker A reads stock after reserving 9 mugs.
    catalog_a.reserve("MUG", 9)
    self.assertEqual(catalog_a.get_product("MUG").stock, 1)

    # Worker B releases 5 mugs.
    catalog_b.release("MUG", 5)

    # Database stock is now 6, but worker A may still see 1.
    with self.assertRaises(OutOfStock):
        catalog_a.reserve("MUG", 2)

Step 3 — Run the test
python -m unittest tests.test_orders.OrderDeskTest.test_stale_cache_does_not_hide_available_stock -v

This test is expected to pass its assertRaises assertion with the current code, demonstrating the stale-cache bug: the database has 6 mugs, but the cached value is only 1.

Send me the output. Then we'll fix the cache correctly and verify all tests again.

import unittest
from datetime import datetime, timezone

from tillpoint import db, reports
from tillpoint.api import App
# from tillpoint.catalog import OutOfStock
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

    def test_daily_sales(self):
        order = self.app.orders.create("ana", [("MUG", 1)])
        noon = datetime(2025, 3, 10, 12, 0, tzinfo=timezone.utc)

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
        self.app.handle("PUT", "/products/MUG", {"price_cents": 1500})
        self.assertEqual(self.app.catalog.get_product("MUG").price_cents, 1500)

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
Replace the entire contents of tests/test_orders.py with this code.

I have included your existing 9 tests and added the stale-cache regression test. I also removed the unnecessary commented-out import.


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

Important: The new stale-cache test is designed to fail with your current catalog.py implementation. That is expected: we need to reproduce the bug before fixing it.

Next step
Save the file, then run this command in PowerShell:

python -m unittest tests.test_orders.OrderDeskTest.test_stale_cache_refreshes_after_other_catalog_releases_stock -v

Send me the complete output. We'll fix the cache issue in tillpoint/catalog.py only after confirming the test fails.


Context window full
Start a new chat with an automatic summary of this conversation, or upgrade to continue here with more context available in every chat.



