"""
run.py — Target App Runner

Command: python run.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,          # Port 8001 — Sentinel 8000 par hoga
        reload=True,        # Dev mode: code change par auto-restart
        log_level="info",
    )
