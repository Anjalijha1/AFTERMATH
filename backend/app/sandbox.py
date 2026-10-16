"""Synthetic support sandbox backed by a real SQLite database (design doc: fake
customer and refund tables). One private in-memory database per run, so runs can
never share a balance and nothing touches a file, network or real payment system.
"""
import sqlite3

CUSTOMER_ID = 'CUST-001'
SEED_EMAIL = 'customer@example.invalid'
SEED_REFUND_LIMIT_MINOR = 100_000  # INR 1000, in paise


class Sandbox:
    def __init__(self, refund_limit_minor: int = SEED_REFUND_LIMIT_MINOR):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE customers (id TEXT PRIMARY KEY, email TEXT NOT NULL,
                                    refund_limit_minor INTEGER NOT NULL);
            CREATE TABLE refunds (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                  customer_id TEXT NOT NULL REFERENCES customers(id),
                                  amount_minor INTEGER NOT NULL CHECK(amount_minor > 0));
        ''')
        self.db.execute('INSERT INTO customers VALUES (?,?,?)', (CUSTOMER_ID, SEED_EMAIL, refund_limit_minor))
        self.db.commit()

    def snapshot(self) -> dict:
        """Read the state straight from the tables (never from runner-held variables)."""
        c = self.db.execute('SELECT * FROM customers WHERE id=?', (CUSTOMER_ID,)).fetchone()
        total, count = self.db.execute(
            'SELECT COALESCE(SUM(amount_minor),0), COUNT(*) FROM refunds WHERE customer_id=?',
            (CUSTOMER_ID,)).fetchone()
        return {'customer_id': c['id'], 'email': c['email'], 'refunded_minor': total,
                'refund_limit_minor': c['refund_limit_minor'], 'refund_count': count}

    # Mutation tools. The caller must only reach these after an allowed policy decision.
    def issue_refund(self, amount_minor: int) -> int:
        cur = self.db.execute('INSERT INTO refunds(customer_id, amount_minor) VALUES (?,?)',
                              (CUSTOMER_ID, amount_minor))
        self.db.commit()
        return cur.lastrowid

    def change_account_email(self, email: str) -> None:
        self.db.execute('UPDATE customers SET email=? WHERE id=?', (email, CUSTOMER_ID))
        self.db.commit()

    def close(self):
        self.db.close()
