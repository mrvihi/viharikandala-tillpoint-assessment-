
Loading older messages…
Continued from
Engineering Assessment Plan (6)
C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> python -m unittest discover -s tests -v
test_two_workers_cannot_oversell_stock (test_catalog_concurrency.CatalogConcurrencyTest.test_two_workers_cannot_oversell_stock) ... ok
test_cancel_paid_order_restocks (test_orders.OrderDeskTest.test_cancel_paid_order_restocks) ... ok
test_cancel_pending_order_restocks (test_orders.OrderDeskTest.test_cancel_pending_order_restocks) ... ok
test_coupon_discount_is_applied_before_tax (test_orders.OrderDeskTest.test_coupon_discount_is_applied_before_tax) ... ok
test_coupon_takes_ten_percent (test_orders.OrderDeskTest.test_coupon_takes_ten_percent) ... ok
test_daily_sales (test_orders.OrderDeskTest.test_daily_sales) ... C:\Python314\Lib\_strptime.py:68: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x0000027C4CFFC9A0>
  class LocaleTime(object):
ResourceWarning: Enable tracemalloc to get the object allocation traceback
C:\Python314\Lib\_strptime.py:68: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x0000027C4CFFCC70>
  class LocaleTime(object):
ResourceWarning: Enable tracemalloc to get the object allocation traceback
C:\Python314\Lib\_strptime.py:68: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x0000027C4CFFCF40>
  class LocaleTime(object):
ResourceWarning: Enable tracemalloc to get the object allocation traceback
C:\Python314\Lib\_strptime.py:68: ResourceWarning: unclosed database in <sqlite3.Connection object at 0x0000027C4CFFD030>
  class LocaleTime(object):
ResourceWarning: Enable tracemalloc to get the object allocation traceback
ok
test_daily_sales_uses_india_local_date (test_orders.OrderDeskTest.test_daily_sales_uses_india_local_date) ... ok
test_duplicate_payment_webhook_is_not_counted_twice (test_orders.OrderDeskTest.test_duplicate_payment_webhook_is_not_counted_twice) ... ok
test_order_totals_with_tax (test_orders.OrderDeskTest.test_order_totals_with_tax) ... ok
test_out_of_stock (test_orders.OrderDeskTest.test_out_of_stock) ... ok
test_payment_marks_order_paid (test_orders.OrderDeskTest.test_payment_marks_order_paid) ... ok
test_price_change (test_orders.OrderDeskTest.test_price_change) ... ok
test_second_successful_payment_is_flagged_for_refund (test_orders.OrderDeskTest.test_second_successful_payment_is_flagged_for_refund) ... ok
test_stale_cache_refreshes_after_other_catalog_releases_stock (test_orders.OrderDeskTest.test_stale_cache_refreshes_after_other_catalog_releases_stock) ... ok

----------------------------------------------------------------------
Ran 14 tests in 0.116s

OK
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> python -m unittest discover -s tests -v
test_two_workers_cannot_oversell_stock (test_catalog_concurrency.CatalogConcurrencyTest.test_two_workers_cannot_oversell_stock) ... ok
test_cancel_paid_order_restocks (test_orders.OrderDeskTest.test_cancel_paid_order_restocks) ... ok
test_cancel_pending_order_restocks (test_orders.OrderDeskTest.test_cancel_pending_order_restocks) ... ok
test_coupon_discount_is_applied_before_tax (test_orders.OrderDeskTest.test_coupon_discount_is_applied_before_tax) ... ok
test_coupon_takes_ten_percent (test_orders.OrderDeskTest.test_coupon_takes_ten_percent) ... ok
test_daily_sales (test_orders.OrderDeskTest.test_daily_sales) ... ok
test_daily_sales_uses_india_local_date (test_orders.OrderDeskTest.test_daily_sales_uses_india_local_date) ... ok
test_duplicate_payment_webhook_is_not_counted_twice (test_orders.OrderDeskTest.test_duplicate_payment_webhook_is_not_counted_twice) ... ok
test_order_totals_with_tax (test_orders.OrderDeskTest.test_order_totals_with_tax) ... ok
test_out_of_stock (test_orders.OrderDeskTest.test_out_of_stock) ... ok
test_partial_payments_combine_to_pay_order (test_orders.OrderDeskTest.test_partial_payments_combine_to_pay_order) ... ok
test_payment_exceeding_order_total_is_flagged_for_refund (test_orders.OrderDeskTest.test_payment_exceeding_order_total_is_flagged_for_refund) ... ok
test_payment_marks_order_paid (test_orders.OrderDeskTest.test_payment_marks_order_paid) ... ok
test_price_change (test_orders.OrderDeskTest.test_price_change) ... ok
test_second_successful_payment_is_flagged_for_refund (test_orders.OrderDeskTest.test_second_successful_payment_is_flagged_for_refund) ... ok
test_stale_cache_refreshes_after_other_catalog_releases_stock (test_orders.OrderDeskTest.test_stale_cache_refreshes_after_other_catalog_releases_stock) ... ok

----------------------------------------------------------------------
Ran 16 tests in 0.119s

OK
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
…
All 16 tests passed
Great! The second run confirms that your updated test file is being used and all 16 tests pass, including:

Duplicate webhook protection

Separate second payment flagged for refund

Two partial payments completing an order

Overpayment flagged for refund

All five earlier assessment fixes

Concurrent stock protection

The ResourceWarning messages also disappeared in the second run after adding tearDown().

The first run showed 14 tests because it appears to have run before the two additional tests were saved. The second run is the one we should use as our current verification result.

