
Loading older messages…
Continued from
Engineering Assessment Plan
diff --git a/tillpoint/db.py b/tillpoint/db.py
index 3392f58..7722c09 100644
--- a/tillpoint/db.py
+++ b/tillpoint/db.py
@@ -43,6 +43,7 @@ CREATE TABLE IF NOT EXISTS payments (
     received_at TEXT NOT NULL
 );
 CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
+CREATE UNIQUE INDEX IF NOT EXISTS idx_payments_event_id ON payments(event_id);
 CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer, created_at);
 """
 
diff --git a/tillpoint/payments.py b/tillpoint/payments.py
index c064a3b..2d2ec46 100644
--- a/tillpoint/payments.py
+++ b/tillpoint/payments.py
@@ -1,3 +1,4 @@
+
 """Payment provider webhooks. The provider retries a delivery until it gets a 2xx, so events can repeat."""
 from . import db
 
@@ -14,22 +15,45 @@ class Payments:
         """event: dict(id, type, order_id, amount_cents). Returns the order's status after the event."""
         if event.get("type") != "payment.succeeded":
             return None
-        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (event["order_id"],)).fetchone()
+
+        order = self.conn.execute(
+            "SELECT * FROM orders WHERE id = ?",
+            (event["order_id"],)
+        ).fetchone()
+
         if order is None:
             raise PaymentError(f"payment for unknown order {event['order_id']}")
+
         if order["status"] == "cancelled":
             raise PaymentError(f"order {order['id']} is cancelled")
+
+        # Store each provider event only once.
         self.conn.execute(
-            "INSERT INTO payments (order_id, event_id, amount_cents, received_at) VALUES (?, ?, ?, ?)",
-            (order["id"], event["id"], event["amount_cents"], db.to_iso(now or db.utcnow())),
+            """
+            INSERT INTO payments (order_id, event_id, amount_cents, received_at)
+            VALUES (?, ?, ?, ?)
+            ON CONFLICT(event_id) DO NOTHING
+            """,
+            (
+                order["id"],
+                event["id"],
+                event["amount_cents"],
+                db.to_iso(now or db.utcnow()),
+            ),
         )
+
         if order["status"] == "pending" and self.paid_cents(order["id"]) >= order["total_cents"]:
-            self.conn.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order["id"],))
+            self.conn.execute(
+                "UPDATE orders SET status = 'paid' WHERE id = ?",
+                (order["id"],)
+            )
             return "paid"
+
         return order["status"]
 
     def paid_cents(self, order_id):
         row = self.conn.execute(
-            "SELECT COALESCE(SUM(amount_cents), 0) AS paid FROM payments WHERE order_id = ?", (order_id,)
+            "SELECT COALESCE(SUM(amount_cents), 0) AS paid FROM payments WHERE order_id = ?",
+            (order_id,)
         ).fetchone()
         return row["paid"]
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
…
I've reviewed the changes. The main fix is correct:

db.py prevents the same event ID from being inserted more than once.

payments.py ignores repeated deliveries of that event.

Different event IDs for the same order are still allowed, which preserves the ability to handle Report 6 separately.

One small cleanup: your diff shows an unnecessary blank line at the very beginning of tests/test_orders.py and tillpoint/payments.py. Remove that first blank line in both files.

Step 1: Save and rerun all tests
python -m unittest discover -s tests -v

Make sure all 8 tests pass.

Step 2: Commit Report 1
Run these commands:

git add tests/test_orders.py tillpoint/db.py tillpoint/payments.py

git commit -m "Fix duplicate payment webhook processing"

Step 3: Verify the commit
git log --oneline -3

git status

Send me the output.

Then we'll start Report 2: Stock incorrectly showing sold out after abandoned checkout.

C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2> cd tillpoint_assignment
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> dir -Force


    Directory: C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment


