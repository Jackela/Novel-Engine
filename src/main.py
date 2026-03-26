"""
Novel Engine - Clean Architecture Application Entry Point
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.apps.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