Step 6 — Check your Git changes before committing
Run these three commands from the tillpoint_assignment folder:

1. Check changed files

git status --short

2. Check for whitespace errors

git diff --check

3. Review the change summary

git diff --stat

Send me all three outputs.

Don't commit yet. I want to verify that only the intended files changed and then we'll test the existing-database migration before creating the Report 6 commit.

C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> git status --short
 M tests/test_orders.py
 M tillpoint/db.py
 M tillpoint/payments.py
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> git diff --check
warning: in the working copy of 'tests/test_orders.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tillpoint/db.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tillpoint/payments.py', LF will be replaced by CRLF the next time Git touches it
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> git diff --stat
warning: in the working copy of 'tests/test_orders.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tillpoint/db.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tillpoint/payments.py', LF will be replaced by CRLF the next time Git touches it
 tests/test_orders.py  | 114 ++++++++++++++++++++++++++++++++++++++++++++++++++
 tillpoint/db.py       |  25 ++++++++++-
 tillpoint/payments.py | 108 +++++++++++++++++++++++++++++++++--------------
 3 files changed, 214 insertions(+), 33 deletions(-)
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
…
Your Git review looks good. Exactly the three intended files are modified:

tests/test_orders.py

tillpoint/db.py

tillpoint/payments.py

git diff --check reported no whitespace errors. The LF/CRLF messages are Windows line-ending warnings, not failures.

Before committing, there's one important thing to verify: the database migration must also work when opening a database created before we added refund_required.

Step 7 — Verify the old-database migration
Copy this entire block into PowerShell from your project folder:

@'
import os
import sqlite3
import tempfile

from tillpoint import db

with tempfile.TemporaryDirectory() as folder:
    path = os.path.join(folder, "legacy.sqlite3")

    # Create a database using the old payments schema.
    old_conn = sqlite3.connect(path)
    old_conn.execute("""
        CREATE TABLE payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            event_id TEXT NOT NULL,
            amount_cents INTEGER NOT NULL,
            received_at TEXT NOT NULL
        )
    """)
    old_conn.close()

    # Opening it with the current code should upgrade the schema.
    conn = db.connect(path)

    columns = {
        row["name"]: row
        for row in conn.execute("PRAGMA table_info(payments)")
    }

    assert "refund_required" in columns
    assert columns["refund_required"]["dflt_value"] == "0"

    print("PASS: Existing database migration works.")
    print("PASS: refund_required defaults to 0.")

    conn.close()
'@ | python -

Expected Both PASS messages.

After that, run the full test suite one final time:

python -m unittest discover -s tests -v

Send me both outputs. If they pass, we'll stage and commit Report 6 separately with:

Handle duplicate successful payments and flag overpayments

Then we'll finish NOTES.md, session logs and the final submission ZIP.

PASS: Existing database migration works.
PASS: refund_required defaults to 0.
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment>
Migration verified
Excellent! The old database upgrades successfully, and existing payment records get refund_required = 0 by default. This means the new change won't incorrectly flag historical payments for refunds.

Step 8 — Run the complete test suite
Run:

python -m unittest discover -s tests -v

Paste the complete output here. We should see all 16 tests passing before committing Report 6.


Context window full
Start a new chat with an automatic summary of this conversation, or upgrade to continue here with more context available in every chat.

C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> python -m unittest discover -s tests -v
test_two_workers_cannot_oversell_stock (test_catalog_concurrency.CatalogConcurrencyTest.test_two_workers_cannot_oversell_stock) ... ok
test_cancel_paid_order_restocks (test_orders.OrderDeskTest.test_cancel_paid_order_restocks) ... ok
test_cancel_pending_order_restocks (test_orders.OrderDeskTest.test_cancel_pending_order_restocks) ... ok
test_coupon_discount_is_applied_before_tax (test_orders.OrderDeskTest.test_coupon_discount_is_applied_before_tax) ... ok
test_coupon_takes_ten_percent (test_orders.OrderDeskTest.test_coupon_takes_ten_percent) ... ok
test_daily_sales (test_orders.OrderDeskTest.test_daily_sales) ... ok
test_daily_sales_uses_india_local_date (test_orders.OrderDeskTest.test_daily_sales_uses_india_local_date) ... ok
test_duplicate_payment_webhook_is_not_counted_twice (test_orders.OrderDeskTest.test_duplicate_payment_webhook_is_not_counted_twice) ... ok
test_order_totals_with_tax (test_orders.OrderDeskTest.test_order_totals_with_tax) ... ok
test_out_of_stock (test_orders.OrderDeskTest.test_out_of_stock) ... ok
test_partial_payments_combine_to_pay_order (test_orders.OrderDeskTest.test_partial_payments_combine_to_pay_order) ... ok
test_payment_exceeding_order_total_is_flagged_for_refund (test_orders.OrderDeskTest.test_payment_exceeding_order_total_is_flagged_for_refund) ... ok
test_payment_marks_order_paid (test_orders.OrderDeskTest.test_payment_marks_order_paid) ... ok
test_price_change (test_orders.OrderDeskTest.test_price_change) ... ok
test_second_successful_payment_is_flagged_for_refund (test_orders.OrderDeskTest.test_second_successful_payment_is_flagged_for_refund) ... ok
test_stale_cache_refreshes_after_other_catalog_releases_stock (test_orders.OrderDeskTest.test_stale_cache_refreshes_after_other_catalog_releases_stock) ... ok

----------------------------------------------------------------------
Ran 16 tests in 0.115s

OK
PS C:\Users\kanda\OneDrive\Desktop\Deep Klarity-2\tillpoint_assignment> 

