
import os
import tempfile
import threading
import unittest

from tillpoint import db
from tillpoint.catalog import Catalog, OutOfStock


class SynchronizedCatalog(Catalog):
    """Make two workers read stock before either worker reserves it."""

    def __init__(self, conn, barrier):
        super().__init__(conn)
        self.barrier = barrier

    def get_product(self, sku):
        product = super().get_product(sku)
        self.barrier.wait(timeout=5)
        return product


class CatalogConcurrencyTest(unittest.TestCase):

    def test_two_workers_cannot_oversell_stock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = os.path.join(temp_dir, "test.sqlite3")

            setup_conn = db.connect(database_path)
            setup_catalog = Catalog(setup_conn)
            setup_catalog.add_product(
                "MUG", "Mug", 1200, stock=5
            )
            setup_conn.close()

            barrier = threading.Barrier(2)
            results = []
            errors = []

            def worker():
                conn = db.connect(database_path)
                try:
                    catalog = SynchronizedCatalog(conn, barrier)
                    catalog.reserve("MUG", 4)
                    results.append("success")
                except Exception as error:
                    errors.append(error)
                finally:
                    conn.close()

            threads = [
                threading.Thread(target=worker),
                threading.Thread(target=worker),
            ]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join(timeout=10)

            self.assertTrue(
                all(not thread.is_alive() for thread in threads),
                "Worker threads did not finish"
            )

            check_conn = db.connect(database_path)
            try:
                remaining_stock = check_conn.execute(
                    "SELECT stock FROM products WHERE sku = 'MUG'"
                ).fetchone()["stock"]
            finally:
                check_conn.close()

            self.assertEqual(len(results), 1)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], OutOfStock)
            self.assertEqual(remaining_stock, 1)


if __name__ == "__main__":
    unittest.main()