Mode                 LastWriteTime         Length Name                                                                                    
----                 -------------         ------ ----                                                                                    
d-----        11/22/2026  11:49 AM                .git                                                                                    
d-----        11/22/2026  11:49 AM                session_logs                                                                            
d-----        11/22/2026  11:49 AM                tests                                                                                   
d-----        11/22/2026  11:49 AM                tillpoint                                                                               
-a----        11/22/2026  11:49 AM             18 .gitignore                                                                              
-a----        11/22/2026  11:49 AM           9434 CANDIDATE_BRIEF.md                                                                      
-a----        11/22/2026  11:49 AM           2876 NOTES.md                                                                                
-a----        11/22/2026  11:49 AM           1222 README.md                                                                               
-a----        11/22/2026  11:49 AM           1086 server.py                                                                               


PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> git status
On branch main
nothing to commit, working tree clean
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> git log --oneline -5
70c0fce (HEAD -> main) Initial commit
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content README.md
# Tillpoint

A small order desk for a shop: a product catalog, orders with coupons and sales tax, payment webhooks and sales reports. Python 3.10+, standard library only, SQLite for storage.

## Run

python3 server.py tillpoint.db 8000


| Method | Path | Body |
|---|---|---|
| POST | /orders | {"customer", "items": [{"sku", "qty"}], "region", "coupon"} |
| GET | /orders/<id> | |
| POST | /orders/<id>/cancel | |
| GET / PUT | /products/<sku> | PUT: {"price_cents"} |
| POST | /webhooks/payments | {"id", "type": "payment.succeeded", "order_id", "amount_cents"} |
| GET | /reports/daily/<YYYY-MM-DD> | {"utc_offset_minutes"} |

Money is integer cents. Timestamps are stored in UTC. The payment provider retries a webhook until it receives a 2xx response.

## Test

python3 -m unittest discover -s tests -v


## Layout

tillpoint/db.py        schema and time helpers
tillpoint/catalog.py   products, stock, read cache
tillpoint/pricing.py   subtotal, coupons, tax
tillpoint/orders.py    create, cancel, ship, list
tillpoint/payments.py  payment webhooks
tillpoint/reports.py   daily sales, top products
tillpoint/api.py       JSON API
server.py              HTTP server

PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> python -m unittest discover -s tests -v
test_cancel_paid_order_restocks (test_orders.OrderDeskTest.test_cancel_paid_order_restocks) ... ok
test_coupon_takes_ten_percent (test_orders.OrderDeskTest.test_coupon_takes_ten_percent) ... ok
test_daily_sales (test_orders.OrderDeskTest.test_daily_sales) ... <frozen importlib._bootstrap>:491: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x000001DD05F6E110>
ResourceWarning: Enable tracemalloc to get the object allocation traceback
<frozen importlib._bootstrap>:491: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x000001DD05F6F4C0>
ResourceWarning: Enable tracemalloc to get the object allocation traceback
ok
test_order_totals_with_tax (test_orders.OrderDeskTest.test_order_totals_with_tax) ... ok
test_out_of_stock (test_orders.OrderDeskTest.test_out_of_stock) ... ok
test_payment_marks_order_paid (test_orders.OrderDeskTest.test_payment_marks_order_paid) ... ok
test_price_change (test_orders.OrderDeskTest.test_price_change) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.174s

OK
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tillpoint\payment.py
Get-Content : Cannot find path 'C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment\tillpoint\payment.py' because it does 
not exist.
At line:1 char:1
+ Get-Content tillpoint\payment.py
+ ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (C:\Users\kanda\...oint\payment.py:String) [Get-Content], ItemNotFoundException
    + FullyQualifiedErrorId : PathNotFound,Microsoft.PowerShell.Commands.GetContentCommand
 
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tillpoint\payments.py
"""Payment provider webhooks. The provider retries a delivery until it gets a 2xx, so events can repeat."""
from . import db


class PaymentError(Exception):
    pass


