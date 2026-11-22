
"""Payment provider webhooks with duplicate and overpayment protection."""
from . import db


class PaymentError(Exception):
    pass


class Payments:
    def __init__(self, conn):
        self.conn = conn

    def handle_event(self, event, now=None):
        """Record a successful payment and return the order's resulting status."""
        if event.get("type") != "payment.succeeded":
            return None

        # Serialize payment decisions so concurrent webhooks cannot both
        # accept payments against the same remaining balance.
        self.conn.execute("BEGIN IMMEDIATE")

        try:
            order = self.conn.execute(
                "SELECT * FROM orders WHERE id = ?",
                (event["order_id"],)
            ).fetchone()

            if order is None:
                raise PaymentError(
                    f"payment for unknown order {event['order_id']}"
                )

            if order["status"] == "cancelled":
                raise PaymentError(f"order {order['id']} is cancelled")

            # Calculate the remaining balance using accepted payments only.
            accepted = self.paid_cents(order["id"])
            remaining = order["total_cents"] - accepted

            amount = event["amount_cents"]

            # Payments after an order is paid, or payments exceeding the
            # remaining balance, must be flagged for refund.
            refund_required = (
                order["status"] != "pending"
                or amount > remaining
            )

            self.conn.execute(
                """
                INSERT INTO payments (
                    order_id,
                    event_id,
                    amount_cents,
                    received_at,
                    refund_required
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO NOTHING
                """,
                (
                    order["id"],
                    event["id"],
                    amount,
                    db.to_iso(now or db.utcnow()),
                    int(refund_required),
                ),
            )

            # Recalculate accepted payments. Duplicate events are ignored
            # by the unique event_id constraint.
            if order["status"] == "pending":
                if self.paid_cents(order["id"]) >= order["total_cents"]:
                    self.conn.execute(
                        "UPDATE orders SET status = 'paid' WHERE id = ?",
                        (order["id"],)
                    )
                    status = "paid"
                else:
                    status = "pending"
            else:
                status = order["status"]

            self.conn.execute("COMMIT")
            return status

        except Exception:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise

    def paid_cents(self, order_id):
        """Return only payments accepted toward the order balance."""
        row = self.conn.execute(
            """
            SELECT COALESCE(SUM(amount_cents), 0) AS paid
            FROM payments
            WHERE order_id = ?
              AND refund_required = 0
            """,
            (order_id,)
        ).fetchone()

        return row["paid"]
