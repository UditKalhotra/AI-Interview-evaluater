"""
Module 1 — Project Scaffolding & Shared Data Layer.

Boots FastAPI, connects to local MongoDB via Motor on startup, and exposes
/health so the frontend (and you) can confirm the backend is up and whether
the database connection succeeded. No business logic yet.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import connect_to_mongo, close_mongo_connection, ping_database, MONGO_DB_NAME
from app.routers import questions, interview


@asynccontextmanager
async def lifespan(app: FastAPI):
    connect_to_mongo()
    yield
    close_mongo_connection()


app = FastAPI(title="Voice Interview System API", lifespan=lifespan)

# Allow the local Next.js dev server to call the API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(questions.router)
app.include_router(interview.router)


@app.get("/health")
async def health():
    db_connected = await ping_database()
    return {
        "status": "ok",
        "database": {
            "connected": db_connected,
            "name": MONGO_DB_NAME,
        },
    }