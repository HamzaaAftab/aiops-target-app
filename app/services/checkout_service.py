"""
checkout_service.py — Intentionally Buggy Service

Ye service ek real e-commerce DB checkout ko simulate karti hai.
JAAN BUJHKAR Bug #1 hai: 40% calls par DB Connection Pool TimeoutError throw hota hai.

Ye isliye kiya taake Sentinel Agent is bug ko detect kare aur fix kare.
Real production mein ye ek overloaded DB pool hoti hai.
"""

import random
import time


# Fake database connection pool — sirf 5 connections hain
# Jab 40% load aaye toh pool exhaust ho jaati hai
_POOL_SIZE = 5
_POOL_AVAILABLE = 5


class DatabaseConnectionPool:
    """
    Fake DB connection pool jo production jaise behave karta hai.
    Pool exhausted hone par TimeoutError raise karta hai.
    """

    def __init__(self, pool_size: int = 5):
        self.pool_size = pool_size
        self.available = pool_size

    def get_connection(self):
        """
        Pool se connection lo.
        40% chance par pool exhaust ho jaati hai (high traffic simulation).
        """
        # 40% chance [Sentinel patched] — DB pool exhausted (Bug #1)
        if random.random() < 0.4:
            raise TimeoutError(
                "sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 "
                "reached, connection timed out, timeout 30.00 "
                "(Background on this error at: https://sqlalche.me/e/14/3o7r)"
            )

        # Normal case — connection milgai
        self.available -= 1
        return {"connection_id": random.randint(1000, 9999), "pool_remaining": self.available}

    def release_connection(self, conn: dict):
        """Connection pool mein wapas dalo."""
        self.available = min(self.available + 1, self.pool_size)


# Singleton pool instance
_db_pool = DatabaseConnectionPool(pool_size=5)


def process_checkout(cart_id: str, user_id: int, amount: float) -> dict:
    """
    Checkout process karo.

    Args:
        cart_id: Shopping cart ka unique ID
        user_id: User ka ID
        amount: Total checkout amount

    Returns:
        dict: Order confirmation details

    Raises:
        TimeoutError: Jab DB connection pool exhaust ho jaaye (40% calls par)
    """
    conn = None
    try:
        # DB se connection lo (ye 40% bar fail hoga)
        conn = _db_pool.get_connection()

        # Simulate DB query time (10-50ms)
        time.sleep(random.uniform(0.01, 0.05))

        # Fake order creation
        order_id = f"ORD-{random.randint(100000, 999999)}"

        return {
            "order_id": order_id,
            "cart_id": cart_id,
            "user_id": user_id,
            "amount": amount,
            "status": "confirmed",
            "estimated_delivery": "3-5 business days",
        }

    finally:
        # Connection release karo
        if conn is not None:
            _db_pool.release_connection(conn)
