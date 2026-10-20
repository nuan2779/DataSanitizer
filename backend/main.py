
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers.upload import router as upload_router
from backend.routers.clean import router as clean_router
from backend.routers.download import router as download_router

# Initialize FastAPI
app = FastAPI(
    title="DataSanitizer API",
    description="Backend for data cleaning web application",
    version="1.0.0"
)

# Allowed frontend origins
origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500"
]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
)

# Register API routes
app.include_router(upload_router, prefix="/api")
app.include_router(clean_router, prefix="/api")
app.include_router(download_router, prefix="/api")

@app.get("/")
def home():
    return {
        "message": "DataSanitizer Backend is running"
    }
