"""
main.py — Target App (Intentionally Buggy FastAPI Application)

Bugs:
  Bug #1 → GET /api/checkout  → 40% calls par DB TimeoutError
  Bug #2 → GET /api/users/2   → Even user IDs par AttributeError (NoneType)

Healthy endpoints (no bugs):
  GET /health         → Always OK
  GET /api/inventory  → Normal response
"""

import logging
import os
import random
import time
import traceback

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# Azure Monitor import — poori app instrument ho jaayegi
from azure.monitor.opentelemetry import configure_azure_monitor

from app.services.checkout_service import process_checkout

# ─── Environment Variables Load Karo ─────────────────────────────────────────
load_dotenv()

APPINSIGHTS_CS = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "") # Checks for Application Insights String
APP_ENV = os.getenv("ENVIRONMENT", "development")

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger("target-app")

# ─── Azure Monitor Setup ──────────────────────────────────────────────────────
# Ye ek line poori FastAPI app ko instrument kar deti hai!
# Har request, har error, har exception automatically Azure mein jaayegi.
if APPINSIGHTS_CS: # If String exists
    configure_azure_monitor(connection_string=APPINSIGHTS_CS) # Configure Azure Monitor
    logger.info("[SUCCESS] Azure Monitor configured - App Insights active")
else:
    logger.warning("[WARNING] APPLICATIONINSIGHTS_CONNECTION_STRING not set - running without monitoring")

# ─── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Target E-Commerce API",
    description="Intentionally buggy app for AIOps Sentinel demo",
    version="1.0.0",
)

# ─── Fake Data ────────────────────────────────────────────────────────────────
# Bug #2: Sirf odd user IDs hain — even ID maango toh None milega → AttributeError
USERS_DB = {
    1: {"id": 1, "name": "Ali Hassan", "email": "ali@example.com", "tier": "gold"},
    3: {"id": 3, "name": "Sara Khan",  "email": "sara@example.com", "tier": "silver"},
    5: {"id": 5, "name": "Umar Ahmed", "email": "umar@example.com", "tier": "bronze"},
    7: {"id": 7, "name": "Fatima Malik","email": "fatima@example.com","tier": "gold"},
}

INVENTORY_DB = [
    {"sku": "LAPTOP-001", "name": "ProBook Laptop",    "stock": 45,  "price": 899.99},
    {"sku": "PHONE-002",  "name": "SmartPhone X",      "stock": 120, "price": 399.99},
    {"sku": "TABLET-003", "name": "TabPro 11",         "stock": 30,  "price": 549.99},
    {"sku": "WATCH-004",  "name": "SmartWatch Series 3","stock": 75, "price": 199.99},
]


# ─── Global Exception Handler ─────────────────────────────────────────────────
@app.exception_handler(Exception) # Global Exception
async def global_exception_handler(request: Request, exc: Exception): # Request Parameter and Exception Parameter
    """
    Saari unhandled exceptions yahan aati hain.
    Error log hoga aur Azure Monitor mein track hoga.
    """
    error_type = type(exc).__name__
    error_msg = str(exc)

    logger.error(
        f"[ERROR] Unhandled Exception | {error_type} | {request.url.path} | {error_msg}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": error_type,
            "message": error_msg,
            "path": str(request.url.path),
            "status": "error",
        },
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint — hamesha OK return karta hai.
    Sentinel isko ping karke check karta hai ke app zinda hai.
    """
    return {
        "status": "ok",
        "service": "target-app",
        "version": "1.0.0",
        "environment": APP_ENV,
    }


@app.get("/api/checkout", tags=["E-Commerce"])
async def checkout(
    cart_id: str = "cart-default",
    user_id: int = 1,
    amount: float = 99.99,
):
    """
    Checkout API — BUG #1 YEH HAI!

    40% calls par DB Connection Pool TimeoutError throw karta hai.
    Ye simulate karta hai ke production mein DB pool exhaust ho gayi.

    Sentinel is error ko detect karega aur automatically fix karega.
    """
    logger.info(f"[INFO] Checkout request | cart={cart_id} | user={user_id} | amount=${amount}")

    try:
        # checkout_service.py mein 40% chance par TimeoutError raise hogi
        result = process_checkout(
            cart_id=cart_id,
            user_id=user_id,
            amount=amount,
        )
        logger.info(f"[SUCCESS] Checkout success | order={result['order_id']}")
        return result

    except TimeoutError as e:
        # Ye error App Insights mein jaayegi!
        logger.error(f"[ERROR] DB Timeout on checkout | cart={cart_id} | Error: {e}")
        raise  # Global handler pakad lega


@app.get("/api/users/{user_id}", tags=["Users"])
async def get_user(user_id: int):
    """
    User fetch karo — BUG #2 YEH HAI!

    USERS_DB mein sirf odd IDs hain (1, 3, 5, 7).
    Even ID (2, 4, 6..) maango → None milega → .get() nahi, direct access → AttributeError!

    Ye simulate karta hai ke code mein None check nahi tha.
    """
    logger.info(f"[INFO] User request | user_id={user_id}")

    # Bug #2: dict.get() nahi — direct index access
    # Jab ID exist na kare toh KeyError aata hai
    # Phir "name" access karne se AttributeError
    user = USERS_DB.get(user_id)  # None milega even IDs par

    # ← BUG: None check nahi kiya! user.get() → AttributeError: 'NoneType'
    user_name = user["name"]  # type: ignore  # Even ID par crash!

    logger.info(f"[SUCCESS] User found | name={user_name}")
    return user


@app.get("/api/inventory", tags=["Inventory"])
async def get_inventory():
    """
    Inventory list — KOI BUG NAHI.
    Ye healthy baseline endpoint hai.
    Sentinel isse dekhega ke app completely broken nahi hai.
    """
    logger.info(f"[INFO] Inventory request | items={len(INVENTORY_DB)}")

    # Small delay simulate karo (DB query)
    time.sleep(random.uniform(0.005, 0.020))

    return {
        "status": "ok",
        "total_items": len(INVENTORY_DB),
        "inventory": INVENTORY_DB,
    }


# ─── Startup / Shutdown Events ────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("[START] Target App starting up...")
    logger.info(f"   Environment  : {APP_ENV}")
    logger.info(f"   App Insights : {'[ACTIVE]' if APPINSIGHTS_CS else '[NOT CONFIGURED]'}")
    logger.info("   Routes:")
    logger.info("     GET /health           -> Always OK")
    logger.info("     GET /api/checkout     -> Bug #1: 40% TimeoutError")
    logger.info("     GET /api/users/{id}   -> Bug #2: Even IDs -> AttributeError")
    logger.info("     GET /api/inventory    -> Always OK (healthy baseline)")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("[STOP] Target App shutting down...")
