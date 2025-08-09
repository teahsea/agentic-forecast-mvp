import os
import json
import uuid
import hmac
import hashlib
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Simple in-memory store for demo (replace with DB in prod)
RUNS: Dict[str, Dict[str, Any]] = {}

N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")  # e.g. https://n8n.example.com/webhook/forecast
N8N_SHARED_SECRET = os.getenv("N8N_SHARED_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")  # public URL of this FastAPI

app = FastAPI(title="Agentic Forecast MVP")

# Allow calls from Streamlit (default localhost:8501)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # simplify for MVP; tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def sign_hmac(body: bytes) -> str:
    if not N8N_SHARED_SECRET:
        return ""
    return "sha256=" + hmac.new(N8N_SHARED_SECRET.encode(), body, hashlib.sha256).hexdigest()

class StartRunRequest(BaseModel):
    user_id: str = "demo-user"
    symbols: List[str] = []
    horizon_days: int = 5
    prompt: Optional[str] = None
    doc_name: Optional[str] = None
    doc_text: Optional[str] = None  # plain text extracted from PDF/TXT
    task: Optional[str] = "auto"    # "auto" | "qa" | "strategy"
    notes: Optional[str] = None

class RunStatus(BaseModel):
    run_id: str
    status: str
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@app.get("/health")
def health():
    return {"ok": True}