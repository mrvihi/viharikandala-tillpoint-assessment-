
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

    def tearDown(self):
        self.conn.close()

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

    def test_daily_sales_uses_india_local_date(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        payment_time = datetime(
            2025, 3, 9, 20, 0, tzinfo=timezone.utc
        )

        self.app.payments.handle_event(
            {
                "id": "evt_india",
                "type": "payment.succeeded",
                "order_id": order["id"],
                "amount_cents": 1200
            },
            now=payment_time
        )

        self.assertEqual(
            reports.daily_sales(
                self.conn,
                "2025-03-10",
                utc_offset_minutes=330
            ),
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

    def test_second_successful_payment_is_flagged_for_refund(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        first_payment = {
            "id": "evt_first_payment",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 1200
        }

        second_payment = {
            "id": "evt_second_payment",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 1200
        }

        self.app.payments.handle_event(first_payment)
        self.app.payments.handle_event(second_payment)

        self.assertEqual(
            self.app.payments.paid_cents(order["id"]),
            1200
        )

        payments = self.conn.execute(
            """
            SELECT event_id, refund_required
            FROM payments
            WHERE order_id = ?
            ORDER BY id
            """,
            (order["id"],)
        ).fetchall()

        self.assertEqual(len(payments), 2)
        self.assertEqual(payments[0]["refund_required"], 0)
        self.assertEqual(payments[1]["refund_required"], 1)

        saved_order = self.app.orders.get(order["id"])
        self.assertEqual(saved_order["status"], "paid")

    def test_partial_payments_combine_to_pay_order(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        first_payment = {
            "id": "evt_partial_1",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 500
        }

        second_payment = {
            "id": "evt_partial_2",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 700
        }

        self.assertEqual(
            self.app.payments.handle_event(first_payment),
            "pending"
        )

        self.assertEqual(
            self.app.payments.handle_event(second_payment),
            "paid"
        )

        self.assertEqual(
            self.app.payments.paid_cents(order["id"]),
            1200
        )

        saved_order = self.app.orders.get(order["id"])
        self.assertEqual(saved_order["status"], "paid")

    def test_payment_exceeding_order_total_is_flagged_for_refund(self):
        order = self.app.orders.create("ana", [("MUG", 1)])

        payment = {
            "id": "evt_overpayment",
            "type": "payment.succeeded",
            "order_id": order["id"],
            "amount_cents": 1500
        }

        self.assertEqual(
            self.app.payments.handle_event(payment),
            "pending"
        )

        self.assertEqual(
            self.app.payments.paid_cents(order["id"]),
            0
        )

        saved_payment = self.conn.execute(
            """
            SELECT refund_required
            FROM payments
            WHERE event_id = ?
            """,
            ("evt_overpayment",)
        ).fetchone()

        self.assertEqual(saved_payment["refund_required"], 1)

        saved_order = self.app.orders.get(order["id"])
        self.assertEqual(saved_order["status"], "pending")


if __name__ == "__main__":
    unittest.main()
