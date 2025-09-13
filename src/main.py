from fastapi import FastAPI
from src.api.search import router as search_router

app = FastAPI(title="apicone", version="0.1.0")

app.include_router(search_router)

# Endpoint /health bajo el prefijo /api/v1
from fastapi import APIRouter
health_router = APIRouter(prefix="/api/v1", tags=["health"])

import time
start_time = time.time()


from src.api.search import INDEX_STATUS

@health_router.get("/health")
def health():
    uptime = int(time.time() - start_time)
    return {
        "status": "ok" if INDEX_STATUS == "ok" else "degraded",
        "uptime": uptime,
        "components": {
            "db": "ok",
            "pinecone": "ok",
            "index": INDEX_STATUS
        }
    }

app.include_router(health_router)
