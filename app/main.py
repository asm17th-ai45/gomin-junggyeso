from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.core.config import CORS_ORIGINS

app = FastAPI(title="Gomin Junggyeso API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1", tags=["chat"])


@app.get("/health")
def health():
    return {"status": "healthy", "service": "gomin-junggyeso-api"}
