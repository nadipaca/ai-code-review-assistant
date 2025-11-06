# app/main.py
from fastapi import FastAPI
from collections import defaultdict
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from fastapi import Request
from fastapi.responses import JSONResponse
import logging
import time

load_dotenv()  # Loads .env vars early so env vars (e.g. JWT_SECRET) are available to imported modules

from app.api import auth
from app.api import profile
from app.api import protected

app = FastAPI(title="AI Code Review API", description="Backend for code review assistant.")

RATE_LIMIT = 30  # requests per minute
user_requests = defaultdict(list)

# CORS - allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust for prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Example root endpoint
@app.get("/")
async def root():
    return {"message": "API running"}

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logging.info(f"Incoming: {request.method} {request.url}")
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logging.error(f"Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    user_ip = request.client.host
    now = time.time()
    # Keep only requests in last minute
    user_requests[user_ip] = [t for t in user_requests[user_ip] if now - t < 60]
    if len(user_requests[user_ip]) >= RATE_LIMIT:
        return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})
    user_requests[user_ip].append(now)
    return await call_next(request)

# Later, you'll include routers for auth, repos, reviews
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(protected.router)
