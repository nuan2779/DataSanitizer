from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.profile import router as profile_router
from backend.routers.upload import router as upload_router
from backend.routers.clean import router as clean_router
from backend.routers.download import router as download_router
from backend.routers.samples import router as samples_router
from backend.routers.benchmark import router as benchmark_router
from backend.routers.auth import router as auth_router
from backend.routers.recipes import router as recipes_router
from backend.routers.history import router as history_router
from backend.database import init_db

# Initialize FastAPI
app = FastAPI(
    title="DataSanitizer API",
    description="Backend for data cleaning web application",
    version="2.0.0"
)

# Initialize database tables on startup
@app.on_event("startup")
def on_startup():
    init_db()

# Allowed frontend origins
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:8000",
    "http://localhost:8000"
]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Register API routes
app.include_router(upload_router, prefix="/api")
app.include_router(clean_router, prefix="/api")
app.include_router(download_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(samples_router, prefix="/api")
app.include_router(benchmark_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(recipes_router, prefix="/api")
app.include_router(history_router, prefix="/api")

@app.get("/")
def home():
    return {
        "message": "DataSanitizer Backend is running",
        "version": "2.0.0"
    }
