import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# --- 1. LOAD ENV VARIABLES FIRST ---
load_dotenv()

# --- 2. LOCAL IMPORTS ---
from backend.database import engine
from backend.models import schema
from backend.routes import auth, users, activities, planning, metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables if they don't exist
schema.Base.metadata.create_all(bind=engine)

# --- 3. INITIALIZE APP ---
app = FastAPI(title="Tri-Coach AI API")

# --- 4. INCLUDE ROUTERS ---
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(activities.router)
app.include_router(planning.router)
app.include_router(metrics.router)

# --- 5. STATIC FILES & HEALTH CHECK ---
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/api/health")
def read_health():
    return {"status": "ok", "message": "FastAPI server is running"}

@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")