
Loading older messages…
unittest.main()
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> INSERT INTO payments (order_id, event_id, amount_cents, received_at)
At line:1 char:31
+ INSERT INTO payments (order_id, event_id, amount_cents, received_at)
+                               ~
Missing argument in parameter list.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : MissingArgument
 
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
You accidentally entered an SQL statement directly into PowerShell. That's why you got the ParserError.

INSERT INTO payments... is SQL code. It belongs inside your Python application's database logic or a SQLite session—not directly at the PowerShell prompt.

Let's continue with the test first. You don't need to run that SQL statement manually.

Step 1: Open the test file
In VS Code, open:

tests/test_orders.py

Inside the OrderDeskTest class, add the test method I shared earlier. Make sure it is indented at the same level as the other def test_... methods.

Step 2: Run only this test
In PowerShell, run:

python -m unittest tests.test_orders.OrderDeskTest.test_duplicate_payment_webhook_is_not_counted_twice -v

Step 3: Send me the output
The original code should fail this test because it inserts the same payment event twice.

Important: Don't type INSERT INTO payments into PowerShell. We'll fix the actual Python and database code after confirming the test failure.

wht i hvae to do
No problem. Follow these steps one by one.

Step 1: Open your project in VS Code
Open this file:

tests/test_orders.py

Step 2: Go to the bottom of the file
Find this line:

unittest.main()

Paste the following code just above unittest.main(), keeping it inside the OrderDeskTest class (same indentation as your other test methods):

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

Step 3: Run the test
Open your VS Code terminal and copy this command:

python -m unittest tests.test_orders.OrderDeskTest.test_duplicate_payment_webhook_is_not_counted_twice -v

Step 4: Send me a screenshot or the complete terminal output.
Don't change payments.py or db.py yet. First, we'll confirm the bug.

"""Creating, cancelling and listing orders."""
from . import db, pricing
from .catalog import Catalog


class OrderError(Exception):
    pass


class Orders:
    def __init__(self, conn, catalog=None):
        self.conn = conn
        self.catalog = catalog or Catalog(conn)

    def create(self, customer, items, region="NONE", coupon_code=None, now=None):
        """items: list of (sku, qty). Reserves stock, redeems the coupon and stores the order, all or nothing."""
        if not items:
            raise OrderError("an order needs at least one item")
        if any(qty <= 0 for _, qty in items):
            raise OrderError("quantities must be positive")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            coupon = self._coupon(coupon_code)
            priced = [(sku, qty, self.catalog.get_product(sku).price_cents) for sku, qty in items]
            totals = pricing.price_order([(price, qty) for _, qty, price in priced], region, coupon)
            for sku, qty, _ in priced:
                self.catalog.reserve(sku, qty)
            if coupon is not None:
                self.conn.execute("UPDATE coupons SET uses = uses + 1 WHERE code = ?", (coupon_code,))
            cur = self.conn.execute(
                "INSERT INTO orders (customer, region, coupon, subtotal_cents, discount_cents, tax_cents,"
                " total_cents, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (customer, region, coupon_code, totals["subtotal_cents"], totals["discount_cents"],
                 totals["tax_cents"], totals["total_cents"], db.to_iso(now or db.utcnow())),
            )
            order_id = cur.lastrowid
            self.conn.executemany(
                "INSERT INTO order_items (order_id, sku, qty, unit_price_cents) VALUES (?, ?, ?, ?)",
                [(order_id, sku, qty, price) for sku, qty, price in priced],
            )
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise
        return self.get(order_id)

    def cancel(self, order_id):
        """Cancel an order that has not shipped. Its stock and its coupon use go back."""
        order = self.get(order_id)
        if order["status"] == "cancelled":
            return order
        if order["status"] == "shipped":
            raise OrderError("a shipped order cannot be cancelled")
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            if order["status"] == "paid":
                for item in order["items"]:
                    self.catalog.release(item["sku"], item["qty"])
            if order["coupon"]:
                self.conn.execute("UPDATE coupons SET uses = uses - 1 WHERE code = ? AND uses > 0", (order["coupon"],))
            self.conn.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise
        return self.get(order_id)

    def ship(self, order_id):
        order = self.get(order_id)
        if order["status"] != "paid":
            raise OrderError("only a paid order can ship")
        self.conn.execute("UPDATE orders SET status = 'shipped' WHERE id = ?", (order_id,))
        return self.get(order_id)

    def get(self, order_id):
        row = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise OrderError(f"no order {order_id}")
        order = dict(row)
        order["items"] = [dict(r) for r in self.conn.execute(
            "SELECT sku, qty, unit_price_cents FROM order_items WHERE order_id = ? ORDER BY rowid", (order_id,))]
        return order

    def list_for(self, customer, page=1, per_page=20):
        rows = self.conn.execute(
            "SELECT id FROM orders WHERE customer = ? ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            (customer, per_page, (page - 1) * per_page),
        ).fetchall()
        return [self.get(r["id"]) for r in rows]

    def _coupon(self, code):
        if code is None:
            return None
        row = self.conn.execute("SELECT * FROM coupons WHERE code = ?", (code,)).fetchone()
        if row is None:
            raise pricing.CouponRejected(f"unknown coupon {code}")
        return row
…
You've shared orders.py. That's okay, but we don't need to change this file for Report 1 yet.

The issue we're investigating is duplicate payment webhooks, and the relevant files are tests/test_orders.py and tillpoint/payments.py.

Please do this next:

Open tests/test_orders.py.

Scroll to the bottom.

Find unittest.main().

Paste the test below immediately above it:

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

5. Run this command in PowerShell:

python -m unittest tests.test_orders.OrderDeskTest.test_duplicate_payment_webhook_is_not_counted_twice -v

Send me the terminal output. We'll fix the problem only after confirming the test fails.


Context window full
Start a new chat with an automatic summary of this conversation, or upgrade to continue here with more context available in every chat.



