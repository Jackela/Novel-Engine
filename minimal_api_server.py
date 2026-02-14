#!/usr/bin/env python3
"""Minimal FastAPI server used by integration tests."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Novel Engine Minimal API is running"}


@app.get("/health")
def health():
    gemini_key_set = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "gemini_key_set": gemini_key_set,
        "gemini_available": gemini_key_set,
    }


@app.get("/characters")
def characters():
    return {"characters": []}


@app.post("/test-gemini")
def test_gemini():
    gemini_key_set = bool(os.getenv("GEMINI_API_KEY"))
    if not gemini_key_set:
        return {"success": False, "error": "Gemini not configured"}
    return {"success": True, "response": "Gemini OK (mocked)"}


if __name__ == "__main__":
    uvicorn.run(
        "minimal_api_server:app", host="127.0.0.1", port=8003, log_level="error"
    )