class Payments:
    def __init__(self, conn):
        self.conn = conn

    def handle_event(self, event, now=None):
        """event: dict(id, type, order_id, amount_cents). Returns the order's status after the event."""
        if event.get("type") != "payment.succeeded":
            return None
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (event["order_id"],)).fetchone()
        if order is None:
            raise PaymentError(f"payment for unknown order {event['order_id']}")
        if order["status"] == "cancelled":
            raise PaymentError(f"order {order['id']} is cancelled")
        self.conn.execute(
            "INSERT INTO payments (order_id, event_id, amount_cents, received_at) VALUES (?, ?, ?, ?)",
            (order["id"], event["id"], event["amount_cents"], db.to_iso(now or db.utcnow())),
        )
        if order["status"] == "pending" and self.paid_cents(order["id"]) >= order["total_cents"]:
            self.conn.execute("UPDATE orders SET status = 'paid' WHERE id = ?", (order["id"],))
            return "paid"
        return order["status"]

    def paid_cents(self, order_id):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) AS paid FROM payments WHERE order_id = ?", (order_id,)
        ).fetchone()
        return row["paid"]
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tillpoint\reports.py 
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
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tillpoint\db.py     
"""SQLite storage. All money is integer cents; all timestamps are UTC ISO-8601 strings."""
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS coupons (
    code TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('percent', 'fixed')),
    value INTEGER NOT NULL,
    min_subtotal_cents INTEGER NOT NULL DEFAULT 0,
    max_uses INTEGER,
    uses INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer TEXT NOT NULL,
    region TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    coupon TEXT,
    subtotal_cents INTEGER NOT NULL,
    discount_cents INTEGER NOT NULL DEFAULT 0,
    tax_cents INTEGER NOT NULL DEFAULT 0,
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id),
    sku TEXT NOT NULL REFERENCES products(sku),
    qty INTEGER NOT NULL,
    unit_price_cents INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    event_id TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    received_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer, created_at);
"""


def connect(path=":memory:"):
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def utcnow():
    return datetime.now(timezone.utc).replace(microsecond=0)


def to_iso(dt):
    return dt.astimezone(
…
Report 1 successfully committed
Excellent! Your first bug fix is saved in Git.

Your commit:

1172330 Fix duplicate payment webhook processing
Your Git status:

On branch main
nothing to commit, working tree clean
This means your changes are safely committed. Don't worry about the earlier PowerShell SQL and indentation errors; you eventually corrected them.

Next: Report 2 — Stock incorrectly showing sold out
Now we'll investigate why stock appears unavailable even when products are still on the shelf, especially after an abandoned checkout.

We will investigate first, not modify code immediately.

Step 1: Open tillpoint/catalog.py
Run this command:

Get-Content tillpoint\catalog.py

Step 2: Send me the complete output
I'll explain:

How stock is currently stored.

How stock is reserved and released.

Whether the catalog cache could be returning stale stock.

How to reproduce the abandoned-checkout bug with a failing test.

We'll follow the same process: reproduce → understand → fix → test → commit.

Your Report 1 is complete. Now let's work on Report 2.

C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> Get-Content tillpoint\catalog.py
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
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
…
Good. We have found two important areas to investigate in catalog.py:

Cached stock: get_product() can return an old stock value if another Catalog instance changes the database. The cache is local to each Catalog object.

Stock reservation: reserve() decreases database stock, while release() increases it. We need to check whether abandoned or cancelled orders correctly release reserved stock.

Let's reproduce the problem before changing anything. That gives us evidence for the fix and a regression test.

Step 2 — Check the existing stock tests
In the same terminal, run:

Get-ChildItem tests

Send me the output. I want to identify the existing stock-related tests so we can add a focused regression test without disturbing the tests that already pass.

Don't edit catalog.py yet. We should first prove exactly why stock appears sold out.


Context window full
Start a new chat with an automatic summary of this conversation, or upgrade to continue here with more context available in every chat.



